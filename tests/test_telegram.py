from __future__ import annotations

from datetime import date, datetime

from watchlist_signal_bot.models import AnalysisResult, PriceZone, SymbolConfig
from watchlist_signal_bot.reports.telegram import render_telegram_summary


def _result(
    *,
    symbol: str,
    name: str,
    trend_label: str,
    trend_score: int,
    short_trend_label: str,
    medium_trend_label: str,
    long_trend_label: str,
    asset_type: str = "equity",
    market: str = "US",
    price: float = 100.0,
    return_20d: float = 1.0,
    return_60d: float = 2.0,
    return_120d: float = 3.0,
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
        long_trend_label=long_trend_label,
        trend_label=trend_label,
        trend_score=trend_score,
        trend_summary=f"{trend_label} 설명입니다.",
        price=price,
        support_zones=[
            PriceZone(lower=68099.0, upper=69499.0, center=68749.0, touches=2)
            if market == "KR"
            else PriceZone(lower=95.0, upper=97.0, center=96.0, touches=2)
        ],
        resistance_zones=[
            PriceZone(lower=72099.0, upper=73499.0, center=72749.0, touches=2)
            if market == "KR"
            else PriceZone(lower=103.0, upper=105.0, center=104.0, touches=2)
        ],
        support_summary=(
            "하단에서는 95.00~97.00 구간이 주요 지지대로 보입니다."
            if market == "US" and asset_type == "index"
            else (
                "하단에서는 $95.00~$97.00 구간이 주요 지지대로 보입니다."
                if market == "US"
                else (
                    "하단에서는 68,000~69,400 구간이 주요 지지대로 보입니다."
                    if asset_type == "index"
                    else "하단에서는 68,000~69,400원 구간이 주요 지지대로 보입니다."
                )
            )
        ),
        resistance_summary=(
            "상단에서는 103.00~105.00 구간이 주요 저항대로 보입니다."
            if market == "US" and asset_type == "index"
            else (
                "상단에서는 $103.00~$105.00 구간이 주요 저항대로 보입니다."
                if market == "US"
                else (
                    "상단에서는 72,000~73,400 구간이 주요 저항대로 보입니다."
                    if asset_type == "index"
                    else "상단에서는 72,000~73,400원 구간이 주요 저항대로 보입니다."
                )
            )
        ),
        sparkline=[1.0, 2.0, 3.0, 4.0],
    )


def test_telegram_summary_renders_trend_sections_and_natural_language():
    bullish = _result(
        symbol="005930",
        name="삼성전자",
        market="KR",
        price=70099.0,
        trend_label="상승 추세",
        trend_score=3,
        short_trend_label="상승 추세",
        medium_trend_label="상승 추세",
        long_trend_label="상승 추세",
        return_20d=4.2,
        return_60d=8.1,
        return_120d=12.4,
    )
    neutral = _result(
        symbol="AAPL",
        name="Apple",
        trend_label="횡보",
        trend_score=2,
        short_trend_label="상승 추세",
        medium_trend_label="횡보",
        long_trend_label="상승 추세",
        price=192.5,
        return_20d=1.1,
        return_60d=3.4,
        return_120d=9.0,
    )
    bearish = _result(
        symbol="NVDA",
        name="NVIDIA",
        trend_label="하락 추세",
        trend_score=-3,
        short_trend_label="하락 추세",
        medium_trend_label="하락 추세",
        long_trend_label="하락 추세",
        price=118.0,
        return_20d=-8.0,
        return_60d=-14.2,
        return_120d=-21.0,
    )

    message = render_telegram_summary(
        [bullish, neutral, bearish],
        failures={},
        github_pages_url="https://yeseolee.github.io/Signal-Pulse/",
    )

    assert "[시그널 봇]" in message
    assert "기준일: 2026-03-20" in message
    assert "[상승 추세]" in message
    assert "[횡보]" in message
    assert "[하락 추세]" in message
    assert "005930 (삼성전자)" in message
    assert "현재가: 70,000원" in message
    assert "추세 구간: 단기 상승 추세 / 중기 상승 추세 / 장기 상승 추세" in message
    assert "수익률: 20일 +4.2% / 60일 +8.1% / 120일 +12.4%" in message
    assert "지지: 하단에서는 68,000~69,400원 구간이 주요 지지대로 보입니다." in message
    assert "저항: 상단에서는 $103.00~$105.00 구간이 주요 저항대로 보입니다." in message
    assert "요약:" not in message
    assert "RSI" not in message
    assert "BREAKOUT" not in message
    assert "벤치마크 실패" not in message
    assert "리포트: https://yeseolee.github.io/Signal-Pulse/" in message


def test_telegram_summary_sorts_index_before_equity_within_same_bucket():
    equity = _result(
        symbol="005930",
        name="삼성전자",
        market="KR",
        asset_type="equity",
        price=70099.0,
        trend_label="상승 추세",
        trend_score=3,
        short_trend_label="상승 추세",
        medium_trend_label="상승 추세",
        long_trend_label="상승 추세",
        return_20d=4.2,
        return_60d=8.1,
        return_120d=12.4,
    )
    index_item = _result(
        symbol="KOSPI",
        name="KOSPI",
        market="KR",
        asset_type="index",
        price=265099.0,
        trend_label="상승 추세",
        trend_score=3,
        short_trend_label="상승 추세",
        medium_trend_label="상승 추세",
        long_trend_label="상승 추세",
        return_20d=2.1,
        return_60d=4.2,
        return_120d=9.9,
    )

    message = render_telegram_summary([equity, index_item], failures={})

    assert message.index("1. KOSPI (KOSPI)") < message.index("2. 005930 (삼성전자)")
    assert "현재가: 265,000" in message
    assert "현재가: 265,000원" not in message
    assert "지지: 하단에서는 68,000~69,400 구간이 주요 지지대로 보입니다." in message
