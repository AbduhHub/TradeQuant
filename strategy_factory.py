from strategies.trend_pullback_v3 import TrendPullbackV3
from strategies.break_retest import BreakRetestStrategy
from strategies.inside_bar import InsideBarStrategy
from strategies.liquidity_sweep import LiquiditySweepStrategy


class StrategyFactory:
    STRATEGIES = {
        "trend_pullback": TrendPullbackV3,
        "break_retest":   BreakRetestStrategy,
        "inside_bar":     InsideBarStrategy,
        "liquidity_sweep": LiquiditySweepStrategy,
    }

    @classmethod
    def available(cls):
        return list(cls.STRATEGIES.keys())

    @classmethod
    def create(cls, key, candles, context=None):
        if key not in cls.STRATEGIES:
            raise ValueError(f"Unknown strategy: {key}")

        StrategyClass = cls.STRATEGIES[key]

        if context is None:
            context = {}
        elif not isinstance(context, dict):
            context = {}

        if key == "liquidity_sweep":
            if "swing_highs" not in context or "swing_lows" not in context:
                raise RuntimeError(
                    "Liquidity Sweep needs swing structure; use single-run mode."
                )

        # TrendPullbackV3 only needs candles; context may carry gaps (ignored)
        if key == "trend_pullback":
            return StrategyClass(candles=candles)

        return StrategyClass(candles=candles, **context)