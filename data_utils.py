import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import Union, Optional


def fetch_stock_data(
    symbol: str, start_date: Union[str, datetime], end_date: Union[str, datetime]
) -> pd.DataFrame:
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
    pd.DataFrame
        DataFrame with OHLCV data
    """
    df = yf.download(symbol, start=start_date, end=end_date)

    # Handle tuple column names by taking the first element
    df.columns = [
        col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns
    ]

    # Ensure all required columns exist
    required_cols = ["open", "high", "low", "close", "volume"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    return df


def prepare_backtest_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare data for backtesting

    Parameters:
    -----------
    df : pd.DataFrame
        Raw OHLCV data

    Returns:
    --------
    pd.DataFrame
        Processed DataFrame ready for backtesting
    """
    # Make a copy to avoid modifying the original
    df = df.copy()

    # Ensure index is datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # Sort by date
    df.sort_index(inplace=True)

    # Remove any missing values
    df.dropna(inplace=True)

    # Ensure all numeric columns are float64
    numeric_columns = ["open", "high", "low", "close", "volume"]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].astype("float64")

    return df
