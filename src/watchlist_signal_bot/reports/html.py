from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from watchlist_signal_bot.models import AnalysisResult, Event


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
    new_signal_rows = history_latest[history_latest["new_events"].fillna("") != ""].to_dict(
        "records"
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
            }
        )
    return summary


def _to_card(result: AnalysisResult) -> dict[str, object]:
    indicators = result.indicators
    return {
        "symbol": result.config.symbol,
        "name": result.config.name,
        "market": result.config.market,
        "group": result.config.group,
        "state": result.state,
        "score": result.score,
        "confidence": result.confidence,
        "source": result.source,
        "data_quality": result.data_quality,
        "benchmark": result.config.benchmark_label or result.config.benchmark or "-",
        "price": f"{result.price:,.2f}",
        "events": [_event_to_dict(event) for event in result.display_events],
        "sparkline_points": _sparkline_points(result.sparkline),
        "metrics": [
            {"label": "20D", "value": _fmt_percent(indicators.get("return_20d"))},
            {"label": "60D", "value": _fmt_percent(indicators.get("return_60d"))},
            {"label": "120D", "value": _fmt_percent(indicators.get("return_120d"))},
            {"label": "RS 60D", "value": _fmt_percent(indicators.get("relative_return_60d"))},
            {"label": "RSI14", "value": _fmt_number(indicators.get("rsi14"))},
            {"label": "Vol x", "value": _fmt_number(indicators.get("volume_ratio_20"))},
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
        "detail": event.detail,
        "class_name": f"badge-{event.polarity}",
    }


def _has_event(result: AnalysisResult, code: str) -> bool:
    return any(event.code == code for event in result.display_events)


def _has_negative(result: AnalysisResult) -> bool:
    return any(event.weight < 0 for event in result.display_events)
