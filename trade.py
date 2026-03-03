class Trade:
    def __init__(
        self,
        entry_idx,
        entry_price,
        direction,
        sl,
        tp,
        size=1.0,
    ):
        self.entry_idx = entry_idx
        self.entry_price = entry_price
        self.direction = direction  
        self.sl = sl
        self.tp = tp
        self.size = size

        self.exit_idx = None
        self.exit_price = None
        self.is_closed = False

        # Metrics
        self._r_multiple = 0.0
        self.total_r = 0.0   
        self.result = None   

    def check_exit(self, idx, candle):
        if self.is_closed:
            return False

        price = candle["close"]

        if self.direction == "long":
            if self.sl is not None and price <= self.sl:
                self._close(idx, self.sl)
                return True
            if self.tp is not None and price >= self.tp:
                self._close(idx, self.tp)
                return True
        else:  # short
            if self.sl is not None and price >= self.sl:
                self._close(idx, self.sl)
                return True
            if self.tp is not None and price <= self.tp:
                self._close(idx, self.tp)
                return True

        return False

    def _close(self, idx, price):
        self.exit_idx = idx
        self.exit_price = price
        self.is_closed = True

        risk = abs(self.entry_price - self.sl) if self.sl is not None else 0.0
        reward = abs(price - self.entry_price)

        if risk == 0:
            self._r_multiple = 0.0
        else:
            self._r_multiple = reward / risk
            if price == self.sl:
                self._r_multiple *= -1

        
        self.total_r = self._r_multiple
        self.result = "WIN" if self._r_multiple > 0 else "LOSS"

    def r_multiple(self):
        return self._r_multiple
