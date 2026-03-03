from loader import load_price_data, detect_gaps
from portfolio_runner import PortfolioRunner
from regime_controller import RegimeController
from exits.scale_trail_exit import ScaleTrailExit
from metrics import calculate_metrics
from risk_simulator import simulate_equity


CSV_PATH = "data/BTC_M1.csv"
TF_MINUTES = 1

STRATEGY_ORDER = [
    "break_retest",
    "trend_pullback",
]


def run():
    data = load_price_data(CSV_PATH)
    gaps = detect_gaps(data, TF_MINUTES)

    regime = RegimeController(data)
    exit_model = ScaleTrailExit(max_bars=60)

    portfolio = PortfolioRunner(
        candles=data,
        gaps=gaps,
        regime_controller=regime,
        strategy_order=STRATEGY_ORDER,
        exit_model=exit_model
    )

    trades = portfolio.run()
    metrics = calculate_metrics(trades)

    print("\n===== BASE PERFORMANCE (R-MULTIPLE) =====")
    print("Trades:", metrics["total_trades"])
    print("Avg R:", round(metrics["average_r"], 3))
    print("Total R:", round(metrics["total_r"], 2))
    print("Max DD (R):", round(metrics["max_drawdown_r"], 2))

    for risk in [0.0025, 0.005, 0.01]:
        result = simulate_equity(trades, risk)

        print(f"\n--- Risk per trade: {risk*100:.2f}% ---")
        print("Final equity:", round(result["final_equity"], 2), "x")
        print("Max drawdown:", round(result["max_drawdown"] * 100, 2), "%")


if __name__ == "__main__":
    run()
