from __future__ import annotations

import numpy as np
import pandas as pd


def add_volatility_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    prev_close = enriched["close"].shift(1)
    true_range = pd.concat(
        [
            enriched["high"] - enriched["low"],
            (enriched["high"] - prev_close).abs(),
            (enriched["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    enriched["atr_14"] = true_range.rolling(14).mean()
    enriched["daily_volatility_20"] = enriched["close"].pct_change().rolling(20).std()
    enriched["day_range_pct"] = (enriched["high"] - enriched["low"]) / enriched["close"]
    enriched["avg_day_range_pct_20"] = enriched["day_range_pct"].rolling(20).mean()
    enriched["range_expansion_ratio"] = enriched["day_range_pct"] / enriched["avg_day_range_pct_20"]

    rolling_mean = enriched["close"].rolling(20).mean()
    rolling_std = enriched["close"].rolling(20).std()
    enriched["bb_mid"] = rolling_mean
    enriched["bb_upper"] = rolling_mean + (rolling_std * 2)
    enriched["bb_lower"] = rolling_mean - (rolling_std * 2)
    enriched["bb_touch_upper"] = enriched["close"] >= enriched["bb_upper"]
    enriched["bb_touch_lower"] = enriched["close"] <= enriched["bb_lower"]
    enriched["bb_width"] = (enriched["bb_upper"] - enriched["bb_lower"]) / rolling_mean.replace(
        0, np.nan
    )
    enriched["squeeze"] = enriched["bb_width"] <= enriched["bb_width"].rolling(20).quantile(0.2)
    return enriched
