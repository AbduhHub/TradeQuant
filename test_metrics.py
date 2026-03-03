from trade import Trade
from metrics import calculate_metrics

def test_metrics_basic():
    t1 = Trade(entry_price=100, sl=90, tp=110)
    t1._r_multiple = 1.0
    t1.total_r = 1.0
    t1.result = "WIN"

    t2 = Trade(entry_price=100, sl=90, tp=95)
    t2._r_multiple = -0.5
    t2.total_r = -0.5
    t2.result = "LOSS"

    trades = [t1, t2]
    metrics = calculate_metrics(trades)

    assert "total_r" in metrics
    assert "win_rate" in metrics
    assert metrics["win_rate"] == 0.5
