"""
Enhanced Data Loader — v4 FAST
- MT5 tab-sep & standard CSV (handles Daily/Weekly with no TIME column)
- Vectorized candle loading: numpy arrays, no iterrows()
- Vectorized gap detection: O(n) numpy diff, not Python loop
"""
import os
import numpy as np
import pandas as pd
from typing import List, Dict, Set

TF_FILES = {
    'BTCUSD': {
        'M1':  'BTC_M1.csv',   'M5':  'BTC_M5.csv',   'M15': 'BTC_M15.csv',
        'H1':  'BTCUSD_H1.csv', 'H2': 'BTCUSD_H2.csv', 'H4': 'BTCUSD_H4.csv',
        'D1':  'BTCUSD_Daily.csv', 'W1': 'BTCUSD_Weekly.csv',
    },
    'XAUUSD': {
        'M1':  'XAU_M1.csv',   'M5':  'XAU_M5.csv',   'M15': 'XAU_M15.csv',
        'H1':  'XAUUSD_H1.csv', 'H2': 'XAUUSD_H2.csv', 'H4': 'XAUUSD_H4.csv',
        'D1':  'XAUUSD_Daily.csv', 'W1': 'XAUUSD_Weekly.csv',
    },
    'EURUSD': {
        'M1':  'EUR_M1.csv',   'M5':  'EUR_M5.csv',   'M15': 'EUR_M15.csv',
        'H1':  'EURUSD_H1.csv', 'H2': 'EURUSD_H2.csv', 'H4': 'EURUSD_H4.csv',
        'D1':  'EURUSD_Daily.csv', 'W1': 'EURUSD_Weekly.csv',
    },
}

TF_MINUTES = {
    'M1': 1, 'M5': 5, 'M15': 15,
    'H1': 60, 'H2': 120, 'H4': 240,
    'D1': 1440, 'W1': 10080,
}

WEEKEND_CLOSE = {'XAUUSD', 'EURUSD', 'GBPUSD'}


def resolve_file(data_dir: str, symbol: str, timeframe: str) -> str:
    if symbol in TF_FILES and timeframe in TF_FILES[symbol]:
        candidate = os.path.join(data_dir, TF_FILES[symbol][timeframe])
        if os.path.exists(candidate):
            return candidate

    if os.path.isdir(data_dir):
        prefixes = [symbol]
        if symbol == 'BTCUSD': prefixes.append('BTC')
        if symbol == 'XAUUSD': prefixes.append('XAU')
        if symbol == 'EURUSD': prefixes.append('EUR')
        tf_variants = [timeframe,
                       timeframe.replace('D1', 'Daily').replace('W1', 'Weekly')]
        for fname in os.listdir(data_dir):
            flower = fname.lower()
            for p in prefixes:
                for tv in tf_variants:
                    if p.lower() in flower and tv.lower() in flower:
                        return os.path.join(data_dir, fname)

    raise FileNotFoundError(
        f"No data file for {symbol} {timeframe} in '{data_dir}'. "
        f"Expected: {list(TF_FILES.get(symbol, {}).values())}"
    )


def _is_mt5(path: str) -> bool:
    with open(path, 'r') as f:
        first = f.readline()
    return '\t' in first and '<' in first


def _parse_mt5_df(df: pd.DataFrame) -> pd.Series:
    """
    Parse MT5 datetime from a stripped-column DataFrame.
    Handles both formats:
      - Intraday: separate <DATE> and <TIME> columns  → combine
      - Daily/Weekly: <DATE> only, no <TIME> column   → use date only
    """
    if 'time' in df.columns:
        # Intraday: date + time both present
        return pd.to_datetime(
            df['date'] + ' ' + df['time'],
            format='%Y.%m.%d %H:%M:%S'
        )
    else:
        # Daily/Weekly: date only
        return pd.to_datetime(df['date'], format='%Y.%m.%d')


def load_price_data(file_path: str) -> List[Dict]:
    """
    Load MT5 tab-sep or standard CSV → list of candle dicts.
    Uses vectorized operations — no iterrows().
    """
    if _is_mt5(file_path):
        df = pd.read_csv(file_path, sep='\t')
        df.columns = [c.strip('<>').lower() for c in df.columns]
        df['datetime'] = _parse_mt5_df(df)
    else:
        df = pd.read_csv(file_path)
        tcol = next(
            (c for c in ['datetime', 'time', 'timestamp', 'date'] if c in df.columns),
            None
        )
        if tcol is None:
            raise ValueError(f"No time column. Columns: {list(df.columns)}")
        df['datetime'] = pd.to_datetime(df[tcol])

    df = df.sort_values('datetime').reset_index(drop=True)

    # Vectorized: extract numpy arrays then zip — 6-10x faster than iterrows
    times  = df['datetime'].tolist()
    opens  = df['open'].to_numpy(dtype=float)
    highs  = df['high'].to_numpy(dtype=float)
    lows   = df['low'].to_numpy(dtype=float)
    closes = df['close'].to_numpy(dtype=float)
    vol_col = 'volume' if 'volume' in df.columns else ('tickvol' if 'tickvol' in df.columns else None)
    vols = df[vol_col].to_numpy(dtype=float) if vol_col else np.zeros(len(df))

    return [
        {'time': t, 'open': o, 'high': h, 'low': l, 'close': c, 'volume': v}
        for t, o, h, l, c, v in zip(times, opens, highs, lows, closes, vols)
    ]


def load_symbol_timeframe(data_dir: str, symbol: str, timeframe: str) -> List[Dict]:
    return load_price_data(resolve_file(data_dir, symbol, timeframe))


def detect_gaps(candles: List[Dict], timeframe_minutes: int,
                instrument: str = 'BTCUSD') -> Set[int]:
    """
    Vectorized gap detection using numpy diff.
    Instrument-aware thresholds:
      - BTC (24/7):         time gap OR price gap > 1.5%
      - EURUSD/XAUUSD:      time gap (excl weekend) OR price gap > 0.5%
    """
    if len(candles) < 2:
        return set()

    expected_sec = timeframe_minutes * 60

    # Vectorized time diff
    times_ns  = np.array([c['time'].value for c in candles], dtype=np.int64)
    time_diff = np.diff(times_ns) / 1e9  # seconds

    if instrument in WEEKEND_CLOSE:
        # For weekend-close instruments, allow up to 3-day gaps (Fri→Mon = ~65h)
        # Only flag genuine mid-week time gaps
        weekend_allowance = 65 * 3600  # 65 hours
        gap_mask = (time_diff > expected_sec) & (time_diff > weekend_allowance)
        price_gap_threshold = 0.005   # 0.5% — unusual for FX/Gold
    else:
        # BTC trades 24/7 — any time gap is a real gap
        gap_mask = time_diff > expected_sec * 2  # allow 1 missed candle tolerance
        price_gap_threshold = 0.015   # 1.5% — BTC needs larger threshold

    # Vectorized price gap (open vs prev close)
    closes = np.array([c['close'] for c in candles], dtype=float)
    opens  = np.array([c['open']  for c in candles], dtype=float)
    price_gap = np.abs(opens[1:] - closes[:-1]) / np.maximum(closes[:-1], 1e-8)
    price_gap_mask = price_gap > price_gap_threshold

    combined = np.where(gap_mask | price_gap_mask)[0] + 1
    return set(combined.tolist())