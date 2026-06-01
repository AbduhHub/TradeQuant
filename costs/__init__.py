"""
Costs Module
============
Transaction cost models for realistic backtesting.
"""

from .transaction_costs import CostModel, InstrumentConfig, get_cost_model, get_instrument_config

# backward compat alias
SymbolCostConfig = InstrumentConfig

__all__ = ['CostModel', 'InstrumentConfig', 'SymbolCostConfig', 'get_cost_model', 'get_instrument_config']