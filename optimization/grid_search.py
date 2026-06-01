"""
Grid Search Optimizer
=====================
Systematically test all parameter combinations to find optimal strategy settings.

This optimizer:
1. Generates all possible parameter combinations
2. Runs backtests for each combination
3. Ranks results by chosen metric (average_r, total_r, win_rate, etc.)
4. Returns best parameters

Author: Trading Engine v2.0 - Phase 2
"""

import itertools
from typing import Dict, List, Any, Callable
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from backtester import Backtester
from metrics import calculate_metrics


class GridSearchOptimizer:
    """
    Exhaustive parameter search optimizer.
    
    Tests all possible combinations of parameters to find optimal settings.
    """
    
    def __init__(self, metric: str = 'average_r', min_trades: int = 100):
        """
        Initialize optimizer.
        
        Args:
            metric: Metric to optimize ('average_r', 'total_r', 'win_rate', 'sharpe')
            min_trades: Minimum number of trades required for valid result
        """
        self.metric = metric
        self.min_trades = min_trades
        self.results = []
    
    def _generate_combinations(self, param_grid: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """
        Generate all possible parameter combinations.
        
        Args:
            param_grid: Dictionary of parameter names to lists of values
            
        Returns:
            List of parameter dictionaries
        """
        # Get parameter names and values
        param_names = list(param_grid.keys())
        param_values = [param_grid[name] for name in param_names]
        
        # Generate all combinations
        combinations = []
        for values in itertools.product(*param_values):
            param_dict = dict(zip(param_names, values))
            combinations.append(param_dict)
        
        return combinations
    
    def optimize(
        self,
        strategy_class: Callable,
        candles: List[Dict],
        param_grid: Dict[str, List[Any]],
        gaps: set = None,
        cost_model = None,
        context: Dict = None,
        instrument: str = 'BTCUSD',
        capital: float = 10000.0,
        risk_pct: float = 0.01,
        verbose: bool = True
    ) -> List[Dict]:
        """
        Run grid search optimization.
        
        Args:
            strategy_class: Strategy class to optimize
            candles: Price data
            param_grid: Dictionary of parameters to test
            gaps: Set of gap indices (optional)
            cost_model: CostModel instance (optional)
            context: Additional context for strategy (optional)
            verbose: Print progress
            
        Returns:
            List of results sorted by metric (best first)
        """
        if gaps is None:
            gaps = set()
        
        if context is None:
            context = {'gaps': gaps}
        else:
            context['gaps'] = gaps
        
        # Generate all combinations
        combinations = self._generate_combinations(param_grid)
        total = len(combinations)
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"GRID SEARCH OPTIMIZATION")
            print(f"{'='*80}")
            print(f"Strategy: {strategy_class.__name__}")
            print(f"Total combinations to test: {total:,}")
            print(f"Optimization metric: {self.metric}")
            print(f"Min trades required: {self.min_trades}")
            print(f"{'='*80}\n")
        
        self.results = []
        start_time = datetime.now()
        
        # Test each combination
        for i, params in enumerate(combinations, 1):
            if verbose and i % max(1, total // 10) == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                eta = (elapsed / i) * (total - i)
                print(f"Progress: {i}/{total} ({i/total*100:.1f}%) - ETA: {eta:.0f}s")
            
            try:
                # Create strategy with parameters
                strategy = strategy_class(candles, **params)
                
                # Add cost model if provided
                if cost_model and hasattr(strategy, 'cost_model'):
                    strategy.cost_model = cost_model
                
                # Run backtest
                backtester = Backtester(
                    candles, gaps, strategy,
                    cost_model=cost_model,
                    capital=capital,
                    risk_pct=risk_pct,
                    instrument=instrument
                )

                # Inject cost model into trades if needed
                if cost_model:
                    from trade import Trade
                    raw_trades = backtester.run()

                    # Recreate trades with cost model
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
                else:
                    trades = backtester.run()
                
                # Calculate metrics
                metrics = calculate_metrics(trades)
                
                # Skip if not enough trades
                if metrics['total_trades'] < self.min_trades:
                    continue
                
                # Store result
                result = {
                    'params': params,
                    'metrics': metrics,
                    'total_trades': metrics['total_trades'],
                    'average_r': metrics['average_r'],
                    'total_r': metrics['total_r'],
                    'win_rate': metrics['win_rate'],
                    'max_dd': metrics['max_drawdown_r']
                }
                
                self.results.append(result)
                
            except Exception as e:
                if verbose:
                    print(f"Error with params {params}: {e}")
                continue
        
        # Sort by chosen metric
        if self.metric == 'average_r':
            self.results.sort(key=lambda x: x['average_r'], reverse=True)
        elif self.metric == 'total_r':
            self.results.sort(key=lambda x: x['total_r'], reverse=True)
        elif self.metric == 'win_rate':
            self.results.sort(key=lambda x: x['win_rate'], reverse=True)
        elif self.metric == 'sharpe':
            # Would need to calculate Sharpe ratio
            self.results.sort(key=lambda x: x['average_r'], reverse=True)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"OPTIMIZATION COMPLETE")
            print(f"{'='*80}")
            print(f"Total time: {elapsed:.1f}s")
            print(f"Valid results: {len(self.results)}/{total}")
            print(f"{'='*80}\n")
            
            # Show top 5 results
            print("TOP 5 RESULTS:")
            print(f"{'='*80}")
            for i, result in enumerate(self.results[:5], 1):
                print(f"\n#{i} - Avg R: {result['average_r']:.3f}, "
                      f"Total R: {result['total_r']:.2f}, "
                      f"Win Rate: {result['win_rate']*100:.1f}%, "
                      f"Trades: {result['total_trades']}")
                print(f"    Parameters: {result['params']}")
            print(f"\n{'='*80}\n")
        
        return self.results
    
    def get_best_params(self) -> Dict[str, Any]:
        """
        Get best parameter set.
        
        Returns:
            Dictionary of best parameters
        """
        if not self.results:
            raise ValueError("No results yet. Run optimize() first.")
        
        return self.results[0]['params']
    
    def get_top_n(self, n: int = 10) -> List[Dict]:
        """
        Get top N results.
        
        Args:
            n: Number of top results to return
            
        Returns:
            List of top N results
        """
        return self.results[:n]
    
    def compare_with_baseline(self, baseline_params: Dict[str, Any]) -> Dict:
        """
        Compare best result with baseline parameters.
        
        Args:
            baseline_params: Baseline parameter set
            
        Returns:
            Comparison dictionary
        """
        if not self.results:
            raise ValueError("No results yet. Run optimize() first.")
        
        best = self.results[0]
        
        # Find baseline in results
        baseline_result = None
        for result in self.results:
            if result['params'] == baseline_params:
                baseline_result = result
                break
        
        if baseline_result is None:
            return {
                'best_params': best['params'],
                'best_metrics': best['metrics'],
                'baseline_found': False
            }
        
        return {
            'best_params': best['params'],
            'best_metrics': best['metrics'],
            'baseline_params': baseline_params,
            'baseline_metrics': baseline_result['metrics'],
            'improvement': {
                'average_r': best['average_r'] - baseline_result['average_r'],
                'total_r': best['total_r'] - baseline_result['total_r'],
                'win_rate': best['win_rate'] - baseline_result['win_rate'],
                'trades': best['total_trades'] - baseline_result['total_trades']
            }
        }


# Example usage
if __name__ == "__main__":
    print("Grid Search Optimizer")
    print("=" * 80)
    print("\nThis module provides parameter optimization for trading strategies.")
    print("\nExample usage:")
    print("""
    from optimization.grid_search import GridSearchOptimizer
    from strategies.trend_pullback import TrendPullbackStrategy
    
    # Define parameter grid
    param_grid = {
        'lookback': [50, 100, 200],
        'threshold': [0.001, 0.002, 0.005],
        'min_rr': [1.5, 2.0, 3.0]
    }
    
    # Run optimization
    optimizer = GridSearchOptimizer(metric='average_r')
    results = optimizer.optimize(
        strategy_class=TrendPullbackStrategy,
        candles=candles,
        param_grid=param_grid,
        cost_model=cost_model
    )
    
    # Get best parameters
    best_params = optimizer.get_best_params()
    print(f"Best parameters: {best_params}")
    """)