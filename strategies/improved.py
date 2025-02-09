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
    )

    def __init__(self):
        super().__init__()
        self.order = None
        self.buy_price = None
        self.stop_price = None

    def next(self):
        if self.order:
            return

        price = self.data.close[0]

        # Log entry conditions for debugging
        self.log_debug_entry(price)

        if not self.position:
            # Entry conditions
            trend_up = price > self.sma[0]
            oversold = self.rsi[0] < 30
            macd_positive = self.macd.lines.macd[0] > self.macd.lines.signal[0]

            if trend_up and oversold and macd_positive:
                # Calculate position size and stop loss
                cash = self.broker.getcash()
                value = self.broker.getvalue()
                risk_amount = value * self.p.stop_loss
                stop_distance = price * self.p.stop_loss
                position_size = int((cash * self.p.position_size) / price)

                self.buy_price = price
                self.stop_price = price - stop_distance
                self.order = self.buy(size=position_size)
                if self.p.debug:
                    self.logger.log_trade(
                        f"BUY CREATE at {price:.2f}, Size: {position_size} shares"
                    )

        else:
            # Exit conditions
            target_price = self.buy_price * (1 + self.p.take_profit)
            exit_condition = (
                price >= target_price or price <= self.stop_price or self.rsi[0] > 75
            )

            # Log exit conditions for debugging
            self.log_debug_exit(price, self.stop_price, target_price)

            if exit_condition:
                self.order = self.sell(size=self.position.size)
                if self.p.debug:
                    self.logger.log_trade(
                        f"SELL CREATE at {price:.2f}, Size: {self.position.size} shares"
                    )
                self.stop_price = None
