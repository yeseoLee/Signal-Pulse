from __future__ import annotations

import requests

from watchlist_signal_bot.models import AnalysisResult
from watchlist_signal_bot.signals import format_price
from watchlist_signal_bot.utils.logging import get_logger
from watchlist_signal_bot.utils.sorting import asset_priority

logger = get_logger(__name__)

TREND_SECTIONS = ("상승 추세", "횡보", "하락 추세")


def render_telegram_summary(
    results: list[AnalysisResult],
    *,
    failures: dict[str, str],
    github_pages_url: str | None = None,
) -> str:
    as_of = max((item.as_of for item in results), default=None)

    lines = [
        "[시그널 봇]",
        f"기준일: {as_of.isoformat() if as_of else '-'}",
        "",
        f"점검 종목: {len(results)}",
        f"상승 추세: {sum(1 for item in results if item.trend_label == '상승 추세')}",
        f"횡보: {sum(1 for item in results if item.trend_label == '횡보')}",
        f"하락 추세: {sum(1 for item in results if item.trend_label == '하락 추세')}",
        f"데이터 실패: {len(failures)}개 종목",
        "",
    ]

    for label in TREND_SECTIONS:
        bucket = _sorted_bucket(results, trend_label=label)
        lines.append(f"[{label}]")
        if not bucket:
            lines.append("- 없음")
        else:
            for index, result in enumerate(bucket, start=1):
                lines.extend(_result_lines(index, result))
        lines.append("")

    if failures:
        lines.append("[수집 실패]")
        for symbol, reason in sorted(failures.items()):
            lines.append(f"- {symbol}: {reason}")
        lines.append("")

    if github_pages_url:
        lines.append(f"리포트: {github_pages_url}")
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


def _sorted_bucket(results: list[AnalysisResult], *, trend_label: str) -> list[AnalysisResult]:
    bucket = [item for item in results if item.trend_label == trend_label]
    if trend_label == "하락 추세":
        return sorted(
            bucket,
            key=lambda item: (
                asset_priority(item.config.asset_type),
                float(item.indicators.get("return_60d") or 0.0),
                item.config.symbol,
            ),
        )
    return sorted(
        bucket,
        key=lambda item: (
            asset_priority(item.config.asset_type),
            -float(item.indicators.get("return_60d") or 0.0),
            item.config.symbol,
        ),
    )


def _result_lines(index: int, result: AnalysisResult) -> list[str]:
    price_label = format_price(
        result.price,
        market=result.config.market,
        asset_type=result.config.asset_type,
    )
    return [
        f"{index}. {result.config.symbol} ({result.config.name})",
        f"   - 현재가: {price_label}",
        f"   - 추세: {result.trend_summary}",
        f"   - 수익률: 20일 {_fmt_percent(result.indicators.get('return_20d'))} / "
        f"60일 {_fmt_percent(result.indicators.get('return_60d'))} / "
        f"120일 {_fmt_percent(result.indicators.get('return_120d'))}",
    ]


def _fmt_percent(value: object) -> str:
    if value is None:
        return "-"
    number = float(value)
    if number != number:
        return "-"
    return f"{number:+.1f}%"
