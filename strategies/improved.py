import backtrader as bt
from typing import Dict
import logging

from .base import BaseStrategy

logger = logging.getLogger(__name__)


class ImprovedStrategy(BaseStrategy):
    """Improved trading strategy with additional logic"""

    params = (
        ("debug", False),
        ("stop_loss", 0.02),
        ("take_profit", 0.05),
        ("position_size", 0.95),
        ("logger", None),
        ("tracker", None),
        ("portfolio_manager", None),
    )

    def __init__(self):
        super().__init__()
        try:
            self.orders = {}
            self.buy_prices = {}
            self.stop_prices = {}

            # Initialize indicators dictionary for each symbol
            self.indicators: Dict[str, Dict] = {}

            for data in self.datas:
                symbol = data._name
                self.indicators[symbol] = {
                    "sma": bt.indicators.SimpleMovingAverage(data.close, period=30),
                    "ema": bt.indicators.ExponentialMovingAverage(
                        data.close, period=20
                    ),
                    "rsi": bt.indicators.RelativeStrengthIndex(data.close, period=14),
                }

                if self.p.debug:
                    self.logger.info(f"Initialized indicators for {symbol}")

        except Exception as e:
            logger.error(f"Error initializing ImprovedStrategy: {e}")
            raise

    def next(self):
        """Implement improved trading logic"""
        try:
            for data in self.datas:
                symbol = data._name
                position = self.getposition(data)

                if not self.orders.get(symbol) and not position:
                    self._check_buy_signals(data, symbol)
                elif position:
                    self._check_sell_signals(data, symbol)

        except Exception as e:
            logger.error(f"Error in next(): {e}")

    def _check_buy_signals(self, data, symbol: str):
        """Check buy signals"""
        try:
            indicators = self.indicators[symbol]

            # Buy conditions
            price_above_sma = data.close[0] > indicators["sma"][0]
            rsi_oversold = indicators["rsi"][0] < 30

            if price_above_sma and rsi_oversold:
                self.buy_stock(data)
                if self.p.debug:
                    self.logger.info(
                        f"Buy signal for {symbol}: Price={data.close[0]:.2f}"
                    )

        except Exception as e:
            logger.error(f"Error checking buy signals for {symbol}: {e}")

    def _check_sell_signals(self, data, symbol: str):
        """Check sell signals"""
        try:
            indicators = self.indicators[symbol]

            # Sell conditions
            price_below_ema = data.close[0] < indicators["ema"][0]
            rsi_overbought = indicators["rsi"][0] > 70

            if price_below_ema and rsi_overbought:
                self.sell_stock(data)
                if self.p.debug:
                    self.logger.info(
                        f"Sell signal for {symbol}: Price={data.close[0]:.2f}"
                    )

        except Exception as e:
            logger.error(f"Error checking sell signals for {symbol}: {e}")
