# Stock Trading Strategy Backtester

A professional-grade backtesting framework for evaluating stock trading strategies using technical indicators and historical data.

## Features

- **Multiple Trading Strategies**
  - Enhanced Strategy with multi-indicator approach
  - Improved Strategy focused on pullback trading
  - Extensible base strategy class for custom implementations

- **Advanced Technical Indicators**
  - Moving Averages (SMA)
  - Relative Strength Index (RSI)
  - MACD (Moving Average Convergence Divergence)
  - Stochastic Oscillator

- **Comprehensive Analysis**
  - Real-time trade logging
  - Performance metrics tracking
  - Interactive visualization
  - Risk management features

- **Interactive Visualization**
  - Price charts with buy/sell signals
  - Equity curve comparison
  - Zoom functionality
  - Custom date range selection

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/stock-backtest.git
cd stock-backtest
```

2. Create and activate a virtual environment:
```
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```
pip install -r requirements.txt
```

## Usage

1. Basic usage with default settings:
```
from datetime import datetime, timedelta
from models import BacktestConfig
from backtest import BacktestEnvironment
from strategies import EnhancedStrategy

# Configure backtest
config = BacktestConfig(
    symbol="AAPL",
    start_date=datetime.now() - timedelta(days=365),
    end_date=datetime.now(),
    starting_cash=100000,
    strategy_class=EnhancedStrategy
)

# Run backtest
backtest = BacktestEnvironment(config)
backtest.run()
```

2. Run the example script:
```
python main.py
```

## Project Structure

```
stock-backtest/
├── backtest.py      # Core backtesting engine
├── strategies/      # Trading strategies
│   ├── base.py     # Base strategy class
│   ├── enhanced.py # Multi-indicator strategy
│   └── improved.py # Pullback trading strategy
├── data_utils.py   # Data fetching and processing
├── plot_utils.py   # Visualization tools
├── loggers.py      # Trade logging
├── trackers.py     # Performance tracking
└── models.py       # Data models and config
```

## Configuration

The `BacktestConfig` class supports the following parameters:

- `symbol`: Stock ticker symbol (e.g., "AAPL")
- `start_date`: Backtest start date
- `end_date`: Backtest end date
- `starting_cash`: Initial capital
- `commission`: Trading commission (default: 0.001)
- `debug_mode`: Enable detailed logging (default: False)
- `strategy_class`: Trading strategy class to use

## Development

1. Install development dependencies:
```
pip install -e ".[dev]"
```

2. Run type checking:
```
mypy .
```

3. Format code:
```
black .
isort .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.