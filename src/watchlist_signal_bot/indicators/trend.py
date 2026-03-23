from __future__ import annotations

import pandas as pd


def add_moving_averages(frame: pd.DataFrame, *, windows: dict[str, int]) -> pd.DataFrame:
    fast = int(windows["fast"])
    short = int(windows["short"])
    medium = int(windows["medium"])

    enriched = frame.copy()
    enriched["sma_fast"] = enriched["close"].rolling(fast).mean()
    enriched["sma_short"] = enriched["close"].rolling(short).mean()
    enriched["sma_medium"] = enriched["close"].rolling(medium).mean()
    enriched["above_sma5"] = enriched["close"] > enriched["sma_fast"]
    enriched["above_sma20"] = enriched["close"] > enriched["sma_short"]
    enriched["above_sma60"] = enriched["close"] > enriched["sma_medium"]
    enriched["sma5_gt_sma20"] = enriched["sma_fast"] > enriched["sma_short"]
    enriched["sma20_gt_sma60"] = enriched["sma_short"] > enriched["sma_medium"]
    return enriched


def add_trend_indicators(frame: pd.DataFrame, *, windows: dict[str, int]) -> pd.DataFrame:
    return add_moving_averages(frame, windows=windows)
