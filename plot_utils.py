import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.widgets import SpanSelector, Button
import pandas as pd


def create_trading_plots(data_df, tracker, starting_value, final_value):
    """
    Create trading plots with price, signals, and equity curves.

    Parameters:
    -----------
    data_df : pandas.DataFrame
        The price data with OHLCV columns
    tracker : DefaultTradeTracker
        Object containing buy/sell signals
    starting_value : float
        Initial portfolio value
    final_value : float
        Final portfolio value
    """
    # Create a figure with two subplots sharing the same x-axis
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(14, 10), sharex=True, constrained_layout=True
    )

    fig.canvas.toolbar_visible = True
    fig.canvas.header_visible = False

    # --- Subplot 1: Price Chart with Trade Markers ---
    ax1.plot(
        data_df.index, data_df["close"], label="Close Price", color="blue", alpha=0.5
    )

    # Plot buy signals
    if tracker.buy_signals:
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
    if tracker.sell_signals:
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
    ax2.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, p: f'${format(int(x), ",")}')
    )

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

    reset_ax = plt.axes([0.8, 0.025, 0.1, 0.04])
    reset_button = plt.Button(reset_ax, "Reset Zoom")
    reset_button.on_clicked(reset_zoom)

    return fig
