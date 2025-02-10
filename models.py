from dataclasses import dataclass
from datetime import datetime
from typing import Type
from strategies import BaseStrategy, EnhancedStrategy


@dataclass
class BacktestConfig:
    """Configuration for backtest parameters"""

    symbols: list[str]
    start_date: datetime
    end_date: datetime
    starting_cash: float
    position_size_per_trade: float = 0.1
    max_positions: int = 5
    commission: float = 0.001
    debug_mode: bool = False
    strategy_class: Type[BaseStrategy] = EnhancedStrategy
    benchmark_symbol: str = "^GSPC"
