"""
Transaction Costs Module
========================
Calculates realistic trading costs including:
- Spread (bid-ask spread)
- Slippage (price movement during order execution)
- Commission (broker fees)

Author: Trading Engine v2.0
"""

from typing import Dict, Optional


class CostModel:
    """
    Models transaction costs for realistic backtesting.
    
    Costs are calculated in the quote currency (e.g., USD for BTCUSD).
    """
    
    def __init__(
        self,
        spread_points: float = 0.0,
        commission_per_lot: float = 0.0,
        slippage_points: float = 0.0,
        point_value: float = 1.0
    ):
        """
        Initialize cost model.
        
        Args:
            spread_points: Spread in points (e.g., 50 for BTC, 1.5 pips for EUR)
            commission_per_lot: Fixed commission per standard lot
            slippage_points: Average slippage in points
            point_value: Value of 1 point in quote currency
        """
        self.spread_points = spread_points
        self.commission_per_lot = commission_per_lot
        self.slippage_points = slippage_points
        self.point_value = point_value
    
    def calculate_entry_cost(
        self,
        price: float,
        lot_size: float,
        direction: str
    ) -> Dict[str, float]:
        """
        Calculate costs incurred when entering a trade.
        
        Args:
            price: Entry price
            lot_size: Position size in lots
            direction: 'long' or 'short'
        
        Returns:
            Dictionary with cost breakdown
        """
        # Spread cost (paid on entry)
        spread_cost = self.spread_points * self.point_value * lot_size
        
        # Commission (if applicable)
        commission = self.commission_per_lot * lot_size
        
        # Slippage (unfavorable price movement)
        slippage_cost = self.slippage_points * self.point_value * lot_size
        
        total_cost = spread_cost + commission + slippage_cost
        
        return {
            'spread_cost': spread_cost,
            'commission': commission,
            'slippage_cost': slippage_cost,
            'total_cost': total_cost,
            'cost_in_points': (self.spread_points + self.slippage_points)
        }
    
    def calculate_exit_cost(
        self,
        price: float,
        lot_size: float,
        direction: str
    ) -> Dict[str, float]:
        """
        Calculate costs incurred when exiting a trade.
        
        Args:
            price: Exit price
            lot_size: Position size in lots
            direction: 'long' or 'short'
        
        Returns:
            Dictionary with cost breakdown
        """
        # Spread cost (paid on exit)
        spread_cost = self.spread_points * self.point_value * lot_size
        
        # Commission (if applicable)
        commission = self.commission_per_lot * lot_size
        
        # Slippage
        slippage_cost = self.slippage_points * self.point_value * lot_size
        
        total_cost = spread_cost + commission + slippage_cost
        
        return {
            'spread_cost': spread_cost,
            'commission': commission,
            'slippage_cost': slippage_cost,
            'total_cost': total_cost,
            'cost_in_points': (self.spread_points + self.slippage_points)
        }
    
    def get_total_round_trip_cost(self, lot_size: float) -> float:
        """
        Calculate total cost for entry + exit (round trip).
        
        Args:
            lot_size: Position size in lots
        
        Returns:
            Total cost in quote currency
        """
        entry_cost = self.calculate_entry_cost(0, lot_size, 'long')
        exit_cost = self.calculate_exit_cost(0, lot_size, 'long')
        
        return entry_cost['total_cost'] + exit_cost['total_cost']
    
    def adjust_price_for_costs(
        self,
        price: float,
        direction: str,
        is_entry: bool = True
    ) -> float:
        """
        Adjust execution price to account for spread and slippage.
        
        Args:
            price: Market price
            direction: 'long' or 'short'
            is_entry: True for entry, False for exit
        
        Returns:
            Adjusted price after costs
        """
        total_cost_points = self.spread_points + self.slippage_points
        
        if direction == 'long':
            if is_entry:
                # Long entry: pay higher (ask price + slippage)
                return price + (total_cost_points * self.point_value / price)
            else:
                # Long exit: receive lower (bid price - slippage)
                return price - (total_cost_points * self.point_value / price)
        else:  # short
            if is_entry:
                # Short entry: sell at lower (bid price - slippage)
                return price - (total_cost_points * self.point_value / price)
            else:
                # Short exit: buy at higher (ask price + slippage)
                return price + (total_cost_points * self.point_value / price)


class SymbolCostConfig:
    """
    Pre-configured cost models for different symbols.
    """
    
    CONFIGS = {
        'BTCUSD': CostModel(
            spread_points=50.0,      # $50 spread
            commission_per_lot=0.0,  # No commission (spread-based)
            slippage_points=10.0,    # $10 slippage
            point_value=1.0
        ),
        'XAUUSD': CostModel(
            spread_points=0.30,      # $0.30 spread (30 cents)
            commission_per_lot=0.0,
            slippage_points=0.10,    # $0.10 slippage
            point_value=1.0
        ),
        'EURUSD': CostModel(
            spread_points=0.00015,   # 1.5 pips
            commission_per_lot=7.0,  # $7 per lot commission
            slippage_points=0.00005, # 0.5 pips
            point_value=1.0
        ),
        'GBPUSD': CostModel(
            spread_points=0.00020,   # 2.0 pips
            commission_per_lot=7.0,
            slippage_points=0.00005,
            point_value=1.0
        ),
    }
    
    @classmethod
    def get_cost_model(cls, symbol: str) -> CostModel:
        """
        Get cost model for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSD')
        
        Returns:
            CostModel for the symbol
        """
        if symbol in cls.CONFIGS:
            return cls.CONFIGS[symbol]
        else:
            # Default: no costs
            return CostModel(
                spread_points=0.0,
                commission_per_lot=0.0,
                slippage_points=0.0,
                point_value=1.0
            )


# Convenience function
def get_cost_model(symbol: str = 'BTCUSD') -> CostModel:
    """
    Get cost model for a symbol.
    
    Args:
        symbol: Trading symbol
    
    Returns:
        CostModel instance
    """
    return SymbolCostConfig.get_cost_model(symbol)
