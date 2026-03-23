from __future__ import annotations

from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from watchlist_signal_bot.models import AnalysisResult
from watchlist_signal_bot.signals import format_price, format_zone
from watchlist_signal_bot.utils.sorting import asset_priority

TREND_ORDER = {
    "상승 추세": 0,
    "횡보": 1,
    "하락 추세": 2,
}

TREND_BADGE_CLASS = {
    "상승 추세": "chip-trend-up",
    "횡보": "chip-trend-flat",
    "하락 추세": "chip-trend-down",
}

MARKET_LABELS = {
    "KR": "한국",
    "US": "미국",
}

GROUP_LABELS = {
    "core_kr": "한국 핵심",
    "core_us": "미국 핵심",
}


def render_html_report(
    results: list[AnalysisResult],
    *,
    failures: dict[str, str],
    history_frame: pd.DataFrame,
) -> str:
    ordered = sorted(
        results,
        key=lambda item: (
            TREND_ORDER.get(item.trend_label, 99),
            asset_priority(item.config.asset_type),
            -item.trend_score,
            -_metric(item, "return_60d"),
            item.config.symbol,
        ),
    )
    latest_date = max(item.as_of for item in ordered).isoformat()
    if "asset_priority" not in history_frame.columns:
        history_frame = history_frame.copy()
        history_frame["asset_priority"] = 1
    history_latest = history_frame[history_frame["as_of"] == latest_date].copy()
    trend_change_rows = (
        history_latest[history_latest["trend_change"].fillna("") != ""]
        .sort_values(by=["asset_priority", "symbol"])
        .to_dict("records")
    )

    trend_sections = [
        {
            "label": label,
            "count": sum(1 for item in ordered if item.trend_label == label),
            "cards": [_to_card(item) for item in ordered if item.trend_label == label],
        }
        for label in ("상승 추세", "횡보", "하락 추세")
    ]

    environment = Environment(
        loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = environment.get_template("report.html.j2")
    return template.render(
        as_of=latest_date,
        total_symbols=len(ordered),
        uptrend_count=sum(1 for item in ordered if item.trend_label == "상승 추세"),
        sideways_count=sum(1 for item in ordered if item.trend_label == "횡보"),
        downtrend_count=sum(1 for item in ordered if item.trend_label == "하락 추세"),
        trend_sections=trend_sections,
        trend_change_rows=trend_change_rows,
        failures=failures,
    )


def _to_card(result: AnalysisResult) -> dict[str, object]:
    indicators = result.indicators
    return {
        "symbol": result.config.symbol,
        "name": result.config.name,
        "market": MARKET_LABELS.get(result.config.market, result.config.market),
        "group": _group_label(result),
        "price": format_price(
            result.price,
            market=result.config.market,
            asset_type=result.config.asset_type,
        ),
        "trend_label": result.trend_label,
        "trend_badge_class": TREND_BADGE_CLASS.get(result.trend_label, "chip-trend-flat"),
        "trend_score": result.trend_score,
        "trend_breakdown": [
            _trend_chip("단기", result.short_trend_label),
            _trend_chip("중기", result.medium_trend_label),
            _trend_chip("장기", result.long_trend_label),
        ],
        "trend_summary": result.trend_summary,
        "returns": [
            {"label": "20일 수익률", "value": _fmt_percent(indicators.get("return_20d"))},
            {"label": "60일 수익률", "value": _fmt_percent(indicators.get("return_60d"))},
            {"label": "120일 수익률", "value": _fmt_percent(indicators.get("return_120d"))},
        ],
        "supports": [
            format_zone(
                zone,
                market=result.config.market,
                asset_type=result.config.asset_type,
            )
            for zone in result.support_zones
        ],
        "resistances": [
            format_zone(
                zone,
                market=result.config.market,
                asset_type=result.config.asset_type,
            )
            for zone in result.resistance_zones
        ],
        "support_summary": result.support_summary,
        "resistance_summary": result.resistance_summary,
        "sparkline_points": _sparkline_points(result.sparkline),
    }


def _metric(result: AnalysisResult, key: str) -> float:
    value = result.indicators.get(key)
    if value is None or pd.isna(value):
        return 0.0
    return float(value)


def _sparkline_points(values: list[float], *, width: int = 220, height: int = 64) -> str:
    if not values:
        return ""
    low = min(values)
    high = max(values)
    spread = high - low or 1.0
    points = []
    for index, value in enumerate(values):
        x = index * (width / max(len(values) - 1, 1))
        y = height - ((value - low) / spread) * height
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def _fmt_percent(value) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):+.1f}%"


def _trend_chip(period: str, label: str) -> dict[str, str]:
    return {
        "label": f"{period} {label}",
        "class_name": TREND_BADGE_CLASS.get(label, "chip-trend-flat"),
    }


def _group_label(result: AnalysisResult) -> str:
    if result.config.asset_type == "index":
        return "지수"
    return GROUP_LABELS.get(result.config.group, result.config.group)
