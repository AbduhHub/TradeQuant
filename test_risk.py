from trade import Trade
from risk_simulation import simulate_equity

def test_simulate_equity_basic_growth():
    t1 = Trade(entry_price=100, sl=90, tp=110)
    t1._r_multiple = 1.0

    t2 = Trade(entry_price=100, sl=90, tp=120)
    t2._r_multiple = 2.0

    trades = [t1, t2]
    risk = 0.01

    equity, max_dd = simulate_equity(trades, risk)

    assert isinstance(equity, list)
    assert equity[0] == 1.0
    assert equity[-1] > 1.0
    assert max_dd >= 0
