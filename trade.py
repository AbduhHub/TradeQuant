"""
Enhanced Trade Class with Transaction Costs
============================================
Backward compatible with original Trade class.
Adds optional cost tracking for realistic backtesting.

Author: Trading Engine v2.0
"""

from typing import Optional, Dict


class Trade:
    """
    Represents a single trade with entry, exit, and P&L tracking.
    
    Enhanced Version: Now supports transaction costs.
    """
    
    def __init__(
        self,
        entry_idx: int,
        entry_price: float,
        direction: str,
        sl: Optional[float],
        tp: Optional[float],
        size: float = 1.0,
        cost_model=None  # NEW: Optional cost model
    ):
        """
        Initialize a trade.
        
        Args:
            entry_idx: Candle index where trade was entered
            entry_price: Entry price
            direction: 'long' or 'short'
            sl: Stop loss price
            tp: Take profit price
            size: Position size in lots
            cost_model: Optional CostModel instance for transaction costs
        """
        self.entry_idx = entry_idx
        self.entry_price = entry_price
        self.direction = direction  
        self.sl = sl
        self.tp = tp
        self.size = size
        
        # Exit tracking
        self.exit_idx = None
        self.exit_price = None
        self.is_closed = False
        
        # Performance metrics (original)
        self._r_multiple = 0.0
        self.total_r = 0.0   
        self.result = None
        
        # NEW: Cost tracking
        self.cost_model = cost_model
        self.entry_costs = {}
        self.exit_costs = {}
        self.total_costs = 0.0
        
        # NEW: Dollar P&L tracking
        self.gross_pnl = 0.0
        self.net_pnl = 0.0
        
        # Calculate entry costs if model provided
        if self.cost_model:
            self.entry_costs = self.cost_model.calculate_entry_cost(
                self.entry_price,
                self.size,
                self.direction
            )
            # Adjust entry price for spread/slippage
            self.actual_entry_price = self.cost_model.adjust_price_for_costs(
                self.entry_price,
                self.direction,
                is_entry=True
            )
        else:
            self.actual_entry_price = self.entry_price
    
    def check_exit(self, idx: int, candle: dict) -> bool:
        """
        Check if trade should exit based on SL/TP.
        
        Args:
            idx: Current candle index
            candle: Current candle data
        
        Returns:
            True if trade exited, False otherwise
        """
        if self.is_closed:
            return False
        
        price = candle["close"]
        
        if self.direction == "long":
            if self.sl is not None and price <= self.sl:
                self._close(idx, self.sl)
                return True
            if self.tp is not None and price >= self.tp:
                self._close(idx, self.tp)
                return True
        else:  # short
            if self.sl is not None and price >= self.sl:
                self._close(idx, self.sl)
                return True
            if self.tp is not None and price <= self.tp:
                self._close(idx, self.tp)
                return True
        
        return False
    
    def _close(self, idx: int, price: float):
        """
        Close the trade and calculate P&L.
        
        Args:
            idx: Exit candle index
            price: Exit price
        """
        self.exit_idx = idx
        self.exit_price = price
        self.is_closed = True
        
        # Adjust exit price for costs if model provided
        if self.cost_model:
            self.actual_exit_price = self.cost_model.adjust_price_for_costs(
                price,
                self.direction,
                is_entry=False
            )
            # Calculate exit costs
            self.exit_costs = self.cost_model.calculate_exit_cost(
                price,
                self.size,
                self.direction
            )
        else:
            self.actual_exit_price = price
        
        # Calculate R-multiple (original logic)
        risk = abs(self.entry_price - self.sl) if self.sl is not None else 0.0
        reward = abs(price - self.entry_price)
        
        if risk == 0:
            self._r_multiple = 0.0
        else:
            self._r_multiple = reward / risk
            if price == self.sl:
                self._r_multiple *= -1
        
        self.total_r = self._r_multiple
        
        # NEW: Calculate gross P&L (without costs)
        if self.direction == "long":
            self.gross_pnl = (self.exit_price - self.entry_price) * self.size
        else:  # short
            self.gross_pnl = (self.entry_price - self.exit_price) * self.size
        
        # NEW: Calculate net P&L (with costs)
        if self.cost_model:
            self.total_costs = (
                self.entry_costs.get('total_cost', 0) + 
                self.exit_costs.get('total_cost', 0)
            )
            self.net_pnl = self.gross_pnl - self.total_costs
            
            # Adjust R-multiple for costs
            if risk > 0:
                cost_in_r = self.total_costs / (risk * self.size)
                self._r_multiple -= cost_in_r
                self.total_r = self._r_multiple
        else:
            self.net_pnl = self.gross_pnl
            self.total_costs = 0.0
        
        # Update result based on net P&L
        self.result = "WIN" if self.net_pnl > 0 else ("LOSS" if self.net_pnl < 0 else "BE")
    
    def r_multiple(self) -> float:
        """
        Get the R-multiple (reward-to-risk ratio).
        
        Returns:
            R-multiple value (negative for losses)
        """
        return self._r_multiple
    
    def get_cost_breakdown(self) -> Dict[str, float]:
        """
        Get detailed cost breakdown.
        
        Returns:
            Dictionary with cost details
        """
        return {
            'entry_spread': self.entry_costs.get('spread_cost', 0),
            'entry_commission': self.entry_costs.get('commission', 0),
            'entry_slippage': self.entry_costs.get('slippage_cost', 0),
            'exit_spread': self.exit_costs.get('spread_cost', 0),
            'exit_commission': self.exit_costs.get('commission', 0),
            'exit_slippage': self.exit_costs.get('slippage_cost', 0),
            'total_costs': self.total_costs,
            'gross_pnl': self.gross_pnl,
            'net_pnl': self.net_pnl
        }
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Trade(direction={self.direction}, "
            f"entry={self.entry_price:.2f}, "
            f"exit={self.exit_price:.2f}, "
            f"R={self._r_multiple:.2f}, "
            f"PnL=${self.net_pnl:.2f})"
        )
