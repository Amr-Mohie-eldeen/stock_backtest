from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Position:
    symbol: str
    size: int
    entry_price: float
    current_price: float


class PortfolioManager:
    """Manages portfolio positions and risk"""

    def __init__(self, max_positions: int, position_size_per_trade: float):
        self.max_positions = max_positions
        self.position_size_per_trade = position_size_per_trade
        self.current_positions = {}

    def can_open_position(self, available_cash: float) -> bool:
        """Check if we can open a new position"""
        return len(self.current_positions) < self.max_positions

    def calculate_position_size(self, available_cash: float, price: float) -> int:
        """Calculate position size in number of shares"""
        position_value = available_cash * self.position_size_per_trade
        return int(position_value / price)

    def add_position(self, symbol: str, size: int, price: float) -> None:
        """Add a new position"""
        self.current_positions[symbol] = {
            "size": size,
            "price": price,
            "value": size * price,
        }

    def remove_position(self, symbol: str) -> None:
        """Remove a position"""
        if symbol in self.current_positions:
            del self.current_positions[symbol]

    def update_position_price(self, symbol: str, price: float) -> None:
        if symbol in self.current_positions:
            self.current_positions[symbol]["price"] = price
