from .base import BaseStrategy


class EnhancedStrategy(BaseStrategy):
    """Enhanced strategy with multiple indicators"""

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
            # Enhanced entry conditions
            trend_up = price > self.sma[0]
            momentum_up = self.rsi[0] > 40
            rsi_condition = self.rsi[0] < 65
            positive_crossover = self.macd.lines.macd[0] > self.macd.lines.signal[0]
            stoch_oversold = self.stoch.lines.percD[0] < 60

            if (
                trend_up
                and momentum_up
                and rsi_condition
                and (positive_crossover or stoch_oversold)
            ):
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
            # Enhanced exit conditions
            target_price = self.buy_price * (1 + self.p.take_profit)
            exit_condition = (
                price >= target_price
                or price <= self.stop_price
                or self.rsi[0] > 75
                or (
                    self.macd.lines.macd[0] < self.macd.lines.signal[0]
                    and self.stoch.lines.percD[0] > 80
                )
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
