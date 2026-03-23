from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from watchlist_signal_bot.fetchers import FDRFetcher
from watchlist_signal_bot.indicators import add_moving_averages, add_return_indicators
from watchlist_signal_bot.models import AnalysisResult, FetchOutcome, SymbolConfig
from watchlist_signal_bot.normalize import normalize_ohlcv
from watchlist_signal_bot.signals import (
    detect_support_resistance,
    detect_trend,
    summarize_levels,
    summarize_trend,
)
from watchlist_signal_bot.storage import ParquetStore
from watchlist_signal_bot.utils.dates import utc_now
from watchlist_signal_bot.utils.retry import retry_call


def select_fetchers(symbol: SymbolConfig):
    del symbol
    return [FDRFetcher()]


def fetch_with_fallback(
    symbol: SymbolConfig,
    *,
    start: date,
    end: date,
    store: ParquetStore,
    fetchers=None,
    attempts: int = 2,
) -> FetchOutcome:
    errors: list[str] = []
    now = utc_now()
    selected_fetchers = fetchers or select_fetchers(symbol)

    for index, fetcher in enumerate(selected_fetchers):
        if not fetcher.supports(symbol):
            continue
        try:
            raw_frame = retry_call(
                lambda fetcher=fetcher: fetcher.fetch(symbol, start, end),
                attempts=attempts,
            )
            normalized = normalize_ohlcv(
                raw_frame,
                symbol=symbol.symbol,
                market=symbol.market,
                source=fetcher.name,
                fetched_at=now,
            )
            quality = "fresh" if index == 0 else "fallback"
            store.write(symbol.symbol, normalized)
            return FetchOutcome(
                symbol=symbol.symbol,
                frame=normalized,
                source=fetcher.name,
                quality=quality,
                fetched_at=now,
                errors=errors,
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{fetcher.name}: {exc}")

    cached = store.load(symbol.symbol)
    if cached is not None and not cached.empty:
        fetched_at = _extract_last_fetched_at(cached)
        normalized = normalize_ohlcv(
            cached,
            symbol=symbol.symbol,
            market=symbol.market,
            source="cache",
            fetched_at=fetched_at,
        )
        return FetchOutcome(
            symbol=symbol.symbol,
            frame=normalized,
            source="cache",
            quality="stale",
            fetched_at=fetched_at,
            errors=errors,
        )

    raise RuntimeError(f"Unable to fetch {symbol.symbol}: {' | '.join(errors)}")


def build_indicator_frame(
    price_frame: pd.DataFrame,
    *,
    thresholds: dict[str, Any],
) -> pd.DataFrame:
    frame = add_moving_averages(price_frame, windows=thresholds["moving_average"])
    frame = add_return_indicators(frame, windows=tuple(thresholds["returns"]["windows"]))
    return frame


def analyze_symbol(
    symbol: SymbolConfig,
    *,
    price_outcome: FetchOutcome,
    thresholds: dict[str, Any],
) -> AnalysisResult:
    indicator_frame = build_indicator_frame(
        price_outcome.frame,
        thresholds=thresholds,
    )
    latest = indicator_frame.iloc[-1]
    short_trend_label, medium_trend_label, long_trend_label, trend_label, trend_score = (
        detect_trend(indicator_frame)
    )

    levels_cfg = thresholds["levels"]
    supports, resistances = detect_support_resistance(
        indicator_frame,
        current_price=float(latest["close"]),
        lookback_days=int(levels_cfg["lookback_days"]),
        pivot_window=int(levels_cfg["pivot_window"]),
        merge_tolerance=float(levels_cfg["merge_tolerance"]),
        zone_width_ratio=float(levels_cfg["zone_width_ratio"]),
        max_supports=int(levels_cfg["max_supports"]),
        max_resistances=int(levels_cfg["max_resistances"]),
    )

    return_20d = _maybe_percent(latest.get("return_20d"))
    return_60d = _maybe_percent(latest.get("return_60d"))
    return_120d = _maybe_percent(latest.get("return_120d"))

    trend_summary = summarize_trend(
        indicator_frame,
        short_trend_label=short_trend_label,
        medium_trend_label=medium_trend_label,
        long_trend_label=long_trend_label,
        trend_label=trend_label,
    )
    support_summary = summarize_levels(
        supports,
        kind="support",
        market=symbol.market,
        asset_type=symbol.asset_type,
    )
    resistance_summary = summarize_levels(
        resistances,
        kind="resistance",
        market=symbol.market,
        asset_type=symbol.asset_type,
    )
    return AnalysisResult(
        config=symbol,
        as_of=indicator_frame.index[-1].date(),
        source=price_outcome.source,
        data_quality=price_outcome.quality,
        fetched_at=price_outcome.fetched_at,
        indicators={
            "close": float(latest["close"]),
            "sma5": _maybe_float(latest.get("sma_fast")),
            "sma20": _maybe_float(latest.get("sma_short")),
            "sma60": _maybe_float(latest.get("sma_medium")),
            "return_20d": return_20d,
            "return_60d": return_60d,
            "return_120d": return_120d,
            "data_points": int(indicator_frame["close"].count()),
        },
        short_trend_label=short_trend_label,
        medium_trend_label=medium_trend_label,
        long_trend_label=long_trend_label,
        trend_label=trend_label,
        trend_score=trend_score,
        trend_summary=trend_summary,
        price=float(latest["close"]),
        support_zones=supports,
        resistance_zones=resistances,
        support_summary=support_summary,
        resistance_summary=resistance_summary,
        sparkline=[float(value) for value in indicator_frame["close"].tail(126).tolist()],
    )


def _extract_last_fetched_at(frame: pd.DataFrame):
    if "fetched_at" not in frame.columns:
        return None
    series = pd.to_datetime(frame["fetched_at"], errors="coerce").dropna()
    if series.empty:
        return None
    return series.max().to_pydatetime()


def _maybe_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _maybe_percent(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value) * 100.0
