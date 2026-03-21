from __future__ import annotations

from datetime import datetime

import pandas as pd

_COLUMN_RENAMES = {
    "시가": "open",
    "고가": "high",
    "저가": "low",
    "종가": "close",
    "거래량": "volume",
    "거래대금": "value",
    "등락률": "change_pct",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
    "Adj Close": "adj_close",
    "AdjClose": "adj_close",
    "Change": "change_pct",
}


def normalize_ohlcv(
    frame: pd.DataFrame,
    *,
    symbol: str,
    market: str,
    source: str,
    fetched_at: datetime | None,
) -> pd.DataFrame:
    if frame.empty:
        raise ValueError(f"Price frame is empty for {symbol}")

    normalized = frame.copy()
    if isinstance(normalized.columns, pd.MultiIndex):
        normalized.columns = [
            "_".join(str(part) for part in values if part).strip("_")
            for values in normalized.columns.to_flat_index()
        ]
    normalized = normalized.rename(columns=_COLUMN_RENAMES)
    normalized.columns = [
        str(column).strip().lower().replace(" ", "_") for column in normalized.columns
    ]

    if not isinstance(normalized.index, pd.DatetimeIndex):
        if "date" in normalized.columns:
            normalized["date"] = pd.to_datetime(normalized["date"])
            normalized = normalized.set_index("date")
        else:
            normalized.index = pd.to_datetime(normalized.index)

    normalized.index = pd.to_datetime(normalized.index).tz_localize(None).normalize()
    normalized = normalized[~normalized.index.duplicated(keep="last")].sort_index()

    for required in ("open", "high", "low", "close", "volume"):
        if required not in normalized.columns:
            if required == "volume":
                normalized["volume"] = 0
            else:
                raise ValueError(f"Missing required column '{required}' for {symbol}")

    for column in ("open", "high", "low", "close", "volume", "adj_close"):
        if column in normalized.columns:
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    if "adj_close" not in normalized.columns or normalized["adj_close"].isna().all():
        normalized["adj_close"] = normalized["close"]

    normalized = normalized[normalized["close"].notna()].copy()
    normalized = normalized[(normalized["open"] > 0) | (normalized["close"] > 0)].copy()
    normalized["volume"] = normalized["volume"].fillna(0)
    normalized["symbol"] = symbol
    normalized["market"] = market
    normalized["source"] = source
    normalized["fetched_at"] = fetched_at

    keep = [
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "symbol",
        "market",
        "source",
        "fetched_at",
    ]
    extra_columns = [column for column in normalized.columns if column not in keep]
    return normalized[keep + extra_columns]
