from strategies.trend_pullback import TrendPullbackStrategy
from strategies.break_retest import BreakRetestStrategy
from strategies.inside_bar import InsideBarStrategy
from strategies.liquidity_sweep import LiquiditySweepStrategy


class StrategyFactory:
    STRATEGIES = {
        "trend_pullback": TrendPullbackStrategy,
        "break_retest": BreakRetestStrategy,
        "inside_bar": InsideBarStrategy,
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

        # Trend Pullback: immutable
        if key == "trend_pullback":
            return StrategyClass(candles)

        # Normalize context
        if context is None:
            context = {}
        elif not isinstance(context, dict):
            context = {}

        # Liquidity Sweep REQUIRES structure
        if key == "liquidity_sweep":
            if "swing_highs" not in context or "swing_lows" not in context:
                raise RuntimeError(
                    "Liquidity Sweep requires swing_highs and swing_lows. "
                    "UI path does not provide structure data."
                )

        return StrategyClass(
            candles=candles,
            **context
        )
