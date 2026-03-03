class BaseExitModel:
    """
    Controls how a trade is managed after entry.
    """

    def on_candle(self, trade, candle, index):
        """
        Called every candle while trade is active.
        Must return True if trade should be closed.
        """
        raise NotImplementedError
