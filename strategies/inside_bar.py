from strategies.base import BaseStrategy
from utils.trade_factory import create_trade


class InsideBarStrategy(BaseStrategy):
    key = "inside_bar"
    name = "Inside Bar (Compression Break)"

    def __init__(self, candles, gaps=None, **kwargs):
        super().__init__(candles)
        self.gaps = gaps
        self.ready_index = 30
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

        window = self.candles[index - 4:index]
        mother = window[0]

        if not all(
            c["high"] <= mother["high"] and c["low"] >= mother["low"]
            for c in window[1:]
        ):
            return None

        c = self.candles[index]
        atr = self._atr(index)

        if c["close"] > mother["high"]:
            direction = "long"
            entry = c["close"]
            sl = entry - atr
            tp = entry + 3 * atr

        elif c["close"] < mother["low"]:
            direction = "short"
            entry = c["close"]
            sl = entry + atr
            tp = entry - 3 * atr

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
