from loader import load_price_data, detect_gaps
from portfolio_runner import PortfolioRunner
from regime_controller import RegimeController
from exits.scale_trail_exit import ScaleTrailExit
from metrics import calculate_metrics
from datetime import datetime


IS_START = 2019
IS_END = 2022
OOS_START = 2023
OOS_END = 2025

STRATEGY_ORDER = [
    "break_retest",
    "trend_pullback",
]


def _split_by_year(candles, start_year, end_year):
    return [c for c in candles if start_year <= c["time"].year <= end_year]


def _run_portfolio_segment(candles, gaps, label):
    regime = RegimeController(candles)
    exit_model = ScaleTrailExit(max_bars=60)

    portfolio = PortfolioRunner(
        candles=candles,
        gaps=gaps,
        regime_controller=regime,
        strategy_order=STRATEGY_ORDER,
        exit_model=exit_model
    )

    trades = portfolio.run()
    metrics = calculate_metrics(trades)

    print(f"\n--- {label} ---")
    if metrics["total_trades"] == 0:
        print("No trades.")
        return metrics

    print("Trades:", metrics["total_trades"])
    print("Win rate:", round(metrics["win_rate"] * 100, 2), "%")
    print("Average R:", round(metrics["average_r"], 3))
    print("Total R:", round(metrics["total_r"], 2))
    print("Max DD (R):", round(metrics["max_drawdown_r"], 2))
    return metrics


def run_walk_forward(csv_path, tf_minutes):
    print(f"\n===== WALK-FORWARD | TF={tf_minutes}m =====")

    full = load_price_data(csv_path)
    full_gaps = detect_gaps(full, tf_minutes)

    # Strict split (no leakage)
    is_data = _split_by_year(full, IS_START, IS_END)
    oos_data = _split_by_year(full, OOS_START, OOS_END)

    is_gaps = detect_gaps(is_data, tf_minutes)
    oos_gaps = detect_gaps(oos_data, tf_minutes)

    is_metrics = _run_portfolio_segment(is_data, is_gaps, "IN-SAMPLE (2019–2022)")
    oos_metrics = _run_portfolio_segment(oos_data, oos_gaps, "OUT-OF-SAMPLE (2023–2025)")

    return is_metrics, oos_metrics


if __name__ == "__main__":
    TIMEFRAMES = {
        "M1": ("data/BTC_M1.csv", 1),
        "M5": ("data/BTC_M5.csv", 5),
        "M15": ("data/BTC_M15.csv", 15),
    }

    for tf, (path, minutes) in TIMEFRAMES.items():
        print(f"\n==============================")
        print(f"TIMEFRAME: {tf}")
        print(f"==============================")
        run_walk_forward(path, minutes)
