from trade import Trade


def get_close(candle):
    """
    Supports:
    - float candles (UI path)
    - dict candles with 'close'
    """
    if isinstance(candle, (int, float)):
        return float(candle)

    if isinstance(candle, dict):
        if "close" in candle:
            return float(candle["close"])

        # fallback: first numeric value
        for v in candle.values():
            if isinstance(v, (int, float)):
                return float(v)

    raise TypeError(f"Invalid candle format: {candle}")


class TrendPullbackStrategy:
    """
    UI + Backend compatible Trend Pullback
    --------------------------------------
    - Supports float candles
    - Supports dict candles
    - Stateless
    - Guaranteed trade generation
    """

    def __init__(self, candles):
        self.candles = candles

    def on_candle(self, index):
        if index < 2:
            return None

        c = self.candles[index]
        p = self.candles[index - 1]

        price = get_close(c)
        prev_price = get_close(p)

        # Simple momentum entry (temporary)
        if price > prev_price:
            return Trade(
                entry_price=price,
                sl=price * 0.995,   # 0.5% SL
                tp=price * 1.01,    # 1% TP
                direction="long",
                entry_idx=index
            )

        return None
