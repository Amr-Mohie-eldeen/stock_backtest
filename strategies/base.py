import backtrader as bt
from typing import Optional, List


class BaseStrategy(bt.Strategy):
    """Base strategy class that handles infrastructure"""

    params = (
        ("debug", False),
        ("logger", None),
        ("tracker", None),
        ("portfolio_manager", None),
    )

    def __init__(self):
        super().__init__()
        self.orders = {}
        self.portfolio_manager = self.p.portfolio_manager
        self.logger = self.p.logger
        self.tracker = self.p.tracker

        # Store indicators per symbol
        self.indicators = {}
        for data in self.datas[:-1]:  # Exclude benchmark data
            symbol = data._name
            self.indicators[symbol] = {
                "sma": bt.indicators.SimpleMovingAverage(data.close, period=20),
                "rsi": bt.indicators.RelativeStrengthIndex(data),
                "macd": bt.indicators.MACD(data),
                "stoch": bt.indicators.StochasticSlow(data),
            }

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            data = order.data
            symbol = data._name
            portfolio_value = self.broker.getvalue()  # Get current portfolio value

            if order.isbuy():
                self.logger.log_trade(
                    f"BUY EXECUTED - Price: {order.executed.price:.2f}, "
                    f"Size: {order.executed.size:.0f} shares, "
                    f"Cost: {order.executed.value:.2f}, "
                    f"Comm: {order.executed.comm:.2f}"
                )
                self.tracker.add_trade(
                    "BUY",
                    order.executed.price,
                    data.datetime.date(0),
                    order.executed.size,
                    portfolio_value,
                )
                self.tracker.add_signal(
                    "BUY", data.datetime.date(0), order.executed.price, data._name
                )
                self.portfolio_manager.add_position(
                    symbol, order.executed.size, order.executed.price
                )
            elif order.issell():
                self.logger.log_trade(
                    f"SELL EXECUTED - Price: {order.executed.price:.2f}, "
                    f"Size: {order.executed.size:.0f} shares, "
                    f"Cost: {order.executed.value:.2f}, "
                    f"Comm: {order.executed.comm:.2f}"
                )
                self.tracker.add_trade(
                    "SELL",
                    order.executed.price,
                    data.datetime.date(0),
                    abs(order.executed.size),
                    portfolio_value,
                )
                self.tracker.add_signal(
                    "SELL", data.datetime.date(0), order.executed.price, data._name
                )
                self.portfolio_manager.remove_position(symbol)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.logger.log_trade(f"Order Failed with Status: {order.getstatusname()}")

        # Clear the order from orders dict
        symbol = order.data._name
        self.orders[symbol] = None

    def log_debug_entry(self, price: float) -> None:
        if self.p.debug:
            self.logger.log_trade(
                f"DEBUG ENTRY: Price: {price:.2f}, "
                f"SMA: {self.indicators[self.data._name]['sma'][0]:.2f}, "
                f"RSI: {self.indicators[self.data._name]['rsi'][0]:.2f} (<65), "
                f"Stoch %D: {self.indicators[self.data._name]['stoch'].lines.percD[0]:.2f} (<60), "
                f"MACD: {self.indicators[self.data._name]['macd'].lines.macd[0]:.2f} vs Signal: {self.indicators[self.data._name]['macd'].lines.signal[0]:.2f}"
            )

    def log_debug_exit(self, price: float, stop: float, target: float) -> None:
        if self.p.debug:
            self.logger.log_trade(
                f"DEBUG EXIT: Price: {price:.2f}, "
                f"Stop: {stop:.2f}, "
                f"Target: {target:.2f}, "
                f"RSI: {self.indicators[self.data._name]['rsi'][0]:.2f} (>75)"
            )

    def stop(self):
        """Called when the strategy is stopped"""
        # Calculate returns
        starting_value = self.broker.startingcash
        final_value = self.broker.getvalue()

        # Debug print actual broker values
        print("\nDEBUG - Broker Values:")
        print(f"Starting Cash: ${starting_value:,.2f}")
        print(f"Final Value: ${final_value:,.2f}")
        print(f"Cash: ${self.broker.getcash():,.2f}")
        print(f"Portfolio Value: ${self.broker.getvalue():,.2f}")
        positions_value = sum(
            pos.size * data.close[0] for data, pos in self.getpositions().items()
        )
        print(f"Positions Value: ${positions_value:,.2f}")

        returns = (final_value - starting_value) / starting_value * 100
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
