from __future__ import annotations

import pandas as pd

from my_watchlist_signal_bot.models import Event


def compute_score(
    latest_row: pd.Series,
    *,
    events: list[Event],
    weights: dict[str, int],
) -> int:
    score = 0
    score += 15 if latest_row.get("return_20d", 0) > 0 else 0
    score += 20 if latest_row.get("return_60d", 0) > 0 else 0
    score += 20 if latest_row.get("return_120d", 0) > 0 else 0

    if latest_row.get("sma20_gt_sma60") and latest_row.get("sma60_gt_sma120"):
        score += 15
    elif latest_row.get("above_sma120"):
        score += 8

    rsi = latest_row.get("rsi_14")
    if pd.notna(rsi):
        if 45 <= rsi <= 70:
            score += 10
        elif 30 <= rsi < 45 or 70 < rsi <= 80:
            score += 5

    if latest_row.get("volume_ratio_20", 0) >= 1.0:
        score += 10

    if latest_row.get("relative_return_60d", 0) > 0:
        score += 10

    for event in events:
        event_weight = weights.get(event.code.lower(), event.weight)
        score += event_weight

    return max(0, min(100, int(round(score))))


def compute_confidence(
    latest_row: pd.Series,
    *,
    data_points: int,
    data_quality: str,
    benchmark_available: bool,
) -> str:
    points = 0
    points += 1 if data_points >= 252 else 0
    points += 1 if latest_row.get("volume_avg_20", 0) > 0 else 0
    points += 1 if benchmark_available else 0
    points += 1 if data_quality in {"fresh", "fallback"} else 0
    points += 1 if latest_row.get("daily_volatility_20", 1.0) <= 0.06 else 0
    if points >= 4:
        return "High"
    if points >= 3:
        return "Medium"
    return "Low"
