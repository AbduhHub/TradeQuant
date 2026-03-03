from strategies.base import BaseStrategy
from utils.trade_factory import create_trade


class BreakRetestStrategy(BaseStrategy):
    key = "break_retest"
    name = "Break-Retest (Adaptive)"

    def __init__(self, candles, gaps=None, **kwargs):
        super().__init__(candles)
        self.gaps = gaps
        self.break_level = None
        self.break_direction = None
        self.break_index = None
        self.cooldown = 0
        self.ready_index = 50

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

        c = self.candles[index]
        p = self.candles[index - 1]

        if self.break_level is None:
            if c["close"] > p["high"]:
                self.break_level = p["high"]
                self.break_direction = "long"
                self.break_index = index
            elif c["close"] < p["low"]:
                self.break_level = p["low"]
                self.break_direction = "short"
                self.break_index = index
            return None

        if index - self.break_index > 10:
            self.break_level = None
            return None

        atr = self._atr(index)

        if self.break_direction == "long" and c["low"] <= self.break_level:
            entry = c["close"]
            sl = entry - atr
            tp = entry + 3 * atr

        elif self.break_direction == "short" and c["high"] >= self.break_level:
            entry = c["close"]
            sl = entry + atr
            tp = entry - 3 * atr

        else:
            return None

        self.break_level = None
        self.cooldown = 5

        return create_trade(
            entry_idx=index,
            entry_price=entry,
            direction=self.break_direction,
            sl=sl,
            tp=tp,
        )
