from __future__ import annotations

from datetime import date

import pandas as pd

from watchlist_signal_bot.fetchers import FDRFetcher
from watchlist_signal_bot.indicators import (
    add_momentum_indicators,
    add_relative_strength,
    add_trend_indicators,
    add_volatility_indicators,
    add_volume_indicators,
)
from watchlist_signal_bot.models import AnalysisResult, FetchOutcome, SymbolConfig
from watchlist_signal_bot.normalize import normalize_ohlcv
from watchlist_signal_bot.signals import (
    classify_state,
    compute_confidence,
    compute_indicator_scores,
    compute_score,
    evaluate_signals,
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
    thresholds: dict,
    benchmark_frame: pd.DataFrame | None = None,
) -> pd.DataFrame:
    frame = add_trend_indicators(price_frame, windows=thresholds["moving_average"])
    frame = add_momentum_indicators(frame, rsi_period=int(thresholds["rsi"]["period"]))
    frame = add_volume_indicators(frame)
    frame = add_volatility_indicators(frame)
    frame = add_relative_strength(frame, benchmark_frame)
    return frame


def analyze_symbol(
    symbol: SymbolConfig,
    *,
    price_outcome: FetchOutcome,
    thresholds: dict,
    benchmark_frame: pd.DataFrame | None = None,
) -> AnalysisResult:
    indicator_frame = build_indicator_frame(
        price_outcome.frame,
        thresholds=thresholds,
        benchmark_frame=benchmark_frame,
    )
    events, display_events, snapshot = evaluate_signals(
        indicator_frame,
        symbol=symbol,
        thresholds=thresholds,
    )
    latest = indicator_frame.iloc[-1]
    score = compute_score(
        latest,
        events=events,
        weights=thresholds.get("score_weights", {}),
    )
    indicator_scores = compute_indicator_scores(
        latest,
        events=events,
        weights=thresholds.get("score_weights", {}),
    )
    confidence = compute_confidence(
        latest,
        data_points=len(indicator_frame),
        data_quality=price_outcome.quality,
        benchmark_available=benchmark_frame is not None and not benchmark_frame.empty,
    )
    return AnalysisResult(
        config=symbol,
        as_of=indicator_frame.index[-1].date(),
        source=price_outcome.source,
        data_quality=price_outcome.quality,
        fetched_at=price_outcome.fetched_at,
        indicators=snapshot,
        indicator_scores=indicator_scores,
        events=events,
        display_events=display_events,
        score=score,
        confidence=confidence,
        state=classify_state(score),
        price=float(latest["close"]),
        sparkline=[float(value) for value in indicator_frame["close"].tail(126).tolist()],
        benchmark_available=benchmark_frame is not None and not benchmark_frame.empty,
    )


def _extract_last_fetched_at(frame: pd.DataFrame):
    if "fetched_at" not in frame.columns:
        return None
    series = pd.to_datetime(frame["fetched_at"], errors="coerce").dropna()
    if series.empty:
        return None
    return series.max().to_pydatetime()
