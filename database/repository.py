"""
Backtest Repository
===================
Data access layer for backtest operations.

Author: Trading Engine v2.0
"""

from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from .models import Backtest, TradeRecord, BacktestMetrics
from .connection import get_db_manager


class BacktestRepository:
    """
    Repository for backtest CRUD operations.
    """
    
    def __init__(self, session: Session = None):
        """
        Initialize repository.
        
        Args:
            session: SQLAlchemy session. If None, will create new sessions per operation.
        """
        self.session = session
        self._use_own_session = session is None
    
    def _get_session(self) -> Session:
        """Get session for database operations."""
        if self.session:
            return self.session
        return get_db_manager().get_session()
    
    def save_backtest(
        self,
        strategy_name: str,
        timeframe: str,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        trades: List,  # List of Trade objects
        metrics: Dict,
        initial_capital: float = 10000.0,
        risk_per_trade: float = 0.01,
        use_costs: bool = False,
        spread_points: float = 0.0,
        commission_per_lot: float = 0.0,
        slippage_points: float = 0.0,
        parameters: Dict = None,
        runtime_seconds: float = None,
        notes: str = None
    ) -> Backtest:
        """
        Save a complete backtest with trades and metrics.
        
        Args:
            strategy_name: Name of the strategy
            timeframe: Trading timeframe (e.g., 'M15')
            symbol: Trading symbol (e.g., 'BTCUSD')
            start_date: Backtest start date
            end_date: Backtest end date
            trades: List of Trade objects
            metrics: Dictionary of performance metrics
            initial_capital: Starting capital
            risk_per_trade: Risk per trade as decimal (e.g., 0.01 = 1%)
            use_costs: Whether transaction costs were applied
            spread_points: Spread in points
            commission_per_lot: Commission per lot
            slippage_points: Slippage in points
            parameters: Strategy parameters (dict)
            runtime_seconds: Backtest execution time
            notes: Optional notes
        
        Returns:
            Saved Backtest object
        """
        session = self._get_session()
        
        try:
            # Create backtest record
            backtest = Backtest(
                strategy_name=strategy_name,
                timeframe=timeframe,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                risk_per_trade=risk_per_trade,
                use_costs=use_costs,
                spread_points=spread_points,
                commission_per_lot=commission_per_lot,
                slippage_points=slippage_points,
                parameters=parameters,
                runtime_seconds=runtime_seconds,
                total_candles=len(trades) if trades else 0,
                notes=notes
            )
            
            session.add(backtest)
            session.flush()  # Get backtest ID
            
            # Save trades
            for trade in trades:
                trade_record = self._trade_to_record(trade, backtest.id)
                session.add(trade_record)
            
            # Save metrics
            metrics_record = self._metrics_to_record(metrics, backtest.id)
            session.add(metrics_record)
            
            session.commit()
            
            print(f"✅ Backtest saved: ID={backtest.id}, Trades={len(trades)}")
            
            return backtest
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            if self._use_own_session:
                session.close()
    
    def _trade_to_record(self, trade, backtest_id: int) -> TradeRecord:
        """Convert Trade object to TradeRecord."""
        costs = trade.get_cost_breakdown() if hasattr(trade, 'get_cost_breakdown') else {}
        
        # Calculate trade duration
        duration = None
        if trade.exit_idx is not None and trade.entry_idx is not None:
            duration = trade.exit_idx - trade.entry_idx
        
        return TradeRecord(
            backtest_id=backtest_id,
            entry_time=getattr(trade, 'entry_time', datetime.utcnow()),
            entry_idx=trade.entry_idx,
            entry_price=trade.entry_price,
            actual_entry_price=getattr(trade, 'actual_entry_price', trade.entry_price),
            exit_time=getattr(trade, 'exit_time', datetime.utcnow()),
            exit_idx=trade.exit_idx,
            exit_price=trade.exit_price,
            actual_exit_price=getattr(trade, 'actual_exit_price', trade.exit_price),
            direction=trade.direction,
            sl_price=trade.sl,
            tp_price=trade.tp,
            lot_size=trade.size,
            r_multiple=trade.r_multiple(),
            gross_pnl=getattr(trade, 'gross_pnl', 0.0),
            net_pnl=getattr(trade, 'net_pnl', 0.0),
            entry_spread_cost=costs.get('entry_spread', 0.0),
            entry_commission=costs.get('entry_commission', 0.0),
            entry_slippage_cost=costs.get('entry_slippage', 0.0),
            exit_spread_cost=costs.get('exit_spread', 0.0),
            exit_commission=costs.get('exit_commission', 0.0),
            exit_slippage_cost=costs.get('exit_slippage', 0.0),
            total_costs=costs.get('total_costs', 0.0),
            result=trade.result,
            trade_duration_candles=duration
        )
    
    def _metrics_to_record(self, metrics: Dict, backtest_id: int) -> BacktestMetrics:
        """Convert metrics dict to BacktestMetrics record."""
        return BacktestMetrics(
            backtest_id=backtest_id,
            total_trades=metrics.get('total_trades', 0),
            winning_trades=metrics.get('wins', 0),
            losing_trades=metrics.get('losses', 0),
            breakeven_trades=metrics.get('breakevens', 0),
            win_rate=metrics.get('win_rate', 0.0),
            average_r=metrics.get('average_r', 0.0),
            total_r=metrics.get('total_r', 0.0),
            max_drawdown_r=metrics.get('max_drawdown_r', 0.0),
            max_drawdown_percent=metrics.get('max_drawdown_percent'),
            sharpe_ratio=metrics.get('sharpe_ratio'),
            profit_factor=metrics.get('profit_factor'),
            expectancy=metrics.get('expectancy'),
            max_consecutive_wins=metrics.get('max_consecutive_wins', 0),
            max_consecutive_losses=metrics.get('max_consecutive_losses', 0)
        )
    
    def get_backtest(self, backtest_id: int) -> Optional[Backtest]:
        """
        Get backtest by ID.
        
        Args:
            backtest_id: Backtest ID
        
        Returns:
            Backtest object or None
        """
        session = self._get_session()
        try:
            return session.query(Backtest).filter(Backtest.id == backtest_id).first()
        finally:
            if self._use_own_session:
                session.close()
    
    def get_all_backtests(self, limit: int = 100) -> List[Backtest]:
        """
        Get all backtests (most recent first).
        
        Args:
            limit: Maximum number of backtests to return
        
        Returns:
            List of Backtest objects
        """
        session = self._get_session()
        try:
            return session.query(Backtest)\
                .order_by(Backtest.created_at.desc())\
                .limit(limit)\
                .all()
        finally:
            if self._use_own_session:
                session.close()
    
    def get_backtests_by_strategy(self, strategy_name: str) -> List[Backtest]:
        """Get all backtests for a specific strategy."""
        session = self._get_session()
        try:
            return session.query(Backtest)\
                .filter(Backtest.strategy_name == strategy_name)\
                .order_by(Backtest.created_at.desc())\
                .all()
        finally:
            if self._use_own_session:
                session.close()
    
    def get_trades(self, backtest_id: int) -> List[TradeRecord]:
        """Get all trades for a backtest."""
        session = self._get_session()
        try:
            return session.query(TradeRecord)\
                .filter(TradeRecord.backtest_id == backtest_id)\
                .order_by(TradeRecord.entry_time)\
                .all()
        finally:
            if self._use_own_session:
                session.close()
    
    def get_metrics(self, backtest_id: int) -> Optional[BacktestMetrics]:
        """Get metrics for a backtest."""
        session = self._get_session()
        try:
            return session.query(BacktestMetrics)\
                .filter(BacktestMetrics.backtest_id == backtest_id)\
                .first()
        finally:
            if self._use_own_session:
                session.close()
    
    def delete_backtest(self, backtest_id: int):
        """
        Delete a backtest (cascades to trades and metrics).
        
        Args:
            backtest_id: Backtest ID to delete
        """
        session = self._get_session()
        try:
            backtest = session.query(Backtest).filter(Backtest.id == backtest_id).first()
            if backtest:
                session.delete(backtest)
                session.commit()
                print(f"✅ Backtest {backtest_id} deleted")
            else:
                print(f"⚠️  Backtest {backtest_id} not found")
        except Exception as e:
            session.rollback()
            raise e
        finally:
            if self._use_own_session:
                session.close()
    
    def compare_backtests(self, backtest_ids: List[int]) -> List[Dict]:
        """
        Compare multiple backtests side by side.
        
        Args:
            backtest_ids: List of backtest IDs to compare
        
        Returns:
            List of dictionaries with backtest comparison data
        """
        session = self._get_session()
        try:
            results = []
            for bt_id in backtest_ids:
                backtest = session.query(Backtest).filter(Backtest.id == bt_id).first()
                if backtest and backtest.metrics:
                    results.append({
                        'id': backtest.id,
                        'strategy': backtest.strategy_name,
                        'symbol': backtest.symbol,
                        'timeframe': backtest.timeframe,
                        'total_trades': backtest.metrics.total_trades,
                        'win_rate': backtest.metrics.win_rate,
                        'average_r': backtest.metrics.average_r,
                        'total_r': backtest.metrics.total_r,
                        'max_dd_r': backtest.metrics.max_drawdown_r,
                        'created_at': backtest.created_at
                    })
            return results
        finally:
            if self._use_own_session:
                session.close()
