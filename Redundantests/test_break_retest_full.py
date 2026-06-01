"""
BREAK-RETEST STRATEGY FULL TEST
================================
Tests Break-Retest strategy on complete dataset with costs.

This strategy is PROFITABLE while Trend Pullback lost money.
"""

import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from loader_enhanced import load_price_data, detect_gaps
from strategies.break_retest import BreakRetestStrategy
from backtester import Backtester
from metrics import calculate_metrics
from costs.transaction_costs import get_cost_model
from trade import Trade


def test_break_retest_full():
    """Test Break-Retest on full BTC M15 dataset."""
    
    print("=" * 80)
    print("BREAK-RETEST STRATEGY - FULL BACKTEST")
    print("=" * 80)
    print()
    
    # Load data
    print("📂 Loading data...")
    candles = load_price_data("data/BTC_M15.csv")
    gaps = detect_gaps(candles, timeframe_minutes=15)
    
    # Use all data
    print(f"   ✓ Total candles: {len(candles):,}")
    print(f"   ✓ Date range: {candles[0]['time'].date()} to {candles[-1]['time'].date()}")
    print(f"   ✓ Gaps detected: {len(gaps)}")
    print()
    
    # === TEST 1: WITHOUT COSTS ===
    print("-" * 80)
    print("TEST 1: Without Transaction Costs")
    print("-" * 80)
    
    strategy_no_cost = BreakRetestStrategy(candles, gaps)
    backtester = Backtester(candles, gaps, strategy_no_cost)
    trades_no_cost = backtester.run()
    metrics_no_cost = calculate_metrics(trades_no_cost)
    
    print(f"Total Trades: {metrics_no_cost['total_trades']}")
    print(f"Win Rate: {metrics_no_cost['win_rate']*100:.2f}%")
    print(f"Average R: {metrics_no_cost['average_r']:.3f}")
    print(f"Total R: {metrics_no_cost['total_r']:.2f}")
    print(f"Max Drawdown (R): {metrics_no_cost['max_drawdown_r']:.2f}")
    print()
    
    # === TEST 2: WITH COSTS ===
    print("-" * 80)
    print("TEST 2: With Transaction Costs (Realistic)")
    print("-" * 80)
    
    cost_model = get_cost_model('BTCUSD')
    print(f"Cost Model: BTCUSD")
    print(f"   Spread: ${cost_model.spread_points}")
    print(f"   Slippage: ${cost_model.slippage_points}")
    print()
    
    # Run with costs
    strategy_with_cost = BreakRetestStrategy(candles, gaps)
    backtester_cost = Backtester(candles, gaps, strategy_with_cost)
    raw_trades = backtester_cost.run()
    
    # Apply costs
    trades_with_cost = []
    for t in raw_trades:
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
        trades_with_cost.append(enhanced)
    
    metrics_with_cost = calculate_metrics(trades_with_cost)
    
    print(f"Total Trades: {metrics_with_cost['total_trades']}")
    print(f"Win Rate: {metrics_with_cost['win_rate']*100:.2f}%")
    print(f"Average R: {metrics_with_cost['average_r']:.3f}")
    print(f"Total R: {metrics_with_cost['total_r']:.2f}")
    print(f"Max Drawdown (R): {metrics_with_cost['max_drawdown_r']:.2f}")
    print()
    
    # Calculate costs
    total_costs = sum(t.total_costs for t in trades_with_cost)
    total_gross = sum(t.gross_pnl for t in trades_with_cost)
    total_net = sum(t.net_pnl for t in trades_with_cost)
    
    print(f"💰 Financial Summary:")
    print(f"   Gross P&L: ${total_gross:,.2f}")
    print(f"   Total Costs: ${total_costs:,.2f}")
    print(f"   Net P&L: ${total_net:,.2f}")
    print()
    
    # === COMPARISON ===
    print("=" * 80)
    print("COMPARISON: Break-Retest vs Trend Pullback")
    print("=" * 80)
    print()
    
    print(f"{'Metric':<25} {'Break-Retest':>15} {'Trend Pullback':>15}")
    print("-" * 80)
    print(f"{'Average R':<25} {metrics_with_cost['average_r']:>15.3f} {-0.621:>15.3f}")
    print(f"{'Total R':<25} {metrics_with_cost['total_r']:>15.2f} {-2948.79:>15.2f}")
    print(f"{'Win Rate (%)':<25} {metrics_with_cost['win_rate']*100:>15.2f} {33.40:>15.2f}")
    print()
    
    # === VERDICT ===
    print("=" * 80)
    print("VERDICT")
    print("=" * 80)
    print()
    
    if metrics_with_cost['average_r'] > 0:
        print("✅ BREAK-RETEST IS PROFITABLE!")
        print(f"   Average R: {metrics_with_cost['average_r']:.3f} (positive expectancy)")
        print(f"   Total R: {metrics_with_cost['total_r']:.2f}")
        print()
        print("NEXT STEPS:")
        print("1. Run parameter optimization on Break-Retest")
        print("2. Perform walk-forward validation")
        print("3. Run Monte Carlo simulation")
        print("4. If all tests pass, consider paper trading")
    else:
        print("❌ BREAK-RETEST ALSO UNPROFITABLE")
        print(f"   Average R: {metrics_with_cost['average_r']:.3f}")
        print()
        print("DIAGNOSIS:")
        print("- Transaction costs may be too high")
        print("- M15 timeframe may be too short for this approach")
        print("- Need to try different strategy types")
    
    print()
    
    return trades_with_cost, metrics_with_cost


if __name__ == "__main__":
    test_break_retest_full()