from exits.base import BaseExitModel


class TimeExit(BaseExitModel):
    def __init__(self, max_bars=30):
        self.max_bars = max_bars

    def on_candle(self, trade, candle, index):
        if trade.initial_risk <= 0:
            return trade.check_exit(candle)

        if index - trade.entry_index >= self.max_bars:
            trade._close(
                candle["time"],
                candle["close"],
                "BE"
            )
            return True

        return trade.check_exit(candle)
