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
        self.logger.propagate = False
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        fh = logging.FileHandler(filename)
        fh.setLevel(logging.DEBUG if debug else logging.INFO)
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
        self._current_trade = False  # Track if we're in a trade

    def add_trade(self, action: str, price: float, date: datetime.date) -> None:
        self.trades.append((action, price, date))
        if action == "BUY":
            self._current_trade = True
        elif action == "SELL" and self._current_trade:
            self._trade_count += 1  # Increment counter when a trade is completed
            self._current_trade = False

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
                self.tracker.add_trade(
                    "BUY", order.executed.price, self.data.datetime.date(0)
                )
                self.tracker.add_signal(
                    "BUY", self.data.datetime.date(0), order.executed.price
                )
            elif order.issell():
                self.logger.log_trade(
                    f"SELL EXECUTED - Price: {order.executed.price:.2f}, "
                    f"Size: {abs(order.executed.size):.0f} shares, "
                    f"Cost: {order.executed.value:.2f}, "
                    f"Comm: {order.executed.comm:.2f}"
                )
                self.tracker.add_trade(
                    "SELL", order.executed.price, self.data.datetime.date(0)
                )
                self.tracker.add_signal(
                    "SELL", self.data.datetime.date(0), order.executed.price
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
    """
    An enhanced strategy designed to beat buy-and-hold by combining:
      - Dual SMA trend confirmation with a minimum spread requirement
      - MACD and RSI momentum confirmation
      - A Stochastic oversold filter
      - ATR-based position sizing
      - A dynamic trailing stop and profit target exit
    """

    params = (
        ("sma_fast", 20),
        ("sma_slow", 50),
        ("atr_period", 14),
        ("risk_pct", 0.02),
        ("trail_percent", 0.02),
        ("profit_target", 2.0),  # 2x risk as profit target
        ("debug", True),
    )

    def init_strategy(self):
        # Core indicators
        self.sma_fast = bt.indicators.SMA(period=self.p.sma_fast)
        self.sma_slow = bt.indicators.SMA(period=self.p.sma_slow)
        self.atr = bt.indicators.ATR(period=self.p.atr_period)
        self.macd = bt.indicators.MACD()  # default periods (12,26,9)
        self.rsi = bt.indicators.RSI()
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)
        # Additional momentum filter
        self.stoch = bt.indicators.Stochastic()  # default parameters

    def next(self):
        # Do not issue a new order if one is already pending.
        if self.order:
            return

        # Ensure indicators are warmed up.
        if not all(
            [
                self.sma_fast[0],
                self.sma_slow[0],
                self.atr[0],
                self.macd.macd[0],
                self.rsi[0],
                self.stoch.percD[0],
            ]
        ):
            return

        price = self.data.close[0]

        # Log current indicator values if debugging is enabled.
        if self.p.debug:
            self.logger.log_trade(
                f"DEBUG: Price: {price:.2f}, SMA_fast: {self.sma_fast[0]:.2f}, "
                f"SMA_slow: {self.sma_slow[0]:.2f}, RSI: {self.rsi[0]:.2f}, "
                f"MACD: {self.macd.macd[0]:.2f}, MACD_signal: {self.macd.signal[0]:.2f}, "
                f"Stoch %D: {self.stoch.percD[0]:.2f}, Crossover: {self.crossover[0]}"
            )

        # Position sizing based on ATR.
        risk_amount = self.broker.get_value() * self.p.risk_pct
        atr_multiplier = 2
        stop_price = price - (self.atr[0] * atr_multiplier)
        risk_per_share = price - stop_price
        if risk_per_share <= 0:
            return
        position_size = int(risk_amount / risk_per_share)

        # --------------------------
        # ENTRY CONDITIONS (Long Only)
        # --------------------------
        if not self.position:
            # Check trend and momentum conditions.
            trend_up = (
                self.sma_fast[0] > self.sma_slow[0]
                and (self.sma_fast[0] - self.sma_slow[0]) / self.sma_slow[0] > 0.005
            )  # relaxed spread: 0.5%
            momentum_up = self.macd.macd[0] > self.macd.signal[0]
            rsi_condition = (
                self.rsi[0] < 45
            )  # relaxed threshold from 40 to 45 for more signals
            price_above_sma = price > self.sma_slow[0]
            stoch_oversold = self.stoch.percD[0] < 25  # relaxed from 20 to 25
            positive_crossover = self.crossover[0] > 0

            # For testing, we require most (but not all) conditions.
            if (
                trend_up
                and momentum_up
                and (rsi_condition or price_above_sma)
                and positive_crossover
                and stoch_oversold
            ):
                self.buy_price = price
                self.stop_price = stop_price  # initial stop loss based on ATR
                self.order = self.buy(size=position_size)
                if self.p.debug:
                    self.logger.log_trade(
                        f"BUY CREATE at {price:.2f}, Size: {position_size} shares"
                    )

        # --------------------------
        # EXIT CONDITIONS
        # --------------------------
        else:
            # Update trailing stop: never lower the stop.
            if self.stop_price is None:
                self.stop_price = price - (self.atr[0] * atr_multiplier)
            else:
                self.stop_price = max(
                    self.stop_price, price * (1 - self.p.trail_percent)
                )

            # Set a profit target.
            target_price = self.buy_price + self.p.profit_target * (
                self.buy_price - self.stop_price
            )

            trend_down = self.sma_fast[0] < self.sma_slow[0]
            momentum_down = self.macd.macd[0] < self.macd.signal[0]
            stop_hit = price < self.stop_price
            profit_target_hit = price >= target_price
            rsi_overbought = self.rsi[0] > 70

            # Exit if any of the following triggers:
            if (
                stop_hit
                or profit_target_hit
                or (trend_down and momentum_down)
                or rsi_overbought
            ):
                self.order = self.sell(size=self.position.size)
                if self.p.debug:
                    self.logger.log_trade(
                        f"SELL CREATE at {price:.2f}, Size: {self.position.size} shares"
                    )
                self.stop_price = None


class ImprovedStrategy(BaseStrategy):
    """
    Improved Strategy: Trade pullbacks in an established uptrend.

    Entry:
      - Confirm uptrend: Price is above a 50‑period SMA.
      - Look for a pullback: RSI falls below a threshold (e.g. 65)
        and Stochastic %D falls below a threshold (e.g. 60).
      - Momentum filter: MACD line is above its signal line.

    Position sizing:
      - Use ATR (14‑period) to set a stop loss of 2×ATR.
      - Position size is chosen so that the total risk per trade
        (stop distance × number of shares) equals a fixed percentage
        (e.g. 2%) of the account value.

    Exit:
      - Exit if price falls below a trailing stop (updated each bar),
      - Or if price reaches a profit target (set at 3× the risk per share),
      - Or if the RSI rises above an exit threshold (e.g. 75).
    """

    params = (
        ("sma_period", 50),
        ("atr_period", 14),
        ("risk_pct", 0.02),
        ("trail_percent", 0.02),  # trailing stop percent (could be tuned)
        ("profit_target", 3.0),  # profit target: 3× risk per share
        ("rsi_entry", 65),  # entry: RSI below 65 (instead of 50)
        ("rsi_exit", 75),  # exit: RSI above 75 (instead of 70)
        ("stoch_threshold", 60),  # entry: Stochastic %D below 60 (instead of 50)
        ("debug", True),
    )

    def init_strategy(self):
        # Trend indicator: 50‑period SMA
        self.sma = bt.indicators.SMA(period=self.p.sma_period)
        # Volatility indicator: ATR for risk calculation
        self.atr = bt.indicators.ATR(period=self.p.atr_period)
        # Momentum indicators
        self.rsi = bt.indicators.RSI()
        self.macd = bt.indicators.MACD()  # default (12,26,9)
        self.stoch = bt.indicators.Stochastic()  # default parameters

    def next(self):
        # Do nothing if an order is already pending.
        if self.order:
            return

        price = self.data.close[0]

        # Ensure sufficient data is loaded.
        if len(self.data) < self.p.sma_period:
            return

        # Determine position size based on risk.
        risk_amount = self.broker.get_value() * self.p.risk_pct
        stop_distance = self.atr[0] * 2.0  # stop loss: 2×ATR
        if stop_distance <= 0:
            return
        risk_per_share = stop_distance
        position_size = int(risk_amount / risk_per_share)
        if position_size <= 0:
            return

        # ---------------------------
        # ENTRY CONDITIONS (Long Only)
        # ---------------------------
        if not self.position:
            trend_up = price > self.sma[0]
            # "Pullback" condition: price's momentum dips.
            oversold = (self.rsi[0] < self.p.rsi_entry) and (
                self.stoch.percD[0] < self.p.stoch_threshold
            )
            macd_positive = self.macd.macd[0] > self.macd.signal[0]

            if self.p.debug:
                self.logger.log_trade(
                    f"DEBUG ENTRY: Price: {price:.2f}, SMA: {self.sma[0]:.2f}, "
                    f"RSI: {self.rsi[0]:.2f} (<{self.p.rsi_entry}), "
                    f"Stoch %D: {self.stoch.percD[0]:.2f} (<{self.p.stoch_threshold}), "
                    f"MACD: {self.macd.macd[0]:.2f} vs Signal: {self.macd.signal[0]:.2f}"
                )

            if trend_up and oversold and macd_positive:
                self.buy_price = price
                self.stop_price = price - stop_distance  # initial stop loss
                self.order = self.buy(size=position_size)
                if self.p.debug:
                    self.logger.log_trade(
                        f"BUY CREATE at {price:.2f}, Size: {position_size} shares"
                    )

        # ---------------------------
        # EXIT CONDITIONS (When in Position)
        # ---------------------------
        else:
            # Update trailing stop: allow it only to move higher.
            if self.stop_price is None:
                self.stop_price = price - stop_distance
            else:
                self.stop_price = max(
                    self.stop_price, price * (1 - self.p.trail_percent)
                )

            # Define a profit target (e.g., 3× risk).
            profit_target = self.buy_price + self.p.profit_target * stop_distance

            # Exit if price falls below the trailing stop,
            # if price reaches/exceeds the profit target,
            # or if RSI becomes overbought.
            exit_condition = (
                (price < self.stop_price)
                or (price >= profit_target)
                or (self.rsi[0] > self.p.rsi_exit)
            )

            if self.p.debug:
                self.logger.log_trade(
                    f"DEBUG EXIT: Price: {price:.2f}, Stop: {self.stop_price:.2f}, "
                    f"Target: {profit_target:.2f}, RSI: {self.rsi[0]:.2f} (>{self.p.rsi_exit})"
                )

            if exit_condition:
                self.order = self.sell(size=self.position.size)
                if self.p.debug:
                    self.logger.log_trade(
                        f"SELL CREATE at {price:.2f}, Size: {self.position.size} shares"
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

# Single debug flag to control all logging
DEBUG_MODE = True  # Set this to True/False to control all debug logging

# Create dependencies using the single debug flag
logger = FileTradeLogger(filename="trading.log", debug=DEBUG_MODE)
tracker = DefaultTradeTracker()

# Add strategy with the same debug flag
cerebro.addstrategy(ImprovedStrategy, logger=logger, tracker=tracker, debug=DEBUG_MODE)

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
