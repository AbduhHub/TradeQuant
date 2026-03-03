class ScaleTrailExit:
    """
    Exit Model:
    - Partial TP at +1R (50%)
    - SL to breakeven after partial
    - Trailing stop after +1R
    - Time-based hard exit
    """

    def __init__(self, max_bars=60):
        self.max_bars = max_bars

    def on_candle(self, trade, candle, index):
        # Duration exit
        if index - trade.entry_index >= self.max_bars:
            trade._close(
                candle["time"],
                candle["close"],
                "TIME"
            )
            return True

        
        # BUY TRADE
        
        if trade.direction == "BUY":
            # Stop loss
            if candle["low"] <= trade.sl:
                trade._close(
                    candle["time"],
                    trade.sl,
                    "SL"
                )
                return True

            # Partial TP at +1R
            if not hasattr(trade, "partial_taken"):
                if candle["high"] >= trade.entry_price + trade.initial_risk:
                    trade.partial_taken = True
                    trade.realized_r = 1.0 * 0.5
                    trade.sl = trade.entry_price  # BE

            # Trailing stop after partial
            if hasattr(trade, "partial_taken"):
                new_sl = candle["low"]
                if new_sl > trade.sl:
                    trade.sl = new_sl

            # Final TP
            if candle["high"] >= trade.tp:
                trade._close(
                    candle["time"],
                    trade.tp,
                    "TP"
                )
                return True

        
        # SELL TRADE
        
        if trade.direction == "SELL":
            if candle["high"] >= trade.sl:
                trade._close(
                    candle["time"],
                    trade.sl,
                    "SL"
                )
                return True

            if not hasattr(trade, "partial_taken"):
                if candle["low"] <= trade.entry_price - trade.initial_risk:
                    trade.partial_taken = True
                    trade.realized_r = 1.0 * 0.5
                    trade.sl = trade.entry_price

            if hasattr(trade, "partial_taken"):
                new_sl = candle["high"]
                if new_sl < trade.sl:
                    trade.sl = new_sl

            if candle["low"] <= trade.tp:
                trade._close(
                    candle["time"],
                    trade.tp,
                    "TP"
                )
                return True

        return False
