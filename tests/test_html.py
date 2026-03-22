from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from watchlist_signal_bot.models import AnalysisResult, Event, SymbolConfig
from watchlist_signal_bot.reports.html import render_html_report


def test_html_report_renders_korean_labels():
    result = AnalysisResult(
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
    history_frame = pd.DataFrame(
        [
            {
                "as_of": "2026-03-20",
                "symbol": "005930",
                "name": "삼성전자",
                "score": 82,
                "new_events": "BREAKOUT_60D;RS_GT_BENCHMARK",
            }
        ]
    )

    html = render_html_report(
        [result],
        failures={},
        benchmark_failures={},
        history_frame=history_frame,
    )

    assert "<html lang=\"ko\">" in html
    assert "<title>시그널 봇</title>" in html
    assert "규칙 기반 관심종목 모니터" in html
    assert "오늘 새로 발생한 신호" in html
    assert "60일 돌파, 상대강도 우위" in html
    assert "강한 상승 추세" in html
    assert "가격 70,000.00" in html
    assert "신뢰도 높음" not in html
    assert "FinanceDataReader" not in html
    assert "신규 수집" not in html
    assert "벤치마크 KOSPI" not in html
