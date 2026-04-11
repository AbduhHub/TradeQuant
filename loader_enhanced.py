"""
Enhanced Data Loader
Supports both standard CSV and MT5 tab-separated format
"""

import pandas as pd
from datetime import datetime


def load_price_data(file_path):
    """
    Load price data from CSV file.
    Supports:
    - Standard CSV with headers
    - MT5 tab-separated format
    """
    # Try to detect file format
    with open(file_path, 'r') as f:
        first_line = f.readline()
    
    # Check if it's MT5 format (tab-separated with angle brackets)
    if '\t' in first_line and '<' in first_line:
        # MT5 format
        df = pd.read_csv(file_path, sep='\t')
        df.columns = [c.strip('<>').lower() for c in df.columns]
        
        # Create datetime column
        df['time'] = pd.to_datetime(
            df['date'] + ' ' + df['time'],
            format='%Y.%m.%d %H:%M:%S'
        )
        
    else:
        # Standard CSV
        df = pd.read_csv(file_path)
    
    # NORMALIZE TIME COLUMN 
    time_col = None
    for col in ['time', 'timestamp', 'date', 'datetime']:
        if col in df.columns:
            time_col = col
            break
    
    if time_col is None:
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
            "volume": row.get("volume", row.get("tickvol", 0))
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
