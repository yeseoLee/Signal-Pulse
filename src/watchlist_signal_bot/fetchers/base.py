from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd

from watchlist_signal_bot.models import SymbolConfig


class FetchError(RuntimeError):
    """Raised when a fetcher cannot retrieve data."""


class BaseFetcher(ABC):
    name = "base"

    def supports(self, symbol: SymbolConfig) -> bool:
        return True

    @abstractmethod
    def fetch(self, symbol: SymbolConfig, start: date, end: date) -> pd.DataFrame:
        raise NotImplementedError
