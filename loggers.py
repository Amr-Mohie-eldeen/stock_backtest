import os
import logging
from typing import Protocol, Optional, runtime_checkable
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime as dt

# Configure root logger
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors in terminal
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@dataclass
class TradeInfo:
    """Data class for storing trade information"""

    action: str
    price: float
    size: int
    value: float
    commission: float
    datetime: dt


@runtime_checkable
class TradeLogger(Protocol):
    """Protocol for trade logging"""

    def log_trade(self, message: str) -> None:
        """Log a trade message"""
        ...


class FileTradeLogger:
    """File-based trade logger implementation"""

    def __init__(self, filename: str = "trading.log", debug: bool = False):
        try:
            self.debug = debug

            # Create logger with unique name
            self.logger = logging.getLogger(f"{__name__}.{id(self)}")
            self.logger.setLevel(logging.DEBUG if debug else logging.INFO)

            # Prevent duplicate logging
            self.logger.propagate = False

            # Ensure log directory exists
            os.makedirs(
                os.path.dirname(filename) if os.path.dirname(filename) else ".",
                exist_ok=True,
            )

            # File handler
            fh = logging.FileHandler(filename)
            fh.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            )
            self.logger.addHandler(fh)

        except Exception as e:
            print(f"Error initializing logger: {e}")
            raise

    def log_trade(self, message: str) -> None:
        """Log a trade message"""
        try:
            if not isinstance(message, str):
                raise ValueError("Message must be a string")

            timestamp = dt.now().strftime("%Y-%m-%d %H:%M:%S")
            self.logger.info(f"{timestamp} - {message}")

            if self.debug:
                # Only print to terminal if debug is True
                print(f"TRADE: {message}")

        except Exception as e:
            print(f"Error logging trade: {e}")

    def error(self, message: str) -> None:
        """Log an error message"""
        try:
            self.logger.error(message)
            if self.debug:
                print(f"ERROR: {message}")
        except Exception as e:
            print(f"Error logging error message: {e}")

    def warning(self, message: str) -> None:
        """Log a warning message"""
        try:
            self.logger.warning(message)
            if self.debug:
                print(f"WARNING: {message}")
        except Exception as e:
            print(f"Error logging warning message: {e}")

    def info(self, message: str) -> None:
        """Log an info message"""
        try:
            self.logger.info(message)
            if self.debug:
                print(f"INFO: {message}")
        except Exception as e:
            print(f"Error logging info message: {e}")

    def log_summary(self, summary: str) -> None:
        """Log a summary message"""
        self.logger.info("\n" + summary + "\n")

    def log_error(self, error: str) -> None:
        """
        Log an error message.

        Parameters:
        -----------
        error : str
            The error message to log
        """
        self.logger.error(error)

    def log_debug(self, message: str) -> None:
        """
        Log a debug message if debug mode is enabled.

        Parameters:
        -----------
        message : str
            The debug message to log
        """
        if self.debug:
            self.logger.debug(message)

    def log_trade_execution(self, trade_info: TradeInfo) -> None:
        """
        Log details of a trade execution.

        Parameters:
        -----------
        trade_info : TradeInfo
            Information about the executed trade
        """
        message = (
            f"{trade_info.action} EXECUTED - "
            f"Price: {trade_info.price:.2f}, "
            f"Size: {trade_info.size} shares, "
            f"Value: {trade_info.value:.2f}, "
            f"Commission: {trade_info.commission:.2f}"
        )
        self.log_trade(message)

    def log_strategy_status(
        self, price: float, indicators: dict, conditions: dict
    ) -> None:
        """
        Log detailed strategy status including indicators and conditions.

        Parameters:
        -----------
        price : float
            Current price
        indicators : dict
            Dictionary of indicator values
        conditions : dict
            Dictionary of strategy conditions
        """
        if not self.debug:
            return

        indicator_str = ", ".join([f"{k}: {v:.2f}" for k, v in indicators.items()])
        condition_str = ", ".join([f"{k}: {v}" for k, v in conditions.items()])

        self.logger.debug(
            f"Price: {price:.2f}, "
            f"Indicators: {indicator_str}, "
            f"Conditions: {condition_str}"
        )

    def __del__(self):
        """Cleanup when logger is destroyed"""
        # Remove handlers to avoid file handle leaks
        if hasattr(self, "logger"):
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
