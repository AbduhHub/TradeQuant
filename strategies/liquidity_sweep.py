from strategies.base import BaseStrategy
from structure import detect_swings_rolling
from utils.trade_factory import create_trade


class LiquiditySweepStrategy(BaseStrategy):
    key = "liquidity_sweep"
    name = "Liquidity Sweep (Confirmed)"

    def __init__(self, candles, gaps=None, **kwargs):
        super().__init__(candles)
        self.gaps = gaps
        self.ready_index = 50
        self.cooldown = 0

    def _atr(self, index, period=14):
        trs = []
        for i in range(index - period + 1, index + 1):
            c = self.candles[i]
            p = self.candles[i - 1]
            trs.append(
                max(
                    c["high"] - c["low"],
                    abs(c["high"] - p["close"]),
                    abs(c["low"] - p["close"]),
                )
            )
        return sum(trs) / len(trs)

    def on_candle(self, index):
        if index < self.ready_index:
            return None

        if self.cooldown > 0:
            self.cooldown -= 1
            return None

        # returns CURRENT swing values
        swing_high, swing_low = detect_swings_rolling(
            self.candles,
            self.gaps,
            index,
            lookback=20,
        )

        c = self.candles[index]
        p = self.candles[index - 1]
        atr = self._atr(index)

        # Sweep high : short
        if swing_high is not None and c["high"] > swing_high and c["close"] < p["close"]:
            direction = "short"
            entry = c["close"]
            sl = entry + atr
            tp = entry - 3 * atr

        # Sweep low : long
        elif swing_low is not None and c["low"] < swing_low and c["close"] > p["close"]:
            direction = "long"
            entry = c["close"]
            sl = entry - atr
            tp = entry + 3 * atr

        else:
            return None

        self.cooldown = 5

        return create_trade(
            entry_idx=index,
            entry_price=entry,
            direction=direction,
            sl=sl,
            tp=tp,
        )
