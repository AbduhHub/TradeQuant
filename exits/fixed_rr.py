from exits.base import BaseExitModel


class FixedRRExit(BaseExitModel):
    """
    Fixed SL / TP exit (baseline)
    """

    def on_candle(self, trade, candle, index):
        return trade.check_exit(candle)
