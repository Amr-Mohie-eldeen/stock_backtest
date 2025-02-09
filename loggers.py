import os
import logging
import datetime
from typing import Protocol, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TradeInfo:
    """Data class for storing trade information"""

    action: str
    price: float
    size: int
    value: float
    commission: float
    datetime: datetime.date


class TradeLogger(Protocol):
    """Protocol defining the interface for trade loggers"""

    def log_trade(self, message: str, dt: Optional[datetime.date] = None) -> None:
        """Log a trade-related message"""
        pass

    def log_summary(self, summary: str) -> None:
        """Log a summary message"""
        pass

    def log_error(self, error: str) -> None:
        """Log an error message"""
        pass

    def log_debug(self, message: str) -> None:
        """Log a debug message"""
        pass


class FileTradeLogger:
    """Implementation of a file-based trade logger"""

    def __init__(self, filename: str = "trading.log", debug: bool = False):
        """
        Initialize the logger with specified filename and debug mode.

        Parameters:
        -----------
        filename : str
            Name of the log file
        debug : bool
            Whether to enable debug logging
        """
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # Full path to log file
        self.log_path = log_dir / filename

        # Remove existing log file
        if os.path.exists(self.log_path):
            os.remove(self.log_path)

        # Set up logger
        self.logger = logging.getLogger("TradingLog")
        self.logger.propagate = False
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)

        # Create and configure file handler
        fh = logging.FileHandler(self.log_path)
        fh.setLevel(logging.DEBUG if debug else logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(message)s")
        fh.setFormatter(formatter)

        # Add handler to logger
        self.logger.addHandler(fh)

        # Log session start
        self.logger.info("=== New Trading Session Started ===")
        self.debug_mode = debug

    def log_trade(self, message: str, dt: Optional[datetime.date] = None) -> None:
        """
        Log a trade-related message.

        Parameters:
        -----------
        message : str
            The message to log
        dt : Optional[datetime.date]
            The date of the trade (optional)
        """
        if dt:
            self.logger.info(f"{dt}: {message}")
        else:
            self.logger.info(message)

    def log_summary(self, summary: str) -> None:
        """
        Log a summary message.

        Parameters:
        -----------
        summary : str
            The summary message to log
        """
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
        if self.debug_mode:
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
        self.log_trade(message, trade_info.datetime)

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
        if not self.debug_mode:
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
