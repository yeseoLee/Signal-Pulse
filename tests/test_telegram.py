from __future__ import annotations

from datetime import date, datetime

from watchlist_signal_bot.models import AnalysisResult, Event, SymbolConfig
from watchlist_signal_bot.reports.telegram import render_telegram_summary


def _result(
    *,
    symbol: str,
    name: str,
    display_event: Event | None,
    events: list[Event],
    indicators: dict,
    quality: str = "fresh",
) -> AnalysisResult:
    return AnalysisResult(
        config=SymbolConfig(symbol=symbol, market="US", name=name, group="core_us"),
        as_of=date(2026, 3, 20),
        source="yfinance",
        data_quality=quality,
        fetched_at=datetime(2026, 3, 20, 18, 0, 0),
        indicators=indicators,
        indicator_scores={
            "moving_average": 0,
            "breakout": 0,
            "rsi": 0,
            "volume": 0,
            "relative_strength": 0,
            "momentum": 0,
        },
        events=events,
        display_events=[display_event] if display_event is not None else [],
        score=0,
        confidence="High",
        state="Neutral",
        price=float(indicators["close"]),
    )


def test_telegram_summary_renders_natural_language_sections():
    bullish = _result(
        symbol="005930",
        name="삼성전자",
        quality="fallback",
        display_event=Event(
            code="BREAKOUT_60D",
            polarity="positive",
            title="Breakout 60D",
            weight=20,
            detail="",
        ),
        events=[
            Event(
                code="BREAKOUT_60D",
                polarity="positive",
                title="Breakout 60D",
                weight=20,
                detail="",
            ),
            Event(
                code="VOLUME_CONFIRMED_BREAKOUT",
                polarity="positive",
                title="Volume Confirmed Breakout",
                weight=10,
                detail="",
            ),
            Event(
                code="RS_GT_BENCHMARK",
                polarity="positive",
                title="Relative Strength Positive",
                weight=15,
                detail="",
            ),
        ],
        indicators={
            "close": 70000.0,
            "sma20": 68000.0,
            "sma60": 66000.0,
            "sma120": 62000.0,
            "rsi14": 61.2,
            "volume_ratio_20": 2.1,
            "relative_return_20d": 2.4,
            "relative_return_60d": 5.8,
            "return_20d": 6.2,
            "return_60d": 14.1,
            "return_120d": 28.3,
        },
    )
    neutral = _result(
        symbol="AAPL",
        name="Apple",
        display_event=Event(
            code="WATCH_NEAR_BREAKOUT",
            polarity="neutral",
            title="Watch Near Breakout",
            weight=6,
            detail="",
        ),
        events=[
            Event(
                code="WATCH_NEAR_BREAKOUT",
                polarity="neutral",
                title="Watch Near Breakout",
                weight=6,
                detail="",
            )
        ],
        indicators={
            "close": 192.0,
            "sma20": 190.0,
            "sma60": 188.0,
            "sma120": 191.0,
            "rsi14": 54.5,
            "volume_ratio_20": 1.0,
            "relative_return_20d": 0.4,
            "relative_return_60d": -0.2,
            "return_20d": 1.5,
            "return_60d": 3.2,
            "return_120d": 7.1,
        },
    )
    bearish = _result(
        symbol="NVDA",
        name="NVIDIA",
        display_event=Event(
            code="BREAKDOWN_20D",
            polarity="negative",
            title="Breakdown 20D",
            weight=-15,
            detail="",
        ),
        events=[
            Event(
                code="BREAKDOWN_20D",
                polarity="negative",
                title="Breakdown 20D",
                weight=-15,
                detail="",
            ),
            Event(
                code="DEAD_CROSS",
                polarity="negative",
                title="Dead Cross",
                weight=-20,
                detail="",
            ),
            Event(
                code="HIGH_VOLUME_SELLING",
                polarity="negative",
                title="High Volume Selling",
                weight=-10,
                detail="",
            ),
            Event(
                code="RS_WEAKENING",
                polarity="negative",
                title="RS Weakening",
                weight=-10,
                detail="",
            ),
        ],
        indicators={
            "close": 118.0,
            "sma20": 123.0,
            "sma60": 129.0,
            "sma120": 141.0,
            "rsi14": 37.8,
            "volume_ratio_20": 2.3,
            "relative_return_20d": -4.2,
            "relative_return_60d": -7.6,
            "return_20d": -8.0,
            "return_60d": -14.2,
            "return_120d": -21.0,
        },
    )

    message = render_telegram_summary(
        [bullish, neutral, bearish],
        failures={},
        benchmark_failures={},
    )

    assert "[시그널 봇]" in message
    assert "기준일: 2026-03-20" in message
    assert "[강세]" in message
    assert "[중립]" in message
    assert "[약세]" in message
    assert "삼성전자" in message
    assert "종가는 20일·60일·120일 이동평균선 위에 있습니다." in message
    assert "종가가 직전 60일 고점을 돌파했습니다." in message
    assert "RSI는 61.2입니다." in message
    assert "거래량은 20일 평균 대비 2.1배입니다. 돌파가 거래량으로 확인됐습니다." in message
    assert "NVIDIA" in message
    assert "데드크로스가 발생했습니다." in message
    assert "종가가 직전 20일 저점을 이탈했습니다." in message
    assert "상대강도가 약화되고 있습니다." in message
    assert "지표점수:" not in message
    assert "Score" not in message
