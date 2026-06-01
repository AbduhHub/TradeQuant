"""
Position Sizing Module
======================
Calculate optimal position sizes based on various risk models.

Supported methods:
1. Fixed Percent Risk - Risk fixed % of capital per trade
2. Kelly Criterion - Optimal fraction based on win rate
3. ATR-Based - Adjust size based on volatility
4. Optimal F - Maximize geometric growth

Author: Trading Engine v2.0 - Phase 2
"""

from typing import Optional


class PositionSizer:
    """
    Calculate position sizes using various risk models.
    """
    
    def __init__(self, capital: float):
        """
        Initialize position sizer.
        
        Args:
            capital: Current account capital
        """
        self.capital = capital
    
    def fixed_percent(
        self,
        risk_percent: float,
        sl_distance: float,
        point_value: float = 1.0
    ) -> float:
        """
        Calculate position size using fixed percentage risk.
        
        Args:
            risk_percent: Percentage of capital to risk (0.01 = 1%)
            sl_distance: Distance to stop loss in price points
            point_value: Value of one price point
            
        Returns:
            Position size in lots
        """
        if sl_distance == 0:
            return 0.0
        
        risk_amount = self.capital * risk_percent
        lot_size = risk_amount / (sl_distance * point_value)
        
        return max(0.01, lot_size)  # Minimum 0.01 lots
    
    def kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float = 0.5
    ) -> float:
        """
        Calculate optimal position size using Kelly Criterion.
        
        Formula: f = (p*b - q) / b
        where:
        - f = fraction of capital to bet
        - p = win probability
        - q = loss probability (1-p)
        - b = win/loss ratio
        
        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount (positive number)
            fraction: Kelly fraction to use (0.5 = half-Kelly, safer)
            
        Returns:
            Fraction of capital to risk (0-1)
        """
        if avg_loss == 0 or win_rate == 0 or win_rate == 1:
            return 0.0
        
        win_loss_ratio = avg_win / avg_loss
        loss_rate = 1 - win_rate
        
        # Kelly formula
        kelly_pct = (win_rate * win_loss_ratio - loss_rate) / win_loss_ratio
        
        # Apply fraction for safety (half-Kelly is common)
        kelly_pct *= fraction
        
        # Cap at 5% even with Kelly
        return max(0.0, min(kelly_pct, 0.05))
    
    def atr_based(
        self,
        atr: float,
        atr_multiplier: float,
        risk_percent: float,
        point_value: float = 1.0
    ) -> float:
        """
        Calculate position size using ATR-based stop loss.
        
        Args:
            atr: Average True Range value
            atr_multiplier: Multiplier for ATR (e.g., 2.0 = 2*ATR)
            risk_percent: Percentage of capital to risk
            point_value: Value of one price point
            
        Returns:
            Position size in lots
        """
        if atr == 0:
            return 0.0
        
        sl_distance = atr * atr_multiplier
        return self.fixed_percent(risk_percent, sl_distance, point_value)
    
    def optimal_f(
        self,
        trade_results: list,
        max_f: float = 0.5
    ) -> float:
        """
        Calculate Optimal F (fraction for maximum geometric growth).
        
        This finds the fraction that would have maximized growth
        on historical trades.
        
        Args:
            trade_results: List of R-multiples from past trades
            max_f: Maximum fraction to test
            
        Returns:
            Optimal fraction of capital to risk
        """
        if not trade_results:
            return 0.01
        
        best_f = 0.01
        best_twr = 0.0
        
        # Test fractions from 0.01 to max_f
        for f in [i/100 for i in range(1, int(max_f*100) + 1)]:
            twr = 1.0
            
            for r in trade_results:
                # Terminal Wealth Relative
                twr *= (1 + r * f)
                
                # Stop if ruined
                if twr <= 0:
                    twr = 0
                    break
            
            if twr > best_twr:
                best_twr = twr
                best_f = f
        
        return best_f
    
    def calculate_lot_size(
        self,
        method: str,
        risk_percent: float = 0.01,
        sl_distance: float = None,
        point_value: float = 1.0,
        **kwargs
    ) -> float:
        """
        Calculate position size using specified method.
        
        Args:
            method: 'fixed_percent', 'kelly', 'atr', or 'optimal_f'
            risk_percent: Risk percentage (for fixed_percent)
            sl_distance: Stop loss distance (for fixed_percent)
            point_value: Value of one point
            **kwargs: Additional parameters for specific methods
            
        Returns:
            Position size in lots
        """
        if method == 'fixed_percent':
            if sl_distance is None:
                raise ValueError("sl_distance required for fixed_percent")
            return self.fixed_percent(risk_percent, sl_distance, point_value)
        
        elif method == 'kelly':
            return self.kelly_criterion(
                win_rate=kwargs.get('win_rate', 0.5),
                avg_win=kwargs.get('avg_win', 1.0),
                avg_loss=kwargs.get('avg_loss', 1.0),
                fraction=kwargs.get('fraction', 0.5)
            )
        
        elif method == 'atr':
            return self.atr_based(
                atr=kwargs.get('atr', 0),
                atr_multiplier=kwargs.get('atr_multiplier', 2.0),
                risk_percent=risk_percent,
                point_value=point_value
            )
        
        elif method == 'optimal_f':
            return self.optimal_f(
                trade_results=kwargs.get('trade_results', []),
                max_f=kwargs.get('max_f', 0.5)
            )
        
        else:
            raise ValueError(f"Unknown method: {method}")


# Example usage
if __name__ == "__main__":
    print("Position Sizing Module")
    print("=" * 80)
    print()
    
    # Example capital
    capital = 10000
    sizer = PositionSizer(capital)
    
    # Example 1: Fixed percent
    print("1. FIXED PERCENT RISK")
    print("-" * 80)
    sl_distance = 500  # $500 stop loss
    risk_pct = 0.01    # 1% risk
    lot_size = sizer.fixed_percent(risk_pct, sl_distance)
    print(f"Capital: ${capital:,.2f}")
    print(f"Risk: {risk_pct*100}%")
    print(f"SL Distance: ${sl_distance}")
    print(f"Position Size: {lot_size:.2f} lots")
    print(f"Risk Amount: ${capital * risk_pct:,.2f}")
    print()
    
    # Example 2: Kelly Criterion
    print("2. KELLY CRITERION")
    print("-" * 80)
    win_rate = 0.55
    avg_win = 150
    avg_loss = 100
    kelly_f = sizer.kelly_criterion(win_rate, avg_win, avg_loss, fraction=0.5)
    print(f"Win Rate: {win_rate*100:.1f}%")
    print(f"Avg Win: ${avg_win}")
    print(f"Avg Loss: ${avg_loss}")
    print(f"Half-Kelly Fraction: {kelly_f*100:.2f}%")
    print(f"Risk Amount: ${capital * kelly_f:,.2f}")
    print()
    
    # Example 3: ATR-based
    print("3. ATR-BASED SIZING")
    print("-" * 80)
    atr = 200
    atr_mult = 2.0
    lot_size_atr = sizer.atr_based(atr, atr_mult, risk_pct)
    print(f"ATR: ${atr}")
    print(f"ATR Multiplier: {atr_mult}x")
    print(f"SL Distance: ${atr * atr_mult}")
    print(f"Position Size: {lot_size_atr:.2f} lots")
    print()
    
    # Example 4: Optimal F
    print("4. OPTIMAL F")
    print("-" * 80)
    trade_results = [1.5, -1.0, 2.0, -1.0, 1.0, -1.0, 3.0, -1.0]  # R-multiples
    optimal_f = sizer.optimal_f(trade_results)
    print(f"Past R-multiples: {trade_results}")
    print(f"Optimal F: {optimal_f*100:.2f}%")
    print(f"Risk Amount: ${capital * optimal_f:,.2f}")
    print()
    
    print("=" * 80)
    print("Use position sizing to optimize risk and maximize growth!")
