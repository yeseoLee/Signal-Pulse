from __future__ import annotations

from datetime import date

import pandas as pd

from my_watchlist_signal_bot.fetchers.base import BaseFetcher, FetchError
from my_watchlist_signal_bot.models import SymbolConfig


class PykrxFetcher(BaseFetcher):
    name = "pykrx"

    def __init__(self, *, adjusted: bool = True):
        self.adjusted = adjusted

    def supports(self, symbol: SymbolConfig) -> bool:
        return symbol.market == "KR" and symbol.asset_type == "equity"

    def fetch(self, symbol: SymbolConfig, start: date, end: date) -> pd.DataFrame:
        try:
            from pykrx import stock
        except ImportError as exc:  # pragma: no cover - depends on optional install
            raise FetchError("pykrx is not installed") from exc

        try:
            frame = stock.get_market_ohlcv_by_date(
                fromdate=start.strftime("%Y%m%d"),
                todate=end.strftime("%Y%m%d"),
                ticker=symbol.symbol,
                adjusted=self.adjusted,
            )
        except Exception as exc:  # noqa: BLE001
            raise FetchError(str(exc)) from exc

        if frame.empty:
            raise FetchError(f"No data returned for {symbol.symbol}")
        return frame
