def calculate_metrics(trades):
    if not trades:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "breakevens": 0,
            "win_rate": 0.0,
            "average_r": 0.0,
            "total_r": 0.0,
            "max_drawdown_r": 0.0,
        }

    total_r = 0.0
    peak = 0.0
    drawdown = 0.0
    max_dd = 0.0

    wins = 0
    losses = 0
    breakevens = 0

    for trade in trades:
        r = trade.total_r
        total_r += r

        # Win / loss classification
        if r > 0:
            wins += 1
        elif r < 0:
            losses += 1
        else:
            breakevens += 1

        # Drawdown tracking
        peak = max(peak, total_r)
        drawdown = peak - total_r
        max_dd = max(max_dd, drawdown)

    total_trades = len(trades)

    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "breakevens": breakevens,
        "win_rate": wins / total_trades,
        "average_r": total_r / total_trades,
        "total_r": total_r,
        "max_drawdown_r": max_dd,
    }
