from __future__ import annotations

import numpy as np
import pandas as pd

from watchlist_signal_bot.indicators import add_moving_averages, add_return_indicators


def _price_frame(*, start: str = "2024-01-01", periods: int = 160) -> pd.DataFrame:
    index = pd.bdate_range(start=start, periods=periods)
    close = pd.Series(np.linspace(100, 180, periods), index=index, dtype="float64")
    return pd.DataFrame(
        {
            "open": close * 0.995,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.linspace(1_000_000, 1_500_000, periods),
        },
        index=index,
    )


def test_indicator_stack_populates_moving_averages_and_returns():
    frame = _price_frame()

    enriched = add_moving_averages(frame, windows={"fast": 5, "short": 20, "medium": 60})
    enriched = add_return_indicators(enriched, windows=(20, 60, 120))

    latest = enriched.iloc[-1]
    assert latest["above_sma5"]
    assert latest["above_sma20"]
    assert latest["above_sma60"]
    assert latest["sma5_gt_sma20"]
    assert latest["sma20_gt_sma60"]
    assert pd.notna(latest["sma_fast"])
    assert pd.notna(latest["sma_short"])
    assert pd.notna(latest["sma_medium"])
    assert pd.notna(latest["return_20d"])
    assert pd.notna(latest["return_60d"])
    assert pd.notna(latest["return_120d"])
