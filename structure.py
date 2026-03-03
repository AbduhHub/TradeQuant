def detect_swings(candles, gap_indices):
    """
    Legacy swing detector (kept ONLY for compatibility).
    Uses full history — DO NOT use for new logic.
    """
    swing_highs = []
    swing_lows = []

    for i in range(2, len(candles) - 2):
        if i in gap_indices:
            continue

        if (
            candles[i]["high"] > candles[i - 1]["high"]
            and candles[i]["high"] > candles[i + 1]["high"]
        ):
            swing_highs.append(i)

        if (
            candles[i]["low"] < candles[i - 1]["low"]
            and candles[i]["low"] < candles[i + 1]["low"]
        ):
            swing_lows.append(i)

    return swing_highs, swing_lows


def detect_swings_rolling(candles, gap_indices, index, lookback=500):
    """
    Rolling adaptive swing detection.
    Returns most recent swing high and low indices.
    """

    start = max(2, index - lookback)
    end = index - 2

    last_high = None
    last_low = None

    for i in range(start, end):
        if (
            i in gap_indices
            or i - 1 in gap_indices
            or i + 1 in gap_indices
        ):
            continue

        if (
            candles[i]["high"] > candles[i - 1]["high"]
            and candles[i]["high"] > candles[i + 1]["high"]
        ):
            last_high = i

        if (
            candles[i]["low"] < candles[i - 1]["low"]
            and candles[i]["low"] < candles[i + 1]["low"]
        ):
            last_low = i

    return last_high, last_low
