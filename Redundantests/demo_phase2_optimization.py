"""
PHASE 2 DEMO: Parameter Optimization
=====================================

This demo shows how to:
1. Define a parameter grid
2. Run grid search optimization
3. Compare optimized vs baseline results
4. Save best parameters

Author: Trading Engine v2.0 - Phase 2
"""

import sys
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from loader_enhanced import load_price_data, detect_gaps
from strategies.trend_pullback_v3 import TrendPullbackV3
from optimization.grid_search import GridSearchOptimizer
from costs.transaction_costs import get_cost_model
from backtester import Backtester
from metrics import calculate_metrics
from trade import Trade


def run_optimization_demo(data_file: str, symbol: str = 'BTCUSD'):
    """
    Run parameter optimization demo.
    
    Args:
        data_file: Path to CSV data
        symbol: Trading symbol
    """
    print("=" * 100)
    print("PHASE 2 DEMO: PARAMETER OPTIMIZATION")
    print("=" * 100)
    print()
    
    # Load data
    print("📂 Loading data...")
    candles = load_price_data(data_file)
    gaps = detect_gaps(candles, timeframe_minutes=15)
    
    # Use subset for faster demo (last 50,000 candles = ~1.4 years on M15)
    # candles = candles[-50000:]
    print(f"   ✓ Using {len(candles):,} candles")
    print(f"   ✓ Date range: {candles[0]['time']} to {candles[-1]['time']}")
    print()
    
    # Get cost model
    cost_model = get_cost_model(symbol)
    print(f"💰 Cost Model: {symbol}")
    print(f"   Spread: ${cost_model.spread_points:.2f}")
    print(f"   Slippage: ${cost_model.slippage_points:.2f}")
    print()
    
    # === BASELINE TEST ===
    print("=" * 100)
    print("STEP 1: BASELINE (Default Parameters)")
    print("=" * 100)
    print()
    
    baseline_params = {
        'lookback': 100,
        'trend_threshold': 0.002,
        'pullback_threshold': 0.005,
        'min_rr': 2.0,
        'atr_multiplier_sl': 1.5,
        'atr_multiplier_tp': 3.0,
        'volume_filter': False,
        'session_filter': False
    }
    
    print("Baseline Parameters:")
    for key, value in baseline_params.items():
        print(f"   {key}: {value}")
    print()
    
    # Run baseline
    strategy_baseline = TrendPullbackV3(candles, **baseline_params)
    backtester_baseline = Backtester(candles, gaps, strategy_baseline)
    trades_baseline_raw = backtester_baseline.run()
    
    # Apply costs
    trades_baseline = []
    for t in trades_baseline_raw:
        enhanced = Trade(
            entry_idx=t.entry_idx,
            entry_price=t.entry_price,
            direction=t.direction,
            sl=t.sl,
            tp=t.tp,
            size=t.size,
            cost_model=cost_model
        )
        enhanced._close(t.exit_idx, t.exit_price)
        trades_baseline.append(enhanced)
    
    metrics_baseline = calculate_metrics(trades_baseline)
    
    print("Baseline Results:")
    print(f"   Total Trades: {metrics_baseline['total_trades']}")
    print(f"   Win Rate: {metrics_baseline['win_rate']*100:.2f}%")
    print(f"   Average R: {metrics_baseline['average_r']:.3f}")
    print(f"   Total R: {metrics_baseline['total_r']:.2f}")
    print(f"   Max DD (R): {metrics_baseline['max_drawdown_r']:.2f}")
    
    if trades_baseline:
        total_costs = sum(t.total_costs for t in trades_baseline)
        total_gross = sum(t.gross_pnl for t in trades_baseline)
        total_net = sum(t.net_pnl for t in trades_baseline)
        print(f"   Gross P&L: ${total_gross:,.2f}")
        print(f"   Costs: ${total_costs:,.2f}")
        print(f"   Net P&L: ${total_net:,.2f}")
    
    print()
    
    # === OPTIMIZATION ===
    print("=" * 100)
    print("STEP 2: GRID SEARCH OPTIMIZATION")
    print("=" * 100)
    print()
    
    # Define parameter grid
    param_grid = {
        'lookback': [50, 100, 200],
        'trend_threshold': [0.001, 0.002, 0.005],
        'pullback_threshold': [0.003, 0.005, 0.010],
        'min_rr': [1.5, 2.0, 3.0],
        'atr_multiplier_sl': [1.0, 1.5, 2.0],
        'atr_multiplier_tp': [2.0, 3.0, 4.0],
        'volume_filter': [False, True],
        'session_filter': [False, True]
    }
    
    print("Parameter Grid:")
    total_combinations = 1
    for key, values in param_grid.items():
        print(f"   {key}: {values}")
        total_combinations *= len(values)
    print()
    print(f"Total combinations: {total_combinations:,}")
    print()
    
    print("⚠️  NOTE: This will take a while...")
    print("   Approximate time: 2-5 minutes")
    print()
    
    input("Press Enter to start optimization...")
    print()
    
    # Run optimization
    optimizer = GridSearchOptimizer(
        metric='average_r',
        min_trades=100
    )
    
    results = optimizer.optimize(
        strategy_class=TrendPullbackV3,
        candles=candles,
        param_grid=param_grid,
        gaps=gaps,
        cost_model=cost_model,
        verbose=True
    )
    
    # === RESULTS ===
    print("=" * 100)
    print("STEP 3: OPTIMIZATION RESULTS")
    print("=" * 100)
    print()
    
    if not results:
        print("❌ No valid results found!")
        print("   Try:")
        print("   - Reducing min_trades requirement")
        print("   - Using more data")
        print("   - Adjusting parameter ranges")
        return
    
    # Best result
    best = results[0]
    print("🏆 BEST PARAMETERS FOUND:")
    print()
    for key, value in best['params'].items():
        baseline_val = baseline_params.get(key, 'N/A')
        print(f"   {key}: {value} (baseline: {baseline_val})")
    print()
    
    print("Best Performance:")
    print(f"   Total Trades: {best['total_trades']}")
    print(f"   Win Rate: {best['win_rate']*100:.2f}%")
    print(f"   Average R: {best['average_r']:.3f}")
    print(f"   Total R: {best['total_r']:.2f}")
    print(f"   Max DD (R): {best['max_dd']:.2f}")
    print()
    
    # === COMPARISON ===
    print("=" * 100)
    print("IMPROVEMENT vs BASELINE")
    print("=" * 100)
    print()
    
    print(f"{'Metric':<25} {'Baseline':>15} {'Optimized':>15} {'Change':>15}")
    print("-" * 100)
    print(f"{'Total Trades':<25} {metrics_baseline['total_trades']:>15} {best['total_trades']:>15} {best['total_trades'] - metrics_baseline['total_trades']:>15}")
    print(f"{'Win Rate (%)':<25} {metrics_baseline['win_rate']*100:>15.2f} {best['win_rate']*100:>15.2f} {(best['win_rate'] - metrics_baseline['win_rate'])*100:>15.2f}")
    print(f"{'Average R':<25} {metrics_baseline['average_r']:>15.3f} {best['average_r']:>15.3f} {best['average_r'] - metrics_baseline['average_r']:>15.3f}")
    print(f"{'Total R':<25} {metrics_baseline['total_r']:>15.2f} {best['total_r']:>15.2f} {best['total_r'] - metrics_baseline['total_r']:>15.2f}")
    print(f"{'Max DD (R)':<25} {metrics_baseline['max_drawdown_r']:>15.2f} {best['max_dd']:>15.2f} {best['max_dd'] - metrics_baseline['max_drawdown_r']:>15.2f}")
    print()
    
    # Calculate improvement percentage
    if metrics_baseline['average_r'] != 0:
        improvement_pct = ((best['average_r'] - metrics_baseline['average_r']) / abs(metrics_baseline['average_r'])) * 100
        print(f"📈 Average R Improvement: {improvement_pct:+.1f}%")
    
    if metrics_baseline['total_r'] != 0:
        total_r_improvement = best['total_r'] - metrics_baseline['total_r']
        print(f"📈 Total R Improvement: {total_r_improvement:+.2f} R")
    
    print()
    
    # === TOP 10 ===
    print("=" * 100)
    print("TOP 10 PARAMETER SETS")
    print("=" * 100)
    print()
    
    print(f"{'Rank':<6} {'Avg R':<10} {'Total R':<12} {'Win %':<10} {'Trades':<10} {'Key Params'}")
    print("-" * 100)
    
    for i, result in enumerate(results[:10], 1):
        key_params = f"lookback={result['params']['lookback']}, min_rr={result['params']['min_rr']}"
        print(f"{i:<6} {result['average_r']:<10.3f} {result['total_r']:<12.2f} {result['win_rate']*100:<10.1f} {result['total_trades']:<10} {key_params}")
    
    print()
    
    # === SAVE RESULTS ===
    print("=" * 100)
    print("SAVING RESULTS")
    print("=" * 100)
    print()
    
    # Save to file
    output_file = 'optimization_results.txt'
    with open(output_file, 'w') as f:
        f.write("PARAMETER OPTIMIZATION RESULTS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date: {datetime.now()}\n")
        f.write(f"Symbol: {symbol}\n")
        f.write(f"Data points: {len(candles):,}\n")
        f.write(f"Combinations tested: {total_combinations:,}\n")
        f.write(f"Valid results: {len(results)}\n\n")
        
        f.write("BEST PARAMETERS:\n")
        f.write("-" * 80 + "\n")
        for key, value in best['params'].items():
            f.write(f"{key}: {value}\n")
        f.write("\n")
        
        f.write("BEST PERFORMANCE:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Trades: {best['total_trades']}\n")
        f.write(f"Win Rate: {best['win_rate']*100:.2f}%\n")
        f.write(f"Average R: {best['average_r']:.3f}\n")
        f.write(f"Total R: {best['total_r']:.2f}\n")
        f.write(f"Max DD: {best['max_dd']:.2f}\n\n")
        
        f.write("TOP 10 RESULTS:\n")
        f.write("-" * 80 + "\n")
        for i, result in enumerate(results[:10], 1):
            f.write(f"\n#{i}\n")
            f.write(f"Avg R: {result['average_r']:.3f}, Total R: {result['total_r']:.2f}, Win Rate: {result['win_rate']*100:.1f}%\n")
            f.write(f"Parameters: {result['params']}\n")
    
    print(f"✓ Results saved to: {output_file}")
    print()
    


def main():
    """Main entry point."""
    data_file = "data/BTC_M15.csv"
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        print("   Please ensure BTC_M15.csv is in the data/ directory")
        return
    
    run_optimization_demo(data_file, symbol='BTCUSD')


if __name__ == "__main__":
    main()
