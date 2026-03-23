from __future__ import annotations

import math
from collections.abc import Iterable
from statistics import mean

import pandas as pd

from watchlist_signal_bot.models import PriceZone


def detect_trend(frame: pd.DataFrame) -> tuple[str, str, str, str, str, int]:
    latest = frame.iloc[-1]
    close = latest.get("close")
    sma5 = latest.get("sma_fast")
    sma20 = latest.get("sma_short")
    sma60 = latest.get("sma_medium")
    sma120 = latest.get("sma_long")

    short_trend_label = _classify_price_vs_average(close=close, average=sma5)
    medium_trend_label = _classify_alignment(close=close, fast=sma5, slow=sma20)
    mid_long_trend_label = _classify_alignment(close=close, fast=sma20, slow=sma60)
    long_trend_label = _classify_alignment(close=close, fast=sma60, slow=sma120)
    trend_label = mid_long_trend_label
    trend_score = (
        _trend_points(short_trend_label)
        + _trend_points(medium_trend_label)
        + _trend_points(mid_long_trend_label)
        + _trend_points(long_trend_label)
    )
    return (
        short_trend_label,
        medium_trend_label,
        mid_long_trend_label,
        long_trend_label,
        trend_label,
        trend_score,
    )


def find_pivot_highs(frame: pd.DataFrame, *, window: int = 3) -> list[tuple[pd.Timestamp, float]]:
    highs = frame["high"]
    pivots: list[tuple[pd.Timestamp, float]] = []
    for index in range(window, len(frame) - window):
        current = highs.iloc[index]
        before = highs.iloc[index - window : index]
        after = highs.iloc[index + 1 : index + window + 1]
        if current > before.max() and current > after.max():
            pivots.append((frame.index[index], float(current)))
    return pivots


def find_pivot_lows(frame: pd.DataFrame, *, window: int = 3) -> list[tuple[pd.Timestamp, float]]:
    lows = frame["low"]
    pivots: list[tuple[pd.Timestamp, float]] = []
    for index in range(window, len(frame) - window):
        current = lows.iloc[index]
        before = lows.iloc[index - window : index]
        after = lows.iloc[index + 1 : index + window + 1]
        if current < before.min() and current < after.min():
            pivots.append((frame.index[index], float(current)))
    return pivots


def merge_price_levels(
    levels: Iterable[tuple[pd.Timestamp, float]],
    *,
    tolerance: float = 0.01,
    zone_width_ratio: float = 0.01,
) -> list[PriceZone]:
    ordered = sorted(levels, key=lambda item: item[1])
    if not ordered:
        return []

    clusters: list[list[tuple[pd.Timestamp, float]]] = [[ordered[0]]]
    for item in ordered[1:]:
        cluster = clusters[-1]
        center = mean(price for _, price in cluster)
        if abs(item[1] - center) / center <= tolerance:
            cluster.append(item)
        else:
            clusters.append([item])

    merged = []
    for cluster in clusters:
        center = mean(price for _, price in cluster)
        last_date = max(timestamp for timestamp, _ in cluster).date()
        merged.append(
            PriceZone(
                lower=center * (1 - zone_width_ratio),
                upper=center * (1 + zone_width_ratio),
                center=center,
                touches=len(cluster),
                last_date=last_date,
            )
        )
    return merged


def detect_support_resistance(
    frame: pd.DataFrame,
    *,
    current_price: float,
    lookback_days: int,
    pivot_window: int,
    merge_tolerance: float,
    zone_width_ratio: float,
    max_supports: int,
    max_resistances: int,
) -> tuple[list[PriceZone], list[PriceZone]]:
    recent = frame.tail(lookback_days).copy()
    pivot_highs = find_pivot_highs(recent, window=pivot_window)
    pivot_lows = find_pivot_lows(recent, window=pivot_window)

    supports = [
        zone
        for zone in merge_price_levels(
            pivot_lows,
            tolerance=merge_tolerance,
            zone_width_ratio=zone_width_ratio,
        )
        if zone.center < current_price
    ]
    resistances = [
        zone
        for zone in merge_price_levels(
            pivot_highs,
            tolerance=merge_tolerance,
            zone_width_ratio=zone_width_ratio,
        )
        if zone.center > current_price
    ]

    supports = sorted(
        supports,
        key=lambda zone: (
            abs(current_price - zone.center),
            -zone.touches,
            -(zone.last_date.toordinal() if zone.last_date else 0),
        ),
    )[:max_supports]
    resistances = sorted(
        resistances,
        key=lambda zone: (
            abs(zone.center - current_price),
            -zone.touches,
            -(zone.last_date.toordinal() if zone.last_date else 0),
        ),
    )[:max_resistances]
    return supports, resistances


def summarize_trend(
    frame: pd.DataFrame,
    *,
    short_trend_label: str,
    medium_trend_label: str,
    mid_long_trend_label: str,
    long_trend_label: str,
    trend_label: str,
) -> str:
    latest = frame.iloc[-1]
    sma5 = latest.get("sma_fast")
    sma20 = latest.get("sma_short")
    sma60 = latest.get("sma_medium")
    sma120 = latest.get("sma_long")

    if pd.isna(sma5) or pd.isna(sma20) or pd.isna(sma60) or pd.isna(sma120):
        return "이동평균 데이터가 충분하지 않아 단기·중단기·중장기·장기 추세 판단이 제한적입니다."

    labels = (
        short_trend_label,
        medium_trend_label,
        mid_long_trend_label,
        long_trend_label,
    )

    if labels == ("상승 추세", "상승 추세", "상승 추세", "상승 추세"):
        return "단기부터 장기까지 상승 구조가 고르게 정렬돼 있습니다."
    if labels == ("하락 추세", "하락 추세", "하락 추세", "하락 추세"):
        return "단기부터 장기까지 하락 구조가 이어지고 있습니다."
    if labels == ("횡보", "횡보", "횡보", "횡보"):
        return "단기부터 장기까지 뚜렷한 방향성 없이 횡보 구간에 머물러 있습니다."

    if trend_label == "상승 추세":
        if short_trend_label == "하락 추세" or medium_trend_label == "하락 추세":
            return (
                "중장기 상승 추세 안에서 단기 또는 중단기 조정이 나타났지만 "
                "구조 자체는 아직 유지되고 있습니다."
            )
        if long_trend_label == "하락 추세":
            return "중장기 구조는 상승 우위지만 장기 추세는 아직 완전히 돌아서지 않았습니다."
        if short_trend_label == "횡보" or medium_trend_label == "횡보":
            return "중장기 상승 우위는 유지되지만 단기 또는 중단기는 숨 고르기 구간입니다."
        return "중장기 상승 우위가 유지되고 있으며 장기 구조도 비교적 안정적입니다."

    if trend_label == "하락 추세":
        if short_trend_label == "상승 추세" or medium_trend_label == "상승 추세":
            return "중장기 하락 추세 속에서 단기 또는 중단기 반등이 나타난 상태입니다."
        if long_trend_label == "상승 추세":
            return "중장기 구조는 약해졌지만 장기 추세는 아직 완전히 꺾이지 않았습니다."
        if short_trend_label == "횡보" or medium_trend_label == "횡보":
            return "중장기 하락 우위가 이어지지만 단기 또는 중단기는 반등 또는 정체 구간입니다."
        return "중장기 하락 우위가 이어지고 있으며 장기 구조도 전반적으로 약합니다."

    up_count = sum(label == "상승 추세" for label in labels)
    down_count = sum(label == "하락 추세" for label in labels)
    if up_count > down_count:
        return (
            "기간별 방향은 엇갈리지만 전체적으로는 상방 우세 속에서 "
            "중장기 기준 횡보가 이어지고 있습니다."
        )
    if down_count > up_count:
        return (
            "기간별 방향은 엇갈리지만 전체적으로는 하방 우세 속에서 "
            "중장기 기준 횡보가 이어지고 있습니다."
        )
    return f"단기부터 장기까지 방향이 엇갈리며, 기준 추세는 중장기 기준 {trend_label}입니다."


def summarize_levels(
    zones: list[PriceZone],
    *,
    kind: str,
    market: str,
    asset_type: str = "equity",
) -> str:
    if not zones:
        if kind == "support":
            return "현재가 아래에서 뚜렷한 지지 가격대는 아직 제한적입니다."
        return "현재가 위에서 뚜렷한 저항 가격대는 아직 제한적입니다."

    labels = [format_zone(zone, market=market, asset_type=asset_type) for zone in zones[:2]]
    if kind == "support":
        if len(labels) == 1:
            return f"하단에서는 {labels[0]} 구간이 1차 지지로 해석됩니다."
        return f"하단에서는 {labels[0]} 구간과 {labels[1]} 구간이 주요 지지대로 보입니다."
    if len(labels) == 1:
        return f"상단에서는 {labels[0]} 구간이 1차 저항으로 해석됩니다."
    return f"상단에서는 {labels[0]} 구간과 {labels[1]} 구간이 주요 저항대로 보입니다."


def format_zone(zone: PriceZone, *, market: str, asset_type: str = "equity") -> str:
    if market == "KR":
        lower = normalize_output_price(zone.lower, market=market)
        upper = normalize_output_price(zone.upper, market=market)
        if asset_type == "index":
            return f"{lower:,.0f}~{upper:,.0f}"
        return f"{lower:,.0f}~{upper:,.0f}원"
    if market == "US":
        if asset_type == "index":
            return f"{zone.lower:,.2f}~{zone.upper:,.2f}"
        return f"${zone.lower:,.2f}~${zone.upper:,.2f}"
    return f"{zone.lower:,.2f}~{zone.upper:,.2f}"


def format_price(value: float, *, market: str, asset_type: str = "equity") -> str:
    normalized = normalize_output_price(value, market=market)
    if market == "KR":
        if asset_type == "index":
            return f"{normalized:,.0f}"
        return f"{normalized:,.0f}원"
    if market == "US":
        if asset_type == "index":
            return f"{normalized:,.2f}"
        return f"${normalized:,.2f}"
    return f"{normalized:,.2f}"


def normalize_output_price(value: float, *, market: str) -> float:
    number = float(value)
    if market == "KR":
        return math.floor(number / 100.0) * 100.0
    return number


def _classify_alignment(*, close, fast, slow) -> str:
    if pd.isna(close) or pd.isna(fast) or pd.isna(slow):
        return "횡보"

    close_value = float(close)
    fast_value = float(fast)
    slow_value = float(slow)

    if close_value > fast_value > slow_value:
        return "상승 추세"
    if close_value < fast_value < slow_value:
        return "하락 추세"
    return "횡보"


def _classify_price_vs_average(*, close, average) -> str:
    if pd.isna(close) or pd.isna(average):
        return "횡보"

    close_value = float(close)
    average_value = float(average)

    if close_value > average_value:
        return "상승 추세"
    if close_value < average_value:
        return "하락 추세"
    return "횡보"


def _trend_points(label: str) -> int:
    return {
        "상승 추세": 1,
        "횡보": 0,
        "하락 추세": -1,
    }.get(label, 0)
