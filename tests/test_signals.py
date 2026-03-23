from __future__ import annotations

import pandas as pd

from watchlist_signal_bot.signals import (
    detect_support_resistance,
    detect_trend,
    format_price,
    format_zone,
)


def test_detect_trend_returns_uptrend_with_full_score():
    frame = pd.DataFrame(
        [
            {
                "close": 112.0,
                "sma_fast": 108.0,
                "sma_short": 106.0,
                "sma_medium": 101.0,
                "return_120d": 0.182,
            }
        ]
    )

    short_trend_label, medium_trend_label, long_trend_label, trend_label, trend_score = (
        detect_trend(frame)
    )

    assert short_trend_label == "상승 추세"
    assert medium_trend_label == "상승 추세"
    assert long_trend_label == "상승 추세"
    assert trend_label == "상승 추세"
    assert trend_score == 3


def test_detect_support_resistance_merges_nearby_pivots_into_zones():
    index = pd.bdate_range(start="2024-01-01", periods=13)
    frame = pd.DataFrame(
        {
            "open": [
                100000,
                101000,
                104000,
                101000,
                100000,
                100000,
                105000,
                100000,
                100000,
                99000,
                104000,
                100000,
                101000,
            ],
            "high": [
                100000,
                103000,
                106000,
                103000,
                100000,
                104000,
                108000,
                104000,
                100000,
                103000,
                107000,
                103000,
                100000,
            ],
            "low": [
                100000,
                98000,
                95000,
                98000,
                100000,
                97000,
                94000,
                97000,
                100000,
                96000,
                95000,
                97000,
                101000,
            ],
            "close": [
                100000,
                100000,
                104000,
                100000,
                99000,
                100000,
                106000,
                100000,
                99000,
                100000,
                105000,
                100000,
                99000,
            ],
            "volume": [1000] * 13,
        },
        index=index,
    )

    supports, resistances = detect_support_resistance(
        frame,
        current_price=99000.0,
        lookback_days=13,
        pivot_window=1,
        merge_tolerance=0.02,
        zone_width_ratio=0.01,
        max_supports=2,
        max_resistances=2,
    )

    assert len(supports) == 1
    assert len(resistances) == 1
    assert supports[0].touches == 3
    assert resistances[0].touches == 3
    assert format_zone(supports[0], market="KR") == "93,700~95,600원"
    assert format_zone(resistances[0], market="US") == "$105,930.00~$108,070.00"
    assert format_zone(supports[0], market="KR", asset_type="index") == "93,700~95,600"
    assert format_price(265099.0, market="KR", asset_type="index") == "265,000"
    assert format_price(5801.55, market="US", asset_type="index") == "5,801.55"
