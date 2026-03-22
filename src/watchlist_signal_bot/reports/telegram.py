from __future__ import annotations

import math

import requests

from watchlist_signal_bot.models import AnalysisResult, Event
from watchlist_signal_bot.utils.logging import get_logger

logger = get_logger(__name__)

QUALITY_LABELS = {
    "fresh": "신규수집",
    "fallback": "대체소스",
    "stale": "캐시재사용",
    "partial": "부분성공",
}


def render_telegram_summary(
    results: list[AnalysisResult],
    *,
    failures: dict[str, str],
    benchmark_failures: dict[str, str],
) -> str:
    ordered = sorted(results, key=lambda item: item.config.symbol)
    bullish = _sort_bucket(
        [item for item in ordered if _bucket_label(item) == "강세"],
        label="강세",
    )
    neutral = _sort_bucket(
        [item for item in ordered if _bucket_label(item) == "중립"],
        label="중립",
    )
    bearish = _sort_bucket(
        [item for item in ordered if _bucket_label(item) == "약세"],
        label="약세",
    )
    as_of = max((item.as_of for item in ordered), default=None)

    lines = [
        "[시그널 봇]",
        f"기준일: {as_of.isoformat() if as_of else '-'}",
        "",
        f"점검 종목: {len(ordered)}",
        f"강세: {len(bullish)}",
        f"중립: {len(neutral)}",
        f"약세: {len(bearish)}",
        f"데이터 실패: {len(failures)}개 종목",
        f"벤치마크 실패: {len(benchmark_failures)}",
        "",
    ]

    for label, bucket in (("강세", bullish), ("중립", neutral), ("약세", bearish)):
        lines.append(f"[{label}]")
        if not bucket:
            lines.append("- 없음")
        else:
            for index, result in enumerate(bucket, start=1):
                lines.extend(_result_lines(index, result))
        lines.append("")
    return "\n".join(lines).rstrip()


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


def _sort_bucket(results: list[AnalysisResult], *, label: str) -> list[AnalysisResult]:
    if label == "강세":
        return sorted(
            results,
            key=lambda item: (
                -_event_count(item.events, "positive"),
                -_metric(item, "return_60d"),
                -_metric(item, "relative_return_60d"),
                item.config.symbol,
            ),
        )
    if label == "약세":
        return sorted(
            results,
            key=lambda item: (
                -_event_count(item.events, "negative"),
                _metric(item, "return_60d"),
                _metric(item, "relative_return_60d"),
                item.config.symbol,
            ),
        )
    return sorted(results, key=lambda item: item.config.symbol)


def _event_count(events: list[Event], polarity: str) -> int:
    return sum(1 for event in events if event.polarity == polarity)


def _metric(result: AnalysisResult, key: str) -> float:
    value = result.indicators.get(key)
    if _is_missing(value):
        return 0.0
    return float(value)


def _bucket_label(result: AnalysisResult) -> str:
    primary = result.display_events[0] if result.display_events else None
    if primary is not None:
        return {
            "positive": "강세",
            "neutral": "중립",
            "negative": "약세",
        }.get(primary.polarity, "중립")

    close = result.indicators.get("close")
    sma120 = result.indicators.get("sma120")
    return_60d = result.indicators.get("return_60d")
    relative_return_60d = result.indicators.get("relative_return_60d")

    if (
        not _is_missing(close)
        and not _is_missing(sma120)
        and float(close) > float(sma120)
        and not _is_missing(return_60d)
        and float(return_60d) > 0
        and (_is_missing(relative_return_60d) or float(relative_return_60d) >= 0)
    ):
        return "강세"
    if (
        not _is_missing(close)
        and not _is_missing(sma120)
        and float(close) < float(sma120)
        and not _is_missing(return_60d)
        and float(return_60d) < 0
        and (_is_missing(relative_return_60d) or float(relative_return_60d) <= 0)
    ):
        return "약세"
    return "중립"


def _result_lines(index: int, result: AnalysisResult) -> list[str]:
    lines = [
        (
            f"{index}. {result.config.symbol} ({result.config.name}) | "
            f"{_quality_label(result.data_quality)}"
        ),
        f"   - {_describe_moving_average(result)}",
        f"   - {_describe_breakout(result)}",
        f"   - {_describe_rsi(result)}",
        f"   - {_describe_volume(result)}",
        f"   - {_describe_relative_strength(result)}",
        f"   - {_describe_momentum(result)}",
    ]
    return lines


def _describe_moving_average(result: AnalysisResult) -> str:
    indicators = result.indicators
    close = indicators.get("close")
    sma20 = indicators.get("sma20")
    sma60 = indicators.get("sma60")
    sma120 = indicators.get("sma120")
    if any(_is_missing(value) for value in (close, sma20, sma60, sma120)):
        return "이동평균 데이터가 아직 충분하지 않습니다."

    close = float(close)
    sma20 = float(sma20)
    sma60 = float(sma60)
    sma120 = float(sma120)
    codes = _event_codes(result)

    if close > sma20 and close > sma60 and close > sma120:
        location = "종가는 20일·60일·120일 이동평균선 위에 있습니다."
    elif close < sma20 and close < sma60 and close < sma120:
        location = "종가는 20일·60일·120일 이동평균선 아래에 있습니다."
    else:
        positions = [
            f"20일선 {'위' if close > sma20 else '아래'}",
            f"60일선 {'위' if close > sma60 else '아래'}",
            f"120일선 {'위' if close > sma120 else '아래'}",
        ]
        location = f"종가는 {', '.join(positions)}에 있습니다."

    if sma20 > sma60 > sma120:
        alignment = "이동평균은 정배열입니다."
    elif sma20 < sma60 < sma120:
        alignment = "이동평균은 역배열입니다."
    else:
        alignment = "이동평균 배열은 혼조입니다."

    if "GOLDEN_CROSS" in codes:
        cross = "골든크로스가 발생했습니다."
    elif "DEAD_CROSS" in codes:
        cross = "데드크로스가 발생했습니다."
    else:
        cross = ""

    return " ".join(part for part in (location, alignment, cross) if part)


def _describe_breakout(result: AnalysisResult) -> str:
    codes = _event_codes(result)
    if "BREAKOUT_60D" in codes:
        return "종가가 직전 60일 고점을 돌파했습니다."
    if "BREAKOUT_20D" in codes:
        return "종가가 직전 20일 고점을 돌파했습니다."
    if "BREAKDOWN_20D" in codes:
        return "종가가 직전 20일 저점을 이탈했습니다."
    if "WATCH_NEAR_BREAKOUT" in codes:
        return "20일 고점 부근까지 올라와 돌파 여부를 볼 구간입니다."
    return "신규 돌파나 20일 저점 이탈 신호는 없습니다."


def _describe_rsi(result: AnalysisResult) -> str:
    rsi = result.indicators.get("rsi14")
    if _is_missing(rsi):
        return "RSI 데이터가 아직 충분하지 않습니다."

    rsi = float(rsi)
    if rsi < 30:
        zone = "과매도 구간입니다."
    elif rsi < 45:
        zone = "약한 구간입니다."
    elif rsi < 70:
        zone = "중립 이상으로 무난한 구간입니다."
    elif rsi <= 75:
        zone = "강하지만 과열권에 가까운 구간입니다."
    else:
        zone = "과열권입니다."
    return f"RSI는 {rsi:.1f}입니다. {zone}"


def _describe_volume(result: AnalysisResult) -> str:
    volume_ratio = result.indicators.get("volume_ratio_20")
    if _is_missing(volume_ratio):
        return "거래량 데이터가 아직 충분하지 않습니다."

    volume_ratio = float(volume_ratio)
    codes = _event_codes(result)
    base = f"거래량은 20일 평균 대비 {volume_ratio:.1f}배입니다."
    if "VOLUME_CONFIRMED_BREAKOUT" in codes:
        return f"{base} 돌파가 거래량으로 확인됐습니다."
    if "HIGH_VOLUME_SELLING" in codes:
        return f"{base} 하락과 함께 매도 압력이 커졌습니다."
    if volume_ratio >= 1.8:
        return f"{base} 평소보다 크게 증가했습니다."
    if volume_ratio <= 0.8:
        return f"{base} 평소보다 한산합니다."
    return f"{base} 평균 수준과 비슷합니다."


def _describe_relative_strength(result: AnalysisResult) -> str:
    relative_return_20d = result.indicators.get("relative_return_20d")
    relative_return_60d = result.indicators.get("relative_return_60d")
    if _is_missing(relative_return_20d) and _is_missing(relative_return_60d):
        return "벤치마크 데이터가 없어 상대강도를 계산하지 못했습니다."

    codes = _event_codes(result)
    rel20_text = _fmt_percent(relative_return_20d)
    rel60_text = _fmt_percent(relative_return_60d)
    if "RS_GT_BENCHMARK" in codes:
        return (
            f"20일 상대수익률은 {rel20_text}, 60일 상대수익률은 {rel60_text}로 "
            "벤치마크보다 강합니다."
        )
    if "RS_WEAKENING" in codes:
        return (
            f"20일 상대수익률은 {rel20_text}, 60일 상대수익률은 {rel60_text}로 "
            "상대강도가 약화되고 있습니다."
        )

    if not _is_missing(relative_return_60d):
        relative_return_60d = float(relative_return_60d)
        if relative_return_60d > 0:
            tail = "벤치마크 대비 우위입니다."
        elif relative_return_60d < 0:
            tail = "벤치마크 대비 약합니다."
        else:
            tail = "벤치마크와 비슷합니다."
    else:
        tail = "장기 비교 데이터는 아직 충분하지 않습니다."
    return f"20일 상대수익률은 {rel20_text}, 60일 상대수익률은 {rel60_text}입니다. {tail}"


def _describe_momentum(result: AnalysisResult) -> str:
    return_20d = result.indicators.get("return_20d")
    return_60d = result.indicators.get("return_60d")
    return_120d = result.indicators.get("return_120d")
    if any(_is_missing(value) for value in (return_20d, return_60d, return_120d)):
        return "20일·60일·120일 수익률 데이터가 아직 충분하지 않습니다."

    return_20d = float(return_20d)
    return_60d = float(return_60d)
    return_120d = float(return_120d)
    base = (
        f"20일/60일/120일 수익률은 {_fmt_percent(return_20d)} / "
        f"{_fmt_percent(return_60d)} / {_fmt_percent(return_120d)}입니다."
    )
    codes = _event_codes(result)
    if "MOMENTUM_ACCELERATING" in codes:
        return f"{base} 단기 모멘텀이 중기 흐름 대비 가속되고 있습니다."
    if return_20d > 0 and return_60d > 0 and return_120d > 0:
        return f"{base} 단기부터 중기까지 상승 흐름이 유지되고 있습니다."
    if return_20d < 0 and return_60d < 0 and return_120d < 0:
        return f"{base} 단기부터 중기까지 모두 약한 흐름입니다."
    if return_20d > 0 > return_60d:
        return f"{base} 단기 반등이 있지만 중기 흐름은 아직 약합니다."
    if return_20d < 0 < return_60d:
        return f"{base} 중기 상승 추세 안에서 단기 조정이 나타났습니다."
    return base


def _event_codes(result: AnalysisResult) -> set[str]:
    return {event.code for event in result.events}


def _is_missing(value: object) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _fmt_percent(value: object) -> str:
    if _is_missing(value):
        return "N/A"
    return f"{float(value):+.1f}%"


def _quality_label(quality: str) -> str:
    return QUALITY_LABELS.get(quality, quality)
