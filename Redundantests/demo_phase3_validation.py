"""
PHASE 3 DEMO: Walk-Forward Testing + Monte Carlo Simulation


This demo shows how to:
1. Run walk-forward testing (validate robustness)
2. Run Monte Carlo simulation (assess risk)
3. Interpret results for presentation

Author: Trading Engine v2.0 - Phase 3
"""

import sys
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from loader_enhanced import load_price_data, detect_gaps
from strategies.trend_pullback_v3 import TrendPullbackV3
from validation.walk_forward import WalkForwardTester
from simulation.monte_carlo import MonteCarloSimulator
from costs.transaction_costs import get_cost_model
from backtester import Backtester
from metrics import calculate_metrics
from trade import Trade


def run_phase3_demo(data_file: str, symbol: str = 'BTCUSD'):
    """
    Run Phase 3 validation demo.
    
    Args:
        data_file: Path to CSV data
        symbol: Trading symbol
    """
    print("=" * 100)
    print("PHASE 3 DEMO: WALK-FORWARD TESTING + MONTE CARLO SIMULATION")
    print("=" * 100)
    print()
    
    # Load data
    print("📂 Loading data...")
    candles = load_price_data(data_file)
    gaps = detect_gaps(candles, timeframe_minutes=15)
    
    # Use last 50,000 candles for testing
    # candles = candles[-50000:]
    print(f"   ✓ Using {len(candles):,} candles")
    print(f"   ✓ Date range: {candles[0]['time'].date()} to {candles[-1]['time'].date()}")
    print()
    
    # Get cost model
    cost_model = get_cost_model(symbol)
    print(f"💰 Cost Model: {symbol}")
    print(f"   Round-trip cost: ${cost_model.spread_points * 2 + cost_model.slippage_points * 2:.0f}")
    print()
    
    # Use optimized parameters from Phase 2
    print("=" * 100)
    print("USING OPTIMIZED PARAMETERS FROM PHASE 2")
    print("=" * 100)
    print()
    
    optimized_params = {
        'lookback': 200,
        'trend_threshold': 0.002,
        'pullback_threshold': 0.003,
        'min_rr': 2.0,
        'atr_multiplier_sl': 2.0,
        'atr_multiplier_tp': 4.0,
        'volume_filter': True,
        'session_filter': True
    }
    
    print("Optimized Parameters:")
    for key, value in optimized_params.items():
        print(f"   {key}: {value}")
    print()
    
    # === PART 1: WALK-FORWARD TESTING ===
    print("=" * 100)
    print("PART 1: WALK-FORWARD TESTING")
    print("=" * 100)
    print()
    print("This validates that optimized parameters work on UNSEEN future data")
    print("(Not just curve-fitted to the training period)")
    print()
    
    input("Press Enter to start walk-forward testing...")
    print()
    
    # Initialize walk-forward tester
    wf_tester = WalkForwardTester(
        in_sample_periods=50000,   
        out_sample_periods=10000,   
        period_type='candles',
        min_trades_per_window=10
    )
    
    # Define parameter grid (smaller for speed)
    param_grid = {
        'lookback': [100, 200],
        'trend_threshold': [0.001, 0.002, 0.005],
        'pullback_threshold': [0.003, 0.005],
        'min_rr': [2.0, 3.0],
        'atr_multiplier_sl': [1.5, 2.0],
        'atr_multiplier_tp': [3.0, 4.0],
        'volume_filter': [True],
        'session_filter': [True, False]
    }
    
    # Run walk-forward
    wf_results = wf_tester.run_walk_forward(
        strategy_class=TrendPullbackV3,
        candles=candles,
        param_grid=param_grid,
        gaps=gaps,
        cost_model=cost_model,
        verbose=True
    )
    
    # Save walk-forward results
    with open('walk_forward_results.txt', 'w') as f:
        f.write("WALK-FORWARD TESTING RESULTS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date: {datetime.now()}\n")
        f.write(f"Symbol: {symbol}\n")
        f.write(f"Windows tested: {wf_results['summary']['total_windows']}\n\n")
        
        f.write("SUMMARY:\n")
        f.write("-" * 80 + "\n")
        summary = wf_results['summary']
        f.write(f"In-sample Avg R:     {summary['in_sample_avg_r_mean']:.3f}\n")
        f.write(f"Out-of-sample Avg R: {summary['out_sample_avg_r_mean']:.3f}\n")
        f.write(f"Degradation:         {summary['degradation_mean']:.3f} ({summary['degradation_pct']:.1f}%)\n")
        f.write(f"Consistency:         {summary['consistency_score']*100:.1f}%\n\n")
        
        f.write("DETAILED RESULTS BY WINDOW:\n")
        f.write("-" * 80 + "\n")
        for result in wf_results['windows']:
            f.write(f"\nWindow {result['window']}:\n")
            f.write(f"  Period: {result['out_sample_period'][0].date()} to {result['out_sample_period'][1].date()}\n")
            f.write(f"  In-sample:  {result['in_sample_metrics']['total_trades']} trades, "
                   f"{result['in_sample_metrics']['average_r']:.3f} avg R\n")
            f.write(f"  Out-sample: {result['out_sample_metrics']['total_trades']} trades, "
                   f"{result['out_sample_metrics']['average_r']:.3f} avg R\n")
            f.write(f"  Best params: {result['best_params']}\n")
    
    print(f"\n✓ Walk-forward results saved to: walk_forward_results.txt")
    print()
    
    # === PART 2: BASELINE BACKTEST FOR MONTE CARLO ===
    print("=" * 100)
    print("PART 2: RUNNING BASELINE BACKTEST")
    print("=" * 100)
    print()
    print("Running strategy with optimized parameters to get trade history...")
    print()
    
    # Run backtest with optimized parameters
    strategy = TrendPullbackV3(candles, **optimized_params)
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
    
    print("Baseline Results:")
    print(f"   Total Trades: {metrics['total_trades']}")
    print(f"   Win Rate: {metrics['win_rate']*100:.2f}%")
    print(f"   Average R: {metrics['average_r']:.3f}")
    print(f"   Total R: {metrics['total_r']:.2f}")
    print()
    
    if metrics['total_trades'] < 30:
        print("⚠️  WARNING: Not enough trades for reliable Monte Carlo simulation")
        print("   Need at least 30 trades, preferably 100+")
        print()
    
    # === PART 3: MONTE CARLO SIMULATION ===
    print("=" * 100)
    print("PART 3: MONTE CARLO SIMULATION")
    print("=" * 100)
    print()
    print("This shows the DISTRIBUTION of possible outcomes by randomizing trade order")
    print("(What COULD have happened with same trades in different sequence)")
    print()
    
    input("Press Enter to start Monte Carlo simulation (10,000 runs)...")
    print()
    
    # Initialize simulator
    mc_sim = MonteCarloSimulator(n_simulations=10000)
    
    # Run simulation
    mc_results = mc_sim.simulate(
        trades=trades,
        initial_capital=10000,
        risk_per_trade=0.01,
        verbose=True
    )
    
    # Save Monte Carlo results
    with open('monte_carlo_results.txt', 'w') as f:
        f.write("MONTE CARLO SIMULATION RESULTS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date: {datetime.now()}\n")
        f.write(f"Symbol: {symbol}\n")
        f.write(f"Trades analyzed: {len(trades)}\n")
        f.write(f"Simulations: {mc_results['simulations']:,}\n")
        f.write(f"Initial capital: ${mc_results['initial_capital']:,.2f}\n\n")
        
        f.write("FINAL EQUITY DISTRIBUTION:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Mean:              ${mc_results['final_equity']['mean']:,.2f}\n")
        f.write(f"Median:            ${mc_results['final_equity']['median']:,.2f}\n")
        f.write(f"95% Confidence:    ${mc_results['final_equity']['p5']:,.2f} - ${mc_results['final_equity']['p95']:,.2f}\n\n")
        
        f.write("RETURN DISTRIBUTION:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Mean:              {mc_results['returns']['mean']:.2f}%\n")
        f.write(f"Median:            {mc_results['returns']['median']:.2f}%\n")
        f.write(f"95% Confidence:    {mc_results['returns']['p5']:.2f}% - {mc_results['returns']['p95']:.2f}%\n\n")
        
        f.write("RISK METRICS:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Risk of Ruin:             {mc_results['risk']['risk_of_ruin']:.2f}%\n")
        f.write(f"Probability of Profit:    {mc_results['risk']['prob_profitable']:.1f}%\n")
        f.write(f"P(Drawdown > 20%):        {mc_results['risk']['prob_dd_gt_20pct']:.1f}%\n")
        f.write(f"P(Drawdown > 30%):        {mc_results['risk']['prob_dd_gt_30pct']:.1f}%\n")
        f.write(f"P(Drawdown > 50%):        {mc_results['risk']['prob_dd_gt_50pct']:.1f}%\n")
    
    print(f"\n✓ Monte Carlo results saved to: monte_carlo_results.txt")
    print()
    
    # === SUMMARY ===
    print("=" * 100)
    print("PHASE 3 COMPLETE - KEY FINDINGS")
    print("=" * 100)
    print()
    
    print("1. WALK-FORWARD VALIDATION:")
    print("-" * 100)
    if wf_results['summary']['degradation_pct'] < 30:
        print(f"   ✅ Strategy is ROBUST - only {wf_results['summary']['degradation_pct']:.1f}% degradation out-of-sample")
    else:
        print(f"   ⚠️  Strategy shows {wf_results['summary']['degradation_pct']:.1f}% degradation - may be overfit")
    
    print(f"   • Consistency: {wf_results['summary']['consistency_score']*100:.1f}% of windows profitable")
    print(f"   • Out-of-sample Avg R: {wf_results['summary']['out_sample_avg_r_mean']:.3f}")
    print()
    
    print("2. MONTE CARLO RISK ASSESSMENT:")
    print("-" * 100)
    print(f"   • Expected return: {mc_results['returns']['median']:.1f}% (median)")
    print(f"   • 95% confidence: {mc_results['returns']['p5']:.1f}% to {mc_results['returns']['p95']:.1f}%")
    print(f"   • Risk of ruin: {mc_results['risk']['risk_of_ruin']:.2f}%")
    print(f"   • Probability of profit: {mc_results['risk']['prob_profitable']:.1f}%")
    print()
    
    print("3. RECOMMENDATIONS:")
    print("-" * 100)
    
    if mc_results['risk']['risk_of_ruin'] > 5:
        print("   ❌ HIGH RISK - Risk of ruin >5%, not recommended for live trading")
    elif mc_results['returns']['median'] < 5:
        print("   ⚠️  MARGINAL - Returns too low to justify risk")
    elif wf_results['summary']['consistency_score'] < 0.5:
        print("   ⚠️  INCONSISTENT - Strategy unreliable across different periods")
    else:
        print("   ✅ ACCEPTABLE - Strategy shows reasonable risk/reward profile")
    
    print()
    
    print("=" * 100)
    print("✅ PHASE 3 VALIDATION COMPLETE!")
    print("=" * 100)
    print()
    
    print("What you learned:")
    print("✓ How to validate strategy robustness (walk-forward)")
    print("✓ How to assess risk distribution (Monte Carlo)")
    print("✓ How to interpret out-of-sample performance")
    print("✓ How to quantify uncertainty in results")
    print()
    
    print("Files created:")
    print("✓ walk_forward_results.txt")
    print("✓ monte_carlo_results.txt")
    print()
    
    print("Next steps:")
    print("1. Review both result files")
    print("2. Move to Phase 4 (PDF Reports + Visualization)")
    print("3. Prepare presentation materials")
    print()


def main():
    """Main entry point."""
    data_file = "data/BTC_M15.csv"
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        print("   Please ensure BTC_M15.csv is in the data/ directory")
        return
    
    run_phase3_demo(data_file, symbol='BTCUSD')


if __name__ == "__main__":
    main()
