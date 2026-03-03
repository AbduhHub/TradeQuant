from metrics import calculate_metrics

def summarize(trades):
    m = calculate_metrics(trades)
    return {
        "total_trades": m["total_trades"],
        "win_rate": round(m["win_rate"] * 100, 2),
        "average_r": round(m["average_r"], 3),
        "total_r": round(m["total_r"], 2),
        "max_drawdown_r": round(m["max_drawdown_r"], 2),
    }
