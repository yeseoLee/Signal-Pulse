from __future__ import annotations

from datetime import date, datetime

from watchlist_signal_bot.models import AnalysisResult, Event, SymbolConfig
from watchlist_signal_bot.reports.telegram import render_telegram_summary


def test_telegram_summary_renders_korean_labels():
    result = AnalysisResult(
        config=SymbolConfig(symbol="005930", market="KR", name="삼성전자", group="core_kr"),
        as_of=date(2026, 3, 20),
        source="pykrx",
        data_quality="fallback",
        fetched_at=datetime(2026, 3, 20, 18, 0, 0),
        indicators={},
        indicator_scores={
            "moving_average": 25,
            "breakout": 10,
            "rsi": 5,
            "volume": 0,
            "relative_strength": 20,
            "momentum": 15,
        },
        events=[
            Event(
                code="RS_GT_BENCHMARK",
                polarity="positive",
                title="Relative Strength Positive",
                weight=15,
                detail="",
            )
        ],
        display_events=[
            Event(
                code="RS_GT_BENCHMARK",
                polarity="positive",
                title="Relative Strength Positive",
                weight=15,
                detail="",
            )
        ],
        score=80,
        confidence="High",
        state="Strong Uptrend",
        price=70000.0,
    )

    message = render_telegram_summary(
        [result],
        failures={},
        benchmark_failures={},
    )

    assert "[시그널 봇]" in message
    assert "기준일: 2026-03-20" in message
    assert "상위 강세" in message
    assert "상대강도 우위" in message
    assert (
        "지표점수: 이평 +25 / 돌파 +10 / RSI +5 / 거래량 0 / 상대강도 +20 / 모멘텀 +15"
        in message
    )
