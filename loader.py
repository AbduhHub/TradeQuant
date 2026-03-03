import pandas as pd
from datetime import datetime


def load_price_data(file_path):
    df = pd.read_csv(file_path)

    #  NORMALIZE TIME COLUMN 
    if "time" in df.columns:
        time_col = "time"
    elif "timestamp" in df.columns:
        time_col = "timestamp"
    elif "date" in df.columns:
        time_col = "date"
    elif "datetime" in df.columns:
        time_col = "datetime"
    else:
        raise ValueError(
            f"No valid time column found. Columns: {list(df.columns)}"
        )

    df[time_col] = pd.to_datetime(df[time_col])

    candles = []
    for _, row in df.iterrows():
        candles.append({
            "time": row[time_col],
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row.get("volume", 0)
        })

    return candles


def detect_gaps(candles, timeframe_minutes):
    """
    Detects missing or duplicate candles.
    Returns a set of indices where a gap occurs.
    """

    expected_delta = timeframe_minutes * 60
    gap_indices = set()

    for i in range(1, len(candles)):
        diff = (candles[i]["time"] - candles[i - 1]["time"]).total_seconds()
        if diff != expected_delta:
            gap_indices.add(i)

    return gap_indices
