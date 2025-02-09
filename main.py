import backtrader as bt
import yfinance as yf
import datetime
import pandas as pd
import matplotlib.pyplot as plt

# -----------------------------
# Set Matplotlib Aesthetics
# -----------------------------
plt.style.use("seaborn-v0_8-darkgrid")  # Use a nicer default style


# -----------------------------
# Define the Strategy
# -----------------------------
class SmaCross(bt.Strategy):
    params = (
        ("sma1_period", 10),
        ("sma2_period", 30),
    )

    def __init__(self):
        self.sma1 = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.p.sma1_period
        )
        self.sma2 = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.p.sma2_period
        )

    def next(self):
        # Check if we're in the market
        if not self.position:
            # Generate a BUY signal when the short SMA crosses above the long SMA
            if self.sma1[0] > self.sma2[0] and self.sma1[-1] <= self.sma2[-1]:
                self.buy()
                self.log("BUY CREATE, {:.2f}".format(self.data.close[0]))
        else:
            # Generate a SELL signal when the short SMA crosses below the long SMA
            if self.sma1[0] < self.sma2[0] and self.sma1[-1] >= self.sma2[-1]:
                self.sell()
                self.log("SELL CREATE, {:.2f}".format(self.data.close[0]))

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()} {txt}")


# -----------------------------
# Data Acquisition using yfinance
# -----------------------------
ticker = "AAPL"
start_date = "2019-01-01"
end_date = "2023-01-01"
data_df = yf.download(ticker, start=start_date, end=end_date)

# Debug: Check the type and columns of the DataFrame
print("Type of data_df:", type(data_df))
print("Columns before flattening:", data_df.columns)

# -----------------------------
# Flatten MultiIndex Columns (if applicable)
# -----------------------------
if isinstance(data_df.columns, pd.MultiIndex):
    # Approach 1: Use the first level of the MultiIndex (which should be the standard names)
    data_df.columns = data_df.columns.get_level_values(0)

# Convert all column names to lowercase
data_df.columns = [col.lower() for col in data_df.columns]
print("Columns after flattening and lowercasing:", data_df.columns)

# -----------------------------
# Set Up Cerebro Engine
# -----------------------------
cerebro = bt.Cerebro()
cerebro.addstrategy(SmaCross, sma1_period=10, sma2_period=30)

# Create a PandasData feed with the cleaned DataFrame
data = bt.feeds.PandasData(dataname=data_df)
cerebro.adddata(data)

# Set initial cash and commission
cerebro.broker.setcash(100000.0)
cerebro.broker.setcommission(commission=0.001)

# -----------------------------
# Run the Backtest and Print Results with Thousand Separators
# -----------------------------
starting_value = cerebro.broker.getvalue()
print(f"Starting Portfolio Value: {format(starting_value, ',.2f')}")

cerebro.run()

final_value = cerebro.broker.getvalue()
print(f"Final Portfolio Value: {format(final_value, ',.2f')}")

# -----------------------------
# Optional: Improved Custom Plot with Matplotlib (Pandas-Based Performance Evaluation)
# -----------------------------
# For additional insights, we can compute and plot the cumulative returns.

# Compute SMAs for the Pandas-based approach (if desired)
data_df["sma_short"] = data_df["close"].rolling(window=10).mean()
data_df["sma_long"] = data_df["close"].rolling(window=30).mean()

# Create a binary signal: 1 when short SMA > long SMA, else 0.
data_df["signal"] = 0
data_df.loc[data_df["sma_short"] > data_df["sma_long"], "signal"] = 1
data_df["position"] = data_df["signal"].diff()

# Compute daily returns and the strategy's returns (using the previous day's signal)
data_df["daily_return"] = data_df["close"].pct_change()
data_df["strategy_return"] = data_df["daily_return"] * data_df["signal"].shift(1)

# Compute cumulative returns for the strategy and for the market
data_df["cumulative_strategy_return"] = (
    1 + data_df["strategy_return"]
).cumprod() * starting_value
data_df["cumulative_market_return"] = (
    1 + data_df["daily_return"]
).cumprod() * starting_value

# Plot the cumulative returns with enhanced formatting
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(
    data_df.index,
    data_df["cumulative_strategy_return"],
    label="Strategy Return",
    linewidth=2,
)
ax.plot(
    data_df.index,
    data_df["cumulative_market_return"],
    label="Market Return",
    linewidth=2,
)

ax.set_title("Cumulative Returns Comparison", fontsize=16)
ax.set_xlabel("Date", fontsize=14)
ax.set_ylabel("Portfolio Value ($)", fontsize=14)  # Updated y-axis label
ax.legend(fontsize=12)
ax.grid(True)

# Format y-axis to show dollar values with commas
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${format(int(x), ",")}'))

plt.tight_layout()

# Print the final market value
final_market_value = data_df["cumulative_market_return"].iloc[-1]
print(f"Final Market Value: {format(final_market_value, ',.2f')}")

plt.show()
