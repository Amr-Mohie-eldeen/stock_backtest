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
            if self.p.debug:
                self.logger.log_debug(
                    f"{symbol} - Price: {price:.2f}, "
                    f"RSI: {indicators['rsi'][0]:.2f}, "
                    f"SMA: {indicators['sma'][0]:.2f}"
                )

            position = self.getposition(data)
            if not position:  # No position - look for entry
                # Enhanced entry conditions
                trend_up = price > indicators["sma"][0]
                momentum_up = indicators["rsi"][0] > 40
                rsi_condition = indicators["rsi"][0] < 65
                positive_crossover = (
                    indicators["macd"].lines.macd[0]
                    > indicators["macd"].lines.signal[0]
                )
                stoch_oversold = indicators["stoch"].lines.percD[0] < 60

                if (
                    trend_up
                    and momentum_up
                    and rsi_condition
                    and (positive_crossover or stoch_oversold)
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

            else:  # Have position - look for exit
                # Enhanced exit conditions
                target_price = self.buy_prices[symbol] * (1 + self.p.take_profit)
                stop_price = self.stop_prices[symbol]

                # Exit conditions
                hit_target = price >= target_price
                hit_stop = price <= stop_price
                rsi_overbought = indicators["rsi"][0] > 75
                macd_crossover_down = (
                    indicators["macd"].lines.macd[0]
                    < indicators["macd"].lines.signal[0]
                )
                stoch_overbought = indicators["stoch"].lines.percD[0] > 80

                if (
                    hit_target
                    or hit_stop
                    or (rsi_overbought and macd_crossover_down)
                    or (stoch_overbought and macd_crossover_down)
                ):
                    self.orders[symbol] = self.sell(data=data, size=position.size)

                    if self.p.debug:
                        exit_reason = (
                            "TARGET"
                            if hit_target
                            else (
                                "STOP"
                                if hit_stop
                                else "TECHNICAL" if rsi_overbought else "STOCHASTIC"
                            )
                        )
                        self.logger.log_trade(
                            f"{symbol} SELL CREATE at {price:.2f}, "
                            f"Size: {position.size} shares, "
                            f"Reason: {exit_reason}"
                        )

    def log_debug_entry(self, price):
        """Log entry conditions for debugging"""
        if not self.p.debug:
            return
