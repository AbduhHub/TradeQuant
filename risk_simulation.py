def simulate_equity(r_values, risk_per_trade):
    """
    r_values: list[float]  -> R-multiples
    risk_per_trade: float  -> e.g. 0.005
    """
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    curve = []

    for r in r_values:
        equity *= (1 + r * risk_per_trade)
        peak = max(peak, equity)
        dd = (peak - equity) / peak
        max_dd = max(max_dd, dd)
        curve.append(equity)

    return curve, max_dd
