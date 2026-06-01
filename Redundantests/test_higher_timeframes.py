"""
Test Break-Retest on Higher Timeframes
=======================================
The problem is NOT your strategy - it's your timeframe!
M15 = too many trades = too many costs

Let's test on H1/H4 where costs matter less.
"""

import sys
import os
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from loader_enhanced import load_price_data, detect_gaps
from strategies.break_retest import BreakRetestStrategy
from backtester import Backtester
from metrics import calculate_metrics
from costs.transaction_costs import get_cost_model
from trade import Trade


def resample_to_timeframe(candles, minutes):
    """Resample M15 data to higher timeframe."""
    df = pd.DataFrame(candles)
    df.set_index('time', inplace=True)
    
    # Resample to target timeframe
    resampled = df.resample(f'{minutes}T').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    # Convert back to list of dicts
    result = []
    for time, row in resampled.iterrows():
        result.append({
            'time': time,
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row['volume']
        })
    
    return result


def test_timeframe(candles_m15, timeframe_minutes, name):
    """Test strategy on a specific timeframe."""
    print(f"\n{'='*80}")
    print(f"TESTING: {name} ({timeframe_minutes} minutes)")
    print(f"{'='*80}")
    
    # Resample data
    candles = resample_to_timeframe(candles_m15, timeframe_minutes)
    print(f"Candles: {len(candles):,}")
    print(f"Date range: {candles[0]['time'].date()} to {candles[-1]['time'].date()}")
    
    gaps = detect_gaps(candles, timeframe_minutes)
    cost_model = get_cost_model('BTCUSD')
    
    # Run backtest
    strategy = BreakRetestStrategy(candles, gaps)
    backtester = Backtester(candles, gaps, strategy)
    raw_trades = backtester.run()
    
    # Apply costs
    trades = []
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
        trades.append(enhanced)
    
    metrics = calculate_metrics(trades)
    
    # Calculate financials
    total_gross = sum(t.gross_pnl for t in trades) if trades else 0
    total_costs = sum(t.total_costs for t in trades) if trades else 0
    total_net = sum(t.net_pnl for t in trades) if trades else 0
    
    print(f"\nRESULTS:")
    print(f"  Trades: {metrics['total_trades']}")
    print(f"  Trades per day: {metrics['total_trades'] / (len(candles) * timeframe_minutes / 1440):.1f}")
    print(f"  Win Rate: {metrics['win_rate']*100:.2f}%")
    print(f"  Average R (with costs): {metrics['average_r']:.3f}")
    print(f"  Total R: {metrics['total_r']:.2f}")
    print(f"  Gross P&L: ${total_gross:,.0f}")
    print(f"  Transaction Costs: ${total_costs:,.0f}")
    print(f"  Net P&L: ${total_net:,.0f}")
    print(f"  Cost/Gross Ratio: {abs(total_costs/total_gross)*100:.1f}%" if total_gross != 0 else "")
    
    return {
        'timeframe': name,
        'trades': metrics['total_trades'],
        'avg_r': metrics['average_r'],
        'total_r': metrics['total_r'],
        'net_pnl': total_net,
        'cost_ratio': abs(total_costs/total_gross)*100 if total_gross != 0 else 0
    }


def main():
    print("="*80)
    print("TIMEFRAME ANALYSIS: Finding the Sweet Spot")
    print("="*80)
    print("\nHypothesis: M15 has too many trades → too many costs")
    print("Solution: Higher timeframe = fewer trades = costs matter less")
    print()
    
    # Load M15 data
    print("Loading M15 data...")
    candles_m15 = load_price_data("data/BTC_M15.csv")
    print(f"Loaded {len(candles_m15):,} M15 candles")
    print()
    
    # Test different timeframes
    results = []
    
    # M15 (baseline - we know this fails)
    print("\n" + "="*80)
    print("BASELINE: M15 (Your Current Timeframe)")
    print("="*80)
    gaps_m15 = detect_gaps(candles_m15, 15)
    strategy_m15 = BreakRetestStrategy(candles_m15, gaps_m15)
    backtester_m15 = Backtester(candles_m15, gaps_m15, strategy_m15)
    raw_m15 = backtester_m15.run()
    
    cost_model = get_cost_model('BTCUSD')
    trades_m15 = []
    for t in raw_m15:
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
        trades_m15.append(enhanced)
    
    metrics_m15 = calculate_metrics(trades_m15)
    results.append({
        'timeframe': 'M15',
        'trades': metrics_m15['total_trades'],
        'avg_r': metrics_m15['average_r'],
        'total_r': metrics_m15['total_r'],
        'net_pnl': sum(t.net_pnl for t in trades_m15),
        'cost_ratio': abs(sum(t.total_costs for t in trades_m15) / sum(t.gross_pnl for t in trades_m15)) * 100
    })
    
    print(f"Avg R: {metrics_m15['average_r']:.3f} | Net PnL: ${sum(t.net_pnl for t in trades_m15):,.0f}")
    
    # M30
    results.append(test_timeframe(candles_m15, 30, "M30"))
    
    # H1
    results.append(test_timeframe(candles_m15, 60, "H1"))
    
    # H4
    results.append(test_timeframe(candles_m15, 240, "H4"))
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY: Timeframe Comparison")
    print("="*80)
    print(f"\n{'Timeframe':<12} {'Trades':<10} {'Avg R':<12} {'Total R':<12} {'Net PnL':<15} {'Cost %':<10}")
    print("-"*80)
    
    for r in results:
        print(f"{r['timeframe']:<12} {r['trades']:<10} {r['avg_r']:<12.3f} {r['total_r']:<12.2f} "
              f"${r['net_pnl']:<14,.0f} {r['cost_ratio']:<10.1f}%")
    
    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)
    
    # Find best timeframe
    profitable = [r for r in results if r['avg_r'] > 0]
    
    if profitable:
        best = max(profitable, key=lambda x: x['avg_r'])
        print(f"\n✅ BEST TIMEFRAME: {best['timeframe']}")
        print(f"   Average R: {best['avg_r']:.3f}")
        print(f"   Total R: {best['total_r']:.2f}")
        print(f"   Net P&L: ${best['net_pnl']:,.0f}")
        print(f"\n🎯 ACTION: Switch to {best['timeframe']} for this strategy!")
    else:
        print("\n❌ NO TIMEFRAME IS PROFITABLE")
        print("\nThis means:")
        print("1. Transaction costs are too high for ANY timeframe")
        print("2. Strategy logic is fundamentally flawed")
        print("3. Or BTC M15 data doesn't suit this strategy type")
        print("\nTRY:")
        print("- Different asset (lower spread)")
        print("- Different broker (lower costs)")
        print("- Completely different strategy approach")


if __name__ == "__main__":
    main()