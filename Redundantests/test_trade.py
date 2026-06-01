from trade import Trade

def test_trade_no_sl_tp_does_not_close():
    trade = Trade(entry_price=100, direction="long")
    closed = trade.check_exit(105)
    assert closed is False
    assert trade.is_closed is False


def test_trade_tp_hit_long():
    trade = Trade(entry_price=100, sl=95, tp=110, direction="long")
    closed = trade.check_exit(110)
    assert closed is True
    assert trade.is_closed is True
    assert trade.result == "WIN"
    assert trade.r_multiple() > 0


def test_trade_sl_hit_long():
    trade = Trade(entry_price=100, sl=95, tp=110, direction="long")
    closed = trade.check_exit(95)
    assert closed is True
    assert trade.is_closed is True
    assert trade.result == "LOSS"
