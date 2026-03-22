from __future__ import annotations

from datetime import date

import pandas as pd

from watchlist_signal_bot.fetchers.base import BaseFetcher, FetchError
from watchlist_signal_bot.models import SymbolConfig


class FDRFetcher(BaseFetcher):
    name = "FinanceDataReader"

    def fetch(self, symbol: SymbolConfig, start: date, end: date) -> pd.DataFrame:
        try:
            import FinanceDataReader as fdr
        except ImportError as exc:  # pragma: no cover - depends on optional install
            raise FetchError("FinanceDataReader is not installed") from exc

        try:
            frame = fdr.DataReader(symbol.symbol, start=start, end=end)
        except Exception as exc:  # noqa: BLE001
            raise FetchError(str(exc)) from exc

        if frame.empty:
            raise FetchError(f"No data returned for {symbol.symbol}")
        return frame
