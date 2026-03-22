from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from watchlist_signal_bot.models import AnalysisResult, Event

STATE_LABELS = {
    "Strong Uptrend": "강한 상승 추세",
    "Uptrend": "상승 추세",
    "Neutral": "중립",
    "Weak": "약세",
    "Breakdown Risk": "하락 위험",
}

MARKET_LABELS = {
    "KR": "한국",
    "US": "미국",
}

GROUP_LABELS = {
    "core_kr": "한국 핵심",
    "core_us": "미국 핵심",
    "benchmarks": "벤치마크",
}

EVENT_LABELS = {
    "BREAKOUT_20D": "20일 돌파",
    "BREAKOUT_60D": "60일 돌파",
    "GOLDEN_CROSS": "골든크로스",
    "RS_GT_BENCHMARK": "상대강도 우위",
    "VOLUME_CONFIRMED_BREAKOUT": "거래량 동반 돌파",
    "MOMENTUM_ACCELERATING": "모멘텀 가속",
    "WATCH_NEAR_BREAKOUT": "돌파 임박",
    "RANGE_COMPRESSION": "박스 압축",
    "PULLBACK_IN_UPTREND": "상승 추세 눌림",
    "DEAD_CROSS": "데드크로스",
    "BREAKDOWN_20D": "20일 이탈",
    "HIGH_VOLUME_SELLING": "거래량 동반 하락",
    "RS_WEAKENING": "상대강도 약화",
    "CLOSE_BELOW_SMA120": "장기선 하회",
    "RSI_OVERHEATED": "RSI 과열",
}


def render_html_report(
    results: list[AnalysisResult],
    *,
    failures: dict[str, str],
    benchmark_failures: dict[str, str],
    history_frame: pd.DataFrame,
) -> str:
    ordered = sorted(results, key=lambda item: item.score, reverse=True)
    latest_date = max(item.as_of for item in ordered).isoformat()
    groups = _group_summary(ordered)
    history_latest = history_frame[history_frame["as_of"] == latest_date].copy()
    if not history_latest.empty:
        history_latest["new_events_label"] = history_latest["new_events"].map(_localize_event_codes)
    new_signal_rows = (
        history_latest[history_latest["new_events"].fillna("") != ""]
        .sort_values(by=["score", "symbol"], ascending=[False, True])
        .to_dict("records")
    )
    environment = Environment(
        loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = environment.get_template("report.html.j2")
    return template.render(
        as_of=latest_date,
        total_symbols=len(ordered),
        signal_count=sum(1 for item in ordered if item.display_events),
        bullish_count=sum(
            1 for item in ordered if any(event.weight > 0 for event in item.display_events)
        ),
        bearish_count=sum(
            1 for item in ordered if any(event.weight < 0 for event in item.display_events)
        ),
        strong_momentum=[_to_card(item) for item in ordered if item.score >= 60][:8],
        pullbacks=[_to_card(item) for item in ordered if _has_event(item, "PULLBACK_IN_UPTREND")][
            :8
        ],
        weakening=[_to_card(item) for item in ordered if item.score < 40 or _has_negative(item)][
            :8
        ],
        all_symbols=[_to_card(item) for item in ordered],
        failures=failures,
        benchmark_failures=benchmark_failures,
        group_summary=groups,
        new_signal_rows=new_signal_rows,
    )


def _group_summary(results: list[AnalysisResult]) -> list[dict[str, str | int | float]]:
    by_group: dict[str, list[AnalysisResult]] = defaultdict(list)
    for result in results:
        by_group[result.config.group].append(result)

    summary = []
    for group, items in sorted(by_group.items()):
        summary.append(
            {
                "group": group,
                "count": len(items),
                "avg_score": round(sum(item.score for item in items) / len(items), 1),
                "bullish": sum(
                    1 for item in items if any(event.weight > 0 for event in item.display_events)
                ),
                "bearish": sum(
                    1 for item in items if any(event.weight < 0 for event in item.display_events)
                ),
                "group_label": _group_label(group),
            }
        )
    return summary


def _to_card(result: AnalysisResult) -> dict[str, object]:
    indicators = result.indicators
    return {
        "symbol": result.config.symbol,
        "name": result.config.name,
        "market": _market_label(result.config.market),
        "group": _group_label(result.config.group),
        "state": _state_label(result.state),
        "state_class_name": _state_class_name(result.state),
        "score": result.score,
        "price": _format_price(result),
        "events": [_event_to_dict(event) for event in result.display_events],
        "sparkline_points": _sparkline_points(result.sparkline),
        "metrics": [
            {"label": "20일", "value": _fmt_percent(indicators.get("return_20d"))},
            {"label": "60일", "value": _fmt_percent(indicators.get("return_60d"))},
            {"label": "120일", "value": _fmt_percent(indicators.get("return_120d"))},
            {
                "label": "상대강도 60일",
                "value": _fmt_percent(indicators.get("relative_return_60d")),
            },
            {"label": "RSI14", "value": _fmt_number(indicators.get("rsi14"))},
            {"label": "거래량 배수", "value": _fmt_number(indicators.get("volume_ratio_20"))},
        ],
    }


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
    return f"{value:.1f}%"


def _fmt_number(value) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:.2f}"


def _event_to_dict(event: Event) -> dict[str, str]:
    return {
        "title": event.title,
        "code": event.code,
        "label": _event_label(event.code),
        "detail": event.detail,
        "class_name": f"badge-{event.polarity}",
    }


def _has_event(result: AnalysisResult, code: str) -> bool:
    return any(event.code == code for event in result.display_events)


def _has_negative(result: AnalysisResult) -> bool:
    return any(event.weight < 0 for event in result.display_events)


def _event_label(code: str) -> str:
    return EVENT_LABELS.get(code, code)


def _localize_event_codes(raw_codes: str) -> str:
    codes = [code for code in str(raw_codes).split(";") if code]
    return ", ".join(_event_label(code) for code in codes)


def _state_label(state: str) -> str:
    return STATE_LABELS.get(state, state)


def _state_class_name(state: str) -> str:
    if state in {"Strong Uptrend", "Uptrend"}:
        return "badge-positive"
    if state in {"Weak", "Breakdown Risk"}:
        return "badge-negative"
    return "badge-neutral"


def _market_label(market: str) -> str:
    return MARKET_LABELS.get(market, market)


def _group_label(group: str) -> str:
    return GROUP_LABELS.get(group, group.replace("_", " "))


def _format_price(result: AnalysisResult) -> str:
    if result.config.market == "KR":
        return f"{result.price:,.0f}원"
    if result.config.market == "US":
        return f"${result.price:,.2f}"
    return f"{result.price:,.2f}"
