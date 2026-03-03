from loader import load_price_data, detect_gaps
from metrics import calculate_metrics
from regime_controller import RegimeController
from portfolio_runner import PortfolioRunner
from exits.scale_trail_exit import ScaleTrailExit


TIMEFRAMES = {
    "M1": ("data/BTC_M1.csv", 1),
    "M5": ("data/BTC_M5.csv", 5),
    "M15": ("data/BTC_M15.csv", 15),
}

STRATEGY_ORDER = [
    "break_retest",
    "trend_pullback",
]


def run_portfolio(data, gaps, tf_label):
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

    print(f"\n===== {tf_label} PORTFOLIO =====")
    if metrics["total_trades"] == 0:
        print("No trades.")
        return

    print("Trades:", metrics["total_trades"])
    print("Win rate:", round(metrics["win_rate"] * 100, 2), "%")
    print("Average R:", round(metrics["average_r"], 3))
    print("Total R:", round(metrics["total_r"], 2))
    print("Max DD (R):", round(metrics["max_drawdown_r"], 2))


if __name__ == "__main__":
    for tf, (path, minutes) in TIMEFRAMES.items():
        data = load_price_data(path)
        gaps = detect_gaps(data, minutes)
        run_portfolio(data, gaps, tf)
