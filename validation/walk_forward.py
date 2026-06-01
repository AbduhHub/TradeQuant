"""
Walk-Forward Testing Module
============================
Validates strategy robustness by testing on unseen future data.

Walk-forward process:
1. Split data into windows (train + test)
2. Optimize parameters on training period
3. Test those parameters on future test period
4. Roll window forward and repeat
5. Analyze out-of-sample performance

This prevents overfitting and shows if optimized parameters
actually work on new data.

Author: Trading Engine v2.0 - Phase 3
"""

from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from optimization.grid_search import GridSearchOptimizer
from backtester import Backtester
from metrics import calculate_metrics


class WalkForwardTester:
    """
    Walk-forward optimization and testing.
    
    Validates strategy robustness by testing on out-of-sample data.
    """
    
    def __init__(
        self,
        in_sample_periods: int = 12,
        out_sample_periods: int = 3,
        period_type: str = 'months',
        min_trades_per_window: int = 20
    ):
        """
        Initialize walk-forward tester.
        
        Args:
            in_sample_periods: Number of periods for optimization
            out_sample_periods: Number of periods for testing
            period_type: 'months', 'weeks', or 'candles'
            min_trades_per_window: Minimum trades required per window
        """
        self.in_sample_periods = in_sample_periods
        self.out_sample_periods = out_sample_periods
        self.period_type = period_type
        self.min_trades = min_trades_per_window
        
        self.windows = []
        self.results = []
    
    def _split_by_time(
        self,
        candles: List[Dict],
        in_sample: int,
        out_sample: int
    ) -> List[Tuple[List[Dict], List[Dict]]]:
        """
        Split data into overlapping windows by time periods.
        
        Args:
            candles: Price data
            in_sample: In-sample period count
            out_sample: Out-of-sample period count
            
        Returns:
            List of (in_sample_data, out_sample_data) tuples
        """
        if self.period_type == 'candles':
            return self._split_by_candle_count(candles, in_sample, out_sample)
        
        # Group candles by month
        from collections import defaultdict
        monthly_data = defaultdict(list)
        
        for candle in candles:
            month_key = (candle['time'].year, candle['time'].month)
            monthly_data[month_key].append(candle)
        
        sorted_months = sorted(monthly_data.keys())
        
        if len(sorted_months) < in_sample + out_sample:
            raise ValueError(
                f"Not enough data. Need {in_sample + out_sample} months, "
                f"have {len(sorted_months)}"
            )
        
        windows = []
        
        # Create rolling windows
        for i in range(len(sorted_months) - in_sample - out_sample + 1):
            # In-sample months
            in_months = sorted_months[i:i + in_sample]
            # Out-sample months
            out_months = sorted_months[i + in_sample:i + in_sample + out_sample]
            
            # Combine candles
            in_data = []
            for month in in_months:
                in_data.extend(monthly_data[month])
            
            out_data = []
            for month in out_months:
                out_data.extend(monthly_data[month])
            
            if len(in_data) > 0 and len(out_data) > 0:
                windows.append((in_data, out_data))
        
        return windows
    
    def _split_by_candle_count(
        self,
        candles: List[Dict],
        in_sample: int,
        out_sample: int
    ) -> List[Tuple[List[Dict], List[Dict]]]:
        """
        Split data by candle count.
        
        Args:
            candles: Price data
            in_sample: Number of candles for training
            out_sample: Number of candles for testing
            
        Returns:
            List of (in_sample_data, out_sample_data) tuples
        """
        windows = []
        total = len(candles)
        window_size = in_sample + out_sample
        
        # Rolling windows with 50% overlap
        step = out_sample
        
        for i in range(0, total - window_size + 1, step):
            in_data = candles[i:i + in_sample]
            out_data = candles[i + in_sample:i + window_size]
            
            if len(out_data) >= out_sample:
                windows.append((in_data, out_data))
        
        return windows
    
    def run_walk_forward(
        self,
        strategy_class,
        candles: List[Dict],
        param_grid: Dict[str, List[Any]],
        gaps: set = None,
        cost_model = None,
        instrument: str = 'BTCUSD',
        capital: float = 10000.0,
        risk_pct: float = 0.01,
        verbose: bool = True
    ) -> Dict:
        """
        Run walk-forward optimization and testing.
        
        Args:
            strategy_class: Strategy class to test
            candles: Full price data
            param_grid: Parameter grid for optimization
            gaps: Gap indices
            cost_model: Cost model for realistic testing
            verbose: Print progress
            
        Returns:
            Dictionary with walk-forward results
        """
        if gaps is None:
            gaps = set()
        
        if verbose:
            print("\n" + "="*80)
            print("WALK-FORWARD TESTING")
            print("="*80)
            print(f"Strategy: {strategy_class.__name__}")
            print(f"In-sample: {self.in_sample_periods} {self.period_type}")
            print(f"Out-sample: {self.out_sample_periods} {self.period_type}")
            print("="*80)
            print()
        
        # Split data into windows
        self.windows = self._split_by_time(
            candles,
            self.in_sample_periods,
            self.out_sample_periods
        )
        
        if verbose:
            print(f"Created {len(self.windows)} walk-forward windows")
            print()
        
        self.results = []
        
        # Process each window
        for i, (in_sample_data, out_sample_data) in enumerate(self.windows, 1):
            if verbose:
                print(f"\nWindow {i}/{len(self.windows)}")
                print("-" * 80)
                print(f"In-sample: {len(in_sample_data):,} candles "
                      f"({in_sample_data[0]['time'].date()} to {in_sample_data[-1]['time'].date()})")
                print(f"Out-sample: {len(out_sample_data):,} candles "
                      f"({out_sample_data[0]['time'].date()} to {out_sample_data[-1]['time'].date()})")
                print()
            
            # Optimize on in-sample
            if verbose:
                print("Optimizing on in-sample data...")
            
            optimizer = GridSearchOptimizer(
                metric='average_r',
                min_trades=self.min_trades
            )
            
            in_results = optimizer.optimize(
                strategy_class=strategy_class,
                candles=in_sample_data,
                param_grid=param_grid,
                gaps=gaps,
                cost_model=cost_model,
                verbose=False
            )
            
            if not in_results:
                if verbose:
                    print("⚠️  No valid results on in-sample, skipping window")
                continue
            
            best_params = in_results[0]['params']
            in_metrics = in_results[0]['metrics']
            
            if verbose:
                print(f"✓ Best in-sample: Avg R = {in_metrics['average_r']:.3f}, "
                      f"Trades = {in_metrics['total_trades']}")
                print(f"  Parameters: {best_params}")
                print()
            
            # Test on out-sample
            if verbose:
                print("Testing on out-of-sample data...")
            
            strategy = strategy_class(out_sample_data, **best_params)
            backtester = Backtester(
                out_sample_data, gaps, strategy,
                cost_model=cost_model,
                capital=capital,
                risk_pct=risk_pct,
                instrument=instrument
            )

            # Apply costs if provided
            if cost_model:
                from trade import Trade
                trades = backtester.run()
            else:
                trades = backtester.run()
            
            out_metrics = calculate_metrics(trades)
            
            if verbose:
                print(f"✓ Out-of-sample: Avg R = {out_metrics['average_r']:.3f}, "
                      f"Trades = {out_metrics['total_trades']}")
                print()
            
            # Store results
            self.results.append({
                'window': i,
                'in_sample_period': (in_sample_data[0]['time'], in_sample_data[-1]['time']),
                'out_sample_period': (out_sample_data[0]['time'], out_sample_data[-1]['time']),
                'best_params': best_params,
                'in_sample_metrics': in_metrics,
                'out_sample_metrics': out_metrics,
                'degradation': in_metrics['average_r'] - out_metrics['average_r']
            })
        
        # Calculate summary statistics
        summary = self._calculate_summary()
        
        if verbose:
            self._print_summary(summary)
        
        return {
            'windows': self.results,
            'summary': summary
        }
    
    def _calculate_summary(self) -> Dict:
        """Calculate summary statistics across all windows."""
        if not self.results:
            return {}
        
        in_avg_rs = [r['in_sample_metrics']['average_r'] for r in self.results]
        out_avg_rs = [r['out_sample_metrics']['average_r'] for r in self.results]
        degradations = [r['degradation'] for r in self.results]
        
        in_total_rs = [r['in_sample_metrics']['total_r'] for r in self.results]
        out_total_rs = [r['out_sample_metrics']['total_r'] for r in self.results]
        
        return {
            'total_windows': len(self.results),
            'in_sample_avg_r_mean': sum(in_avg_rs) / len(in_avg_rs),
            'out_sample_avg_r_mean': sum(out_avg_rs) / len(out_avg_rs),
            'degradation_mean': sum(degradations) / len(degradations),
            'degradation_pct': (sum(degradations) / sum(in_avg_rs) * 100) if sum(in_avg_rs) != 0 else 0,
            'in_sample_total_r_sum': sum(in_total_rs),
            'out_sample_total_r_sum': sum(out_total_rs),
            'profitable_windows_in': sum(1 for r in in_avg_rs if r > 0),
            'profitable_windows_out': sum(1 for r in out_avg_rs if r > 0),
            'consistency_score': sum(1 for r in out_avg_rs if r > 0) / len(out_avg_rs)
        }
    
    def _print_summary(self, summary: Dict):
        """Print summary statistics."""
        if not summary or summary.get('total_windows', 0) == 0:
            print("\nNo valid walk-forward windows created.")
            print("Check dataset size vs in/out sample periods.")
            return
        print("\n" + "="*80)
        print("WALK-FORWARD SUMMARY")
        print("="*80)
        print()
        
        print(f"Total Windows Tested: {summary['total_windows']}")
        print()
        
        print("Average R Performance:")
        print(f"  In-Sample:     {summary['in_sample_avg_r_mean']:>8.3f}")
        print(f"  Out-of-Sample: {summary['out_sample_avg_r_mean']:>8.3f}")
        print(f"  Degradation:   {summary['degradation_mean']:>8.3f} ({summary['degradation_pct']:.1f}%)")
        print()
        
        print("Total R Performance:")
        print(f"  In-Sample:     {summary['in_sample_total_r_sum']:>8.2f} R")
        print(f"  Out-of-Sample: {summary['out_sample_total_r_sum']:>8.2f} R")
        print()
        
        print("Profitability:")
        print(f"  In-Sample Windows:  {summary['profitable_windows_in']}/{summary['total_windows']} "
              f"({summary['profitable_windows_in']/summary['total_windows']*100:.1f}%)")
        print(f"  Out-Sample Windows: {summary['profitable_windows_out']}/{summary['total_windows']} "
              f"({summary['profitable_windows_out']/summary['total_windows']*100:.1f}%)")
        print()
        
        print(f"Consistency Score: {summary['consistency_score']*100:.1f}%")
        print()
        
        # Interpretation
        print("INTERPRETATION:")
        print("-" * 80)
        
        if summary['degradation_pct'] < 20:
            print("✅ EXCELLENT: Low degradation (<20%) - Strategy is robust!")
        elif summary['degradation_pct'] < 40:
            print("⚠️  MODERATE: Some degradation (20-40%) - Acceptable but not ideal")
        else:
            print("❌ HIGH: Severe degradation (>40%) - Strategy is overfit!")
        
        print()
        
        if summary['consistency_score'] > 0.7:
            print("✅ CONSISTENT: Strategy profitable in 70%+ of windows")
        elif summary['consistency_score'] > 0.5:
            print("⚠️  INCONSISTENT: Strategy profitable in 50-70% of windows")
        else:
            print("❌ UNRELIABLE: Strategy profitable in <50% of windows")

        
        
        print()


# Example usage
if __name__ == "__main__":
    print("Walk-Forward Testing Module")
    print("=" * 80)
    print("\nThis module validates strategy robustness through walk-forward testing.")
    print("\nExample usage:")
    print("""
    from validation.walk_forward import WalkForwardTester
    from strategies.trend_pullback_v3_FIXED import TrendPullbackV3
    
    # Initialize tester
    wf_tester = WalkForwardTester(
        in_sample_periods=12,   # 12 months for optimization
        out_sample_periods=3,   # 3 months for testing
        period_type='months'
    )
    
    # Define parameter grid
    param_grid = {
        'lookback': [100, 200],
        'min_rr': [2.0, 3.0]
    }
    
    # Run walk-forward test
    results = wf_tester.run_walk_forward(
        strategy_class=TrendPullbackV3,
        candles=candles,
        param_grid=param_grid,
        cost_model=cost_model
    )
    
    # Results show if strategy works out-of-sample!
    """)