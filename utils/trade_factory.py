from trade import Trade


def create_trade(
    *,
    entry_idx: int,
    entry_price: float,
    direction: str,
    sl: float | None,
    tp: float | None,
    size: float = 1.0,
):
    """
    SAFE Trade constructor.
    Uses entry_idx ONLY to avoid module shadowing issues.
    """

    return Trade(
        entry_idx=entry_idx,
        entry_price=entry_price,
        direction=direction,
        sl=sl,
        tp=tp,
        size=size,
    )
