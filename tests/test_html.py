from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from watchlist_signal_bot.models import AnalysisResult, PriceZone, SymbolConfig
from watchlist_signal_bot.reports.html import render_html_report


def _result(
    *,
    symbol: str,
    market: str,
    name: str,
    asset_type: str = "equity",
    trend_label: str,
    trend_score: int,
    short_trend_label: str,
    medium_trend_label: str,
    mid_long_trend_label: str,
    long_trend_label: str,
    price: float,
    return_20d: float,
    return_60d: float,
    return_120d: float,
) -> AnalysisResult:
    return AnalysisResult(
        config=SymbolConfig(
            symbol=symbol,
            market=market,
            name=name,
            group="core",
            asset_type=asset_type,
        ),
        as_of=date(2026, 3, 20),
        source="FinanceDataReader",
        data_quality="fresh",
        fetched_at=datetime(2026, 3, 20, 18, 0, 0),
        indicators={
            "return_20d": return_20d,
            "return_60d": return_60d,
            "return_120d": return_120d,
        },
        short_trend_label=short_trend_label,
        medium_trend_label=medium_trend_label,
        mid_long_trend_label=mid_long_trend_label,
        long_trend_label=long_trend_label,
        trend_label=trend_label,
        trend_score=trend_score,
        trend_summary=f"{trend_label} 요약 문장입니다.",
        price=price,
        support_zones=[
            PriceZone(lower=264399, upper=267499, center=265949, touches=2)
            if market == "KR" and asset_type == "index"
            else PriceZone(lower=68099, upper=69499, center=68749, touches=2),
        ]
        if market == "KR"
        else [PriceZone(lower=182.40, upper=186.10, center=184.25, touches=2)],
        resistance_zones=[
            PriceZone(lower=270099, upper=273499, center=271799, touches=2)
            if market == "KR" and asset_type == "index"
            else PriceZone(lower=72099, upper=73499, center=72749, touches=2),
        ]
        if market == "KR"
        else [PriceZone(lower=198.60, upper=202.20, center=200.40, touches=2)],
        support_summary="하단에서는 첫 번째 가격대가 주요 지지로 보입니다.",
        resistance_summary="상단에서는 첫 번째 가격대가 주요 저항으로 보입니다.",
        sparkline=[1.0, 2.0, 3.0, 4.0],
    )


def test_html_report_renders_trend_and_price_zone_layout():
    kr_result = _result(
        symbol="005930",
        market="KR",
        name="삼성전자",
        trend_label="상승 추세",
        trend_score=3,
        short_trend_label="상승 추세",
        medium_trend_label="상승 추세",
        mid_long_trend_label="상승 추세",
        long_trend_label="상승 추세",
        price=70099.0,
        return_20d=4.2,
        return_60d=8.1,
        return_120d=12.4,
    )
    us_result = _result(
        symbol="AAPL",
        market="US",
        name="Apple",
        trend_label="횡보",
        trend_score=1,
        short_trend_label="상승 추세",
        medium_trend_label="횡보",
        mid_long_trend_label="횡보",
        long_trend_label="상승 추세",
        price=192.5,
        return_20d=1.1,
        return_60d=3.4,
        return_120d=9.0,
    )
    history_frame = pd.DataFrame(
        [
            {
                "as_of": "2026-03-20",
                "symbol": "005930",
                "name": "삼성전자",
                "asset_priority": 1,
                "previous_trend_label": "횡보",
                "trend_label": "상승 추세",
                "trend_change": "횡보 -> 상승 추세",
                "return_20d": 4.2,
                "return_60d": 8.1,
                "return_120d": 12.4,
            }
        ]
    )

    html = render_html_report(
        [kr_result, us_result],
        failures={},
        history_frame=history_frame,
    )

    assert "<html lang=\"ko\">" in html
    assert "<title>Watchlist Signal Bot</title>" in html
    assert "주간 기술적 분석 보고서" in html
    assert "추세 변화" in html
    assert "상승 추세" in html
    assert "횡보" in html
    assert "기준 상승 추세" not in html
    assert "단기 상승 추세" in html
    assert "중단기 횡보" in html
    assert "중장기 횡보" in html
    assert "장기 상승 추세" in html
    assert "20일 수익률" in html
    assert "68,000~69,400원" in html
    assert "$182.40~$186.10" in html
    assert "70,000원" in html
    assert "$192.50" in html
    assert "하단에서는 첫 번째 가격대가 주요 지지로 보입니다." not in html
    assert "상단에서는 첫 번째 가격대가 주요 저항으로 보입니다." not in html
    assert "종합 요약" not in html
    assert "FinanceDataReader" not in html
    assert "신규 수집" not in html


def test_html_report_sorts_index_before_equity_within_same_section():
    index_result = _result(
        symbol="KOSPI",
        market="KR",
        name="KOSPI",
        asset_type="index",
        trend_label="상승 추세",
        trend_score=3,
        short_trend_label="상승 추세",
        medium_trend_label="상승 추세",
        mid_long_trend_label="상승 추세",
        long_trend_label="상승 추세",
        price=265099.0,
        return_20d=2.1,
        return_60d=4.2,
        return_120d=9.9,
    )
    equity_result = _result(
        symbol="005930",
        market="KR",
        name="삼성전자",
        asset_type="equity",
        trend_label="상승 추세",
        trend_score=3,
        short_trend_label="상승 추세",
        medium_trend_label="상승 추세",
        mid_long_trend_label="상승 추세",
        long_trend_label="상승 추세",
        price=70099.0,
        return_20d=4.2,
        return_60d=8.1,
        return_120d=12.4,
    )

    html = render_html_report(
        [equity_result, index_result],
        failures={},
        history_frame=pd.DataFrame(
            columns=["as_of", "asset_priority", "symbol", "trend_change"]
        ),
    )

    assert html.index("KOSPI (KOSPI)") < html.index("005930 (삼성전자)")
    assert "한국 · 지수" in html
    assert "265,000" in html
    assert "265,000원" not in html
    assert "264,300~267,400" in html
    assert "264,300~267,400원" not in html
