from exits.base import BaseExitModel


class PartialTPExit(BaseExitModel):
    """
    50% at 1R, move SL to BE, rest to TP
    """

    def on_candle(self, trade, candle, index):
        if trade.initial_risk <= 0:
            return trade.check_exit(candle)
        if trade.exit_price is not None:
            return True

        # Calculate current R
        if trade.direction == "BUY":
            r = (candle["high"] - trade.entry_price) / trade.initial_risk
        else:
            r = (trade.entry_price - candle["low"]) / trade.initial_risk

        # Take partial at +1R
        if not trade.partial_taken and r >= 1.0:
            trade.partial_taken = True
            trade.sl = trade.entry_price  # move SL to BE

        # Final exit check
        return trade.check_exit(candle)
