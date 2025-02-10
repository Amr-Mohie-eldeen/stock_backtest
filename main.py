import matplotlib.pyplot as plt
from datetime import datetime, timedelta

from models import BacktestConfig
from backtest import BacktestEnvironment, BacktestResults
from loggers import FileTradeLogger
from trackers import DefaultTradeTracker
from strategies import ImprovedStrategy, EnhancedStrategy


def main():
    # Set Matplotlib style
    plt.style.use("seaborn-v0_8-darkgrid")

    # Create configuration
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

    # Initialize dependencies
    logger = FileTradeLogger(filename="trading.log", debug=config.debug_mode)
    tracker = DefaultTradeTracker()

    # Setup and run backtest
    backtest = BacktestEnvironment(config, logger, tracker)
    backtest.setup()
    strategy, final_value = backtest.run()

    # Analyze and display results
    results = BacktestResults(
        config.starting_cash,
        final_value,
        tracker,
        backtest.data_dfs,
        backtest.benchmark_df,
    )
    results.print_summary()
    results.plot_results()


if __name__ == "__main__":
    main()
