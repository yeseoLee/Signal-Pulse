from __future__ import annotations

import pandas as pd

from watchlist_signal_bot.models import SymbolConfig
from watchlist_signal_bot.pipeline import build_indicator_frame
from watchlist_signal_bot.signals import classify_state, compute_score, evaluate_signals

THRESHOLDS = {
    "moving_average": {"short": 20, "medium": 60, "long": 120},
    "breakout": {
        "short_window": 20,
        "medium_window": 60,
        "long_window": 120,
        "near_breakout_buffer": 0.98,
    },
    "volume": {"spike_ratio": 1.8},
    "rsi": {"period": 14, "overbought": 70, "oversold": 30},
    "score_weights": {
        "breakout_20d": 10,
        "breakout_60d": 20,
        "golden_cross": 15,
        "above_sma120": 10,
        "rs_positive": 15,
        "volume_confirmation": 10,
        "dead_cross": -20,
    },
}


def _breakout_frame() -> pd.DataFrame:
    index = pd.bdate_range(start="2024-01-01", periods=260)
    close = pd.Series(range(100, 360), index=index, dtype="float64")
    close.iloc[-1] = close.iloc[-2] * 1.12
    frame = pd.DataFrame(index=index)
    frame["close"] = close
    frame["open"] = close * 0.995
    frame["high"] = close * 1.01
    frame["low"] = close * 0.99
    frame["adj_close"] = close
    frame["volume"] = 1_000_000
    frame.loc[frame.index[-1], "volume"] = 2_400_000
    return frame


def test_breakout_signal_scores_as_uptrend():
    symbol = SymbolConfig(symbol="NVDA", market="US", name="NVIDIA", group="core_us")
    prices = _breakout_frame()
    benchmark = prices.copy()
    benchmark["close"] = benchmark["close"] * 0.97

    indicators = build_indicator_frame(prices, thresholds=THRESHOLDS, benchmark_frame=benchmark)
    events, display_events, _ = evaluate_signals(indicators, symbol=symbol, thresholds=THRESHOLDS)
    score = compute_score(indicators.iloc[-1], events=events, weights=THRESHOLDS["score_weights"])

    codes = {event.code for event in display_events}
    assert "BREAKOUT_60D" in codes
    assert "VOLUME_CONFIRMED_BREAKOUT" in {event.code for event in events}
    assert score >= 60
    assert classify_state(score) in {"Uptrend", "Strong Uptrend"}
