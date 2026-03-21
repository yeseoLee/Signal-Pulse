from __future__ import annotations

import pandas as pd

from watchlist_signal_bot.models import Event


def compute_indicator_scores(
    latest_row: pd.Series,
    *,
    events: list[Event],
    weights: dict[str, int],
) -> dict[str, int]:
    event_map = {event.code: event for event in events}
    scores = {
        "moving_average": 0,
        "breakout": 0,
        "rsi": 0,
        "volume": 0,
        "relative_strength": 0,
        "momentum": 0,
    }

    scores["moving_average"] += 8 if latest_row.get("above_sma20") else 0
    scores["moving_average"] += 12 if latest_row.get("above_sma60") else 0
    scores["moving_average"] += 15 if latest_row.get("above_sma120") else -10
    scores["moving_average"] += 8 if latest_row.get("sma20_gt_sma60") else 0
    scores["moving_average"] += 10 if latest_row.get("sma60_gt_sma120") else 0
    scores["moving_average"] += _event_weight(event_map, weights, "GOLDEN_CROSS", 15)
    scores["moving_average"] += _event_weight(event_map, weights, "DEAD_CROSS", -20)
    scores["moving_average"] += _event_weight(event_map, weights, "CLOSE_BELOW_SMA120", -10)

    scores["breakout"] += _event_weight(event_map, weights, "BREAKOUT_20D", 10)
    scores["breakout"] += _event_weight(event_map, weights, "BREAKOUT_60D", 20)
    scores["breakout"] += 25 if latest_row.get("breakout_120d") else 0
    scores["breakout"] += _event_weight(event_map, weights, "WATCH_NEAR_BREAKOUT", 6)
    scores["breakout"] += _event_weight(event_map, weights, "BREAKDOWN_20D", -15)

    rsi = latest_row.get("rsi_14")
    if pd.notna(rsi):
        if 45 <= rsi < 70:
            scores["rsi"] += 10
        elif 35 <= rsi < 45 or 70 <= rsi <= 75:
            scores["rsi"] += 5
        elif rsi < 30:
            scores["rsi"] -= 10
        elif rsi > 75:
            scores["rsi"] -= 5
    scores["rsi"] += _event_weight(event_map, weights, "RSI_OVERHEATED", -5)

    if latest_row.get("up_on_volume"):
        scores["volume"] += 8
    if latest_row.get("volume_ratio_20", 0) >= 1.0 and latest_row.get("up_day"):
        scores["volume"] += 4
    scores["volume"] += _event_weight(event_map, weights, "VOLUME_CONFIRMED_BREAKOUT", 10)
    scores["volume"] += _event_weight(event_map, weights, "HIGH_VOLUME_SELLING", -10)

    if latest_row.get("relative_return_20d", 0) > 0:
        scores["relative_strength"] += 8
    if latest_row.get("relative_return_60d", 0) > 0:
        scores["relative_strength"] += 12
    scores["relative_strength"] += _event_weight(event_map, weights, "RS_GT_BENCHMARK", 15)
    scores["relative_strength"] += _event_weight(event_map, weights, "RS_WEAKENING", -10)

    scores["momentum"] += 10 if latest_row.get("return_20d", 0) > 0 else -10
    scores["momentum"] += 15 if latest_row.get("return_60d", 0) > 0 else -15
    scores["momentum"] += 15 if latest_row.get("return_120d", 0) > 0 else -15
    scores["momentum"] += _event_weight(event_map, weights, "MOMENTUM_ACCELERATING", 10)

    return scores


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


def positive_indicator_score(indicator_scores: dict[str, int]) -> int:
    return sum(score for score in indicator_scores.values() if score > 0)


def negative_indicator_score(indicator_scores: dict[str, int]) -> int:
    return sum(-score for score in indicator_scores.values() if score < 0)


def _event_weight(
    event_map: dict[str, Event],
    weights: dict[str, int],
    code: str,
    default: int,
) -> int:
    if code not in event_map:
        return 0
    return weights.get(code.lower(), default)
