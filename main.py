import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging
import sys

from models import BacktestConfig
from backtest import BacktestEnvironment, BacktestResults
from loggers import FileTradeLogger
from trackers import DefaultTradeTracker
from strategies import ImprovedStrategy, EnhancedStrategy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("backtest.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main():
    """Main execution function"""
    try:
        # Set Matplotlib style
        plt.style.use("seaborn-v0_8-darkgrid")

        # Create configuration
        try:
            config = BacktestConfig(
                symbols=["AAPL", "MSFT", "GOOGL", "AMZN"],
                start_date=datetime.now() - timedelta(days=365 * 4),
                end_date=datetime.now(),
                starting_cash=100000,
                position_size_per_trade=0.1,  # 10% per trade
                max_positions=5,
                debug_mode=True,
                strategy_class=EnhancedStrategy,
            )
            logger.info("Configuration created successfully")
        except Exception as e:
            logger.error(f"Error creating configuration: {e}")
            return

        # Initialize dependencies
        try:
            logger_component = FileTradeLogger(
                filename="trading.log", debug=config.debug_mode
            )
            tracker = DefaultTradeTracker()
            logger.info("Components initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            return

        # Setup and run backtest
        try:
            backtest = BacktestEnvironment(config, logger_component, tracker)
            backtest.setup()
            strategy, final_value = backtest.run()
            logger.info(f"Backtest completed. Final value: ${final_value:,.2f}")
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return

        # Analyze and display results
        try:
            results = BacktestResults(
                config.starting_cash,
                final_value,
                tracker,
                backtest.data_dfs,
                backtest.benchmark_df,
            )
            results.print_summary()
            results.plot_results()
            logger.info("Results displayed successfully")
        except Exception as e:
            logger.error(f"Error displaying results: {e}")

    except Exception as e:
        logger.error(f"Critical error in main execution: {e}")
    finally:
        plt.close("all")  # Clean up any open plots


if __name__ == "__main__":
    main()
