"""
PHASE 1 DEMO (SIMPLIFIED): Transaction Costs Integration
=========================================================

This demo shows transaction costs integration WITHOUT database
(database requires SQLAlchemy which needs network)

Demonstrates:
1. Running backtests WITH and WITHOUT transaction costs
2. Comparing the impact of costs on performance
3. Trade-level cost breakdown

Author: Trading Engine v2.0
"""

import sys
import os

# Add parent directory to path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# Import modules
from loader_enhanced import load_price_data, detect_gaps
from backtester import Backtester
from strategy_factory import StrategyFactory
from metrics import calculate_metrics
from costs.transaction_costs import CostModel, SymbolCostConfig
from trade import Trade


def run_cost_comparison(data_file: str, symbol: str = 'BTCUSD'):
    """
    Run demo comparing backtests with and without costs.
    
    Args:
        data_file: Path to CSV file
        symbol: Trading symbol
    """
    print("=" * 80)
    print("PHASE 1 DEMO: Transaction Costs Impact Analysis")
    print("=" * 80)
    print()
    
    # Load data
    print(f"📂 Loading data from: {data_file}")
    candles = load_price_data(data_file)
    print(f"   ✓ Loaded {len(candles):,} candles")
    print(f"   ✓ Date range: {candles[0]['time']} to {candles[-1]['time']}")
    print()
    
    # Detect gaps
    gaps = detect_gaps(candles, timeframe_minutes=15)
    print(f"   ✓ Detected {len(gaps)} gaps in data")
    print()
    
    # Strategy to test
    strategy_name = 'break_retest'
    print(f"📊 Testing Strategy: {strategy_name}")
    print()
    
    # === BACKTEST 1: WITHOUT COSTS ===
    print("-" * 80)
    print("TEST 1: Backtest WITHOUT Transaction Costs (Original)")
    print("-" * 80)
    
    strategy_no_cost = StrategyFactory.create(
        strategy_name, 
        candles, 
        {'gaps': gaps}
    )
    
    backtester_no_cost = Backtester(candles, gaps, strategy_no_cost)
    trades_no_cost = backtester_no_cost.run()
    metrics_no_cost = calculate_metrics(trades_no_cost)
    
    print(f"Total Trades: {metrics_no_cost['total_trades']}")
    print(f"Win Rate: {metrics_no_cost['win_rate']*100:.2f}%")
    print(f"Average R: {metrics_no_cost['average_r']:.3f}")
    print(f"Total R: {metrics_no_cost['total_r']:.2f}")
    print(f"Max Drawdown (R): {metrics_no_cost['max_drawdown_r']:.2f}")
    print()
    
    # === BACKTEST 2: WITH COSTS ===
    print("-" * 80)
    print("TEST 2: Backtest WITH Transaction Costs (Realistic)")
    print("-" * 80)
    
    # Get cost model for symbol
    cost_model = SymbolCostConfig.get_cost_model(symbol)
    print(f"Cost Model for {symbol}:")
    print(f"   Spread: {cost_model.spread_points} points")
    print(f"   Commission: ${cost_model.commission_per_lot} per lot")
    print(f"   Slippage: {cost_model.slippage_points} points")
    print()
    
    # Create strategy
    strategy_with_cost = StrategyFactory.create(
        strategy_name, 
        candles, 
        {'gaps': gaps}
    )
    
    # Run backtest and inject cost model
    trades_with_cost = []
    backtester_with_cost = Backtester(candles, gaps, strategy_with_cost)
    raw_trades = backtester_with_cost.run()
    
    # Recreate trades with cost model
    for trade in raw_trades:
        enhanced_trade = Trade(
            entry_idx=trade.entry_idx,
            entry_price=trade.entry_price,
            direction=trade.direction,
            sl=trade.sl,
            tp=trade.tp,
            size=trade.size,
            cost_model=cost_model  # Add cost model
        )
        # Force exit with same parameters
        enhanced_trade._close(trade.exit_idx, trade.exit_price)
        trades_with_cost.append(enhanced_trade)
    
    metrics_with_cost = calculate_metrics(trades_with_cost)
    
    print(f"Total Trades: {metrics_with_cost['total_trades']}")
    print(f"Win Rate: {metrics_with_cost['win_rate']*100:.2f}%")
    print(f"Average R: {metrics_with_cost['average_r']:.3f}")
    print(f"Total R: {metrics_with_cost['total_r']:.2f}")
    print(f"Max Drawdown (R): {metrics_with_cost['max_drawdown_r']:.2f}")
    print()
    
    # Calculate total costs
    total_costs = sum(t.total_costs for t in trades_with_cost)
    total_gross_pnl = sum(t.gross_pnl for t in trades_with_cost)
    total_net_pnl = sum(t.net_pnl for t in trades_with_cost)
    
    print(f"💰 Financial Summary:")
    print(f"   Gross P&L: ${total_gross_pnl:,.2f}")
    print(f"   Total Costs: ${total_costs:,.2f}")
    print(f"   Net P&L: ${total_net_pnl:,.2f}")
    print(f"   Cost as % of Gross: {abs(total_costs/total_gross_pnl)*100:.2f}%")
    print()
    
    # === COMPARISON TABLE ===
    print("=" * 80)
    print("IMPACT ANALYSIS: Costs vs No Costs")
    print("=" * 80)
    print()
    
    print(f"{'Metric':<25} {'Without Costs':>15} {'With Costs':>15} {'Impact':>15}")
    print("-" * 80)
    print(f"{'Total Trades':<25} {metrics_no_cost['total_trades']:>15} {metrics_with_cost['total_trades']:>15} {0:>15}")
    print(f"{'Win Rate (%)':<25} {metrics_no_cost['win_rate']*100:>15.2f} {metrics_with_cost['win_rate']*100:>15.2f} {(metrics_with_cost['win_rate'] - metrics_no_cost['win_rate'])*100:>15.2f}")
    print(f"{'Average R':<25} {metrics_no_cost['average_r']:>15.3f} {metrics_with_cost['average_r']:>15.3f} {metrics_with_cost['average_r'] - metrics_no_cost['average_r']:>15.3f}")
    print(f"{'Total R':<25} {metrics_no_cost['total_r']:>15.2f} {metrics_with_cost['total_r']:>15.2f} {metrics_with_cost['total_r'] - metrics_no_cost['total_r']:>15.2f}")
    print(f"{'Max DD (R)':<25} {metrics_no_cost['max_drawdown_r']:>15.2f} {metrics_with_cost['max_drawdown_r']:>15.2f} {metrics_with_cost['max_drawdown_r'] - metrics_no_cost['max_drawdown_r']:>15.2f}")
    print(f"{'Total Costs ($)':<25} {'$0.00':>15} {f'${total_costs:,.2f}':>15} {f'-${total_costs:,.2f}':>15}")
    print()
    
    # === TRADE-LEVEL ANALYSIS ===
    print("=" * 80)
    print("SAMPLE TRADE BREAKDOWN (First 5 trades with costs)")
    print("=" * 80)
    print()
    
    for i, trade in enumerate(trades_with_cost[:5], 1):
        costs = trade.get_cost_breakdown()
        print(f"Trade #{i}: {trade.direction.upper()}")
        print(f"   Entry: ${trade.entry_price:.2f} → Actual: ${trade.actual_entry_price:.2f}")
        print(f"   Exit: ${trade.exit_price:.2f} → Actual: ${trade.actual_exit_price:.2f}")
        print(f"   Gross P&L: ${costs['gross_pnl']:.2f}")
        print(f"   Total Costs: ${costs['total_costs']:.2f}")
        print(f"   Net P&L: ${costs['net_pnl']:.2f}")
        print(f"   R-Multiple: {trade.r_multiple():.3f} | Result: {trade.result}")
        print()
    
    # === COST BREAKDOWN ===
    print("=" * 80)
    print("AGGREGATE COST BREAKDOWN")
    print("=" * 80)
    print()
    
    total_entry_spread = sum(t.entry_costs.get('spread_cost', 0) for t in trades_with_cost)
    total_exit_spread = sum(t.exit_costs.get('spread_cost', 0) for t in trades_with_cost)
    total_entry_slippage = sum(t.entry_costs.get('slippage_cost', 0) for t in trades_with_cost)
    total_exit_slippage = sum(t.exit_costs.get('slippage_cost', 0) for t in trades_with_cost)
    total_commission = sum(
        t.entry_costs.get('commission', 0) + t.exit_costs.get('commission', 0) 
        for t in trades_with_cost
    )
    
    print(f"Entry Spread Costs:  ${total_entry_spread:,.2f}")
    print(f"Exit Spread Costs:   ${total_exit_spread:,.2f}")
    print(f"Entry Slippage:      ${total_entry_slippage:,.2f}")
    print(f"Exit Slippage:       ${total_exit_slippage:,.2f}")
    print(f"Commissions:         ${total_commission:,.2f}")
    print("-" * 40)
    print(f"TOTAL COSTS:         ${total_costs:,.2f}")
    print()
    
    # === PERFORMANCE DEGRADATION ===
    print("=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)
    print()
    
    r_degradation = metrics_no_cost['total_r'] - metrics_with_cost['total_r']
    avg_r_degradation = metrics_no_cost['average_r'] - metrics_with_cost['average_r']
    
    print(f"✓ Transaction costs reduced Total R by {r_degradation:.2f} R")
    print(f"✓ Average R per trade decreased by {avg_r_degradation:.3f}")
    print(f"✓ Costs consumed {abs(total_costs/total_gross_pnl)*100:.2f}% of gross profits")
    print(f"✓ Net profitability: ${total_net_pnl:,.2f}")
    
    if metrics_with_cost['average_r'] < 0:
        print(f"\n⚠️  WARNING: Strategy is UNPROFITABLE after costs!")
        print(f"   Average R is negative ({metrics_with_cost['average_r']:.3f})")
        print(f"   Consider:")
        print(f"   - Optimizing entry/exit logic")
        print(f"   - Trading higher timeframes")
        print(f"   - Using lower-cost broker")
    elif metrics_with_cost['average_r'] < 0.5:
        print(f"\n⚠️  CAUTION: Low expectancy after costs")
        print(f"   Average R is {metrics_with_cost['average_r']:.3f}")
        print(f"   Strategy may not be robust in live trading")
    else:
        print(f"\n✅ Strategy remains profitable after costs")
        print(f"   Average R: {metrics_with_cost['average_r']:.3f}")
    
    print()
    
    print("=" * 80)
    print("✅ PHASE 1 DEMO COMPLETE!")
    print("=" * 80)
    print()
    print("What you learned:")
    print("✓ How to integrate transaction costs into backtesting")
    print("✓ The impact of costs on strategy performance")
    print("✓ How to analyze cost breakdown")
    print("✓ How to identify if a strategy is profitable after costs")
    print()
    print("Next steps:")
    print("1. Test other strategies (break_retest, inside_bar, liquidity_sweep)")
    print("2. Experiment with different symbols (XAUUSD, EURUSD)")
    print("3. Adjust cost parameters to match your broker")
    print("4. Install SQLAlchemy to enable database features")
    print("5. Move to Phase 2: Parameter Optimization & Risk Management")
    print()


def main():
    """Main entry point."""
    # Check if data file exists
    data_file = "data/BTC_M15.csv"
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        print(f"   Please copy your CSV file to the data/ directory")
        return
    
    # Run demo
    run_cost_comparison(data_file, symbol='BTCUSD')


if __name__ == "__main__":
    main()
