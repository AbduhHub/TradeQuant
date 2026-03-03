from backtester import Backtester
from strategy_factory import StrategyFactory
from risk_simulation import simulate_equity


def generate_uptrend(n=200):
    """
    Synthetic clean uptrend with shallow pullbacks.
    This is the MINIMUM environment where a trend-pullback
    strategy should not fail completely.
    """
    price = 100
    data = []

    for i in range(n):
        if i % 10 == 0:
            price -= 1   # pullback
        else:
            price += 2   # trend impulse
        data.append(price)

    return data


def test_trend_pullback_produces_trades():
    data = generate_uptrend()
    gaps = []  # trend pullback should not depend on gaps

    strategy = StrategyFactory.create(
        name="trend_pullback",
        data=data
    )

    bt = Backtester(data, gaps, strategy)
    trades = bt.run()

    assert len(trades) > 0, "Trend Pullback produced zero trades"


def test_trend_pullback_trades_close():
    data = generate_uptrend()
    gaps = []

    strategy = StrategyFactory.create(
        name="trend_pullback",
        data=data
    )

    bt = Backtester(data, gaps, strategy)
    trades = bt.run()

    assert all(t.is_closed for t in trades), "Some trades never closed"


def test_trend_pullback_expectancy_not_horrible():
    """
    This does NOT require profitability.
    It only rejects completely broken logic.
    """
    data = generate_uptrend()
    gaps = []

    strategy = StrategyFactory.create(
        name="trend_pullback",
        data=data
    )

    bt = Backtester(data, gaps, strategy)
    trades = bt.run()

    avg_r = sum(t.r_multiple() for t in trades) / len(trades)

    # This threshold is intentionally lenient
    assert avg_r > -0.5, f"Expectancy too negative: {avg_r:.2f}"


def test_trend_pullback_equity_curve():
    data = generate_uptrend()
    gaps = []

    strategy = StrategyFactory.create(
        name="trend_pullback",
        data=data
    )

    bt = Backtester(data, gaps, strategy)
    trades = bt.run()

    equity, max_dd = simulate_equity(trades, risk_per_trade=0.01)

    assert isinstance(equity, list)
    assert equity[-1] > 0, "Equity curve collapsed"
    assert max_dd < 1.0, "Drawdown is catastrophic"
