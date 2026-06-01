from backtester import Backtester
from trade import Trade

class DummyStrategy:
    def __init__(self):
        self.used = False

    def on_candle(self, i):
        if i == 0 and not self.used:
            self.used = True
            return Trade(
                entry_price=100,
                sl=95,
                tp=105,
                direction="long"
            )
        return None


def test_backtester_runs_and_closes_trade():
    data = [100, 101, 102, 103, 105]
    gaps = []

    strategy = DummyStrategy()
    bt = Backtester(data, gaps, strategy)
    trades = bt.run()

    assert len(trades) == 1
    assert trades[0].is_closed
    assert trades[0].result == "WIN"
