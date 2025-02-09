import backtrader as bt
from typing import Optional, List


class BaseStrategy(bt.Strategy):
    """Base strategy class that handles infrastructure"""

    params = (
        ("debug", False),
        ("logger", None),
        ("tracker", None),
    )

    def __init__(self):
        super().__init__()
        self.order = None
        self.buy_price = None
        self.stop_price = None

        # Store logger and tracker from params
        self.logger = self.p.logger
        self.tracker = self.p.tracker

        # Store indicators for debug logging
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=20)
        self.rsi = bt.indicators.RelativeStrengthIndex()
        self.macd = bt.indicators.MACD()
        self.stoch = bt.indicators.StochasticSlow()

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
                # Track both the trade and the signal
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
                # Track both the trade and the signal
                self.tracker.add_trade(
                    "SELL", order.executed.price, self.data.datetime.date(0)
                )
                self.tracker.add_signal(
                    "SELL", self.data.datetime.date(0), order.executed.price
                )

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.logger.log_trade(f"Order Failed with Status: {order.getstatusname()}")

        self.order = None

    def log_debug_entry(self, price: float) -> None:
        if self.p.debug:
            self.logger.log_trade(
                f"DEBUG ENTRY: Price: {price:.2f}, "
                f"SMA: {self.sma[0]:.2f}, "
                f"RSI: {self.rsi[0]:.2f} (<65), "
                f"Stoch %D: {self.stoch.lines.percD[0]:.2f} (<60), "
                f"MACD: {self.macd.lines.macd[0]:.2f} vs Signal: {self.macd.lines.signal[0]:.2f}"
            )

    def log_debug_exit(self, price: float, stop: float, target: float) -> None:
        if self.p.debug:
            self.logger.log_trade(
                f"DEBUG EXIT: Price: {price:.2f}, "
                f"Stop: {stop:.2f}, "
                f"Target: {target:.2f}, "
                f"RSI: {self.rsi[0]:.2f} (>75)"
            )

    def stop(self):
        """Called when the strategy is stopped"""
        # Calculate returns
        starting_value = self.broker.startingcash
        final_value = self.broker.getvalue()
        returns = (final_value - starting_value) / starting_value * 100

        # Get performance metrics
        metrics = self.tracker.get_performance_metrics()

        # Create summary
        summary = (
            "\n=== Trading Summary ===\n"
            f"Starting Value: ${starting_value:,.2f}\n"
            f"Final Value: ${final_value:,.2f}\n"
            f"Return: {returns:.2f}%\n"
            f"Total Trades: {metrics['total_trades']}\n"
            f"Winning Trades: {metrics['winning_trades']}\n"
            f"Losing Trades: {metrics['losing_trades']}\n"
            f"Win Rate: {metrics['win_rate']:.2f}%\n"
            "===================="
        )

        # Log the summary
        self.logger.log_summary(summary)
