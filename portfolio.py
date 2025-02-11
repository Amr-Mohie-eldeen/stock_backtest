from typing import Dict, Optional
import logging
from dataclasses import dataclass, field

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents a single position in the portfolio"""

    symbol: str
    size: int
    entry_price: float
    current_price: float = field(default=0.0)

    def __post_init__(self):
        """Validate position data"""
        try:
            if not isinstance(self.symbol, str) or not self.symbol.strip():
                raise ValueError("Symbol must be a non-empty string")
            if not isinstance(self.size, int) or self.size <= 0:
                raise ValueError("Size must be a positive integer")
            if not isinstance(self.entry_price, (int, float)) or self.entry_price <= 0:
                raise ValueError("Entry price must be a positive number")
            if (
                not isinstance(self.current_price, (int, float))
                or self.current_price < 0
            ):
                raise ValueError("Current price must be a non-negative number")
        except Exception as e:
            logger.error(f"Error validating position: {e}")
            raise

    def update_price(self, price: float) -> None:
        """Update the current price of the position"""
        try:
            if not isinstance(price, (int, float)) or price <= 0:
                raise ValueError(f"Invalid price update: {price}")
            self.current_price = price
        except Exception as e:
            logger.error(f"Error updating position price: {e}")
            raise

    def get_value(self) -> float:
        """Calculate the current value of the position"""
        try:
            return self.size * self.current_price
        except Exception as e:
            logger.error(f"Error calculating position value: {e}")
            return 0.0

    def get_unrealized_pnl(self) -> float:
        """Calculate unrealized profit/loss"""
        try:
            return self.size * (self.current_price - self.entry_price)
        except Exception as e:
            logger.error(f"Error calculating unrealized PnL: {e}")
            return 0.0


class PortfolioManager:
    """Manages portfolio positions and risk"""

    def __init__(self, max_positions: int, position_size_per_trade: float):
        """Initialize portfolio manager"""
        try:
            if not isinstance(max_positions, int) or max_positions <= 0:
                raise ValueError("max_positions must be a positive integer")
            if (
                not isinstance(position_size_per_trade, float)
                or not 0 < position_size_per_trade <= 1
            ):
                raise ValueError(
                    "position_size_per_trade must be a float between 0 and 1"
                )

            self.max_positions = max_positions
            self.position_size_per_trade = position_size_per_trade
            self.positions: Dict[str, Position] = {}
            logger.info("Portfolio manager initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing portfolio manager: {e}")
            raise

    def add_position(self, symbol: str, size: int, entry_price: float) -> bool:
        """Add a new position to the portfolio"""
        try:
            # Validate inputs
            if not isinstance(symbol, str) or not symbol.strip():
                raise ValueError(f"Invalid symbol: {symbol}")
            if not isinstance(size, int) or size <= 0:
                raise ValueError(f"Invalid size: {size}")
            if not isinstance(entry_price, (int, float)) or entry_price <= 0:
                raise ValueError(f"Invalid entry price: {entry_price}")

            # Check position limits
            if len(self.positions) >= self.max_positions:
                logger.warning(
                    f"Cannot add position for {symbol}: Maximum positions reached"
                )
                return False

            # Add position
            self.positions[symbol] = Position(
                symbol=symbol,
                size=size,
                entry_price=entry_price,
                current_price=entry_price,
            )
            logger.info(f"Added position: {symbol} x {size} @ ${entry_price:.2f}")
            return True

        except Exception as e:
            logger.error(f"Error adding position for {symbol}: {e}")
            return False

    def remove_position(self, symbol: str) -> bool:
        """Remove a position from the portfolio"""
        try:
            if not isinstance(symbol, str) or not symbol.strip():
                raise ValueError(f"Invalid symbol: {symbol}")

            if symbol in self.positions:
                position = self.positions.pop(symbol)
                logger.info(f"Removed position: {symbol} x {position.size}")
                return True
            else:
                logger.warning(f"Position not found: {symbol}")
                return False

        except Exception as e:
            logger.error(f"Error removing position for {symbol}: {e}")
            return False

    def update_position(self, symbol: str, current_price: float) -> bool:
        """Update the current price of a position"""
        try:
            if not isinstance(symbol, str) or not symbol.strip():
                raise ValueError(f"Invalid symbol: {symbol}")
            if not isinstance(current_price, (int, float)) or current_price <= 0:
                raise ValueError(f"Invalid price: {current_price}")

            if symbol in self.positions:
                self.positions[symbol].update_price(current_price)
                return True
            return False

        except Exception as e:
            logger.error(f"Error updating position for {symbol}: {e}")
            return False

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get a specific position"""
        try:
            if not isinstance(symbol, str) or not symbol.strip():
                raise ValueError(f"Invalid symbol: {symbol}")
            return self.positions.get(symbol)
        except Exception as e:
            logger.error(f"Error getting position for {symbol}: {e}")
            return None

    def get_total_value(self) -> float:
        """Calculate total portfolio value"""
        try:
            return sum(position.get_value() for position in self.positions.values())
        except Exception as e:
            logger.error(f"Error calculating total portfolio value: {e}")
            return 0.0

    def get_position_count(self) -> int:
        """Get number of current positions"""
        try:
            return len(self.positions)
        except Exception as e:
            logger.error(f"Error getting position count: {e}")
            return 0
