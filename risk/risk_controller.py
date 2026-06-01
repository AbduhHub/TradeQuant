"""
Risk Management Controller
===========================
Implements trading limits and safeguards to prevent account blow-up.

Features:
- Daily loss limits
- Weekly loss limits
- Maximum drawdown protection
- Consecutive loss limits
- Trade frequency limits
- Session filters

Author: Trading Engine v2.0 - Phase 2
"""

from datetime import datetime, timedelta
from typing import List, Tuple, Optional


class RiskController:
    """
    Control trading based on risk limits.
    
    Prevents trading when risk limits are exceeded.
    """
    
    def __init__(
        self,
        initial_capital: float,
        max_daily_loss_pct: float = 0.02,
        max_weekly_loss_pct: float = 0.05,
        max_drawdown_pct: float = 0.20,
        max_consecutive_losses: int = 5,
        max_trades_per_day: int = 10,
        min_hours_between_trades: float = 1.0,
        allowed_sessions: List[str] = None
    ):
        """
        Initialize risk controller.
        
        Args:
            initial_capital: Starting capital
            max_daily_loss_pct: Maximum daily loss (0.02 = 2%)
            max_weekly_loss_pct: Maximum weekly loss (0.05 = 5%)
            max_drawdown_pct: Maximum drawdown from peak (0.20 = 20%)
            max_consecutive_losses: Stop after N losses in a row
            max_trades_per_day: Maximum trades allowed per day
            min_hours_between_trades: Minimum hours between trades
            allowed_sessions: List of allowed trading sessions
        """
        self.initial_capital = initial_capital
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_weekly_loss_pct = max_weekly_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_consecutive_losses = max_consecutive_losses
        self.max_trades_per_day = max_trades_per_day
        self.min_hours_between_trades = min_hours_between_trades
        self.allowed_sessions = allowed_sessions or ['all']
        
        # Tracking
        self.peak_equity = initial_capital
        self.daily_start_equity = {}
        self.weekly_start_equity = {}
    
    def can_trade(
        self,
        current_equity: float,
        current_time: datetime,
        recent_trades: List
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if trading is allowed.
        
        Args:
            current_equity: Current account equity
            current_time: Current timestamp
            recent_trades: List of recent Trade objects
            
        Returns:
            Tuple of (can_trade: bool, reason: str)
        """
        # Check daily loss limit
        can, reason = self._check_daily_loss(current_equity, current_time)
        if not can:
            return False, reason
        
        # Check weekly loss limit
        can, reason = self._check_weekly_loss(current_equity, current_time)
        if not can:
            return False, reason
        
        # Check maximum drawdown
        can, reason = self._check_max_drawdown(current_equity)
        if not can:
            return False, reason
        
        # Check consecutive losses
        can, reason = self._check_consecutive_losses(recent_trades)
        if not can:
            return False, reason
        
        # Check daily trade limit
        can, reason = self._check_daily_trade_limit(recent_trades, current_time)
        if not can:
            return False, reason
        
        # Check time between trades
        can, reason = self._check_time_between_trades(recent_trades, current_time)
        if not can:
            return False, reason
        
        # Check trading session
        can, reason = self._check_session(current_time)
        if not can:
            return False, reason
        
        return True, None
    
    def _check_daily_loss(
        self,
        current_equity: float,
        current_time: datetime
    ) -> Tuple[bool, Optional[str]]:
        """Check daily loss limit."""
        day_key = current_time.date()
        
        # Set daily start if new day
        if day_key not in self.daily_start_equity:
            self.daily_start_equity[day_key] = current_equity
        
        daily_start = self.daily_start_equity[day_key]
        daily_loss = (daily_start - current_equity) / daily_start
        
        if daily_loss > self.max_daily_loss_pct:
            return False, f"Daily loss limit exceeded: {daily_loss*100:.2f}%"
        
        return True, None
    
    def _check_weekly_loss(
        self,
        current_equity: float,
        current_time: datetime
    ) -> Tuple[bool, Optional[str]]:
        """Check weekly loss limit."""
        week_key = current_time.isocalendar()[:2]  # (year, week)
        
        # Set weekly start if new week
        if week_key not in self.weekly_start_equity:
            self.weekly_start_equity[week_key] = current_equity
        
        weekly_start = self.weekly_start_equity[week_key]
        weekly_loss = (weekly_start - current_equity) / weekly_start
        
        if weekly_loss > self.max_weekly_loss_pct:
            return False, f"Weekly loss limit exceeded: {weekly_loss*100:.2f}%"
        
        return True, None
    
    def _check_max_drawdown(
        self,
        current_equity: float
    ) -> Tuple[bool, Optional[str]]:
        """Check maximum drawdown."""
        self.peak_equity = max(self.peak_equity, current_equity)
        drawdown = (self.peak_equity - current_equity) / self.peak_equity
        
        if drawdown > self.max_drawdown_pct:
            return False, f"Max drawdown exceeded: {drawdown*100:.2f}%"
        
        return True, None
    
    def _check_consecutive_losses(
        self,
        recent_trades: List
    ) -> Tuple[bool, Optional[str]]:
        """Check consecutive losses."""
        if not recent_trades:
            return True, None
        
        consecutive_losses = 0
        for trade in reversed(recent_trades):
            if hasattr(trade, 'result'):
                if trade.result == 'LOSS':
                    consecutive_losses += 1
                else:
                    break
        
        if consecutive_losses >= self.max_consecutive_losses:
            return False, f"Consecutive loss limit: {consecutive_losses} losses"
        
        return True, None
    
    def _check_daily_trade_limit(
        self,
        recent_trades: List,
        current_time: datetime
    ) -> Tuple[bool, Optional[str]]:
        """Check daily trade limit — only counts trades entered TODAY."""
        if not recent_trades:
            return True, None

        today = current_time.date()
        trades_today = 0

        for trade in recent_trades:
            # Use trade_time attribute if available (set during replay),
            # otherwise fall back to checking entry_idx (unknown date → skip)
            trade_date = getattr(trade, 'trade_time', None)
            if trade_date is not None:
                if hasattr(trade_date, 'date'):
                    trade_date = trade_date.date()
                if trade_date == today:
                    trades_today += 1

        if trades_today >= self.max_trades_per_day:
            return False, f"Daily trade limit reached: {trades_today} trades today"

        return True, None
    
    def _check_time_between_trades(
        self,
        recent_trades: List,
        current_time: datetime
    ) -> Tuple[bool, Optional[str]]:
        """Check minimum time between trades."""
        if not recent_trades:
            return True, None
        
        # Would need actual trade times, simplified here
        # In real implementation, check last trade exit time
        
        return True, None
    
    def _check_session(
        self,
        current_time: datetime
    ) -> Tuple[bool, Optional[str]]:
        """Check if within allowed trading session."""
        if 'all' in self.allowed_sessions:
            return True, None
        
        hour = current_time.hour
        
        # Define sessions
        sessions = {
            'asian': range(0, 8),
            'london': range(8, 16),
            'new_york': range(13, 21),
            'sydney': range(22, 24)
        }
        
        current_session = None
        for session, hours in sessions.items():
            if hour in hours:
                current_session = session
                break
        
        if current_session not in self.allowed_sessions:
            return False, f"Outside trading hours (current: {current_session})"
        
        return True, None
    
    def update_equity(self, equity: float, timestamp: datetime):
        """
        Update equity tracking.
        
        Args:
            equity: New equity value
            timestamp: Current timestamp
        """
        self.peak_equity = max(self.peak_equity, equity)
        
        # Reset daily if new day
        day_key = timestamp.date()
        if day_key not in self.daily_start_equity:
            self.daily_start_equity[day_key] = equity
        
        # Reset weekly if new week
        week_key = timestamp.isocalendar()[:2]
        if week_key not in self.weekly_start_equity:
            self.weekly_start_equity[week_key] = equity
    
    def get_status(self, current_equity: float) -> dict:
        """
        Get current risk status.
        
        Args:
            current_equity: Current equity
            
        Returns:
            Dictionary with risk metrics
        """
        drawdown = (self.peak_equity - current_equity) / self.peak_equity
        
        return {
            'peak_equity': self.peak_equity,
            'current_equity': current_equity,
            'drawdown_pct': drawdown * 100,
            'drawdown_limit_pct': self.max_drawdown_pct * 100,
            'risk_usage_pct': (drawdown / self.max_drawdown_pct) * 100
        }


# Example usage
if __name__ == "__main__":
    print("Risk Management Controller")
    print("=" * 80)
    print()
    
    # Initialize
    initial_capital = 10000
    controller = RiskController(
        initial_capital=initial_capital,
        max_daily_loss_pct=0.02,
        max_weekly_loss_pct=0.05,
        max_drawdown_pct=0.20,
        max_consecutive_losses=5,
        max_trades_per_day=10
    )
    
    # Test scenarios
    print("SCENARIO 1: Normal trading")
    print("-" * 80)
    can_trade, reason = controller.can_trade(10000, datetime.now(), [])
    print(f"Can trade: {can_trade}")
    print(f"Reason: {reason or 'All checks passed'}")
    print()
    
    print("SCENARIO 2: Daily loss limit hit")
    print("-" * 80)
    can_trade, reason = controller.can_trade(9700, datetime.now(), [])
    print(f"Can trade: {can_trade}")
    print(f"Reason: {reason or 'All checks passed'}")
    print()
    
    print("SCENARIO 3: Maximum drawdown")
    print("-" * 80)
    controller.peak_equity = 10000
    can_trade, reason = controller.can_trade(7900, datetime.now(), [])
    print(f"Can trade: {can_trade}")
    print(f"Reason: {reason or 'All checks passed'}")
    print()
    
    print("=" * 80)
    print("Risk controller protects your account from catastrophic losses!")