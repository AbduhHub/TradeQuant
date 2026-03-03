from backtester import Backtester
from strategy_factory import StrategyFactory
from risk_simulation import simulate_equity


def generate_mixed_market(n=500):
    """
    Market with:
    - uptrend
    - pullbacks
    - chop
    This is MUCH closer to reality than a clean trend.
    """
    price = 100
    data = []

    for i in range(n):
        if i % 50 < 30:
            price += 2      # trend
        elif i % 50 < 40:
            price -= 3      # pullback
        else:
            price += 1 if i % 2 == 0 else -1  # chop
        data.append(price)

    return data


def test_trend_pullback_expectancy_analysis():
    data = generate_mixed_market()
    gaps = []

    strategy = StrategyFactory.create(
        name="trend_pullback",
        data=data
    )

    bt = Backtester(data, gaps, strategy)
    trades = bt.run()

    assert len(trades) > 10, "Too few trades for expectancy analysis"

    r_values = [t.r_multiple() for t in trades]

    expectancy = sum(r_values) / len(r_values)
    wins = [r for r in r_values if r > 0]
    losses = [r for r in r_values if r < 0]

    win_rate = len(wins) / len(r_values)
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0

    equity, max_dd = simulate_equity(trades, risk_per_trade=0.01)

    print("\n===== TREND PULLBACK EXPECTANCY REPORT =====")
    print(f"Trades        : {len(trades)}")
    print(f"Expectancy R  : {expectancy:.3f}")
    print(f"Win rate      : {win_rate:.2%}")
    print(f"Avg win (R)   : {avg_win:.2f}")
    print(f"Avg loss (R)  : {avg_loss:.2f}")
    print(f"Final equity  : {equity[-1]:.2f}x")
    print(f"Max drawdown  : {max_dd:.2%}")
    print("===========================================\n")

    # HARD REJECTION CRITERIA
    assert expectancy > 0, "Negative expectancy – strategy is not viable"
