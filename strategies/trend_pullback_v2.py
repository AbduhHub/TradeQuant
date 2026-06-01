"""
Trend Pullback Strategy V2 - Optimizable Version
==================================================
Enhanced version with tunable parameters for optimization.

Parameters:
- lookback: Period for trend detection
- trend_threshold: Minimum % change to confirm trend
- pullback_threshold: Maximum % pullback allowed
- min_rr: Minimum risk:reward ratio
- atr_multiplier: ATR multiplier for SL/TP
- volume_filter: Require volume confirmation

Author: Trading Engine v2.0 - Phase 2
"""

from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from trade import Trade


class TrendPullbackV2:
    """
    Optimizable trend pullback strategy.
    
    This version has parameters that can be tuned via grid search.
    """
    
    def __init__(
        self,
        candles: list,
        lookback: int = 100,
        trend_threshold: float = 0.002,
        pullback_threshold: float = 0.005,
        min_rr: float = 2.0,
        atr_period: int = 14,
        atr_multiplier_sl: float = 1.5,
        atr_multiplier_tp: float = 3.0,
        volume_filter: bool = False,
        session_filter: bool = False
    ):
        """
        Initialize strategy with parameters.
        
        Args:
            candles: Price data
            lookback: Candles to look back for trend
            trend_threshold: Min % change for trend (0.002 = 0.2%)
            pullback_threshold: Max % pullback allowed
            min_rr: Minimum risk:reward ratio
            atr_period: Period for ATR calculation
            atr_multiplier_sl: ATR multiplier for stop loss
            atr_multiplier_tp: ATR multiplier for take profit
            volume_filter: Require above-average volume
            session_filter: Only trade during active sessions
        """
        self.candles = candles
        self.lookback = lookback
        self.trend_threshold = trend_threshold
        self.pullback_threshold = pullback_threshold
        self.min_rr = min_rr
        self.atr_period = atr_period
        self.atr_multiplier_sl = atr_multiplier_sl
        self.atr_multiplier_tp = atr_multiplier_tp
        self.volume_filter = volume_filter
        self.session_filter = session_filter
        
        # Pre-calculate ATR for all candles
        self.atr_values = self._calculate_atr()
    
    def _calculate_atr(self) -> list:
        """Calculate ATR for all candles."""
        atr = [0.0] * len(self.candles)
        
        for i in range(self.atr_period, len(self.candles)):
            tr_sum = 0
            for j in range(i - self.atr_period, i):
                candle = self.candles[j]
                prev_candle = self.candles[j-1] if j > 0 else candle
                
                high = candle['high']
                low = candle['low']
                prev_close = prev_candle['close']
                
                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close)
                )
                tr_sum += tr
            
            atr[i] = tr_sum / self.atr_period
        
        return atr
    
    def _is_uptrend(self, index: int) -> bool:
        """
        Check if price is in uptrend.
        
        Args:
            index: Current candle index
            
        Returns:
            True if uptrend detected
        """
        if index < self.lookback:
            return False
        
        current_price = self.candles[index]['close']
        past_price = self.candles[index - self.lookback]['close']
        
        change_pct = (current_price - past_price) / past_price
        
        return change_pct > self.trend_threshold
    
    def _is_downtrend(self, index: int) -> bool:
        """Check if price is in downtrend."""
        if index < self.lookback:
            return False
        
        current_price = self.candles[index]['close']
        past_price = self.candles[index - self.lookback]['close']
        
        change_pct = (current_price - past_price) / past_price
        
        return change_pct < -self.trend_threshold
    
    def _is_pullback(self, index: int, direction: str) -> bool:
    
        lookback = min(20, self.lookback // 5)  # 20 candles or 1/5 of trend lookback
        
        if index < lookback:
            return False
        
        current = self.candles[index]['close']
        recent_high = max(c['high'] for c in self.candles[index-lookback:index])
        recent_low = min(c['low'] for c in self.candles[index-lookback:index])


        if direction == 'long':
            # Pullback from recent high
            pullback_pct = (recent_high - current) / recent_high
            return 0.001 < pullback_pct < self.pullback_threshold
        else:
            # Pullback from recent low
            pullback_pct = (current - recent_low) / recent_low
            return 0.001 < pullback_pct < self.pullback_threshold
    
    def _check_volume(self, index: int) -> bool:
        if not self.volume_filter:
            return True
        
        if index < 20:
            return True
        
        current_vol = self.candles[index].get('volume', 0)
        if current_vol == 0:  # No volume data
            return True
        
        avg_vol = sum(c.get('volume', 0) for c in self.candles[index-20:index]) / 20
        
        # Require 20% above average
        return current_vol > avg_vol * 1.2
    
    def _check_session(self, index: int) -> bool:
        """Check if within trading session."""
        if not self.session_filter:
            return True
        
        # Simple session filter based on hour
        time = self.candles[index]['time']
        hour = time.hour
        
        # London (8-12) or New York (13-17) sessions
        return (8 <= hour <= 12) or (13 <= hour <= 17)
    
    def _calculate_trend_strength(self, index: int) -> float:
        """Calculate trend strength using ADX-like logic"""
        if index < self.lookback:
            return 0.0
        
        prices = [c['close'] for c in self.candles[index-self.lookback:index]]
        
        # Calculate linear regression slope
        x = list(range(len(prices)))
        n = len(prices)
        
        sum_x = sum(x)
        sum_y = sum(prices)
        sum_xy = sum(xi * yi for xi, yi in zip(x, prices))
        sum_x2 = sum(xi * xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Normalize by price
        trend_strength = abs(slope) / prices[-1]
        
        return trend_strength
    
    def on_candle(self, index: int) -> Optional[Trade]:
        """
        Generate trading signal.
        
        Args:
            index: Current candle index
            
        Returns:
            Trade object if signal generated, None otherwise
        """
        # Need enough history
        if index < max(self.lookback, self.atr_period):
            return None
        
        # Get current data
        candle = self.candles[index]
        price = candle['close']
        atr = self.atr_values[index]
        
        if atr == 0:
            return None
        
        # Check filters
        if not self._check_volume(index):
            return None
        
        if not self._check_session(index):
            return None
        
        trend_strength = self._calculate_trend_strength(index)

        # Filter weak trends
        if trend_strength < 0.0001:
            return None

        # Long setup: uptrend + pullback
        if self._is_uptrend(index) and self._is_pullback(index, 'long'):
            # Calculate SL/TP using ATR
            sl = price - (atr * self.atr_multiplier_sl)
            tp = price + (atr * self.atr_multiplier_tp)
            
            # Check min R:R
            risk = abs(price - sl)
            reward = abs(tp - price)
            
            if risk > 0 and (reward / risk) >= self.min_rr:
                return Trade(
                    entry_idx=index,
                    entry_price=price,
                    direction='long',
                    sl=sl,
                    tp=tp,
                    size=1.0
                )
        
        # Short setup: downtrend + pullback
        elif self._is_downtrend(index) and self._is_pullback(index, 'short'):
            sl = price + (atr * self.atr_multiplier_sl)
            tp = price - (atr * self.atr_multiplier_tp)
            
            risk = abs(price - sl)
            reward = abs(price - tp)
            
            if risk > 0 and (reward / risk) >= self.min_rr:
                return Trade(
                    entry_idx=index,
                    entry_price=price,
                    direction='short',
                    sl=sl,
                    tp=tp,
                    size=1.0
                )
        
        return None


# Example usage
if __name__ == "__main__":
    print("Trend Pullback Strategy V2 - Optimizable")
    print("=" * 80)
    print("\nThis strategy has tunable parameters for optimization:")
    print("- lookback: Trend detection period")
    print("- trend_threshold: Minimum trend strength")
    print("- pullback_threshold: Maximum pullback allowed")
    print("- min_rr: Minimum risk:reward ratio")
    print("- atr_multiplier_sl/tp: Stop loss and take profit sizing")
    print("- volume_filter: Require volume confirmation")
    print("- session_filter: Trade only during active sessions")
