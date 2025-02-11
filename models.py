from dataclasses import dataclass
from datetime import datetime
from typing import List, Type, Optional
import logging
from strategies.base import BaseStrategy

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Configuration for backtest parameters"""

    symbols: List[str]
    start_date: datetime
    end_date: datetime
    starting_cash: float
    position_size_per_trade: float
    max_positions: int
    debug_mode: bool
    strategy_class: Type[BaseStrategy]

    def __post_init__(self):
        """Validate configuration after initialization"""
        try:
            # Validate symbols
            if not isinstance(self.symbols, list) or not self.symbols:
                raise ValueError("symbols must be a non-empty list of strings")
            if not all(isinstance(s, str) and s.strip() for s in self.symbols):
                raise ValueError("All symbols must be non-empty strings")
            self.symbols = [s.upper().strip() for s in self.symbols]

            # Validate dates
            if not isinstance(self.start_date, datetime):
                raise ValueError("start_date must be a datetime object")
            if not isinstance(self.end_date, datetime):
                raise ValueError("end_date must be a datetime object")
            if self.start_date >= self.end_date:
                raise ValueError("start_date must be before end_date")

            # Validate numeric parameters
            if (
                not isinstance(self.starting_cash, (int, float))
                or self.starting_cash <= 0
            ):
                raise ValueError("starting_cash must be a positive number")
            if (
                not isinstance(self.position_size_per_trade, float)
                or not 0 < self.position_size_per_trade <= 1
            ):
                raise ValueError(
                    "position_size_per_trade must be a float between 0 and 1"
                )
            if not isinstance(self.max_positions, int) or self.max_positions <= 0:
                raise ValueError("max_positions must be a positive integer")

            # Validate strategy class
            if not isinstance(self.strategy_class, type) or not issubclass(
                self.strategy_class, BaseStrategy
            ):
                raise ValueError("strategy_class must be a subclass of BaseStrategy")

            # Validate debug mode
            if not isinstance(self.debug_mode, bool):
                raise ValueError("debug_mode must be a boolean")

        except Exception as e:
            logger.error(f"Error validating backtest configuration: {e}")
            raise

    def get_timeframe_days(self) -> int:
        """Calculate the number of days in the backtest period"""
        try:
            delta = self.end_date - self.start_date
            return delta.days
        except Exception as e:
            logger.error(f"Error calculating timeframe: {e}")
            return 0

    def get_symbols_str(self) -> str:
        """Get a comma-separated string of symbols"""
        try:
            return ", ".join(self.symbols)
        except Exception as e:
            logger.error(f"Error formatting symbols: {e}")
            return ""

    def to_dict(self) -> dict:
        """Convert config to dictionary for serialization"""
        try:
            return {
                "symbols": self.symbols,
                "start_date": self.start_date.isoformat(),
                "end_date": self.end_date.isoformat(),
                "starting_cash": self.starting_cash,
                "position_size_per_trade": self.position_size_per_trade,
                "max_positions": self.max_positions,
                "debug_mode": self.debug_mode,
                "strategy_name": self.strategy_class.__name__,
            }
        except Exception as e:
            logger.error(f"Error converting config to dict: {e}")
            return {}

    @classmethod
    def from_dict(cls, data: dict) -> Optional["BacktestConfig"]:
        """Create config from dictionary"""
        try:
            # Import strategy dynamically
            strategy_name = data.get("strategy_name", "")
            strategy_module = __import__(
                f"strategies.{strategy_name.lower()}", fromlist=[strategy_name]
            )
            strategy_class = getattr(strategy_module, strategy_name)

            return cls(
                symbols=data["symbols"],
                start_date=datetime.fromisoformat(data["start_date"]),
                end_date=datetime.fromisoformat(data["end_date"]),
                starting_cash=float(data["starting_cash"]),
                position_size_per_trade=float(data["position_size_per_trade"]),
                max_positions=int(data["max_positions"]),
                debug_mode=bool(data["debug_mode"]),
                strategy_class=strategy_class,
            )
        except Exception as e:
            logger.error(f"Error creating config from dict: {e}")
            return None
