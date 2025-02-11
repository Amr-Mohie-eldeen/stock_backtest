import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import Union, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_stock_data(
    symbol: str, start_date: Union[str, datetime], end_date: Union[str, datetime]
) -> Optional[pd.DataFrame]:
    """
    Fetch stock data from Yahoo Finance

    Parameters:
    -----------
    symbol : str
        Stock symbol (e.g., 'AAPL')
    start_date : Union[str, datetime]
        Start date for data fetch
    end_date : Union[str, datetime]
        End date for data fetch

    Returns:
    --------
    Optional[pd.DataFrame]
        DataFrame with OHLCV data or None if fetch fails
    """
    try:
        # Input validation
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("Invalid symbol provided")

        if not start_date or not end_date:
            raise ValueError("Start and end dates must be provided")

        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)

        if start_date >= end_date:
            raise ValueError("Start date must be before end date")

        # Fetch data
        logger.info(f"Fetching data for {symbol}")
        df = yf.download(symbol, start=start_date, end=end_date)

        if df.empty:
            logger.warning(f"No data retrieved for {symbol}")
            return None

        # Handle tuple column names
        df.columns = [
            col[0].lower() if isinstance(col, tuple) else col.lower()
            for col in df.columns
        ]

        # Validate required columns
        required_cols = ["open", "high", "low", "close", "volume"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")

        return df

    except pd.errors.ParserError as e:
        logger.error(f"Error parsing dates: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return None


def prepare_backtest_data(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Prepare data for backtesting

    Parameters:
    -----------
    df : pd.DataFrame
        Raw OHLCV data

    Returns:
    --------
    Optional[pd.DataFrame]
        Processed DataFrame ready for backtesting or None if processing fails
    """
    try:
        if df is None or df.empty:
            raise ValueError("Input DataFrame is empty or None")

        # Make a copy to avoid modifying the original
        df = df.copy()

        # Ensure index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        # Check for invalid dates
        if df.index.isnull().any():
            raise ValueError("DataFrame contains invalid dates")

        # Sort by date
        df.sort_index(inplace=True)

        # Check for and handle missing values
        if df.isnull().any().any():
            logger.warning(f"Found {df.isnull().sum().sum()} missing values")
            df.dropna(inplace=True)

        if df.empty:
            raise ValueError("DataFrame is empty after removing missing values")

        # Ensure all numeric columns are float64
        numeric_columns = ["open", "high", "low", "close", "volume"]
        for col in numeric_columns:
            if col in df.columns:
                try:
                    df[col] = df[col].astype("float64")
                except Exception as e:
                    logger.error(f"Error converting {col} to float64: {e}")
                    raise ValueError(f"Invalid data in {col} column")

        # Validate data integrity
        if (df["high"] < df["low"]).any():
            raise ValueError("Found high prices lower than low prices")
        if (df["close"] < 0).any() or (df["volume"] < 0).any():
            raise ValueError("Found negative prices or volumes")

        return df

    except Exception as e:
        logger.error(f"Error preparing backtest data: {e}")
        return None
