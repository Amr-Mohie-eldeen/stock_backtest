import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.widgets import SpanSelector, Button
import pandas as pd
import numpy as np
from typing import Dict
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QMainWindow


def calculate_strategy_equity_curve(tracker, starting_value: float) -> pd.Series:
    """Calculate equity curve from trade history"""
    trades = tracker.get_trade_history()
    if not trades:
        return pd.Series()

    # Sort trades by date
    sorted_trades = sorted(trades, key=lambda x: x.date)
    daily_values = {}
    daily_values[sorted_trades[0].date] = starting_value  # initial value

    for trade in sorted_trades:
        daily_values[trade.date] = trade.portfolio_value

    equity_curve = pd.Series(daily_values)

    # Reindex to include all dates between the first and last trade
    full_date_range = pd.date_range(
        start=min(daily_values.keys()), end=max(daily_values.keys()), freq="D"
    )
    equity_curve = equity_curve.reindex(full_date_range, method="ffill")
    return equity_curve


def calculate_benchmark_returns(
    benchmark_df: pd.DataFrame, starting_value: float
) -> pd.Series:
    """Calculate benchmark equity curve"""
    if benchmark_df.empty:
        return pd.Series()

    initial_price = benchmark_df["close"].iloc[0]
    normalized_values = starting_value * (benchmark_df["close"] / initial_price)
    return pd.Series(normalized_values, index=benchmark_df.index)


def create_trading_plots(
    data_dfs: Dict[str, pd.DataFrame],
    benchmark_df: pd.DataFrame,
    tracker,
    starting_value: float,
    final_value: float,
) -> None:
    """Create all trading plots"""
    num_stocks = len(data_dfs)
    fig = plt.figure(figsize=(15, 4 * (num_stocks + 1)))
    gs = fig.add_gridspec(num_stocks + 1, 1, hspace=0.4)

    # Get signals from the tracker.
    # They may be 2-tuples (date, price) or 3-tuples (date, price, symbol)
    buy_signals, sell_signals = tracker.get_signals()

    # List to store axes for later zoom reset
    all_axes = []

    # Loop over each stock symbol and its DataFrame
    for i, (symbol, df) in enumerate(data_dfs.items()):
        ax = fig.add_subplot(gs[i])
        all_axes.append(ax)

        # Plot the price data
        ax.plot(df.index, df["close"], label=f"{symbol} Price", color="blue")

        # --- Adjusted Signal Filtering ---
        # Instead of checking if the signal date is in df.index,
        # we check whether it falls between the minimum and maximum dates.
        if buy_signals:
            if len(buy_signals[0]) == 3:
                # Signals include symbol info; do a case-insensitive match
                symbol_buys = [
                    (pd.Timestamp(date), price)
                    for date, price, sym in buy_signals
                    if sym.upper() == symbol.upper()
                    and (df.index.min() <= pd.Timestamp(date) <= df.index.max())
                ]
                symbol_sells = [
                    (pd.Timestamp(date), price)
                    for date, price, sym in sell_signals
                    if sym.upper() == symbol.upper()
                    and (df.index.min() <= pd.Timestamp(date) <= df.index.max())
                ]
            elif len(buy_signals[0]) == 2:
                # Signals are generic; filter by date range only.
                symbol_buys = [
                    (pd.Timestamp(date), price)
                    for date, price in buy_signals
                    if df.index.min() <= pd.Timestamp(date) <= df.index.max()
                ]
                symbol_sells = [
                    (pd.Timestamp(date), price)
                    for date, price in sell_signals
                    if df.index.min() <= pd.Timestamp(date) <= df.index.max()
                ]
            else:
                symbol_buys, symbol_sells = [], []
        else:
            symbol_buys, symbol_sells = [], []

        # Plot buy signals (green triangle)
        if symbol_buys:
            buy_dates, buy_prices = zip(*symbol_buys)
            ax.scatter(
                buy_dates,
                buy_prices,
                marker="^",
                color="green",
                s=100,
                label="Buy Signal",
                zorder=5,
            )

        # Plot sell signals (red inverted triangle)
        if symbol_sells:
            sell_dates, sell_prices = zip(*symbol_sells)
            ax.scatter(
                sell_dates,
                sell_prices,
                marker="v",
                color="red",
                s=100,
                label="Sell Signal",
                zorder=5,
            )

        # Format the stock plot axes
        ax.grid(True)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.2f}"))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        ax.set_title(f"{symbol} Price and Signals", fontsize=12, pad=10)
        ax.legend(loc="upper left")

    # Portfolio performance subplot
    ax_portfolio = fig.add_subplot(gs[-1])
    all_axes.append(ax_portfolio)

    strategy_values = calculate_strategy_equity_curve(tracker, starting_value)
    benchmark_values = calculate_benchmark_returns(benchmark_df, starting_value)

    if not strategy_values.empty:
        ax_portfolio.plot(
            strategy_values.index,
            strategy_values.values,
            label=f"Strategy (${final_value:,.0f})",
            color="blue",
            linewidth=2,
        )

    if not benchmark_values.empty:
        ax_portfolio.plot(
            benchmark_values.index,
            benchmark_values.values,
            label=f"S&P 500 (${benchmark_values.iloc[-1]:,.0f})",
            color="gray",
            linewidth=2,
            alpha=0.7,
        )

    ax_portfolio.set_title("Portfolio Value vs Benchmark", fontsize=12, pad=10)
    ax_portfolio.legend(loc="upper left")
    ax_portfolio.grid(True)
    ax_portfolio.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))
    ax_portfolio.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax_portfolio.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.setp(ax_portfolio.xaxis.get_majorticklabels(), rotation=45)

    # Store original x-axis limits for each subplot (for resetting zoom)
    original_xlim = [ax.get_xlim() for ax in all_axes]

    # --- Zoom Functionality ---
    def make_on_select(ax):
        def on_select(xmin, xmax):
            ax.set_xlim(xmin, xmax)
            fig.canvas.draw_idle()

        return on_select

    # Keep references to SpanSelector objects so they are not garbage-collected.
    span_selectors = []
    for ax in all_axes:
        ss = SpanSelector(
            ax,
            make_on_select(ax),
            "horizontal",
            useblit=True,
            props=dict(alpha=0.3, facecolor="lightblue"),
            interactive=True,
            drag_from_anywhere=True,
            button=1,
        )
        span_selectors.append(ss)

    # --- Reset Zoom Button ---
    reset_ax = plt.axes([0.8, 0.01, 0.1, 0.03])
    reset_button = Button(reset_ax, "Reset Zoom")

    def reset_zoom(event):
        for ax, lim in zip(all_axes, original_xlim):
            ax.set_xlim(lim)
        fig.canvas.draw_idle()

    reset_button.on_clicked(reset_zoom)

    plt.tight_layout()
    plt.show()
