from __future__ import annotations

import numpy as np
import pandas as pd

from my_watchlist_signal_bot.indicators import (
    add_momentum_indicators,
    add_relative_strength,
    add_trend_indicators,
    add_volatility_indicators,
    add_volume_indicators,
)


def _price_frame(seed: int = 7, *, start: str = "2024-01-01", periods: int = 320) -> pd.DataFrame:
    index = pd.bdate_range(start=start, periods=periods)
    rng = np.random.default_rng(seed)
    close = pd.Series(np.linspace(100, 190, periods) + rng.normal(0, 1.0, periods), index=index)
    return pd.DataFrame(
        {
            "open": close * 0.995,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "adj_close": close,
            "volume": np.linspace(1_000_000, 1_800_000, periods),
        },
        index=index,
    )


def test_indicator_stack_populates_expected_columns():
    frame = _price_frame()
    benchmark = _price_frame(seed=11) * [0.99, 0.99, 0.99, 0.99, 0.99, 1.0]

    enriched = add_trend_indicators(frame, windows={"short": 20, "medium": 60, "long": 120})
    enriched = add_momentum_indicators(enriched, rsi_period=14)
    enriched = add_volume_indicators(enriched)
    enriched = add_volatility_indicators(enriched)
    enriched = add_relative_strength(enriched, benchmark)

    latest = enriched.iloc[-1]
    assert latest["sma20_gt_sma60"]
    assert latest["sma60_gt_sma120"]
    assert pd.notna(latest["rsi_14"])
    assert pd.notna(latest["atr_14"])
    assert pd.notna(latest["relative_return_60d"])
