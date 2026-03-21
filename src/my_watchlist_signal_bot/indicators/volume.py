from __future__ import annotations

import pandas as pd


def add_volume_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    enriched["volume_avg_20"] = enriched["volume"].rolling(20).mean()
    enriched["volume_ratio_20"] = enriched["volume"] / enriched["volume_avg_20"]
    enriched["up_day"] = enriched["close"] > enriched["close"].shift(1)
    enriched["down_day"] = enriched["close"] < enriched["close"].shift(1)
    enriched["up_on_volume"] = enriched["up_day"] & (enriched["volume_ratio_20"] >= 1.0)
    enriched["down_on_volume"] = enriched["down_day"] & (enriched["volume_ratio_20"] >= 1.0)
    return enriched
