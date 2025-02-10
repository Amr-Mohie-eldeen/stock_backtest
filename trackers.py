from typing import List, Tuple, Protocol
import datetime
from dataclasses import dataclass, field


@dataclass
class Trade:
    action: str
    price: float
    date: datetime.date
    size: int
    value: float
    returns: float = 0.0
    portfolio_value: float = 0.0


class TradeTracker(Protocol):
    def add_trade(self, action: str, price: float, date: datetime.date) -> None:
        pass

    def add_signal(self, signal_type: str, date: datetime.date, price: float) -> None:
        pass

    @property
    def trade_count(self) -> int:
        pass


class DefaultTradeTracker:
    def __init__(self):
        self._trade_count: int = 0
        self.trades: List[Trade] = []
        self.buy_signals: List[Tuple[datetime.date, float]] = []
        self.sell_signals: List[Tuple[datetime.date, float]] = []
        self._current_trade = False
        self._last_buy_price = None
        self._last_position_size = None
        self._last_position_value = None
        self._portfolio_value = None

    def add_trade(
        self,
        action: str,
        price: float,
        date: datetime.date,
        size: int,
        portfolio_value: float,
    ) -> None:
        """Add a trade to the tracker"""
        value = price * size
        returns = 0.0
        self._portfolio_value = portfolio_value

        if action == "BUY":
            self._last_buy_price = price
            self._last_position_size = size
            self._last_position_value = value
            self._current_trade = True
        elif action == "SELL" and self._current_trade:
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

    def add_signal(
        self, signal_type: str, date: datetime.date, price: float, symbol: str
    ) -> None:
        """Add a ticker-specific signal for plotting"""
        if signal_type == "BUY":
            self.buy_signals.append((date, price, symbol))
        elif signal_type == "SELL":
            self.sell_signals.append((date, price, symbol))

    @property
    def trade_count(self) -> int:
        """Get the number of completed trades"""
        return self._trade_count

    def get_trade_history(self) -> List[Trade]:
        """Get the full trade history"""
        return self.trades

    def get_signals(
        self,
    ) -> Tuple[List[Tuple[datetime.date, float]], List[Tuple[datetime.date, float]]]:
        """Get buy and sell signals for plotting"""
        return self.buy_signals, self.sell_signals

    def reset(self) -> None:
        """Reset the tracker"""
        self._trade_count = 0
        self.trades.clear()
        self.buy_signals.clear()
        self.sell_signals.clear()
        self._current_trade = False
        self._last_buy_price = None
        self._last_position_size = None
        self._last_position_value = None
        self._portfolio_value = None

    def get_performance_metrics(self) -> dict:
        """Calculate performance metrics"""
        total_trades = len([t for t in self.trades if t.action == "SELL"])
        winning_trades = len(
            [t for t in self.trades if t.action == "SELL" and t.returns > 0]
        )
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
        }
