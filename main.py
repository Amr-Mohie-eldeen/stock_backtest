import backtrader as bt
import yfinance as yf
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import os
import logging
from matplotlib.widgets import SpanSelector
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, List, Tuple, Optional

# -----------------------------
# Set Matplotlib Aesthetics
# -----------------------------
plt.style.use("seaborn-v0_8-darkgrid")  # Adjust if necessary


# -----------------------------
# Define the Strategy
# -----------------------------
class TradeLogger(Protocol):
    def log_trade(self, message: str, dt: Optional[datetime.date] = None) -> None:
        pass

    def log_summary(self, summary: str) -> None:
        pass


class TradeTracker(Protocol):
    def add_trade(self, action: str, price: float, date: datetime.date) -> None:
        pass

    def add_signal(self, signal_type: str, date: datetime.date, price: float) -> None:
        pass

    @property
    def trade_count(self) -> int:
        pass


@dataclass
class Trade:
    action: str
    price: float
    date: datetime.date
    size: int
    value: float
    commission: float


# Concrete implementations
class FileTradeLogger:
    def __init__(self, filename: str = "trading.log", debug: bool = False):
        if os.path.exists(filename):
            os.remove(filename)
        self.logger = logging.getLogger("TradingLog")
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        fh = logging.FileHandler(filename)
        fh.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        self.logger.addHandler(fh)
        self.logger.info("=== New Trading Session Started ===")

    def log_trade(self, message: str, dt: Optional[datetime.date] = None) -> None:
        if dt:
            message = f"{dt.isoformat()} {message}"
        self.logger.info(message)

    def log_summary(self, summary: str) -> None:
        self.logger.info(summary)


class DefaultTradeTracker:
    def __init__(self):
        self._trade_count: int = 0
        self.trades: List[Tuple[str, float, datetime.date]] = []
        self.buy_signals: List[Tuple[datetime.date, float]] = []
        self.sell_signals: List[Tuple[datetime.date, float]] = []

    def add_trade(self, action: str, price: float, date: datetime.date) -> None:
        self.trades.append((action, price, date))
        if action == "BUY":
            self._trade_count += 1

    def add_signal(self, signal_type: str, date: datetime.date, price: float) -> None:
        if signal_type == "BUY":
            self.buy_signals.append((date, price))
        elif signal_type == "SELL":
            self.sell_signals.append((date, price))

    @property
    def trade_count(self) -> int:
        return self._trade_count


class BaseStrategy(bt.Strategy):
    """Base strategy class that handles infrastructure"""

    def __init__(self, logger: TradeLogger, tracker: TradeTracker):
        super().__init__()
        self.logger = logger
        self.tracker = tracker
        self.order = None
        self.buy_price = None
        self.stop_price = None
        self.val_start = self.broker.get_cash()

        # Initialize strategy-specific components
        self.init_strategy()

    def init_strategy(self):
        """Override this method to initialize strategy-specific indicators"""
        pass

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.logger.log_trade(
                    f"BUY EXECUTED - Price: {order.executed.price:.2f}, "
                    f"Size: {order.executed.size:.0f} shares, "
                    f"Cost: {order.executed.value:.2f}, "
                    f"Comm: {order.executed.comm:.2f}"
                )
            elif order.issell():
                self.logger.log_trade(
                    f"SELL EXECUTED - Price: {order.executed.price:.2f}, "
                    f"Size: {abs(order.executed.size):.0f} shares, "
                    f"Cost: {order.executed.value:.2f}, "
                    f"Comm: {order.executed.comm:.2f}"
                )

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.logger.log_trade(f"Order Failed with Status: {order.getstatusname()}")

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.logger.log_trade(
            f"""
        TRADE COMPLETED:
        Gross Profit: {trade.pnl:.2f}
        Net Profit: {trade.pnlcomm:.2f}
        Commission: {trade.commission:.2f}
        """
        )

    def stop(self):
        """Log final strategy statistics"""
        summary = f"""
        === Strategy Summary ===
        Starting Value: ${self.val_start:,.2f}
        Final Value: ${self.broker.get_cash():,.2f}
        Total Return: {((self.broker.get_cash() - self.val_start) / self.val_start) * 100:.2f}%
        Total Completed Trades: {self.tracker.trade_count}
        """
        self.logger.log_summary(summary)


class EnhancedStrategy(BaseStrategy):
    """Your actual trading strategy"""

    params = (
        ("sma_fast", 20),
        ("sma_slow", 50),
        ("atr_period", 14),
        ("risk_pct", 0.02),
        ("trail_percent", 0.02),
        ("debug", False),
    )

    def init_strategy(self):
        # Core indicators
        self.sma_fast = bt.indicators.SMA(period=self.p.sma_fast)
        self.sma_slow = bt.indicators.SMA(period=self.p.sma_slow)
        self.atr = bt.indicators.ATR(period=self.p.atr_period)
        self.macd = bt.indicators.MACD()
        self.rsi = bt.indicators.RSI()
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)

    def next(self):
        if self.order:
            return

        # Only trade if we have all indicators warmed up
        if not all(
            [
                self.sma_fast[0],
                self.sma_slow[0],
                self.atr[0],
                self.macd.macd[0],
                self.rsi[0],
            ]
        ):
            return

        # Position sizing based on ATR
        risk_amount = self.broker.get_value() * self.p.risk_pct
        atr_stops = 2
        price = self.data.close[0]
        stop_price = price - (self.atr[0] * atr_stops)
        position_size = int((risk_amount / (price - stop_price)))

        # Entry conditions for long positions
        if not self.position:
            trend_up = self.sma_fast[0] > self.sma_slow[0]
            momentum_up = self.macd.macd[0] > self.macd.signal[0]
            rsi_oversold = self.rsi[0] < 40
            price_above_sma = price > self.sma_slow[0]

            if (
                trend_up
                and momentum_up
                and (rsi_oversold or price_above_sma)
                and self.crossover > 0
            ):

                self.buy_price = price
                self.stop_price = stop_price
                self.order = self.buy(size=position_size)
                self.tracker.add_trade("BUY", price, self.data.datetime.date(0))
                self.tracker.add_signal("BUY", self.data.datetime.date(0), price)
                self.logger.log_trade(
                    f"BUY CREATE at {price:.2f}, Size: {position_size} shares (Trade #{self.tracker.trade_count})"
                )

        # Exit conditions
        else:
            if self.stop_price is None:
                self.stop_price = price - (self.atr[0] * atr_stops)
            else:
                self.stop_price = max(
                    self.stop_price, price * (1 - self.p.trail_percent)
                )

            trend_down = self.sma_fast[0] < self.sma_slow[0]
            momentum_down = self.macd.macd[0] < self.macd.signal[0]
            stop_hit = price < self.stop_price
            rsi_overbought = self.rsi[0] > 70

            if stop_hit or (trend_down and momentum_down) or rsi_overbought:
                self.order = self.sell(size=self.position.size)
                self.tracker.add_trade("SELL", price, self.data.datetime.date(0))
                self.tracker.add_signal("SELL", self.data.datetime.date(0), price)
                self.logger.log_trade(
                    f"SELL CREATE at {price:.2f}, Size: {self.position.size} shares (Trade #{self.tracker.trade_count})"
                )
                self.stop_price = None


# -----------------------------
# Data Acquisition using yfinance
# -----------------------------
ticker = "AAPL"
start_date = "2019-01-01"
end_date = "2023-01-01"
data_df = yf.download(ticker, start=start_date, end=end_date)

# Flatten MultiIndex columns (if needed) and lowercase them
if isinstance(data_df.columns, pd.MultiIndex):
    data_df.columns = data_df.columns.get_level_values(0)
data_df.columns = [col.lower() for col in data_df.columns]

# -----------------------------
# Set Up Cerebro Engine
# -----------------------------
cerebro = bt.Cerebro()

# Create dependencies
logger = FileTradeLogger(debug=False)
tracker = DefaultTradeTracker()

# Add strategy with injected dependencies
cerebro.addstrategy(EnhancedStrategy, logger=logger, tracker=tracker)

data = bt.feeds.PandasData(dataname=data_df)
cerebro.adddata(data)

# Broker settings
cerebro.broker.setcash(100000.0)
cerebro.broker.setcommission(commission=0.001)

# (Optional) Add analyzers for performance tracking
cerebro.addanalyzer(bt.analyzers.Returns)
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer)

# Run the backtest
starting_value = cerebro.broker.getvalue()
print(f"Starting Portfolio Value: {format(starting_value, ',.2f')}")

results = cerebro.run()
strat = results[0]

final_value = cerebro.broker.getvalue()
print(f"Final Portfolio Value: {format(final_value, ',.2f')}")
print("\nDetailed Performance Analysis:")
print(f"Total Return: {((final_value - starting_value) / starting_value) * 100:.2f}%")
print(f"Total Completed Trades: {strat.tracker.trade_count}")
# -----------------------------
# Plotting Performance with Trade Markers and Buy & Hold Returns
# -----------------------------
import matplotlib.dates as mdates

# Create a figure with two subplots sharing the same x-axis
fig, (ax1, ax2) = plt.subplots(
    2, 1, figsize=(14, 10), sharex=True, constrained_layout=True
)

# Remove the experimental toolbar setting
# plt.rcParams["toolbar"] = "toolmanager"  # Remove this line
fig.canvas.toolbar_visible = True
fig.canvas.header_visible = False

# --- Subplot 1: Price Chart with Trade Markers ---
ax1.plot(data_df.index, data_df["close"], label="Close Price", color="blue", alpha=0.5)

# Plot buy signals
if tracker.buy_signals:  # Use tracker instead of strat
    buy_dates = [pd.Timestamp(d) for d, _ in tracker.buy_signals]
    buy_prices = [price for _, price in tracker.buy_signals]
    ax1.scatter(
        buy_dates,
        buy_prices,
        marker="^",
        color="green",
        s=100,
        label="Buy Signal",
        zorder=5,
    )

# Plot sell signals
if tracker.sell_signals:  # Use tracker instead of strat
    sell_dates = [pd.Timestamp(d) for d, _ in tracker.sell_signals]
    sell_prices = [price for _, price in tracker.sell_signals]
    ax1.scatter(
        sell_dates,
        sell_prices,
        marker="v",
        color="red",
        s=100,
        label="Sell Signal",
        zorder=5,
    )

ax1.set_title("Price Chart with Trade Signals", fontsize=16)
ax1.set_ylabel("Price ($)", fontsize=14)
ax1.legend(fontsize=12)
ax1.grid(True)

# --- Subplot 2: Cumulative Returns Comparison ---
strategy_values = (
    pd.Series(
        [starting_value, final_value], index=[data_df.index[0], data_df.index[-1]]
    )
    .reindex(data_df.index)
    .interpolate(method="linear")
)

ax2.plot(strategy_values, label="Strategy Equity", linewidth=2, color="purple")

market_values = (1 + data_df["close"].pct_change()).cumprod() * starting_value
ax2.plot(market_values, label="Buy & Hold Equity", linewidth=2, color="orange")

ax2.set_title("Cumulative Returns Comparison", fontsize=16)
ax2.set_xlabel("Date", fontsize=14)
ax2.set_ylabel("Equity ($)", fontsize=14)
ax2.legend(fontsize=12)
ax2.grid(True)
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${format(int(x), ",")}'))

# Improve date formatting
ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
plt.xticks(rotation=45)


# Enable zoom functionality
def on_select(xmin, xmax):
    ax1.set_xlim(xmin, xmax)
    ax2.set_xlim(xmin, xmax)
    fig.canvas.draw()


# Add span selector to both plots
span1 = SpanSelector(
    ax1,
    on_select,
    "horizontal",
    useblit=True,
    props=dict(alpha=0.3, facecolor="tab:blue"),
    interactive=True,
    drag_from_anywhere=True,
)

span2 = SpanSelector(
    ax2,
    on_select,
    "horizontal",
    useblit=True,
    props=dict(alpha=0.3, facecolor="tab:blue"),
    interactive=True,
    drag_from_anywhere=True,
)


# Add reset zoom button
def reset_zoom(event):
    ax1.set_xlim(data_df.index[0], data_df.index[-1])
    ax2.set_xlim(data_df.index[0], data_df.index[-1])
    fig.canvas.draw()


# Add reset button
reset_ax = plt.axes([0.8, 0.025, 0.1, 0.04])
reset_button = plt.Button(reset_ax, "Reset Zoom")
reset_button.on_clicked(reset_zoom)

plt.show()
