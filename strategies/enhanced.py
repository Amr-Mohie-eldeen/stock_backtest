import backtrader as bt
from typing import Dict
import logging

from .base import BaseStrategy

logger = logging.getLogger(__name__)


class EnhancedStrategy(BaseStrategy):
    """Enhanced trading strategy with multiple technical indicators"""

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
            # Initialize indicators dictionary for each symbol
            self.indicators: Dict[str, Dict] = {}

            for data in self.datas:
                symbol = data._name
                self.indicators[symbol] = {
                    "sma20": bt.indicators.SimpleMovingAverage(data.close, period=20),
                    "sma50": bt.indicators.SimpleMovingAverage(data.close, period=50),
                    "rsi": bt.indicators.RelativeStrengthIndex(data.close, period=14),
                    "macd": bt.indicators.MACD(data.close),
                    "bbands": bt.indicators.BollingerBands(data.close, period=20),
                }

                if self.p.debug:
                    self.logger.info(f"Initialized indicators for {symbol}")

        except Exception as e:
            self.logger.error(f"Error initializing EnhancedStrategy: {e}")
            raise

    def next(self):
        """Implement enhanced trading logic"""
        try:
            for data in self.datas:
                symbol = data._name
                position = self.getposition(data)

                if not self.orders.get(symbol) and not position:
                    self._check_buy_signals(data, symbol)
                elif position:
                    self._check_sell_signals(data, symbol)

        except Exception as e:
            self.logger.error(f"Error in next(): {e}")

    def _check_buy_signals(self, data, symbol: str):
        """Check buy signals"""
        try:
            indicators = self.indicators[symbol]

            # Price crosses above SMA20
            price_cross_up = (
                data.close[0] > indicators["sma20"][0]
                and data.close[-1] <= indicators["sma20"][-1]
            )

            # RSI shows upward momentum
            rsi_momentum = (
                indicators["rsi"][0] > indicators["rsi"][-1]
                and indicators["rsi"][0] < 70  # Not overbought
            )

            # MACD line crosses above signal line
            macd_crossover = (
                indicators["macd"].macd[0] > indicators["macd"].signal[0]
                and indicators["macd"].macd[-1] <= indicators["macd"].signal[-1]
            )

            # Price bounces off lower Bollinger Band
            bb_bounce = (
                data.close[-1] <= indicators["bbands"].lines.bot[-1]
                and data.close[0] > indicators["bbands"].lines.bot[0]
            )

            # Buy if any two signals are true
            signals = [price_cross_up, rsi_momentum, macd_crossover, bb_bounce]
            if sum(signals) >= 2:
                self.buy_stock(data)
                if self.p.debug:
                    self.logger.info(
                        f"Buy signal for {symbol}: Price={data.close[0]:.2f}"
                    )

        except Exception as e:
            self.logger.error(f"Error checking buy signals for {symbol}: {e}")

    def _check_sell_signals(self, data, symbol: str):
        """Check sell signals"""
        try:
            indicators = self.indicators[symbol]

            # Price crosses below SMA20
            price_cross_down = (
                data.close[0] < indicators["sma20"][0]
                and data.close[-1] >= indicators["sma20"][-1]
            )

            # RSI shows downward momentum
            rsi_momentum = (
                indicators["rsi"][0] < indicators["rsi"][-1]
                and indicators["rsi"][0] > 30  # Not oversold
            )

            # MACD line crosses below signal line
            macd_crossunder = (
                indicators["macd"].macd[0] < indicators["macd"].signal[0]
                and indicators["macd"].macd[-1] >= indicators["macd"].signal[-1]
            )

            # Price hits upper Bollinger Band
            bb_resistance = data.close[0] >= indicators["bbands"].lines.top[0]

            # Sell if any two signals are true
            signals = [price_cross_down, rsi_momentum, macd_crossunder, bb_resistance]
            if sum(signals) >= 2:
                self.sell_stock(data)
                if self.p.debug:
                    self.logger.info(
                        f"Sell signal for {symbol}: Price={data.close[0]:.2f}"
                    )

        except Exception as e:
            self.logger.error(f"Error checking sell signals for {symbol}: {e}")

    def log_debug_entry(self, price):
        """Log entry conditions for debugging"""
        if not self.p.debug:
            return
