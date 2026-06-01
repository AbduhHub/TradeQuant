"""
Transaction Costs Module — v2 (Unified Raw-Price System)
=========================================================
All costs expressed per BASE UNIT to match the backtester's position sizing:

  BTCUSD : cost per BTC coin
  XAUUSD : cost per troy oz
  EURUSD : cost per EUR unit   ← was previously per standard lot (×100,000 error)

This aligns with trade.py gross_pnl = price_diff * size_in_base_units.

Reference costs (round-trip):
  BTCUSD : $40 per BTC  (spread ~$15 + slippage ~$5, ×2 sides)
  XAUUSD : $0.90 per oz (~$0.35 spread + $0.10 slip, ×2 sides)
  EURUSD : $0.000106 per EUR  ($10.6 per std lot / 100,000 units)
            breakdown: spread=$1.5 + comm=$3.5 + slip=$0.3 per side per lot
                       → ($1.5+$3.5+$0.3)/100000 = $0.0000530/EUR per side
"""
from typing import Dict


class CostModel:
    """Models transaction costs. All monetary values in USD."""

    def __init__(
        self,
        spread_cost: float = 0.0,       # USD per base unit per side
        commission_per_lot: float = 0.0, # USD per base unit per side
        slippage_cost: float = 0.0,      # USD per base unit per side
        contract_size: float = 1.0,      # informational only (not used in calc)
        pip_value: float = 1.0           # informational only (not used in calc)
    ):
        self.spread_cost = spread_cost
        self.commission_per_lot = commission_per_lot
        self.slippage_cost = slippage_cost
        self.contract_size = contract_size
        self.pip_value = pip_value

    def calculate_entry_cost(self, price: float, lot_size: float, direction: str) -> Dict[str, float]:
        """lot_size here is in base units (BTC, oz, EUR)."""
        spread     = self.spread_cost        * lot_size
        commission = self.commission_per_lot * lot_size
        slippage   = self.slippage_cost      * lot_size
        total      = spread + commission + slippage
        return {
            'spread_cost': spread, 'commission': commission,
            'slippage_cost': slippage, 'total_cost': total
        }

    def calculate_exit_cost(self, price: float, lot_size: float, direction: str) -> Dict[str, float]:
        return self.calculate_entry_cost(price, lot_size, direction)

    def get_total_round_trip_cost(self, lot_size: float) -> float:
        return self.calculate_entry_cost(0, lot_size, 'long')['total_cost'] * 2

    def adjust_price_for_costs(self, price: float, direction: str, is_entry: bool = True) -> float:
        """Adjust execution price for spread+slippage as a fractional price move."""
        adj = (self.spread_cost + self.slippage_cost) / max(price, 1e-8)
        if direction == 'long':
            return price * (1 + adj) if is_entry else price * (1 - adj)
        else:
            return price * (1 - adj) if is_entry else price * (1 + adj)


class InstrumentConfig:
    """
    Per-instrument cost configs in BASE UNIT terms.

    BTCUSD : 1 unit = 1 BTC.  $15 spread + $5 slip per BTC per side.
    XAUUSD : 1 unit = 1 oz.   $0.35 spread + $0.10 slip per oz per side.
    EURUSD : 1 unit = 1 EUR.  Derived from standard-lot costs ÷ 100,000:
               spread $1.5/lot  → $0.000015/EUR
               commission $3.5/lot/side → $0.000035/EUR/side
               slippage $0.3/lot/side   → $0.000003/EUR/side
    """
    CONFIGS = {
        'BTCUSD': {
            'cost_model': CostModel(
                spread_cost=15.0,         # $15 per BTC per side
                commission_per_lot=0.0,
                slippage_cost=5.0,        # $5 per BTC per side
                contract_size=1.0,
                pip_value=1.0
            ),
            'default_capital': 10000,
            'min_lot': 0.001,
            'max_lot': 2.5,
            'lot_step': 0.001,
            'description': 'Bitcoin/USD — $40 round-trip per BTC'
        },
        'XAUUSD': {
            'cost_model': CostModel(
                spread_cost=0.35,         # $0.35 per oz per side
                commission_per_lot=0.0,
                slippage_cost=0.10,       # $0.10 per oz per side
                contract_size=100.0,      # informational: 100 oz = 1 standard lot
                pip_value=1.0
            ),
            'default_capital': 10000,
            'min_lot': 0.01,
            'max_lot': 50.0,
            'lot_step': 0.01,
            'description': 'Gold/USD — $0.90 round-trip per oz'
        },
        'EURUSD': {
            'cost_model': CostModel(
                # Standard lot (100k EUR): spread=$1.5, comm=$3.5, slip=$0.3 per side
                # Per EUR unit: divide by 100,000
                spread_cost=0.000015,       # $0.000015 per EUR per side
                commission_per_lot=0.000035, # $0.000035 per EUR per side
                slippage_cost=0.000003,      # $0.000003 per EUR per side
                contract_size=100000.0,     # informational
                pip_value=1.0
            ),
            'default_capital': 10000,
            'min_lot': 1000.0,             # 0.01 standard lots = 1,000 EUR
            'max_lot': 900000.0,           # 9 standard lots = 900,000 EUR
            'lot_step': 1000.0,
            'description': 'EUR/USD — ~$0.000106/EUR round-trip (~$10.6 per std lot)'
        },
    }

    @classmethod
    def get(cls, symbol: str) -> Dict:
        return cls.CONFIGS.get(symbol, {
            'cost_model': CostModel(),
            'default_capital': 10000,
            'min_lot': 0.01,
            'max_lot': 10.0,
            'lot_step': 0.01,
            'description': f'{symbol} — no cost model configured'
        })

    @classmethod
    def get_cost_model(cls, symbol: str) -> CostModel:
        return cls.get(symbol)['cost_model']

    @classmethod
    def available_symbols(cls):
        return list(cls.CONFIGS.keys())


def get_cost_model(symbol: str = 'BTCUSD') -> CostModel:
    return InstrumentConfig.get_cost_model(symbol)

def get_instrument_config(symbol: str) -> Dict:
    return InstrumentConfig.get(symbol)