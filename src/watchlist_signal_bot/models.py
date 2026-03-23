from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import pandas as pd


@dataclass(slots=True)
class SymbolConfig:
    symbol: str
    market: str
    name: str
    group: str
    asset_type: str = "equity"
    active: bool = True
    currency: str | None = None
    thresholds: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FetchOutcome:
    symbol: str
    frame: pd.DataFrame
    source: str
    quality: str
    fetched_at: datetime | None
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PriceZone:
    lower: float
    upper: float
    center: float
    touches: int
    last_date: date | None = None


@dataclass(slots=True)
class AnalysisResult:
    config: SymbolConfig
    as_of: date
    source: str
    data_quality: str
    fetched_at: datetime | None
    indicators: dict[str, Any]
    short_trend_label: str
    medium_trend_label: str
    mid_long_trend_label: str
    long_trend_label: str
    trend_label: str
    trend_score: int
    trend_summary: str
    price: float
    support_zones: list[PriceZone] = field(default_factory=list)
    resistance_zones: list[PriceZone] = field(default_factory=list)
    support_summary: str = ""
    resistance_summary: str = ""
    sparkline: list[float] = field(default_factory=list)
