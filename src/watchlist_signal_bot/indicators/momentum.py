from __future__ import annotations

import pandas as pd


def add_return_indicators(
    frame: pd.DataFrame,
    *,
    windows: tuple[int, ...] | list[int],
) -> pd.DataFrame:
    enriched = frame.copy()
    for window in windows:
        enriched[f"return_{int(window)}d"] = enriched["close"].pct_change(int(window))
    return enriched


def add_momentum_indicators(frame: pd.DataFrame, *, rsi_period: int) -> pd.DataFrame:
    del rsi_period
    return add_return_indicators(frame, windows=(20, 60, 120))
