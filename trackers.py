from typing import List, Tuple, Protocol
import datetime
from dataclasses import dataclass, field


@dataclass
class Trade:
    action: str
    price: float
    date: datetime.date
    size: int = 0
    value: float = 0.0
    commission: float = 0.0


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

    def add_trade(self, action: str, price: float, date: datetime.date) -> None:
        """Add a trade to the tracker"""
        trade = Trade(action=action, price=price, date=date)
        self.trades.append(trade)

        if action == "BUY":
            self._current_trade = True
        elif action == "SELL" and self._current_trade:
            self._trade_count += 1
            self._current_trade = False

    def add_signal(self, signal_type: str, date: datetime.date, price: float) -> None:
        """Add a signal for plotting"""
        if signal_type == "BUY":
            self.buy_signals.append((date, price))
        elif signal_type == "SELL":
            self.sell_signals.append((date, price))

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

    def get_performance_metrics(self) -> dict:
        """Calculate and return performance metrics"""
        if not self.trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
            }

        winning_trades = 0
        losing_trades = 0
        current_buy_price = None

        for trade in self.trades:
            if trade.action == "BUY":
                current_buy_price = trade.price
            elif trade.action == "SELL" and current_buy_price is not None:
                if trade.price > current_buy_price:
                    winning_trades += 1
                else:
                    losing_trades += 1
                current_buy_price = None

        total_completed_trades = winning_trades + losing_trades
        win_rate = (
            (winning_trades / total_completed_trades * 100)
            if total_completed_trades > 0
            else 0
        )

        return {
            "total_trades": total_completed_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
        }
