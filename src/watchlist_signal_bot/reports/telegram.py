from __future__ import annotations

from collections import Counter

import requests

from watchlist_signal_bot.models import AnalysisResult
from watchlist_signal_bot.signals import negative_indicator_score, positive_indicator_score
from watchlist_signal_bot.utils.logging import get_logger

logger = get_logger(__name__)

STATE_LABELS = {
    "Strong Uptrend": "강한 상승 추세",
    "Uptrend": "상승 추세",
    "Neutral": "중립",
    "Weak": "약세",
    "Breakdown Risk": "하락 위험",
}

QUALITY_LABELS = {
    "fresh": "신규수집",
    "fallback": "대체소스",
    "stale": "캐시재사용",
    "partial": "부분성공",
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
    "PULLBACK_IN_UPTREND": "상승추세 눌림",
    "DEAD_CROSS": "데드크로스",
    "BREAKDOWN_20D": "20일 이탈",
    "HIGH_VOLUME_SELLING": "거래량 동반 하락",
    "RS_WEAKENING": "상대강도 약화",
    "CLOSE_BELOW_SMA120": "장기선 하회",
    "RSI_OVERHEATED": "RSI 과열",
}

INDICATOR_LABELS = {
    "moving_average": "이평",
    "breakout": "돌파",
    "rsi": "RSI",
    "volume": "거래량",
    "relative_strength": "상대강도",
    "momentum": "모멘텀",
}


def render_telegram_summary(
    results: list[AnalysisResult],
    *,
    failures: dict[str, str],
    benchmark_failures: dict[str, str],
) -> str:
    ordered = sorted(
        results,
        key=lambda item: (
            positive_indicator_score(item.indicator_scores),
            -negative_indicator_score(item.indicator_scores),
            item.score,
        ),
        reverse=True,
    )
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
        "[시그널 봇]",
        f"기준일: {as_of}",
        "",
        f"신호 발생: {signal_count} / {len(ordered)} 종목",
        f"강세: {len(bullish)}",
        f"약세: {len(bearish)}",
        f"중립 관찰: {len(neutral)}",
        f"데이터 실패: {len(failures)}개 종목",
        f"벤치마크 실패: {len(benchmark_failures)}",
        "",
        "상위 강세",
    ]
    lines.extend(_top_lines(bullish))
    lines.append("")
    lines.append("상위 위험")
    lines.extend(_top_lines(bearish or ordered[-5:], reverse=False))
    lines.append("")
    lines.append("상태 분포")
    lines.extend(f"- {_state_label(state)}: {count}" for state, count in state_counts.most_common())
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
    ordered = sorted(
        results,
        key=lambda item: _ranking_score(item, reverse=reverse),
        reverse=True,
    )[:5]
    if not ordered:
        return ["- 없음"]

    lines = []
    for index, result in enumerate(ordered, start=1):
        event_summary = ", ".join(_event_label(event.code) for event in result.display_events)
        if not event_summary:
            event_summary = _state_label(result.state)
        lines.append(
            f"{index}. {result.config.symbol} ({result.config.name}) - "
            f"{event_summary} | {_quality_label(result.data_quality)}"
        )
        lines.append(f"   지표점수: {_indicator_score_line(result.indicator_scores)}")
    return lines


def _ranking_score(result: AnalysisResult, *, reverse: bool) -> tuple[int, int, int]:
    if reverse:
        return (
            positive_indicator_score(result.indicator_scores),
            -negative_indicator_score(result.indicator_scores),
            result.score,
        )
    return (
        negative_indicator_score(result.indicator_scores),
        -positive_indicator_score(result.indicator_scores),
        -result.score,
    )


def _indicator_score_line(indicator_scores: dict[str, int]) -> str:
    return " / ".join(
        f"{label} {_signed(indicator_scores[key])}"
        for key, label in INDICATOR_LABELS.items()
    )


def _signed(value: int) -> str:
    if value > 0:
        return f"+{value}"
    return str(value)


def _state_label(state: str) -> str:
    return STATE_LABELS.get(state, state)


def _event_label(code: str) -> str:
    return EVENT_LABELS.get(code, code)


def _quality_label(quality: str) -> str:
    return QUALITY_LABELS.get(quality, quality)
