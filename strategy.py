from trade import Trade


class BreakRetestStrategy:
    def __init__(self, candles, swing_highs, swing_lows):
        self.candles = candles

        # Sort swing indices once
        self.swing_highs = sorted(swing_highs)
        self.swing_lows = sorted(swing_lows)

        self.high_ptr = 0
        self.low_ptr = 0

        self.last_swing_high = None
        self.last_swing_low = None

        self.broken_level = None
        self.direction = None

        self.active_trade = None

    def on_candle(self, index):
        candle = self.candles[index]

        # Update latest swing high
        while self.high_ptr < len(self.swing_highs) and self.swing_highs[self.high_ptr] < index:
            self.last_swing_high = self.swing_highs[self.high_ptr]
            self.high_ptr += 1

        # Update latest swing low
        while self.low_ptr < len(self.swing_lows) and self.swing_lows[self.low_ptr] < index:
            self.last_swing_low = self.swing_lows[self.low_ptr]
            self.low_ptr += 1

        # BREAK DETECTION
        if self.broken_level is None:
            if self.last_swing_high is not None:
                level = self.candles[self.last_swing_high]["high"]
                if candle["close"] > level:
                    self.broken_level = level
                    self.direction = "BUY"
                    return None

            if self.last_swing_low is not None:
                level = self.candles[self.last_swing_low]["low"]
                if candle["close"] < level:
                    self.broken_level = level
                    self.direction = "SELL"
                    return None

        # RETEST DETECTION
        if self.broken_level is not None:
            if self.direction == "BUY":
                if candle["low"] <= self.broken_level:
                    entry = candle["close"]
                    sl = candle["low"]
                    tp = entry + 3 * (entry - sl)

                    self.active_trade = Trade(
                        "BUY", candle["time"], entry, sl, tp
                    )
                    self._reset_structure()
                    return self.active_trade

            else:  # SELL
                if candle["high"] >= self.broken_level:
                    entry = candle["close"]
                    sl = candle["high"]
                    tp = entry - 3 * (sl - entry)

                    self.active_trade = Trade(
                        "SELL", candle["time"], entry, sl, tp
                    )
                    self._reset_structure()
                    return self.active_trade

        return None

    def on_trade_closed(self):
        self.active_trade = None

    def _reset_structure(self):
        self.broken_level = None
        self.direction = None
