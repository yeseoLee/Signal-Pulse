from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from watchlist_signal_bot.models import AnalysisResult, Event, SymbolConfig
from watchlist_signal_bot.reports.html import render_html_report


def test_html_report_renders_korean_labels():
    kr_result = AnalysisResult(
        config=SymbolConfig(
            symbol="005930",
            market="KR",
            name="삼성전자",
            group="core_kr",
            benchmark="KS11",
            benchmark_label="KOSPI",
        ),
        as_of=date(2026, 3, 20),
        source="FinanceDataReader",
        data_quality="fresh",
        fetched_at=datetime(2026, 3, 20, 18, 0, 0),
        indicators={
            "return_20d": 4.2,
            "return_60d": 8.1,
            "return_120d": 12.4,
            "relative_return_60d": 3.5,
            "rsi14": 61.2,
            "volume_ratio_20": 1.8,
        },
        indicator_scores={
            "moving_average": 0,
            "breakout": 0,
            "rsi": 0,
            "volume": 0,
            "relative_strength": 0,
            "momentum": 0,
        },
        events=[
            Event(
                code="BREAKOUT_60D",
                polarity="positive",
                title="60일 돌파",
                weight=20,
                detail="종가가 직전 60일 고점을 상향 돌파했습니다.",
            )
        ],
        display_events=[
            Event(
                code="BREAKOUT_60D",
                polarity="positive",
                title="60일 돌파",
                weight=20,
                detail="종가가 직전 60일 고점을 상향 돌파했습니다.",
            )
        ],
        score=82,
        confidence="High",
        state="Strong Uptrend",
        price=70000.0,
        sparkline=[65000.0, 66000.0, 67000.0, 70000.0],
        benchmark_available=True,
    )
    us_result = AnalysisResult(
        config=SymbolConfig(
            symbol="AAPL",
            market="US",
            name="Apple",
            group="core_us",
            benchmark="SPY",
            benchmark_label="SPY",
        ),
        as_of=date(2026, 3, 20),
        source="FinanceDataReader",
        data_quality="fresh",
        fetched_at=datetime(2026, 3, 20, 18, 0, 0),
        indicators={
            "return_20d": 2.1,
            "return_60d": 4.3,
            "return_120d": 9.9,
            "relative_return_60d": 1.2,
            "rsi14": 58.4,
            "volume_ratio_20": 1.2,
        },
        indicator_scores={
            "moving_average": 0,
            "breakout": 0,
            "rsi": 0,
            "volume": 0,
            "relative_strength": 0,
            "momentum": 0,
        },
        events=[
            Event(
                code="WATCH_NEAR_BREAKOUT",
                polarity="neutral",
                title="돌파 임박",
                weight=6,
                detail="20일 고점 근처까지 접근했습니다.",
            )
        ],
        display_events=[
            Event(
                code="WATCH_NEAR_BREAKOUT",
                polarity="neutral",
                title="돌파 임박",
                weight=6,
                detail="20일 고점 근처까지 접근했습니다.",
            )
        ],
        score=61,
        confidence="High",
        state="Uptrend",
        price=192.5,
        sparkline=[182.0, 184.0, 188.0, 192.5],
        benchmark_available=True,
    )
    history_frame = pd.DataFrame(
        [
            {
                "as_of": "2026-03-20",
                "symbol": "005930",
                "name": "삼성전자",
                "score": 82,
                "new_events": "BREAKOUT_60D;RS_GT_BENCHMARK",
            },
            {
                "as_of": "2026-03-20",
                "symbol": "AAPL",
                "name": "Apple",
                "score": 61,
                "new_events": "WATCH_NEAR_BREAKOUT",
            }
        ]
    )

    html = render_html_report(
        [kr_result, us_result],
        failures={},
        benchmark_failures={},
        history_frame=history_frame,
    )

    assert "<html lang=\"ko\">" in html
    assert "<title>Watchlist Signal Bot</title>" in html
    assert "규칙 기반 관심종목 모니터" in html
    assert "오늘 새로 발생한 신호" in html
    assert "60일 돌파, 상대강도 우위" in html
    assert "강한 상승 추세" in html
    assert "가격 70,000원" in html
    assert "가격 $192.50" in html
    assert "신뢰도 높음" not in html
    assert "FinanceDataReader" not in html
    assert "신규 수집" not in html
    assert "벤치마크 KOSPI" not in html
