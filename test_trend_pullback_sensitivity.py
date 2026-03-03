from backtester import Backtester
from strategy_factory import StrategyFactory
from risk_simulation import simulate_equity


def generate_market(n=600):
    price = 100
    data = []

    for i in range(n):
        if i % 60 < 40:
            price += 2
        elif i % 60 < 50:
            price -= 3
        else:
            price += 1 if i % 2 == 0 else -1
        data.append(price)

    return data


def run_with_params(data, ema_period, sl_dist, tp_dist):
    gaps = []

    strategy = StrategyFactory.create(
        name="trend_pullback",
        data=data,
        ema_period=ema_period,
        sl_dist=sl_dist,
        tp_dist=tp_dist,
    )

    bt = Backtester(data, gaps, strategy)
    trades = bt.run()

    if len(trades) == 0:
        return {
            "trades": 0,
            "expectancy": -999,
            "final_equity": 0,
            "max_dd": 1.0,
        }

    r_vals = [t.r_multiple() for t in trades]
    expectancy = sum(r_vals) / len(r_vals)
    equity, max_dd = simulate_equity(trades, risk_per_trade=0.01)

    return {
        "trades": len(trades),
        "expectancy": expectancy,
        "final_equity": equity[-1],
        "max_dd": max_dd,
    }


def test_parameter_sensitivity():
    data = generate_market()

    base = run_with_params(data, ema_period=20, sl_dist=2, tp_dist=4)

    variants = [
        ("ema_15", 15, 2, 4),
        ("ema_25", 25, 2, 4),
        ("sl_1", 20, 1, 4),
        ("sl_3", 20, 3, 4),
        ("tp_3", 20, 2, 3),
        ("tp_5", 20, 2, 5),
    ]

    print("\n===== PARAMETER SENSITIVITY REPORT =====")
    print(f"BASE: {base}")

    for name, ema, sl, tp in variants:
        result = run_with_params(data, ema, sl, tp)
        print(f"{name.upper()}: {result}")

        # HARD FAILURE CONDITIONS
        assert result["trades"] > 0, f"{name}: no trades"
        assert result["expectancy"] > -0.5, f"{name}: expectancy collapse"
        assert result["final_equity"] > 0.5, f"{name}: equity collapse"

    print("=======================================\n")
