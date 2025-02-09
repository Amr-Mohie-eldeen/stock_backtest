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


class BacktestEnvironment:
    """Handles backtest environment setup and execution"""

    def __init__(
        self, config: BacktestConfig, logger: TradeLogger, tracker: TradeTracker
    ):
        self.config = config
        self.logger = logger
        self.tracker = tracker
        self.cerebro = bt.Cerebro()
        self.data_df = None

    def setup(self) -> None:
        """Set up the backtest environment"""
        # Fetch and prepare data
        self.data_df = fetch_stock_data(
            self.config.symbol, self.config.start_date, self.config.end_date
        )
        self.data_df = prepare_backtest_data(self.data_df)

        # Add strategy with dependencies
        self.cerebro.addstrategy(
            self.config.strategy_class,
            logger=self.logger,
            tracker=self.tracker,
            debug=self.config.debug_mode,
        )

        # Add data and set broker parameters
        data = bt.feeds.PandasData(dataname=self.data_df)
        self.cerebro.adddata(data)
        self.cerebro.broker.setcash(self.config.starting_cash)
        self.cerebro.broker.setcommission(commission=self.config.commission)

    def run(self) -> Tuple[BaseStrategy, float]:
        """Run the backtest"""
        print("\nStarting Backtest...")
        results = self.cerebro.run()
        return results[0], self.cerebro.broker.getvalue()


class BacktestResults:
    """Handles backtest result analysis and presentation"""

    def __init__(
        self,
        starting_cash: float,
        final_value: float,
        tracker: TradeTracker,
        data_df: pd.DataFrame,
    ):
        self.starting_cash = starting_cash
        self.final_value = final_value
        self.tracker = tracker
        self.data_df = data_df

    def print_summary(self) -> None:
        """Print backtest results summary"""
        returns = (self.final_value - self.starting_cash) / self.starting_cash * 100
        print(f"\nFinal Portfolio Value: ${self.final_value:,.2f}")
        print(f"Return: {returns:.2f}%")
        print(f"Number of Trades: {self.tracker.trade_count}")

    def plot_results(self) -> None:
        """Create and display result plots"""
        fig = create_trading_plots(
            self.data_df, self.tracker, self.starting_cash, self.final_value
        )
        plt.show()
