"""
PHASE 1 DEMO: Transaction Costs + Database Integration
=======================================================

This script demonstrates:
1. Running backtests WITH and WITHOUT transaction costs
2. Comparing the impact of costs on performance
3. Saving results to database
4. Querying historical backtests
5. Generating comparison reports

Author: Trading Engine v2.0
"""

import sys
import os
from datetime import datetime
import pandas as pd

# Add parent directory to path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# Import modules
from loader_enhanced import load_price_data, detect_gaps
from backtester import Backtester
from strategy_factory import StrategyFactory
from metrics import calculate_metrics
from costs.transaction_costs import CostModel, SymbolCostConfig
from database.connection import DatabaseManager
from database.repository import BacktestRepository
from trade import Trade


def run_comparison_demo(data_file: str, symbol: str = 'BTCUSD'):
    """
    Run demo comparing backtests with and without costs.
    
    Args:
        data_file: Path to CSV file
        symbol: Trading symbol
    """
    print("=" * 80)
    print("PHASE 1 DEMO: Transaction Costs & Database Integration")
    print("=" * 80)
    print()
    
    # Load data
    print(f"📂 Loading data from: {data_file}")
    candles = load_price_data(data_file)
    print(f"   ✓ Loaded {len(candles)} candles")
    print(f"   ✓ Date range: {candles[0]['time']} to {candles[-1]['time']}")
    print()
    
    # Detect gaps
    gaps = detect_gaps(candles, timeframe_minutes=15)
    print(f"   ✓ Detected {len(gaps)} gaps in data")
    print()
    
    # Initialize database
    print("🗄️  Initializing database...")
    from database.connection import DatabaseManager

    db_manager = DatabaseManager('backtest_results.db')
    db_manager.initialize()   # ✅ IMPORTANT
    # with db_manager.session_scope() as session:
    #     repo = BacktestRepository(session)
    #     repo.save_backtest(...)
    print("   ✓ Database ready")
    print()
    
    # Strategy to test
    strategy_name = 'break_retest'
    print(f"📊 Testing Strategy: {strategy_name}")
    print()
    
    #  BACKTEST 1: WITHOUT COSTS 
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
    
        # Save to database
    with db_manager.session_scope() as session:
        repo = BacktestRepository(session)

        bt_no_cost = repo.save_backtest(
            strategy_name=strategy_name,
            timeframe='M15',
            symbol=symbol,
            start_date=candles[0]['time'],
            end_date=candles[-1]['time'],
            initial_capital=10000.0,
            risk_per_trade=0.01,
            use_costs=False,
            trades=trades_no_cost,
            metrics=metrics_no_cost,
            notes="Baseline backtest without transaction costs"
        )
        backtest_id_no_cost = bt_no_cost.id
        print(f"💾 Saved to database (ID: {backtest_id_no_cost})")
    print()
    
    #  BACKTEST 2: WITH COSTS 
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
    
    # Create strategy with cost model
    # We need to modify strategy to pass cost_model to Trade objects
    # For now, we'll manually create trades with costs
    
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
    print(f"💰 Total Transaction Costs: ${total_costs:.2f}")
    print()
    
    # Save to database
    with db_manager.session_scope() as session:
        repo = BacktestRepository(session)
        bt_with_cost = repo.save_backtest(
            strategy_name=strategy_name,
            timeframe='M15',
            symbol=symbol,
            start_date=candles[0]['time'],
            end_date=candles[-1]['time'],
            initial_capital=10000.0,
            risk_per_trade=0.01,
            use_costs=True,
            spread_points=cost_model.spread_points,
            commission_per_lot=cost_model.commission_per_lot,
            slippage_points=cost_model.slippage_points,
            trades=trades_with_cost,
            metrics=metrics_with_cost,
            notes="Realistic backtest with transaction costs"
        )
        backtest_id_with_cost = bt_with_cost.id
        print(f"💾 Saved to database (ID: {backtest_id_with_cost})")
    print()
    
    #  COMPARISON 
    print("=" * 80)
    print("IMPACT ANALYSIS: Costs vs No Costs")
    print("=" * 80)
    print()
    
    comparison = pd.DataFrame({
        'Metric': [
            'Total Trades',
            'Win Rate (%)',
            'Average R',
            'Total R',
            'Max DD (R)',
            'Total Costs ($)'
        ],
        'Without Costs': [
            metrics_no_cost['total_trades'],
            f"{metrics_no_cost['win_rate']*100:.2f}",
            f"{metrics_no_cost['average_r']:.3f}",
            f"{metrics_no_cost['total_r']:.2f}",
            f"{metrics_no_cost['max_drawdown_r']:.2f}",
            "$0.00"
        ],
        'With Costs': [
            metrics_with_cost['total_trades'],
            f"{metrics_with_cost['win_rate']*100:.2f}",
            f"{metrics_with_cost['average_r']:.3f}",
            f"{metrics_with_cost['total_r']:.2f}",
            f"{metrics_with_cost['max_drawdown_r']:.2f}",
            f"${total_costs:.2f}"
        ],
        'Impact': [
            0,
            f"{(metrics_with_cost['win_rate'] - metrics_no_cost['win_rate'])*100:.2f}%",
            f"{metrics_with_cost['average_r'] - metrics_no_cost['average_r']:.3f}",
            f"{metrics_with_cost['total_r'] - metrics_no_cost['total_r']:.2f}",
            f"{metrics_with_cost['max_drawdown_r'] - metrics_no_cost['max_drawdown_r']:.2f}",
            f"-${total_costs:.2f}"
        ]
    })
    
    print(comparison.to_string(index=False))
    print()
    
    #  DATABASE QUERY DEMO 
    print("=" * 80)
    print("DATABASE QUERY DEMO")
    print("=" * 80)
    print()
    
    print("📊 All saved backtests:")
    with db_manager.session_scope() as session:
        repo = BacktestRepository(session)
        all_backtests = repo.get_all_backtests()
        for bt in all_backtests[-5:]:  # Show last 5
            print(f"   ID {bt.id}: {bt.strategy_name} on {bt.symbol} "
                f"[{bt.start_date.date()}] - "
                f"Costs: {bt.use_costs}, "
                f"Trades: {bt.metrics.total_trades if bt.metrics else 'N/A'}")
    print()
    
    print("🔍 Comparing specific backtests:")
    bt1 = repo.get_backtest(backtest_id_no_cost)
    bt2 = repo.get_backtest(backtest_id_with_cost)
    
    print(f"\nBacktest {bt1.id} (No Costs):")
    print(f"   Strategy: {bt1.strategy_name}")
    print(f"   Symbol: {bt1.symbol}")
    print(f"   Win Rate: {bt1.metrics.win_rate*100:.2f}%")
    print(f"   Total R: {bt1.metrics.total_r:.2f}")
    
    print(f"\nBacktest {bt2.id} (With Costs):")
    print(f"   Strategy: {bt2.strategy_name}")
    print(f"   Symbol: {bt2.symbol}")
    print(f"   Win Rate: {bt2.metrics.win_rate*100:.2f}%")
    print(f"   Total R: {bt2.metrics.total_r:.2f}")
    print(f"   Total Costs: ${bt2.metrics.total_costs:.2f}")
    print()
    
    #  TRADE-LEVEL ANALYSIS 
    print("=" * 80)
    print("SAMPLE TRADE BREAKDOWN (First 3 trades with costs)")
    print("=" * 80)
    print()
    
    for i, trade in enumerate(trades_with_cost[:3], 1):
        costs = trade.get_cost_breakdown()
        print(f"Trade #{i}:")
        print(f"   Direction: {trade.direction.upper()}")
        print(f"   Entry: ${trade.entry_price:.2f} → Actual: ${trade.actual_entry_price:.2f}")
        print(f"   Exit: ${trade.exit_price:.2f} → Actual: ${trade.actual_exit_price:.2f}")
        print(f"   Gross P&L: ${costs['gross_pnl']:.2f}")
        print(f"   Costs:")
        print(f"      Entry Spread: ${costs['entry_spread']:.2f}")
        print(f"      Entry Commission: ${costs['entry_commission']:.2f}")
        print(f"      Entry Slippage: ${costs['entry_slippage']:.2f}")
        print(f"      Exit Spread: ${costs['exit_spread']:.2f}")
        print(f"      Exit Commission: ${costs['exit_commission']:.2f}")
        print(f"      Exit Slippage: ${costs['exit_slippage']:.2f}")
        print(f"   Total Costs: ${costs['total_costs']:.2f}")
        print(f"   Net P&L: ${costs['net_pnl']:.2f}")
        print(f"   R-Multiple: {trade.r_multiple():.3f}")
        print(f"   Result: {trade.result}")
        print()
    
    
    print("Summary:")
    print(f"✓ Demonstrated transaction costs impact")
    print(f"✓ Saved {len(all_backtests)} backtests to database")
    print(f"✓ Cost impact on Total R: {metrics_with_cost['total_r'] - metrics_no_cost['total_r']:.2f} R")
    print(f"✓ Total transaction costs: ${total_costs:.2f}")
    print()
    


def main():
    """Main entry point."""
    # Check if data file exists
    data_file = "data/BTC_M15.csv"
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        print(f"   Please copy your CSV file to the data/ directory")
        print(f"   Or provide path as argument")
        return
    
    # Run demo
    run_comparison_demo(data_file, symbol='BTCUSD')


if __name__ == "__main__":
    main()
