"""
run_all_tests.py — Supreme Test Runner v2
==========================================
Fixes from v1:
  - D1/W1 now work (Daily/Weekly MT5 format parsed correctly)
  - EURUSD position sizing fixed (pip-aware, no more 20k lot sizes)
  - MC Phase 5: uses already-loaded candles, no re-read from disk → no OOM
  - Candle cache: each file loaded once, reused across strategies and costs variants
  - Progress timing per phase

Tests:
  Phase 1 — All backtests: 3 symbols × up to 8 TFs × 3 strategies × costs ON/OFF
  Phase 2 — Position sizing: fixed, kelly, optimal_f on H1
  Phase 3 — Grid search: TrendPullbackV3 on H1/H4/D1
  Phase 4 — Walk-forward: TrendPullbackV3 on H1/D1 (12mo in / 3mo out)
  Phase 5 — Monte Carlo: 5000 sims, uses in-memory trades, no re-read

Output files (project root):
  results_cache.json          ← loaded by app.py Tab 11 instantly
  results_full.csv
  results_position_sizing.csv
  results_grid_search.csv
  results_walk_forward.csv
  results_monte_carlo.csv
"""

import os, sys, json, time, traceback
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import numpy as np
import pandas as pd

from loader_enhanced import (
    load_price_data, detect_gaps, resolve_file,
    TF_MINUTES, _is_mt5
)
from backtester import Backtester
from strategy_factory import StrategyFactory
from metrics import calculate_metrics
from costs.transaction_costs import InstrumentConfig, get_cost_model
from risk.position_sizer import PositionSizer
from simulation.monte_carlo import MonteCarloSimulator
from optimization.grid_search import GridSearchOptimizer
from validation.walk_forward import WalkForwardTester
from strategies.trend_pullback_v3 import TrendPullbackV3

DATA_DIR   = os.path.join(ROOT, "data")
SYMBOLS    = ["BTCUSD", "XAUUSD", "EURUSD"]
TIMEFRAMES = ["M1", "M5", "M15", "H1", "H4", "D1", "W1"]
STRATEGIES = ["trend_pullback", "break_retest", "inside_bar"]  # liquidity_sweep needs structure
CAPITAL    = 10000.0
RISK_PCT   = 0.01

GS_TIMEFRAMES  = ["H1", "H4", "D1"]
WF_TIMEFRAMES  = ["H1", "D1"]
MC_SIMS        = 5000
MC_MIN_TRADES  = 30


#  helpers 

def file_available(symbol, tf):
    try:
        resolve_file(DATA_DIR, symbol, tf)
        return True
    except FileNotFoundError:
        return False


# Global candle cache: loaded once per (symbol, tf)
_CANDLE_CACHE = {}

def get_candles(symbol, tf):
    key = (symbol, tf)
    if key not in _CANDLE_CACHE:
        _CANDLE_CACHE[key] = load_price_data(resolve_file(DATA_DIR, symbol, tf))
    return _CANDLE_CACHE[key]


def _run_single(symbol, tf, strategy_key, cost_model,
                capital=CAPITAL, risk_pct=RISK_PCT, candles=None):
    if candles is None:
        candles = get_candles(symbol, tf)
    tf_min  = TF_MINUTES.get(tf, 15)
    gaps    = detect_gaps(candles, tf_min, instrument=symbol)
    ctx     = {'gaps': gaps}
    strategy = StrategyFactory.create(strategy_key, candles, ctx)
    bt = Backtester(candles, gaps, strategy,
                    cost_model=cost_model, capital=capital,
                    risk_pct=risk_pct, instrument=symbol)
    trades  = bt.run()
    metrics = calculate_metrics(trades, initial_capital=capital)
    return trades, candles, gaps, metrics


def safe_float(v, default=0.0):
    try:
        f = float(v)
        return f if (f == f and abs(f) < 1e15) else default  # reject NaN/Inf/astronomical
    except Exception:
        return default


#  PHASE 1 

def run_all_backtests():
    results_cache = {}
    rows_main = []
    print(f"\n{'='*70}\nPHASE 1: All Backtests\n{'='*70}")

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            if not file_available(symbol, tf):
                print(f"  SKIP {symbol} {tf} — no data file")
                continue

            # Load candles once for this (symbol, tf)
            try:
                candles = get_candles(symbol, tf)
            except Exception as e:
                print(f"  LOAD ERR {symbol} {tf}: {e}")
                continue

            for strategy_key in STRATEGIES:
                for costs_on in [True, False]:
                    cm  = get_cost_model(symbol) if costs_on else None
                    tag = f"{symbol} {tf} {strategy_key} costs={'ON' if costs_on else 'OFF'}"
                    ck  = f"{symbol}|{tf}|{strategy_key}|{'costs' if costs_on else 'nocosts'}"
                    t0  = time.perf_counter()
                    try:
                        trades, _, gaps, m = _run_single(
                            symbol, tf, strategy_key, cm, candles=candles)
                        elapsed = time.perf_counter() - t0

                        row = {
                            'symbol': symbol, 'timeframe': tf,
                            'strategy': strategy_key, 'costs_on': costs_on,
                            'total_trades':     m['total_trades'],
                            'wins':             m['wins'],
                            'losses':           m['losses'],
                            'win_rate':         safe_float(m['win_rate']),
                            'average_r':        safe_float(m['average_r']),
                            'total_r':          safe_float(m['total_r']),
                            'net_pnl':          safe_float(m['net_pnl']),
                            'gross_pnl':        safe_float(m['gross_pnl']),
                            'total_costs':      safe_float(m['total_costs']),
                            'return_pct':       safe_float(m['return_pct']),
                            'max_drawdown_pct': safe_float(m['max_drawdown_pct']),
                            'profit_factor':    safe_float(m['profit_factor'],
                                                           default=0.0
                                                           ) if m['profit_factor'] != float('inf') else 999.0,
                            'candles':          len(candles),
                            'gaps':             len(gaps),
                            'elapsed_s':        round(elapsed, 2),
                            'status':           'ok',
                        }
                        results_cache[ck] = row
                        rows_main.append(row)
                        print(f"  ✅ {tag:<55} trades={m['total_trades']:5d}  "
                              f"R={m['average_r']:+.3f}  net=${m['net_pnl']:+.0f}  "
                              f"({elapsed:.1f}s)")
                    except Exception as e:
                        elapsed = time.perf_counter() - t0
                        results_cache[ck] = {
                            'symbol': symbol, 'timeframe': tf,
                            'strategy': strategy_key, 'costs_on': costs_on,
                            'status': f"ERROR: {str(e)[:100]}"
                        }
                        print(f"  ❌ {tag:<55} {str(e)[:60]}")

    ok   = sum(1 for r in rows_main if r.get('status') == 'ok')
    errs = sum(1 for v in results_cache.values() if 'ERROR' in str(v.get('status','')))
    print(f"\n  Phase 1 done: {len(rows_main)} ok, {errs} errors\n")
    return results_cache, rows_main


#  PHASE 2 

def run_position_sizing(results_cache):
    print(f"\n{'='*70}\nPHASE 2: Position Sizing\n{'='*70}")
    rows_ps = []

    for symbol in SYMBOLS:
        if not file_available(symbol, 'H1'):
            continue
        try:
            candles = get_candles(symbol, 'H1')
            trades_base, _, _, m_base = _run_single(
                symbol, 'H1', 'trend_pullback', get_cost_model(symbol), candles=candles)
        except Exception as e:
            print(f"  ❌ {symbol} H1 base run: {e}")
            continue

        if not trades_base or m_base['total_trades'] < 10:
            continue

        r_multiples = [t.total_r for t in trades_base]
        sizer = PositionSizer(CAPITAL)

        kelly_f = sizer.kelly_criterion(
            m_base['win_rate'],
            abs(m_base.get('avg_win_r', 1.0)),
            abs(m_base.get('avg_loss_r', 1.0)),
            fraction=0.5
        )
        opt_f = sizer.optimal_f(r_multiples)

        methods = {
            'fixed_1pct': RISK_PCT,
            'kelly_half':  kelly_f,
            'optimal_f':   opt_f,
        }

        for method, risk in methods.items():
            actual_risk = max(0.001, min(risk, 0.05))
            try:
                t_m, _, _, m_m = _run_single(
                    symbol, 'H1', 'trend_pullback',
                    get_cost_model(symbol),
                    capital=CAPITAL, risk_pct=actual_risk, candles=candles)
                rows_ps.append({
                    'symbol': symbol, 'timeframe': 'H1',
                    'sizing_method': method,
                    'risk_pct':    round(actual_risk * 100, 3),
                    'total_trades': m_m['total_trades'],
                    'net_pnl':      round(m_m['net_pnl'], 2),
                    'return_pct':   round(m_m['return_pct'], 2),
                    'max_dd_pct':   round(m_m['max_drawdown_pct'] * 100, 2),
                    'avg_r':        round(m_m['average_r'], 3),
                })
                print(f"  {symbol} H1 {method:<15} risk={actual_risk*100:.2f}%  "
                      f"net=${m_m['net_pnl']:+.0f}  dd={m_m['max_drawdown_pct']*100:.1f}%")
            except Exception as e:
                print(f"  ❌ {symbol} H1 {method}: {e}")

    return rows_ps


#  PHASE 3 

def run_grid_searches():
    print(f"\n{'='*70}\nPHASE 3: Grid Search (TrendPullbackV3)\n{'='*70}")

    param_grid = {
        'lookback':          [50, 100, 200],
        'min_rr':            [1.5, 2.0, 2.5, 3.0],
        'atr_multiplier_sl': [1.0, 1.5, 2.0],
    }
    rows_gs = []

    for symbol in SYMBOLS:
        for tf in GS_TIMEFRAMES:
            if not file_available(symbol, tf):
                continue
            t0 = time.perf_counter()
            try:
                candles = get_candles(symbol, tf)
                gaps    = detect_gaps(candles, TF_MINUTES[tf], instrument=symbol)
                cm      = get_cost_model(symbol)

                optimizer = GridSearchOptimizer(metric='average_r', min_trades=20)
                results   = optimizer.optimize(
                    strategy_class=TrendPullbackV3,
                    candles=candles,
                    param_grid=param_grid,
                    gaps=gaps,
                    cost_model=cm,
                    instrument=symbol,
                    verbose=False
                )
                elapsed = time.perf_counter() - t0

                if results:
                    for rank, r in enumerate(results[:5], 1):
                        rows_gs.append({
                            'symbol': symbol, 'timeframe': tf, 'rank': rank,
                            'lookback': r['params'].get('lookback'),
                            'min_rr':   r['params'].get('min_rr'),
                            'atr_sl':   r['params'].get('atr_multiplier_sl'),
                            'total_trades': r['total_trades'],
                            'avg_r':    round(r['average_r'], 3),
                            'total_r':  round(r['total_r'], 2),
                            'win_rate': round(r['win_rate'] * 100, 1),
                            'max_dd_r': round(r['max_dd'], 2),
                        })
                    best = results[0]
                    print(f"  ✅ {symbol} {tf:<4} {len(results):3d} valid combos  "
                          f"best: lookback={best['params']['lookback']}  "
                          f"min_rr={best['params']['min_rr']}  "
                          f"avg_r={best['average_r']:+.3f}  ({elapsed:.0f}s)")
                else:
                    print(f"  ⚠️  {symbol} {tf} — no valid combos ({elapsed:.0f}s)")

            except Exception as e:
                print(f"  ❌ {symbol} {tf}: {str(e)[:80]}")

    return rows_gs


#  PHASE 4 

def run_walk_forwards():
    print(f"\n{'='*70}\nPHASE 4: Walk-Forward (TrendPullbackV3)\n{'='*70}")

    param_grid = {'lookback': [100, 200], 'min_rr': [2.0, 2.5]}
    rows_wf = []

    for symbol in SYMBOLS:
        for tf in WF_TIMEFRAMES:
            if not file_available(symbol, tf):
                continue
            t0 = time.perf_counter()
            try:
                candles = get_candles(symbol, tf)
                gaps    = detect_gaps(candles, TF_MINUTES[tf], instrument=symbol)
                cm      = get_cost_model(symbol)

                wf = WalkForwardTester(
                    in_sample_periods=12,
                    out_sample_periods=3,
                    period_type='months',
                    min_trades_per_window=15
                )
                res = wf.run_walk_forward(
                    strategy_class=TrendPullbackV3,
                    candles=candles,
                    param_grid=param_grid,
                    gaps=gaps,
                    cost_model=cm,
                    instrument=symbol,
                    verbose=False
                )
                elapsed = time.perf_counter() - t0
                summary = res['summary']
                windows = res['windows']

                if not windows:
                    print(f"  ⚠️  {symbol} {tf} — not enough data for windows")
                    continue

                rows_wf.append({
                    'symbol': symbol, 'timeframe': tf,
                    'windows':           summary['total_windows'],
                    'in_avg_r':          round(summary['in_sample_avg_r_mean'], 3),
                    'out_avg_r':         round(summary['out_sample_avg_r_mean'], 3),
                    'degradation_pct':   round(summary['degradation_pct'], 1),
                    'consistency_score': round(summary['consistency_score'] * 100, 1),
                    'profitable_out_pct': round(
                        summary['profitable_windows_out'] / summary['total_windows'] * 100, 1),
                })
                print(f"  ✅ {symbol} {tf:<4} {summary['total_windows']} windows  "
                      f"in={summary['in_sample_avg_r_mean']:+.3f}  "
                      f"out={summary['out_sample_avg_r_mean']:+.3f}  "
                      f"degrad={summary['degradation_pct']:.1f}%  ({elapsed:.0f}s)")

            except Exception as e:
                print(f"  ❌ {symbol} {tf}: {str(e)[:80]}")

    return rows_wf


#  PHASE 5 

def run_monte_carlos(rows_main):
    """
    Uses in-memory trades from the results_cache Phase 1 runs.
    Re-runs the backtest once per (symbol, tf, strategy) using cached candles,
    then feeds trades to MC — NO re-reading from disk.
    """
    print(f"\n{'='*70}\nPHASE 5: Monte Carlo ({MC_SIMS} sims)\n{'='*70}")
    rows_mc = []

    # Only costs-on, enough trades
    eligible = [r for r in rows_main
                if r.get('status') == 'ok'
                and r.get('costs_on', True)
                and r.get('total_trades', 0) >= MC_MIN_TRADES]

    print(f"  {len(eligible)} combos eligible\n")

    for row in eligible:
        symbol   = row['symbol']
        tf       = row['timeframe']
        strategy = row['strategy']
        t0 = time.perf_counter()
        try:
            # Use cached candles — no disk read
            candles = get_candles(symbol, tf)
            trades, _, _, _ = _run_single(
                symbol, tf, strategy, get_cost_model(symbol), candles=candles)

            if len(trades) < MC_MIN_TRADES:
                continue

            simulator = MonteCarloSimulator(n_simulations=MC_SIMS)
            stats     = simulator.simulate(
                trades, CAPITAL, risk_per_trade=RISK_PCT, verbose=False)

            elapsed = time.perf_counter() - t0
            rows_mc.append({
                'symbol': symbol, 'timeframe': tf, 'strategy': strategy,
                'trades':          len(trades),
                'risk_of_ruin':    round(stats['risk']['risk_of_ruin'], 2),
                'prob_profitable': round(stats['risk']['prob_profitable'], 1),
                'median_return':   round(stats['returns']['median'], 2),
                'p5_return':       round(stats['returns']['p5'], 2),
                'p95_return':      round(stats['returns']['p95'], 2),
                'median_max_dd':   round(stats['drawdowns']['median'], 2),
                'prob_dd_gt_20':   round(stats['risk']['prob_dd_gt_20pct'], 1),
                'prob_dd_gt_30':   round(stats['risk']['prob_dd_gt_30pct'], 1),
                'eq_p5':           round(stats['final_equity']['p5'], 2),
                'eq_median':       round(stats['final_equity']['median'], 2),
                'eq_p95':          round(stats['final_equity']['p95'], 2),
            })
            print(f"  ✅ {symbol} {tf:<4} {strategy:<20} "
                  f"ruin={stats['risk']['risk_of_ruin']:.1f}%  "
                  f"median_ret={stats['returns']['median']:+.1f}%  ({elapsed:.0f}s)")

        except Exception as e:
            print(f"  ❌ {symbol} {tf} {strategy}: {str(e)[:60]}")

    return rows_mc


#  save helpers 

def save_json(data, path):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  Saved → {os.path.basename(path)}")

def save_csv(rows, path):
    if not rows:
        print(f"  (empty — skipping {os.path.basename(path)})")
        return
    pd.DataFrame(rows).to_csv(path, index=False)
    print(f"  Saved {len(rows)} rows → {os.path.basename(path)}")


#  main 

if __name__ == '__main__':
    overall_start = time.perf_counter()
    print(f"\n{'='*70}")
    print("SUPREME TEST RUNNER v2 — Trading Engine")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")

    results_cache, rows_main = run_all_backtests()
    rows_ps  = run_position_sizing(results_cache)
    rows_gs  = run_grid_searches()
    rows_wf  = run_walk_forwards()
    rows_mc  = run_monte_carlos(rows_main)

    print(f"\n{'='*70}\nSAVING\n{'='*70}")
    save_json(results_cache, os.path.join(ROOT, 'results_cache.json'))
    save_csv(rows_main,      os.path.join(ROOT, 'results_full.csv'))
    save_csv(rows_ps,        os.path.join(ROOT, 'results_position_sizing.csv'))
    save_csv(rows_gs,        os.path.join(ROOT, 'results_grid_search.csv'))
    save_csv(rows_wf,        os.path.join(ROOT, 'results_walk_forward.csv'))
    save_csv(rows_mc,        os.path.join(ROOT, 'results_monte_carlo.csv'))

    elapsed = time.perf_counter() - overall_start
    ok    = sum(1 for r in rows_main if r.get('status') == 'ok')
    errs  = sum(1 for r in rows_main if r.get('status', 'ok') != 'ok')
    profit = sum(1 for r in rows_main if r.get('status') == 'ok' and r.get('net_pnl', 0) > 0)

    print(f"\n{'='*70}\nSUMMARY\n{'='*70}")
    print(f"  Backtests:       {len(rows_main)}  ({ok} ok, {errs} errors)")
    print(f"  Profitable:      {profit} / {ok}")
    print(f"  Grid combos:     {len(rows_gs)}")
    print(f"  WF windows:      {sum(r.get('windows',0) for r in rows_wf)}")
    print(f"  MC runs:         {len(rows_mc)}")
    print(f"  Total time:      {elapsed/60:.1f} min")

    good = [r for r in rows_main if r.get('status') == 'ok' and r.get('net_pnl')]
    if good:
        best  = max(good, key=lambda r: r['net_pnl'])
        worst = min(good, key=lambda r: r['net_pnl'])
        print(f"\n  🏆 Best:  {best['symbol']} {best['timeframe']} {best['strategy']} "
              f"{'costs' if best['costs_on'] else 'no-costs'} → "
              f"${best['net_pnl']:+,.0f} ({best['return_pct']:+.1f}%)")
        print(f"  💀 Worst: {worst['symbol']} {worst['timeframe']} {worst['strategy']} "
              f"{'costs' if worst['costs_on'] else 'no-costs'} → "
              f"${worst['net_pnl']:+,.0f} ({worst['return_pct']:+.1f}%)")
    print(f"\n  ✅ Done. Open dashboard Tab 11 to browse results.\n")