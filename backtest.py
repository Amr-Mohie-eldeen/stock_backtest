from typing import Tuple
import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt

from models import BacktestConfig
from loggers import TradeLogger
from trackers import TradeTracker
from strategies import BaseStrategy
from plot_utils import create_trading_plots
from data_utils import fetch_stock_data, prepare_backtest_data
from portfolio import PortfolioManager


class BacktestEnvironment:
    """Handles backtest environment setup and execution"""

    def __init__(
        self, config: BacktestConfig, logger: TradeLogger, tracker: TradeTracker
    ):
        self.config = config
        self.logger = logger
        self.tracker = tracker
        self.cerebro = bt.Cerebro()
        self.data_dfs = {}
        self.benchmark_df = None

    def setup(self) -> None:
        """Set up the backtest environment"""
        # Set initial cash
        self.cerebro.broker.setcash(self.config.starting_cash)

        # Fetch and prepare data for all symbols
        for symbol in self.config.symbols:
            df = fetch_stock_data(symbol, self.config.start_date, self.config.end_date)
            if df is not None:
                self.data_dfs[symbol] = prepare_backtest_data(df)
                # Add data feed for the stock
                data = bt.feeds.PandasData(dataname=self.data_dfs[symbol], name=symbol)
                self.cerebro.adddata(data)

        # Fetch benchmark data and add it as the last data feed
        self.benchmark_df = fetch_stock_data(
            "SPY", self.config.start_date, self.config.end_date
        )
        if self.benchmark_df is not None:
            self.benchmark_df = prepare_backtest_data(self.benchmark_df)
            benchmark_data = bt.feeds.PandasData(dataname=self.benchmark_df, name="SPY")
            self.cerebro.adddata(benchmark_data)

        # Initialize portfolio manager
        portfolio_manager = PortfolioManager(
            max_positions=self.config.max_positions,
            position_size_per_trade=self.config.position_size_per_trade,
        )

        # Add strategy with dependencies
        self.cerebro.addstrategy(
            self.config.strategy_class,
            portfolio_manager=portfolio_manager,
            logger=self.logger,
            tracker=self.tracker,
            debug=self.config.debug_mode,
        )

    def run(self) -> Tuple[BaseStrategy, float]:
        """Run the backtest"""
        # Run the backtest
        results = self.cerebro.run()
        strategy = results[0]

        # Get final portfolio value
        final_value = self.cerebro.broker.getvalue()

        return strategy, final_value


class BacktestResults:
    """Handles analysis and visualization of backtest results"""

    def __init__(
        self,
        starting_cash: float,
        final_value: float,
        tracker: TradeTracker,
        data_dfs: dict,
        benchmark_df: pd.DataFrame,
    ):
        self.starting_cash = starting_cash
        self.final_value = final_value
        self.tracker = tracker
        self.data_dfs = data_dfs
        self.benchmark_df = benchmark_df

    def print_summary(self) -> None:
        """Print performance summary"""
        returns = (self.final_value - self.starting_cash) / self.starting_cash * 100
        metrics = self.tracker.get_performance_metrics()

        print("\n=== Trading Summary ===")
        print(f"Starting Value: ${self.starting_cash:,.2f}")
        print(f"Final Value: ${self.final_value:,.2f}")
        print(f"Return: {returns:.2f}%")
        print(f"Total Trades: {metrics['total_trades']}")
        print(f"Winning Trades: {metrics['winning_trades']}")
        print(f"Losing Trades: {metrics['losing_trades']}")
        print(f"Win Rate: {metrics['win_rate']:.2f}%")
        print("====================")

    def plot_results(self) -> None:
        """Create and display result plots"""
        create_trading_plots(
            self.data_dfs,
            self.benchmark_df,
            self.tracker,
            self.starting_cash,
            self.final_value,
        )
        plt.show()
