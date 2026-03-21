from __future__ import annotations

from collections import Counter

import requests

from watchlist_signal_bot.models import AnalysisResult
from watchlist_signal_bot.utils.logging import get_logger

logger = get_logger(__name__)


def render_telegram_summary(
    results: list[AnalysisResult],
    *,
    failures: dict[str, str],
    benchmark_failures: dict[str, str],
) -> str:
    ordered = sorted(results, key=lambda item: item.score, reverse=True)
    signal_count = sum(1 for item in ordered if item.display_events)
    bullish = [item for item in ordered if any(event.weight > 0 for event in item.display_events)]
    bearish = [item for item in ordered if any(event.weight < 0 for event in item.display_events)]
    neutral = [
        item
        for item in ordered
        if item not in bullish and item not in bearish and any(item.display_events)
    ]
    state_counts = Counter(item.state for item in ordered)
    as_of = max(item.as_of for item in ordered).isoformat()

    lines = [
        "[My Watchlist Signal Bot]",
        f"Date: {as_of}",
        "",
        f"Signals: {signal_count} / {len(ordered)} symbols",
        f"Bullish: {len(bullish)}",
        f"Bearish: {len(bearish)}",
        f"Neutral watch: {len(neutral)}",
        f"Data failures: {len(failures)} symbol(s)",
        f"Benchmark failures: {len(benchmark_failures)}",
        "",
        "Top Bullish",
    ]
    lines.extend(_top_lines(bullish))
    lines.append("")
    lines.append("Top Risk")
    lines.extend(_top_lines(bearish or ordered[-5:], reverse=False))
    lines.append("")
    lines.append("State Mix")
    lines.extend(f"- {state}: {count}" for state, count in state_counts.most_common())
    return "\n".join(lines)


def send_telegram_message(message: str, *, bot_token: str | None, chat_id: str | None) -> None:
    if not bot_token or not chat_id:
        logger.info("Telegram credentials are missing; skipping Telegram delivery")
        return

    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    response.raise_for_status()


def _top_lines(results: list[AnalysisResult], *, reverse: bool = True) -> list[str]:
    ordered = sorted(results, key=lambda item: item.score, reverse=reverse)[:5]
    if not ordered:
        return ["- None"]

    lines = []
    for index, result in enumerate(ordered, start=1):
        event_summary = ", ".join(event.code for event in result.display_events) or result.state
        lines.append(
            f"{index}. {result.config.symbol} ({result.config.name}) - {event_summary} | "
            f"Score {result.score} | {result.data_quality}"
        )
    return lines
