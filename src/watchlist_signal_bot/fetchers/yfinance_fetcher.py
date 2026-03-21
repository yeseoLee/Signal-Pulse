from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from watchlist_signal_bot.fetchers.base import BaseFetcher, FetchError
from watchlist_signal_bot.models import SymbolConfig


class YFinanceFetcher(BaseFetcher):
    name = "yfinance"

    def supports(self, symbol: SymbolConfig) -> bool:
        return symbol.market == "US" or symbol.asset_type in {"etf", "index"}

    def fetch(self, symbol: SymbolConfig, start: date, end: date) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError as exc:  # pragma: no cover - depends on optional install
            raise FetchError("yfinance is not installed") from exc

        cache_dir = Path(os.getenv("YFINANCE_CACHE_DIR", "/tmp/py-yfinance"))
        cache_dir.mkdir(parents=True, exist_ok=True)
        if hasattr(yf, "set_tz_cache_location"):
            yf.set_tz_cache_location(str(cache_dir))

        try:
            frame = yf.download(
                symbol.symbol,
                start=start,
                end=end + timedelta(days=1),
                interval="1d",
                auto_adjust=False,
                progress=False,
            )
        except Exception as exc:  # noqa: BLE001
            raise FetchError(str(exc)) from exc

        if frame.empty:
            raise FetchError(f"No data returned for {symbol.symbol}")
        return frame
