from __future__ import annotations

import numpy as np
import pandas as pd


def add_trend_indicators(frame: pd.DataFrame, *, windows: dict[str, int]) -> pd.DataFrame:
    short = int(windows["short"])
    medium = int(windows["medium"])
    long = int(windows["long"])

    enriched = frame.copy()
    for label, window in (("short", short), ("medium", medium), ("long", long)):
        enriched[f"sma_{label}"] = enriched["close"].rolling(window).mean()

    enriched["above_sma20"] = enriched["close"] > enriched["sma_short"]
    enriched["above_sma60"] = enriched["close"] > enriched["sma_medium"]
    enriched["above_sma120"] = enriched["close"] > enriched["sma_long"]
    enriched["sma20_gt_sma60"] = enriched["sma_short"] > enriched["sma_medium"]
    enriched["sma60_gt_sma120"] = enriched["sma_medium"] > enriched["sma_long"]
    enriched["golden_cross"] = (enriched["sma_short"] > enriched["sma_medium"]) & (
        enriched["sma_short"].shift(1) <= enriched["sma_medium"].shift(1)
    )
    enriched["dead_cross"] = (enriched["sma_short"] < enriched["sma_medium"]) & (
        enriched["sma_short"].shift(1) >= enriched["sma_medium"].shift(1)
    )

    for label, window in (("20d", short), ("60d", medium), ("120d", long), ("252d", 252)):
        enriched[f"prior_high_{label}"] = enriched["high"].rolling(window).max().shift(1)
        enriched[f"prior_low_{label}"] = enriched["low"].rolling(window).min().shift(1)

    enriched["breakout_20d"] = enriched["close"] > enriched["prior_high_20d"]
    enriched["breakout_60d"] = enriched["close"] > enriched["prior_high_60d"]
    enriched["breakout_120d"] = enriched["close"] > enriched["prior_high_120d"]
    enriched["breakdown_20d"] = enriched["close"] < enriched["prior_low_20d"]
    enriched["higher_high"] = (enriched["high"] > enriched["high"].shift(1)) & (
        enriched["high"].shift(1) > enriched["high"].shift(2)
    )
    enriched["higher_low"] = (enriched["low"] > enriched["low"].shift(1)) & (
        enriched["low"].shift(1) > enriched["low"].shift(2)
    )

    range_span = enriched["prior_high_20d"] - enriched["prior_low_20d"]
    enriched["range_percentile_20d"] = np.where(
        range_span > 0,
        (enriched["close"] - enriched["prior_low_20d"]) / range_span,
        np.nan,
    )
    enriched["distance_from_52w_high"] = (
        enriched["close"] / enriched["prior_high_252d"] - 1.0
    ) * 100.0
    enriched["distance_from_52w_low"] = (
        enriched["close"] / enriched["prior_low_252d"] - 1.0
    ) * 100.0
    return enriched
