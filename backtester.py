class Backtester:
    def __init__(self, candles, gaps, strategy):
        self.candles = candles
        self.strategy = strategy
        self.open_trade = None
        self.trades = []

    def run(self):
        for i in range(len(self.candles)):
            candle = self.candles[i]

            # Check exit first
            if self.open_trade:
                if self.open_trade.check_exit(i, candle):
                    self.trades.append(self.open_trade)
                    self.open_trade = None

            # Entry
            if self.open_trade is None:
                trade = self.strategy.on_candle(i)
                if trade:
                    self.open_trade = trade

        # force-close last trade
        if self.open_trade:
            last_idx = len(self.candles) - 1
            self.open_trade.exit_idx = last_idx
            self.open_trade.exit_price = self.open_trade.entry_price
            self.open_trade.result = "BE"
            self.trades.append(self.open_trade)
            self.open_trade = None

        return self.trades
