from typing import Tuple, Optional, Dict
import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt
import logging
from datetime import datetime

from models import BacktestConfig
from loggers import TradeLogger
from trackers import TradeTracker
from strategies import BaseStrategy
from plot_utils import create_trading_plots
from data_utils import fetch_stock_data, prepare_backtest_data
from portfolio import PortfolioManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BacktestEnvironment:
    """Handles backtest environment setup and execution"""

    def __init__(
        self, config: BacktestConfig, logger: TradeLogger, tracker: TradeTracker
    ):
        try:
            if not isinstance(config, BacktestConfig):
                raise ValueError("Invalid config object")
            if not isinstance(tracker, TradeTracker):
                raise ValueError("Invalid tracker object")

            self.config = config
            self.logger = logger
            self.tracker = tracker
            self.cerebro = bt.Cerebro()
            self.data_dfs: Dict[str, pd.DataFrame] = {}
            self.benchmark_df: Optional[pd.DataFrame] = None

        except Exception as e:
            print(f"Error initializing backtest environment: {e}")
            raise

    def setup(self) -> None:
        """Set up the backtest environment"""
        try:
            # Set initial cash
            if self.config.starting_cash <= 0:
                raise ValueError("Starting cash must be positive")
            self.cerebro.broker.setcash(self.config.starting_cash)

            # Fetch and prepare data for all symbols
            if not self.config.symbols:
                raise ValueError("No symbols provided for backtesting")

            for symbol in self.config.symbols:
                try:
                    df = fetch_stock_data(
                        symbol, self.config.start_date, self.config.end_date
                    )
                    if df is None:
                        logger.warning(f"No data available for {symbol}, skipping")
                        continue

                    prepared_df = prepare_backtest_data(df)
                    if prepared_df is None:
                        logger.warning(f"Failed to prepare data for {symbol}, skipping")
                        continue

                    self.data_dfs[symbol] = prepared_df
                    data = bt.feeds.PandasData(
                        dataname=self.data_dfs[symbol], name=symbol
                    )
                    self.cerebro.adddata(data)
                    logger.info(f"Successfully added data for {symbol}")

                except Exception as e:
                    logger.error(f"Error processing symbol {symbol}: {e}")
                    continue

            if not self.data_dfs:
                raise ValueError("No valid data available for any symbol")

            # Fetch benchmark data and add it as the last data feed
            self.benchmark_df = fetch_stock_data(
                "SPY", self.config.start_date, self.config.end_date
            )
            if self.benchmark_df is None:
                logger.warning("No benchmark data available")
            else:
                self.benchmark_df = prepare_backtest_data(self.benchmark_df)
                benchmark_data = bt.feeds.PandasData(
                    dataname=self.benchmark_df, name="SPY"
                )
                self.cerebro.adddata(benchmark_data)

            # Initialize portfolio manager
            try:
                portfolio_manager = PortfolioManager(
                    max_positions=self.config.max_positions,
                    position_size_per_trade=self.config.position_size_per_trade,
                )
            except Exception as e:
                logger.error(f"Error initializing portfolio manager: {e}")
                raise

            # Add strategy with required components
            try:
                strategy_kwargs = {
                    "debug": self.config.debug_mode,
                    "logger": self.logger,
                    "tracker": self.tracker,
                    "portfolio_manager": portfolio_manager,
                }

                self.cerebro.addstrategy(self.config.strategy_class, **strategy_kwargs)
                logger.info("Strategy added successfully with all components")

            except Exception as e:
                logger.error(f"Error adding strategy: {e}")
                raise

        except Exception as e:
            logger.error(f"Error in setup: {e}")
            raise

    def run(self) -> Tuple[BaseStrategy, float]:
        """Run the backtest"""
        try:
            if not self.data_dfs:
                raise ValueError("No data available for backtesting")

            # Run the backtest
            strategies = self.cerebro.run()
            if not strategies:
                raise RuntimeError("Backtest failed to generate strategies")

            strategy = strategies[0]
            final_value = self.cerebro.broker.getvalue()

            logger.info(
                f"Backtest completed. Final portfolio value: ${final_value:,.2f}"
            )
            return strategy, final_value

        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            raise


class BacktestResults:
    """Handles analysis and visualization of backtest results"""

    def __init__(
        self,
        starting_cash: float,
        final_value: float,
        tracker: TradeTracker,
        data_dfs: Dict[str, pd.DataFrame],
        benchmark_df: Optional[pd.DataFrame],
    ):
        try:
            # Validate inputs
            if not isinstance(starting_cash, (int, float)) or starting_cash <= 0:
                raise ValueError("Invalid starting cash value")
            if not isinstance(final_value, (int, float)):
                raise ValueError("Invalid final value")
            if not isinstance(tracker, TradeTracker):
                raise ValueError("Invalid tracker object")
            if not isinstance(data_dfs, dict) or not data_dfs:
                raise ValueError("Invalid or empty data_dfs")

            self.starting_cash = starting_cash
            self.final_value = final_value
            self.tracker = tracker
            self.data_dfs = data_dfs
            self.benchmark_df = benchmark_df

        except Exception as e:
            logger.error(f"Error initializing backtest results: {e}")
            raise

    def print_summary(self) -> None:
        """Print performance summary"""
        try:
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

        except Exception as e:
            logger.error(f"Error printing summary: {e}")
            print("Error generating trading summary")

    def plot_results(self) -> None:
        """Create and display result plots"""
        try:
            create_trading_plots(
                self.data_dfs,
                self.benchmark_df,
                self.tracker,
                self.starting_cash,
                self.final_value,
            )
        except Exception as e:
            logger.error(f"Error creating plots: {e}")
            print("Error generating trading plots")
