from __future__ import annotations

from dataclasses import replace
from datetime import date

import pandas as pd

from watchlist_signal_bot.fetchers.base import BaseFetcher
from watchlist_signal_bot.models import SymbolConfig
from watchlist_signal_bot.pipeline import fetch_with_fallback, select_fetchers
from watchlist_signal_bot.storage import ParquetStore


class FailingFetcher(BaseFetcher):
    name = "failer"

    def fetch(self, symbol: SymbolConfig, start: date, end: date) -> pd.DataFrame:
        raise RuntimeError("boom")


class SuccessFetcher(BaseFetcher):
    name = "success"

    def fetch(self, symbol: SymbolConfig, start: date, end: date) -> pd.DataFrame:
        index = pd.bdate_range(start="2024-01-01", periods=5)
        return pd.DataFrame(
            {
                "Open": [10, 11, 12, 13, 14],
                "High": [11, 12, 13, 14, 15],
                "Low": [9, 10, 11, 12, 13],
                "Close": [10, 11, 12, 13, 14],
                "Adj Close": [10, 11, 12, 13, 14],
                "Volume": [100, 100, 100, 100, 100],
            },
            index=index,
        )


def test_select_fetchers_uses_finance_data_reader_only():
    symbol = SymbolConfig(symbol="AAPL", market="US", name="Apple", group="core")

    fetchers = select_fetchers(symbol)

    assert len(fetchers) == 1
    assert fetchers[0].name == "FinanceDataReader"


def test_fetch_with_secondary_source(tmp_path):
    store = ParquetStore(tmp_path)
    symbol = SymbolConfig(symbol="AAPL", market="US", name="Apple", group="core")

    outcome = fetch_with_fallback(
        symbol,
        start=date(2024, 1, 1),
        end=date(2024, 1, 31),
        store=store,
        fetchers=[FailingFetcher(), SuccessFetcher()],
        attempts=1,
    )

    assert outcome.source == "success"
    assert outcome.quality == "fallback"
    assert "failer: boom" in outcome.errors[0]
    assert store.path_for(symbol.symbol).exists()


def test_fetch_uses_stale_cache_when_all_sources_fail(tmp_path):
    store = ParquetStore(tmp_path)
    symbol = SymbolConfig(symbol="AAPL", market="US", name="Apple", group="core")
    seeded = fetch_with_fallback(
        symbol,
        start=date(2024, 1, 1),
        end=date(2024, 1, 31),
        store=store,
        fetchers=[SuccessFetcher()],
        attempts=1,
    )
    cached_symbol = replace(symbol)

    outcome = fetch_with_fallback(
        cached_symbol,
        start=date(2024, 2, 1),
        end=date(2024, 2, 28),
        store=store,
        fetchers=[FailingFetcher()],
        attempts=1,
    )

    assert seeded.frame.drop(columns=["source"]).equals(outcome.frame.drop(columns=["source"]))
    assert outcome.source == "cache"
    assert outcome.quality == "stale"
