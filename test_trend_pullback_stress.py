from backtester import Backtester
from strategy_factory import StrategyFactory
from risk_simulation import simulate_equity
import random



# MARKET GENERATORS

def sideways_market(n=500):
    price = 100
    data = []
    for _ in range(n):
        price += random.choice([-1, 0, 1])
        data.append(price)
    return data


def random_walk(n=500):
    price = 100
    data = []
    for _ in range(n):
        price += random.choice([-2, -1, 1, 2])
        data.append(price)
    return data


def high_volatility(n=500):
    price = 100
    data = []
    for _ in range(n):
        price += random.choice([-5, -4, 4, 5])
        data.append(price)
    return data


def regime_switching(n=600):
    price = 100
    data = []

    for i in range(n):
        if i < 150:
            price += 2              # uptrend
        elif i < 300:
            price += random.choice([-2, 2])  # chop
        elif i < 450:
            price -= 2              # downtrend
        else:
            price += random.choice([-3, 3])  # chaos
        data.append(price)

    return data



# STRESS TEST CORE

def run_strategy(data):
    gaps = []

    strategy = StrategyFactory.create(
        name="trend_pullback",
        data=data
    )

    bt = Backtester(data, gaps, strategy)
    trades = bt.run()

    if len(trades) == 0:
        return {
            "trades": 0,
            "expectancy": -999,
            "final_equity": 0,
            "max_dd": 1.0
        }

    r_vals = [t.r_multiple() for t in trades]
    expectancy = sum(r_vals) / len(r_vals)

    equity, max_dd = simulate_equity(trades, risk_per_trade=0.01)

    return {
        "trades": len(trades),
        "expectancy": expectancy,
        "final_equity": equity[-1],
        "max_dd": max_dd
    }



# TESTS

def test_sideways_market():
    result = run_strategy(sideways_market())

    print("\n--- SIDEWAYS MARKET ---")
    print(result)

    assert result["trades"] > 0, "No trades in sideways market"
    assert result["expectancy"] > -0.5, "Strategy collapses in chop"
    assert result["final_equity"] > 0.5, "Equity destroyed in chop"


def test_random_walk():
    result = run_strategy(random_walk())

    print("\n--- RANDOM WALK ---")
    print(result)

    assert result["trades"] > 0, "No trades in random walk"
    assert result["expectancy"] > -0.6, "Negative expectancy too large"
    assert result["final_equity"] > 0.4, "Equity destroyed in randomness"


def test_high_volatility():
    result = run_strategy(high_volatility())

    print("\n--- HIGH VOLATILITY ---")
    print(result)

    assert result["trades"] > 0, "No trades in high volatility"
    assert result["final_equity"] > 0.3, "Strategy blown up by volatility"
    assert result["max_dd"] < 0.9, "Drawdown unacceptable"


def test_regime_switching():
    result = run_strategy(regime_switching())

    print("\n--- REGIME SWITCHING ---")
    print(result)

    assert result["trades"] > 0, "No trades across regimes"
    assert result["expectancy"] > -0.4, "Strategy fails regime switching"
    assert result["final_equity"] > 0.6, "Equity collapses across regimes"
