"""
Database Module
===============
SQLite database integration for persisting backtest results.

Author: Trading Engine v2.0
"""

from .models import Base, Backtest, TradeRecord, BacktestMetrics
from .connection import DatabaseManager, get_db_manager, reset_db_manager
from .repository import BacktestRepository

__all__ = [
    'Base',
    'Backtest',
    'TradeRecord',
    'BacktestMetrics',
    'DatabaseManager',
    'get_db_manager',
    'reset_db_manager',
    'BacktestRepository'
]
