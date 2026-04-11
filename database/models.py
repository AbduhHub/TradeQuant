"""
Database Models
===============
SQLAlchemy models for persisting backtest results.

Tables:
- backtests: Backtest configuration and metadata
- trades: Individual trade records
- backtest_metrics: Aggregated performance metrics

Author: Trading Engine v2.0
"""

from sqlalchemy import (
    Column, Integer, Float, String, DateTime, JSON, 
    ForeignKey, Text, Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Backtest(Base):
    """
    Represents a single backtest run.
    """
    __tablename__ = 'backtests'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Configuration
    strategy_name = Column(String(100), nullable=False)
    timeframe = Column(String(10), nullable=False)
    symbol = Column(String(20), nullable=False, default='BTCUSD')
    
    # Date range
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Risk parameters
    initial_capital = Column(Float, nullable=False, default=10000.0)
    risk_per_trade = Column(Float, nullable=False, default=0.01)
    
    # Cost model
    use_costs = Column(Boolean, default=False)
    spread_points = Column(Float, default=0.0)
    commission_per_lot = Column(Float, default=0.0)
    slippage_points = Column(Float, default=0.0)
    
    # Strategy parameters (stored as JSON)
    parameters = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    runtime_seconds = Column(Float, nullable=True)
    total_candles = Column(Integer, nullable=True)
    
    # Description/notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    trades = relationship('TradeRecord', back_populates='backtest', cascade='all, delete-orphan')
    metrics = relationship('BacktestMetrics', back_populates='backtest', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Backtest(id={self.id}, strategy={self.strategy_name}, symbol={self.symbol}, date={self.start_date})>"


class TradeRecord(Base):
    """
    Represents a single trade execution.
    """
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    backtest_id = Column(Integer, ForeignKey('backtests.id'), nullable=False)
    
    # Entry details
    entry_time = Column(DateTime, nullable=False)
    entry_idx = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    actual_entry_price = Column(Float, nullable=True)  # After costs
    
    # Exit details
    exit_time = Column(DateTime, nullable=False)
    exit_idx = Column(Integer, nullable=False)
    exit_price = Column(Float, nullable=False)
    actual_exit_price = Column(Float, nullable=True)  # After costs
    
    # Trade parameters
    direction = Column(String(10), nullable=False)  # 'long' or 'short'
    sl_price = Column(Float, nullable=True)
    tp_price = Column(Float, nullable=True)
    lot_size = Column(Float, nullable=False, default=1.0)
    
    # Performance metrics
    r_multiple = Column(Float, nullable=False)
    gross_pnl = Column(Float, nullable=True)
    net_pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    
    # Cost breakdown
    entry_spread_cost = Column(Float, default=0.0)
    entry_commission = Column(Float, default=0.0)
    entry_slippage_cost = Column(Float, default=0.0)
    exit_spread_cost = Column(Float, default=0.0)
    exit_commission = Column(Float, default=0.0)
    exit_slippage_cost = Column(Float, default=0.0)
    total_costs = Column(Float, default=0.0)
    
    # Result
    result = Column(String(10), nullable=False)  # 'WIN', 'LOSS', 'BE'
    
    # Trade metadata
    trade_duration_candles = Column(Integer, nullable=True)
    
    # Relationship
    backtest = relationship('Backtest', back_populates='trades')
    
    def __repr__(self):
        return f"<Trade(id={self.id}, direction={self.direction}, R={self.r_multiple:.2f}, PnL=${self.net_pnl:.2f})>"


class BacktestMetrics(Base):
    """
    Aggregated performance metrics for a backtest.
    """
    __tablename__ = 'backtest_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    backtest_id = Column(Integer, ForeignKey('backtests.id'), nullable=False, unique=True)
    
    # Trade statistics
    total_trades = Column(Integer, nullable=False)
    winning_trades = Column(Integer, nullable=False)
    losing_trades = Column(Integer, nullable=False)
    breakeven_trades = Column(Integer, default=0)
    
    # Win rate
    win_rate = Column(Float, nullable=False)
    
    # R-multiple metrics
    average_r = Column(Float, nullable=False)
    total_r = Column(Float, nullable=False)
    average_win_r = Column(Float, nullable=True)
    average_loss_r = Column(Float, nullable=True)
    
    # Dollar P&L
    total_gross_pnl = Column(Float, nullable=True)
    total_net_pnl = Column(Float, nullable=True)
    total_costs = Column(Float, default=0.0)
    
    # Drawdown metrics
    max_drawdown_r = Column(Float, nullable=False)
    max_drawdown_percent = Column(Float, nullable=True)
    max_drawdown_dollars = Column(Float, nullable=True)
    
    # Advanced metrics
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    expectancy = Column(Float, nullable=True)
    
    # Risk metrics
    largest_win = Column(Float, nullable=True)
    largest_loss = Column(Float, nullable=True)
    average_trade_duration = Column(Float, nullable=True)  # in candles
    
    # Streak analysis
    max_consecutive_wins = Column(Integer, default=0)
    max_consecutive_losses = Column(Integer, default=0)
    
    # Final equity
    final_equity = Column(Float, nullable=True)
    total_return_percent = Column(Float, nullable=True)
    
    # Relationship
    backtest = relationship('Backtest', back_populates='metrics')
    
    def __repr__(self):
        return f"<Metrics(backtest_id={self.backtest_id}, trades={self.total_trades}, win_rate={self.win_rate:.2%})>"
