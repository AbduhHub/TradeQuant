class BaseStrategy:
    def __init__(self, candles, risk_per_trade=None):
        self.candles = candles
        self.risk_per_trade = risk_per_trade

    def run(self, gaps):
        raise NotImplementedError("Strategy must implement run()")
