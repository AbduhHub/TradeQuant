import random
from backtester import Backtester
from strategy_factory import StrategyFactory
from risk_simulation import simulate_equity


def generate_market(n=800):
    price = 100
    data = []

    for i in range(n):
        if i % 80 < 50:
            price += 2
        elif i % 80 < 65:
            price -= 3
        else:
            price += random.choice([-2, 2])
        data.append(price)

    return data


def monte_carlo_ruin(r_values, risk_per_trade, runs=5000, ruin_level=0.5):
    """
    ruin_level = equity level considered 'ruin'
    0.5 = 50% drawdown
    """
    ruin_count = 0
    max_dds = []

    for _ in range(runs):
        equity = 1.0
        peak = 1.0
        shuffled = r_values[:]
        random.shuffle(shuffled)

        for r in shuffled:
            equity *= (1 + r * risk_per_trade)
            peak = max(peak, equity)
            dd = (peak - equity) / peak

            if equity <= ruin_level:
                ruin_count += 1
                break

        max_dds.append(dd)

    return ruin_count / runs, max(max_dds)


def test_risk_of_ruin_analysis():
    data = generate_market()
    gaps = []

    strategy = StrategyFactory.create(
        name="trend_pullback",
        data=data
    )

    bt = Backtester(data, gaps, strategy)
    trades = bt.run()

    assert len(trades) > 30, "Too few trades for risk analysis"

    r_values = [t.r_multiple() for t in trades]

    print("\n===== RISK OF RUIN ANALYSIS =====")
    print(f"Total trades: {len(r_values)}")

    for risk in [0.0025, 0.005, 0.01, 0.02]:
        ruin_prob, worst_dd = monte_carlo_ruin(
            r_values,
            risk_per_trade=risk
        )

        print(f"\nRisk per trade: {risk*100:.2f}%")
        print(f"  Ruin probability : {ruin_prob*100:.2f}%")
        print(f"  Worst DD (MC)    : {worst_dd*100:.2f}%")

        # HARD SAFETY RULES
        assert ruin_prob < 0.10, "Risk of ruin too high"
        assert worst_dd < 0.80, "Drawdown psychologically lethal"

    print("================================\n")
