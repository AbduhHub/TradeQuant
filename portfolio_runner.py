from metrics import calculate_metrics
from strategy_factory import StrategyFactory


def run_portfolio(
    candles,
    gaps,
    strategy_keys,
    risk_per_trade=1.0
):
    trades = []

    for key in strategy_keys:
        strategy = StrategyFactory.create(
            key=key,
            candles=candles
        )
        trades.extend(strategy.run(gaps))

    metrics = calculate_metrics(trades)
    return trades, metrics
