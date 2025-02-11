import backtrader as bt
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from loggers import TradeLogger
from trackers import TradeTracker
from portfolio import PortfolioManager

# Configure logging
logger = logging.getLogger(__name__)


class BaseStrategy(bt.Strategy):
    """Base strategy class that handles infrastructure"""

    params = (
        ("debug", False),
        ("logger", None),
        ("tracker", None),
        ("portfolio_manager", None),
    )

    def __init__(self):
        try:
            # Get components from params
            self.logger = self.params.logger
            self.tracker = self.params.tracker
            self.portfolio_manager = self.params.portfolio_manager

            # Validate required attributes
            if not hasattr(self, "logger") or not isinstance(self.logger, TradeLogger):
                raise ValueError("Strategy requires a valid logger")
            if not hasattr(self, "tracker") or not isinstance(
                self.tracker, TradeTracker
            ):
                raise ValueError("Strategy requires a valid tracker")
            if not hasattr(self, "portfolio_manager") or not isinstance(
                self.portfolio_manager, PortfolioManager
            ):
                raise ValueError("Strategy requires a valid portfolio manager")

            # Initialize strategy components
            self.orders: Dict[str, Any] = {}  # Track open orders
            self.current_positions = {}  # Track current positions

            # Store initial portfolio value
            self.starting_portfolio_value = self.broker.getvalue()

            if self.p.debug:
                self.logger.info(
                    f"Strategy initialized with portfolio value: ${self.starting_portfolio_value:,.2f}"
                )

        except Exception as e:
            logger.error(f"Error initializing strategy: {e}")
            raise

    def notify_order(self, order):
        """Handle order notifications"""
        try:
            if order.status in [order.Submitted, order.Accepted]:
                return

            if order.status in [order.Completed]:
                data = order.data
                symbol = data._name
                portfolio_value = self.broker.getvalue()

                try:
                    if order.isbuy():
                        self._handle_buy_order(order, data, symbol, portfolio_value)
                    elif order.issell():
                        self._handle_sell_order(order, data, symbol, portfolio_value)
                except Exception as e:
                    self.logger.error(
                        f"Error handling {order.isbuy() and 'buy' or 'sell'} order: {e}"
                    )

            elif order.status in [order.Canceled, order.Margin, order.Rejected]:
                self.logger.error(f"Order failed: {order.status}")
                self.orders[order.data._name] = None

        except Exception as e:
            self.logger.error(f"Error in notify_order: {e}")

    def _handle_buy_order(self, order, data, symbol: str, portfolio_value: float):
        """Handle buy order completion"""
        try:
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
                symbol,
            )

            self.tracker.add_signal(
                "BUY", data.datetime.date(0), order.executed.price, symbol
            )

            self.portfolio_manager.add_position(
                symbol, order.executed.size, order.executed.price
            )

            self.orders[symbol] = None
            self.current_positions[symbol] = order.executed.size

        except Exception as e:
            self.logger.error(f"Error handling buy order completion: {e}")
            raise

    def _handle_sell_order(self, order, data, symbol: str, portfolio_value: float):
        """Handle sell order completion"""
        try:
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
                symbol,
            )

            self.tracker.add_signal(
                "SELL", data.datetime.date(0), order.executed.price, symbol
            )

            self.portfolio_manager.remove_position(symbol)

            self.orders[symbol] = None
            self.current_positions.pop(symbol, None)

        except Exception as e:
            self.logger.error(f"Error handling sell order completion: {e}")
            raise

    def buy_stock(self, data, size: Optional[int] = None) -> bool:
        """Place a buy order"""
        try:
            if self.orders.get(data._name):
                return False  # Order already pending

            if size is None:
                size = self.get_position_size(data)
                if size is None:
                    self.logger.error(
                        f"Could not determine position size for {data._name}"
                    )
                    return False

            order = self.buy(data=data, size=size)
            self.orders[data._name] = order
            return True

        except Exception as e:
            self.logger.error(f"Error placing buy order: {e}")
            return False

    def sell_stock(self, data) -> bool:
        """Place a sell order"""
        try:
            if self.orders.get(data._name):
                return False  # Order already pending

            position = self.getposition(data)
            if not position:
                self.logger.warning(f"No position to sell for {data._name}")
                return False

            order = self.sell(data=data, size=position.size)
            self.orders[data._name] = order
            return True

        except Exception as e:
            self.logger.error(f"Error placing sell order: {e}")
            return False

    def get_position_size(self, data) -> Optional[int]:
        """Calculate position size based on portfolio value"""
        try:
            portfolio_value = self.broker.getvalue()
            price = data.close[0]
            if price <= 0:
                raise ValueError(f"Invalid price for {data._name}: {price}")

            position_value = (
                portfolio_value * self.portfolio_manager.position_size_per_trade
            )
            size = int(position_value / price)

            if size <= 0:
                self.logger.warning(
                    f"Calculated position size too small for {data._name}"
                )
                return None

            return size

        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return None

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
