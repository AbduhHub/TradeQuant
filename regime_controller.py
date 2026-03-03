from datetime import time


class RegimeController:
    """
    Mixed Regime Controller
    Allows multiple strategies depending on market state
    """

    def __init__(self, candles):
        self.candles = candles

        self.ema50 = None
        self.ema200 = None
        self.alpha50 = 2 / (50 + 1)
        self.alpha200 = 2 / (200 + 1)

        self.atr = None
        self.alpha_atr = 2 / (14 + 1)

        self.vwap_pv = 0.0
        self.vwap_vol = 0.0

    
    # INDICATORS
    
    def _update_ema(self, price):
        if self.ema50 is None:
            self.ema50 = self.ema200 = price
        else:
            self.ema50 = price * self.alpha50 + self.ema50 * (1 - self.alpha50)
            self.ema200 = price * self.alpha200 + self.ema200 * (1 - self.alpha200)

    def _update_atr(self, candle, prev):
        tr = max(
            candle["high"] - candle["low"],
            abs(candle["high"] - prev["close"]),
            abs(candle["low"] - prev["close"]),
        )

        if self.atr is None:
            self.atr = tr
        else:
            self.atr = tr * self.alpha_atr + self.atr * (1 - self.alpha_atr)

    def _update_vwap(self, candle):
        tp = (candle["high"] + candle["low"] + candle["close"]) / 3
        vol = candle.get("volume", 1.0)
        self.vwap_pv += tp * vol
        self.vwap_vol += vol
        return self.vwap_pv / max(self.vwap_vol, 1e-9)

    def _in_session(self, t):
        return time(7, 0) <= t.time() <= time(16, 0)

    
    # REGIME DECISION
    
    def get_allowed_strategies(self, index):
        if index < 200:
            return []

        candle = self.candles[index]
        prev = self.candles[index - 1]

        self._update_ema(candle["close"])
        self._update_atr(candle, prev)
        vwap = self._update_vwap(candle)

        if not self._in_session(candle["time"]):
            return []

        allowed = []

        #  Trend Regime 
        ema_gap = abs(self.ema50 - self.ema200) / candle["close"]
        if ema_gap > 0.0015:
            allowed.append("trend_pullback")

        #  Balanced / Structure 
        if abs(candle["close"] - vwap) / candle["close"] < 0.001:
            allowed.append("break_retest")

        #  Low Volatility 
        if self.atr and self.atr / candle["close"] < 0.0005:
            allowed.append("inside_bar")

        return allowed
