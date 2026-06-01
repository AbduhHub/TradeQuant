"""
Trend Pullback Strategy V3 - FIXED VERSION
===========================================
CRITICAL FIX: Now waits for price to RESUME trend after pullback
instead of entering during the pullback itself.

Original bug: Entered during pullback, often caught falling knives
Fixed logic: Waits for momentum to return in trend direction

Author: Trading Engine v2.0 - FIXED
"""

from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from trade import Trade


class TrendPullbackV3:
    """
    FIXED Trend Pullback Strategy.
    
    Key changes from V2:
    1. Waits for price to resume trend after pullback
    2. Requires bullish candle after pullback (for longs)
    3. Adds momentum confirmation
    4. Better volume filter implementation
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
        session_filter: bool = False,
        require_momentum_confirmation: bool = True  # NEW
    ):
        """
        Initialize fixed strategy.
        
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
            require_momentum_confirmation: Wait for price to resume trend (RECOMMENDED)
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
        self.require_momentum_confirmation = require_momentum_confirmation
        
        # Pre-calculate ATR
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
        """Check if price is in uptrend."""
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
    
    def _is_pullback_complete_and_resuming(self, index: int, direction: str) -> bool:
        """
        FIXED VERSION: Check if pullback is complete AND price is resuming trend.
        
        This is the critical fix! Instead of entering during the pullback,
        we wait for the pullback to complete and momentum to return.
        
        Args:
            index: Current candle index
            direction: 'long' or 'short'
            
        Returns:
            True if pullback completed and trend resuming
        """
        lookback = min(20, self.lookback // 5)
        
        if index < lookback + 2:
            return False
        
        current = self.candles[index]
        prev = self.candles[index - 1]
        prev2 = self.candles[index - 2]
        
        # Get recent high/low during pullback period
        recent_high = max(c['high'] for c in self.candles[index-lookback:index])
        recent_low = min(c['low'] for c in self.candles[index-lookback:index])
        
        if direction == 'long':
            # Calculate pullback depth from recent high
            pullback_pct = (recent_high - recent_low) / recent_high
            
            # Pullback must be significant but not too deep
            if not (0.002 < pullback_pct < self.pullback_threshold):
                return False
            
            # CRITICAL FIX: Wait for price to resume uptrend
            if self.require_momentum_confirmation:
                # Price must be:
                # 1. Above recent low (pullback complete)
                # 2. Current candle is bullish (close > open)
                # 3. Price moving up (current > previous)
                # 4. Previous candle was also up (momentum building)
                
                price_above_low = current['close'] > recent_low * 1.002
                current_bullish = current['close'] > current['open']
                price_rising = current['close'] > prev['close']
                momentum_building = prev['close'] > prev2['close']
                
                return (price_above_low and current_bullish and 
                       price_rising and momentum_building)
            else:
                # Original logic (less strict)
                pullback_size = (recent_high - current['close']) / recent_high
                return 0.001 < pullback_size < self.pullback_threshold
        
        else:  # short
            pullback_pct = (recent_high - recent_low) / recent_low
            
            if not (0.002 < pullback_pct < self.pullback_threshold):
                return False
            
            # Wait for price to resume downtrend
            if self.require_momentum_confirmation:
                price_below_high = current['close'] < recent_high * 0.998
                current_bearish = current['close'] < current['open']
                price_falling = current['close'] < prev['close']
                momentum_building = prev['close'] < prev2['close']
                
                return (price_below_high and current_bearish and 
                       price_falling and momentum_building)
            else:
                pullback_size = (current['close'] - recent_low) / recent_low
                return 0.001 < pullback_size < self.pullback_threshold
    
    def _check_volume(self, index: int) -> bool:
        """Check if volume is above average (FIXED)."""
        if not self.volume_filter:
            return True
        
        if index < 20:
            return True
        
        current_vol = self.candles[index].get('volume', 0)
        
        # If no volume data, skip filter
        if current_vol == 0:
            return True
        
        avg_vol = sum(c.get('volume', 0) for c in self.candles[index-20:index]) / 20
        
        # Require 20% above average
        return current_vol > avg_vol * 1.2
    
    def _check_session(self, index: int) -> bool:
        """Check if within trading session."""
        if not self.session_filter:
            return True
        
        time = self.candles[index]['time']
        hour = time.hour
        
        # London (8-12) or New York (13-17) sessions
        return (8 <= hour <= 12) or (13 <= hour <= 17)
    
    def on_candle(self, index: int) -> Optional[Trade]:
        """
        Generate trading signal with FIXED logic.
        
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
        
        # Long setup: uptrend + pullback complete + resuming up
        if self._is_uptrend(index) and self._is_pullback_complete_and_resuming(index, 'long'):
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
        
        # Short setup: downtrend + pullback complete + resuming down
        elif self._is_downtrend(index) and self._is_pullback_complete_and_resuming(index, 'short'):
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
    print("Trend Pullback Strategy V3 - FIXED")
    print("=" * 80)
    print("\nCRITICAL FIX APPLIED:")
    print("✓ Now waits for pullback to COMPLETE before entering")
    print("✓ Requires momentum confirmation (price resuming trend)")
    print("✓ Avoids catching falling knives during pullback")
    print("\nThis should dramatically improve performance!")