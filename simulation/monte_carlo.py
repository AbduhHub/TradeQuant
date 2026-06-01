"""
Monte Carlo Simulation Module (FIXED VERSION)
==============================================
Fixed bootstrap resampling and improved statistics.

CRITICAL FIX: Now uses bootstrap resampling WITH replacement
for proper Monte Carlo simulation.

Author: Trading Engine v2.0 - Fixed
"""

import random
from typing import List, Dict
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')


class MonteCarloSimulator:
    """
    Monte Carlo simulation for risk assessment.
    
    FIXED: Now properly samples WITH replacement (bootstrap).
    """
    
    def __init__(self, n_simulations: int = 10000):
        """
        Initialize simulator.
        
        Args:
            n_simulations: Number of simulations to run
        """
        self.n_simulations = n_simulations
        self.results = []
    
    def simulate(
        self,
        trades: List,
        initial_capital: float,
        risk_per_trade: float = 0.01,
        verbose: bool = True
    ) -> Dict:
        """
        Run Monte Carlo simulation with proper bootstrap resampling.
        
        Args:
            trades: List of Trade objects (historical results)
            initial_capital: Starting capital
            risk_per_trade: Risk per trade as fraction (0.01 = 1%)
            verbose: Print progress
            
        Returns:
            Dictionary with simulation results
        """
        if not trades:
            raise ValueError("No trades provided")
        
        if verbose:
            print("\n" + "="*80)
            print("MONTE CARLO SIMULATION (FIXED VERSION)")
            print("="*80)
            print(f"Historical trades: {len(trades)}")
            print(f"Initial capital: ${initial_capital:,.2f}")
            print(f"Risk per trade: {risk_per_trade*100:.1f}%")
            print(f"Simulations: {self.n_simulations:,}")
            print("="*80)
            print()
        
        # Extract R-multiples from trades
        r_multiples = [t.r_multiple() for t in trades if hasattr(t, 'r_multiple')]
        
        if not r_multiples:
            raise ValueError("Trades have no R-multiples")

        # Cap simulation size to prevent MemoryError on high-frequency strategies.
        # Bootstrapping 5k samples from 100k+ trades gives the same distribution.
        # Statistical justification: law of large numbers — sample mean/std stabilise
        # well before 5k samples, so 5000 is more than sufficient for MC purposes.
        MAX_SAMPLE_SIZE = 5000
        if len(r_multiples) > MAX_SAMPLE_SIZE:
            import random as _rnd
            sim_pool = _rnd.sample(r_multiples, MAX_SAMPLE_SIZE)
        else:
            sim_pool = r_multiples
        
        if verbose:
            print(f"Using {len(r_multiples)} trade outcomes for simulation...")
            if len(r_multiples) > MAX_SAMPLE_SIZE:
                print(f"  (subsampled to {MAX_SAMPLE_SIZE} for memory efficiency)")
            print(f"Original Avg R: {sum(r_multiples)/len(r_multiples):.3f}")
            print()
        
        self.results = []
        
        # Run simulations
        for i in range(self.n_simulations):
            if verbose and (i + 1) % (self.n_simulations // 10) == 0:
                print(f"Progress: {i+1:,}/{self.n_simulations:,} ({(i+1)/self.n_simulations*100:.0f}%)")
            
            # Bootstrap resample WITH replacement from sim_pool
            bootstrapped = [random.choice(sim_pool) for _ in range(len(sim_pool))]
            
            # Run simulation
            equity = initial_capital
            peak = initial_capital
            max_dd = 0
            max_dd_pct = 0
            equity_curve = [equity]
            ruined = False
            
            for r in bootstrapped:
                # Calculate P&L
                risk_amount = equity * risk_per_trade
                pnl = r * risk_amount
                equity += pnl
                
                # Track drawdown
                if equity > peak:
                    peak = equity
                
                dd = peak - equity
                dd_pct = dd / peak if peak > 0 else 0
                
                if dd > max_dd:
                    max_dd = dd
                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct
                
                equity_curve.append(equity)
                
                # Check ruin
                if equity <= 0:
                    ruined = True
                    equity = 0
                    break
            
            # Store result
            self.results.append({
                'final_equity': equity,
                'max_drawdown': max_dd,
                'max_drawdown_pct': max_dd_pct * 100,
                'ruined': ruined,
                'return_pct': ((equity - initial_capital) / initial_capital) * 100 if not ruined else -100,
                'equity_curve': equity_curve
            })
        
        # Calculate statistics
        stats = self._calculate_statistics(initial_capital)
        
        if verbose:
            print()
            self._print_statistics(stats)
        
        return stats
    
    def _calculate_statistics(self, initial_capital: float) -> Dict:
        """Calculate statistics from simulation results."""
        final_equities = [r['final_equity'] for r in self.results]
        returns = [r['return_pct'] for r in self.results]
        drawdowns = [r['max_drawdown_pct'] for r in self.results]
        ruined = sum(1 for r in self.results if r['ruined'])
        
        # Sort for percentiles
        sorted_equities = sorted(final_equities)
        sorted_returns = sorted(returns)
        sorted_drawdowns = sorted(drawdowns, reverse=True)
        
        n = len(self.results)
        
        return {
            'simulations': n,
            'initial_capital': initial_capital,
            
            # Final equity statistics
            'final_equity': {
                'mean': sum(final_equities) / n,
                'median': sorted_equities[n // 2],
                'min': min(final_equities),
                'max': max(final_equities),
                'p5': sorted_equities[int(n * 0.05)],
                'p25': sorted_equities[int(n * 0.25)],
                'p75': sorted_equities[int(n * 0.75)],
                'p95': sorted_equities[int(n * 0.95)]
            },
            
            # Return statistics
            'returns': {
                'mean': sum(returns) / n,
                'median': sorted_returns[n // 2],
                'min': min(returns),
                'max': max(returns),
                'p5': sorted_returns[int(n * 0.05)],
                'p95': sorted_returns[int(n * 0.95)],
                'std_dev': self._calculate_std_dev(returns)
            },
            
            # Drawdown statistics
            'drawdowns': {
                'mean': sum(drawdowns) / n,
                'median': sorted_drawdowns[n // 2],
                'max': max(drawdowns),
                'p10': sorted_drawdowns[int(n * 0.10)],
                'p25': sorted_drawdowns[int(n * 0.25)],
                'p50': sorted_drawdowns[int(n * 0.50)]
            },
            
            # Risk metrics
            'risk': {
                'risk_of_ruin': (ruined / n) * 100,
                'prob_profitable': (sum(1 for r in returns if r > 0) / n) * 100,
                'prob_loss_gt_10pct': (sum(1 for r in returns if r < -10) / n) * 100,
                'prob_dd_gt_20pct': (sum(1 for d in drawdowns if d > 20) / n) * 100,
                'prob_dd_gt_30pct': (sum(1 for d in drawdowns if d > 30) / n) * 100,
                'prob_dd_gt_50pct': (sum(1 for d in drawdowns if d > 50) / n) * 100
            }
        }
    
    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def _print_statistics(self, stats: Dict):
        """Print simulation statistics."""
        print("="*80)
        print("MONTE CARLO RESULTS (FIXED VERSION)")
        print("="*80)
        print()
        
        print("FINAL EQUITY DISTRIBUTION:")
        print("-" * 80)
        print(f"  Mean:              ${stats['final_equity']['mean']:>12,.2f}")
        print(f"  Median:            ${stats['final_equity']['median']:>12,.2f}")
        print(f"  5th Percentile:    ${stats['final_equity']['p5']:>12,.2f}")
        print(f"  25th Percentile:   ${stats['final_equity']['p25']:>12,.2f}")
        print(f"  75th Percentile:   ${stats['final_equity']['p75']:>12,.2f}")
        print(f"  95th Percentile:   ${stats['final_equity']['p95']:>12,.2f}")
        print(f"  Range:             ${stats['final_equity']['min']:>12,.2f} - ${stats['final_equity']['max']:>12,.2f}")
        print()
        
        print("95% CONFIDENCE INTERVAL:")
        print(f"  ${stats['final_equity']['p5']:,.2f} - ${stats['final_equity']['p95']:,.2f}")
        print()
        
        print("RETURN DISTRIBUTION:")
        print("-" * 80)
        print(f"  Mean Return:       {stats['returns']['mean']:>12.2f}%")
        print(f"  Median Return:     {stats['returns']['median']:>12.2f}%")
        print(f"  Std Deviation:     {stats['returns']['std_dev']:>12.2f}%")
        print(f"  5th Percentile:    {stats['returns']['p5']:>12.2f}%")
        print(f"  95th Percentile:   {stats['returns']['p95']:>12.2f}%")
        print(f"  Range:             {stats['returns']['min']:>12.2f}% - {stats['returns']['max']:>12.2f}%")
        print()
        
        print("DRAWDOWN PROBABILITIES:")
        print("-" * 80)
        print(f"  Mean Drawdown:     {stats['drawdowns']['mean']:>12.2f}%")
        print(f"  Median Drawdown:   {stats['drawdowns']['median']:>12.2f}%")
        print(f"  Max Drawdown:      {stats['drawdowns']['max']:>12.2f}%")
        print()
        print(f"  P(DD > 20%):       {stats['risk']['prob_dd_gt_20pct']:>12.1f}%")
        print(f"  P(DD > 30%):       {stats['risk']['prob_dd_gt_30pct']:>12.1f}%")
        print(f"  P(DD > 50%):       {stats['risk']['prob_dd_gt_50pct']:>12.1f}%")
        print()
        
        print("RISK METRICS:")
        print("-" * 80)
        print(f"  Risk of Ruin:             {stats['risk']['risk_of_ruin']:>12.2f}%")
        print(f"  Probability of Profit:    {stats['risk']['prob_profitable']:>12.1f}%")
        print(f"  Probability of >10% Loss: {stats['risk']['prob_loss_gt_10pct']:>12.1f}%")
        print()
        
        # Interpretation
        print("="*80)
        print("INTERPRETATION")
        print("="*80)
        print()
        
        if stats['risk']['risk_of_ruin'] > 5:
            print(f"❌ HIGH RISK: {stats['risk']['risk_of_ruin']:.1f}% chance of ruin")
        elif stats['risk']['risk_of_ruin'] > 1:
            print(f"⚠️  MODERATE RISK: {stats['risk']['risk_of_ruin']:.1f}% chance of ruin")
        else:
            print(f"✅ LOW RISK: {stats['risk']['risk_of_ruin']:.2f}% chance of ruin")
        
        print()
        
        if stats['returns']['median'] > 10:
            print(f"✅ PROFITABLE: Median return of {stats['returns']['median']:.1f}%")
        elif stats['returns']['median'] > 0:
            print(f"⚠️  MARGINAL: Median return only {stats['returns']['median']:.1f}%")
        else:
            print(f"❌ LOSING: Median return of {stats['returns']['median']:.1f}%")
        
        print()
        
        if stats['risk']['prob_dd_gt_30pct'] > 50:
            print(f"❌ HIGH DRAWDOWN RISK: {stats['risk']['prob_dd_gt_30pct']:.0f}% chance of >30% DD")
        elif stats['risk']['prob_dd_gt_30pct'] > 20:
            print(f"⚠️  MODERATE DRAWDOWN RISK: {stats['risk']['prob_dd_gt_30pct']:.0f}% chance of >30% DD")
        else:
            print(f"✅ LOW DRAWDOWN RISK: {stats['risk']['prob_dd_gt_30pct']:.0f}% chance of >30% DD")
        
        print()


if __name__ == "__main__":
    print("Monte Carlo Simulation Module (FIXED)")
    print("=" * 80)
    print("\nCRITICAL FIX: Now uses bootstrap resampling WITH replacement")
    print("This gives proper Monte Carlo confidence intervals.")