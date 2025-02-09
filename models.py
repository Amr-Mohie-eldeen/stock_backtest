from dataclasses import dataclass
from datetime import datetime
from typing import Type
from strategies import BaseStrategy, EnhancedStrategy


@dataclass
class BacktestConfig:
    """Configuration for backtest parameters"""

    symbol: str
    start_date: datetime
    end_date: datetime
    starting_cash: float
    commission: float = 0.001
    debug_mode: bool = False
    strategy_class: Type[BaseStrategy] = EnhancedStrategy
