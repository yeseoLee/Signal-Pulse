from __future__ import annotations

import numpy as np
import pandas as pd


def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def add_momentum_indicators(frame: pd.DataFrame, *, rsi_period: int) -> pd.DataFrame:
    enriched = frame.copy()
    for window in (5, 20, 60, 120, 252):
        enriched[f"return_{window}d"] = enriched["close"].pct_change(window)

    enriched["roc_20"] = enriched["close"].pct_change(20) * 100.0
    enriched["rsi_14"] = _rsi(enriched["close"], rsi_period)

    low_14 = enriched["low"].rolling(14).min()
    high_14 = enriched["high"].rolling(14).max()
    denominator = (high_14 - low_14).replace(0, np.nan)
    enriched["stoch_k"] = ((enriched["close"] - low_14) / denominator) * 100.0
    enriched["stoch_d"] = enriched["stoch_k"].rolling(3).mean()
    enriched["momentum_accelerating"] = enriched["return_20d"] > (enriched["return_60d"] / 3.0)
    return enriched


def add_relative_strength(
    frame: pd.DataFrame, benchmark_frame: pd.DataFrame | None
) -> pd.DataFrame:
    enriched = frame.copy()
    if benchmark_frame is None or benchmark_frame.empty:
        enriched["benchmark_close"] = np.nan
        enriched["benchmark_return_20d"] = np.nan
        enriched["benchmark_return_60d"] = np.nan
        enriched["relative_return_20d"] = np.nan
        enriched["relative_return_60d"] = np.nan
        enriched["relative_ratio"] = np.nan
        enriched["relative_ratio_sma20"] = np.nan
        enriched["rs_positive"] = False
        enriched["rs_weakening"] = False
        return enriched

    benchmark = benchmark_frame[["close"]].rename(columns={"close": "benchmark_close"})
    merged = enriched.join(benchmark, how="left")
    merged["benchmark_close"] = merged["benchmark_close"].ffill()
    merged["benchmark_return_20d"] = merged["benchmark_close"].pct_change(20)
    merged["benchmark_return_60d"] = merged["benchmark_close"].pct_change(60)
    merged["relative_return_20d"] = merged["return_20d"] - merged["benchmark_return_20d"]
    merged["relative_return_60d"] = merged["return_60d"] - merged["benchmark_return_60d"]
    merged["relative_ratio"] = merged["close"] / merged["benchmark_close"]
    merged["relative_ratio_sma20"] = merged["relative_ratio"].rolling(20).mean()
    merged["rs_positive"] = (merged["relative_return_60d"] > 0) & (
        merged["relative_ratio"] > merged["relative_ratio_sma20"]
    )
    merged["rs_weakening"] = (merged["relative_return_20d"] < 0) & (
        merged["relative_ratio"] < merged["relative_ratio_sma20"]
    )
    return merged
