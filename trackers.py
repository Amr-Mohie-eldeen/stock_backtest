from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import datetime
import logging
from collections import defaultdict
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Represents a single trade"""

    action: str
    price: float
    date: datetime.date
    size: int
    value: float
    returns: float
    portfolio_value: float

    def __post_init__(self):
        """Validate trade data after initialization"""
        if not isinstance(self.action, str) or self.action not in ["BUY", "SELL"]:
            raise ValueError("Invalid action type")
        if not isinstance(self.price, (int, float)) or self.price <= 0:
            raise ValueError("Invalid price")
        if not isinstance(self.size, int) or self.size <= 0:
            raise ValueError("Invalid size")
        if (
            not isinstance(self.portfolio_value, (int, float))
            or self.portfolio_value < 0
        ):
            raise ValueError("Invalid portfolio value")


class TradeTracker(ABC):
    """Abstract base class for trade tracking"""

    @abstractmethod
    def add_trade(
        self,
        action: str,
        price: float,
        date: datetime.date,
        size: int,
        portfolio_value: float,
        symbol: str = None,
    ) -> None:
        """Add a trade to the tracker"""
        pass

    @abstractmethod
    def add_signal(
        self, signal_type: str, date: datetime.date, price: float, symbol: str
    ) -> None:
        """Add a signal for plotting"""
        pass

    @abstractmethod
    def get_signals(self) -> Tuple[List[Tuple], List[Tuple]]:
        """Get all signals for plotting"""
        pass

    @abstractmethod
    def get_trade_history(self) -> List[Trade]:
        """Get all trades"""
        pass

    @abstractmethod
    def get_performance_metrics(self) -> Dict:
        """Calculate performance metrics"""
        pass


class DefaultTradeTracker(TradeTracker):
    """Default implementation of TradeTracker"""

    def __init__(self):
        self._trade_count: int = 0
        self.trades: List[Trade] = []
        self.buy_signals: List[Tuple[datetime.date, float, str]] = []
        self.sell_signals: List[Tuple[datetime.date, float, str]] = []
        self._current_trade = False
        self._last_buy_price: Optional[float] = None
        self._last_position_size: Optional[int] = None
        self._last_position_value: Optional[float] = None
        self._portfolio_value: Optional[float] = None
        self._symbol_trades: Dict[str, List[Trade]] = defaultdict(list)

    def add_trade(
        self,
        action: str,
        price: float,
        date: datetime.date,
        size: int,
        portfolio_value: float,
        symbol: str = None,
    ) -> None:
        """Add a trade to the tracker"""
        try:
            # Validate inputs
            if not isinstance(action, str) or action not in ["BUY", "SELL"]:
                raise ValueError(f"Invalid action: {action}")
            if not isinstance(price, (int, float)) or price <= 0:
                raise ValueError(f"Invalid price: {price}")
            if not isinstance(size, int) or size <= 0:
                raise ValueError(f"Invalid size: {size}")
            if not isinstance(portfolio_value, (int, float)) or portfolio_value < 0:
                raise ValueError(f"Invalid portfolio value: {portfolio_value}")

            value = price * size
            returns = 0.0
            self._portfolio_value = portfolio_value

            if action == "BUY":
                if self._current_trade:
                    logger.warning("Opening new position while another is still open")
                self._last_buy_price = price
                self._last_position_size = size
                self._last_position_value = value
                self._current_trade = True
            elif action == "SELL":
                if not self._current_trade:
                    logger.warning("Attempting to sell without an open position")
                    return
                if self._last_position_value is None:
                    logger.error("Last position value is None during sell")
                    return
                returns = (
                    (price * size) - self._last_position_value
                ) / self._last_position_value
                self._trade_count += 1
                self._current_trade = False
                self._last_buy_price = None
                self._last_position_size = None
                self._last_position_value = None

            trade = Trade(
                action=action,
                price=price,
                date=date,
                size=size,
                value=value,
                returns=returns,
                portfolio_value=portfolio_value,
            )
            self.trades.append(trade)

            if symbol:
                self._symbol_trades[symbol].append(trade)

        except Exception as e:
            logger.error(f"Error adding trade: {e}")
            raise

    def add_signal(
        self, signal_type: str, date: datetime.date, price: float, symbol: str
    ) -> None:
        """Add a signal for plotting"""
        try:
            # Validate inputs
            if not isinstance(signal_type, str) or signal_type not in ["BUY", "SELL"]:
                raise ValueError(f"Invalid signal type: {signal_type}")
            if not isinstance(price, (int, float)) or price <= 0:
                raise ValueError(f"Invalid price: {price}")
            if not isinstance(symbol, str) or not symbol.strip():
                raise ValueError(f"Invalid symbol: {symbol}")

            if signal_type == "BUY":
                self.buy_signals.append((date, price, symbol))
            elif signal_type == "SELL":
                self.sell_signals.append((date, price, symbol))

        except Exception as e:
            logger.error(f"Error adding signal: {e}")
            raise

    def get_signals(self) -> Tuple[List[Tuple], List[Tuple]]:
        """Get all signals for plotting"""
        try:
            return self.buy_signals, self.sell_signals
        except Exception as e:
            logger.error(f"Error getting signals: {e}")
            return [], []

    def get_trade_history(self) -> List[Trade]:
        """Get all trades"""
        try:
            return self.trades
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []

    def get_symbol_trades(self, symbol: str) -> List[Trade]:
        """Get trades for a specific symbol"""
        try:
            if not isinstance(symbol, str) or not symbol.strip():
                raise ValueError(f"Invalid symbol: {symbol}")
            return self._symbol_trades[symbol]
        except Exception as e:
            logger.error(f"Error getting trades for symbol {symbol}: {e}")
            return []

    def get_performance_metrics(self) -> Dict:
        """Calculate performance metrics"""
        try:
            total_trades = len(self.trades)
            winning_trades = sum(1 for trade in self.trades if trade.returns > 0)
            losing_trades = sum(1 for trade in self.trades if trade.returns < 0)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            return {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
            }
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
            }
