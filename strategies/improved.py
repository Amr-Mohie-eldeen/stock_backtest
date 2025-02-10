from .base import BaseStrategy


class ImprovedStrategy(BaseStrategy):
    """Improved strategy for trading pullbacks"""

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
        self.orders = {}
        self.buy_prices = {}
        self.stop_prices = {}

    def next(self):
        # Skip the last data feed (benchmark)
        for data in self.datas[:-1]:
            symbol = data._name
            if symbol in self.orders and self.orders[symbol]:
                continue

            price = data.close[0]
            indicators = self.indicators[symbol]

            # Log entry conditions for debugging
            self.log_debug_entry(price)

            if not self.getposition(data):
                # Entry conditions
                trend_up = price > indicators["sma"][0]
                oversold = indicators["rsi"][0] < 30
                macd_positive = (
                    indicators["macd"].lines.macd[0]
                    > indicators["macd"].lines.signal[0]
                )

                if (
                    trend_up
                    and oversold
                    and macd_positive
                    and self.portfolio_manager.can_open_position(self.broker.getcash())
                ):
                    # Calculate position size using portfolio manager
                    position_size = self.portfolio_manager.calculate_position_size(
                        self.broker.getcash(), price
                    )

                    self.buy_prices[symbol] = price
                    self.stop_prices[symbol] = price * (1 - self.p.stop_loss)
                    self.orders[symbol] = self.buy(data=data, size=position_size)

                    if self.p.debug:
                        self.logger.log_trade(
                            f"{symbol} BUY CREATE at {price:.2f}, Size: {position_size} shares"
                        )

            else:
                # Exit conditions
                target_price = self.buy_prices[symbol] * (1 + self.p.take_profit)
                exit_condition = (
                    price >= target_price
                    or price <= self.stop_prices[symbol]
                    or indicators["rsi"][0] > 70
                    or indicators["macd"].lines.macd[0]
                    < indicators["macd"].lines.signal[0]
                )

                if exit_condition:
                    position = self.getposition(data)
                    self.orders[symbol] = self.sell(data=data, size=position.size)
                    if self.p.debug:
                        self.logger.log_trade(
                            f"{symbol} SELL CREATE at {price:.2f}, Size: {position.size} shares"
                        )
                    self.stop_prices[symbol] = None
