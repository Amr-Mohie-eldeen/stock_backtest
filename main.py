import backtrader as bt
import yfinance as yf
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import os
import logging
from matplotlib.widgets import SpanSelector

# -----------------------------
# Set Matplotlib Aesthetics
# -----------------------------
plt.style.use("seaborn-v0_8-darkgrid")  # Adjust if necessary


# -----------------------------
# Define the Strategy
# -----------------------------
class EnhancedStrategy(bt.Strategy):
    params = (
        ("rsi_period", 14),
        ("rsi_overbought", 60),  # Consider lowering if exits never occur
        ("rsi_oversold", 45),
        ("macd_fast", 12),
        ("macd_slow", 26),
        ("macd_signal", 9),
        ("bb_period", 20),
        ("bb_devfactor", 1.5),
        ("trail_percent", 0.02),  # Trailing stop percentage
        ("debug", False),  # Add debug parameter, default to False
    )

    def __init__(self):
        # Setup logging first
        if os.path.exists("trading.log"):
            os.remove("trading.log")
        self.logger = logging.getLogger("TradingLog")
        self.logger.setLevel(logging.DEBUG if self.p.debug else logging.INFO)
        fh = logging.FileHandler("trading.log")
        fh.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        self.logger.addHandler(fh)
        self.logger.info("=== New Trading Session Started ===")

        # Indicators
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        self.macd = bt.indicators.MACD(
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal,
        )
        self.bb = bt.indicators.BollingerBands(
            period=self.p.bb_period, devfactor=self.p.bb_devfactor
        )

        # Order tracking
        self.order = None

        # For trailing stop
        self.highest_price = 0
        self.lowest_price = float("inf")

        # Tracking portfolio value and trade history
        self.val_start = self.broker.get_cash()
        self.portfolio_value = []
        self.trade_count = 0  # Count completed round-trip trades
        self.trades = []
        self.in_position = False

        # Lists to record individual buy and sell signals
        self.buy_signals = []  # Each element will be (date, price)
        self.sell_signals = []  # Each element will be (date, price)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"BUY EXECUTED - Price: {order.executed.price:.2f}, Size: {order.executed.size:.0f} shares, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}"
                )
                self.in_position = True
                self.highest_price = order.executed.price
            elif order.issell():
                self.log(
                    f"SELL EXECUTED - Price: {order.executed.price:.2f}, Size: {abs(order.executed.size):.0f} shares, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}"
                )
                self.in_position = False
                self.highest_price = 0

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order Failed with Status: {order.getstatusname()}")

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log(
            f"""
        TRADE COMPLETED:
        Gross Profit: {trade.pnl:.2f}
        Net Profit: {trade.pnlcomm:.2f}
        Commission: {trade.commission:.2f}
        """
        )

    def next(self):
        if self.order:
            return

        # Update portfolio value tracking
        current_value = self.broker.get_cash()
        if self.position:
            current_value += self.position.size * self.data.close[0]
        self.portfolio_value.append(current_value)

        # Debug logging only if debug is enabled
        if self.p.debug and len(self.portfolio_value) % 5 == 0:
            highest_price = self.highest_price if self.in_position else 0.0
            trailing_stop = (
                self.highest_price * (1 - self.p.trail_percent)
                if self.in_position
                else 0.0
            )

            self.log(
                f"""
            Debug Values:
            Position Size: {self.position.size if self.position else 0}
            Cash: {self.broker.get_cash():.2f}
            RSI: {self.rsi[0]:.2f}
            MACD: {self.macd.macd[0]:.2f}
            MACD Signal: {self.macd.signal[0]:.2f}
            Close Price: {self.data.close[0]:.2f}
            BB Top: {self.bb.lines.top[0]:.2f}
            BB Bottom: {self.bb.lines.bot[0]:.2f}
            Current Position: {'Yes' if self.in_position else 'No'}
            Current Portfolio Value: {current_value:.2f}
            Trade Count: {self.trade_count}
            Highest Price: {highest_price:.2f}
            Trailing Stop: {trailing_stop:.2f}
            """
            )

        # Check for buy conditions
        if not self.position:
            rsi_condition = self.rsi[0] < self.p.rsi_oversold
            bb_condition = self.data.close[0] < self.bb.lines.bot[0]
            macd_condition = self.macd.macd[0] > self.macd.signal[0]

            conditions_met = sum([rsi_condition, bb_condition, macd_condition])

            if conditions_met >= 1:
                cash = self.broker.get_cash()
                size = int((cash * 0.95) / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
                    self.trade_count += 1
                    self.trades.append(
                        ("BUY", self.data.close[0], self.data.datetime.date(0))
                    )
                    # Store buy signal for plotting
                    self.buy_signals.append(
                        (self.data.datetime.date(0), self.data.close[0])
                    )
                    self.log(
                        f"BUY CREATE at {self.data.close[0]:.2f}, Size: {size} shares (Trade #{self.trade_count})"
                    )

        # Check for sell conditions
        elif self.position.size > 0:
            if self.data.close[0] > self.highest_price:
                self.highest_price = self.data.close[0]

            trailing_stop = self.highest_price * (1 - self.p.trail_percent)

            rsi_condition = self.rsi[0] > self.p.rsi_overbought
            bb_condition = self.data.close[0] > self.bb.lines.top[0]
            macd_condition = self.macd.macd[0] < self.macd.signal[0]
            stop_condition = self.data.close[0] < trailing_stop

            if any([rsi_condition, bb_condition, macd_condition, stop_condition]):
                self.order = self.sell(size=self.position.size)
                self.trades.append(
                    ("SELL", self.data.close[0], self.data.datetime.date(0))
                )
                # Store sell signal for plotting
                self.sell_signals.append(
                    (self.data.datetime.date(0), self.data.close[0])
                )
                self.log(
                    f"SELL CREATE at {self.data.close[0]:.2f}, Size: {self.position.size} shares (Trade #{self.trade_count})"
                )

    def stop(self):
        # Calculate total trades (we store them as tuples of (action, price, date))
        buy_trades = [t for t in self.trades if t[0] == "BUY"]
        sell_trades = [t for t in self.trades if t[0] == "SELL"]
        completed_trades = min(len(buy_trades), len(sell_trades))

        summary = f"""
        === Strategy Summary ===
        Starting Value: ${self.val_start:,.2f}
        Final Value: ${self.portfolio_value[-1]:,.2f}
        Total Return: {((self.portfolio_value[-1] - self.val_start) / self.val_start) * 100:.2f}%
        Total Completed Trades: {completed_trades}
        """
        self.log(summary, print_to_screen=True)

        # Log detailed trade history to file only
        self.log("\nDetailed Trade History:", print_to_screen=False)
        for trade in self.trades:
            self.log(
                f"Action: {trade[0]}, Price: ${trade[1]:.2f}, Date: {trade[2]}",
                print_to_screen=False,
            )

    def log(self, txt, dt=None, print_to_screen=False):
        dt = dt or self.datas[0].datetime.date(0)
        message = f"{dt.isoformat()} {txt}"
        self.logger.info(message)
        if print_to_screen:
            print(message)


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
cerebro.addstrategy(EnhancedStrategy)

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
print(f"Total Completed Trades: {strat.trade_count}")
# -----------------------------
# Plotting Performance with Trade Markers and Buy & Hold Returns
# -----------------------------
import matplotlib.dates as mdates

# Create a figure with two subplots sharing the same x-axis
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

# Enable zooming and panning
plt.rcParams["toolbar"] = "toolmanager"
fig.canvas.toolbar_visible = True
fig.canvas.header_visible = False

# --- Subplot 1: Price Chart with Trade Markers ---
ax1.plot(data_df.index, data_df["close"], label="Close Price", color="blue", alpha=0.5)

# Plot buy signals
if strat.buy_signals:
    buy_dates = [pd.Timestamp(d) for d, _ in strat.buy_signals]
    buy_prices = [price for _, price in strat.buy_signals]
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
if strat.sell_signals:
    sell_dates = [pd.Timestamp(d) for d, _ in strat.sell_signals]
    sell_prices = [price for _, price in strat.sell_signals]
    ax1.scatter(
        sell_dates,
        sell_prices,
        marker="v",
        color="red",
        s=100,
        label="Sell Signal",
        zorder=5,
    )

ax1.set_title("AAPL Price Chart with Trade Signals", fontsize=16)
ax1.set_ylabel("Price ($)", fontsize=14)
ax1.legend(fontsize=12)
ax1.grid(True)

# --- Subplot 2: Cumulative Returns Comparison ---
strategy_values = pd.Series(
    strat.portfolio_value, index=data_df.index[: len(strat.portfolio_value)]
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

plt.tight_layout()
plt.show()
