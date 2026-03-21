from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import pandas as pd


@dataclass(slots=True)
class BenchmarkConfig:
    label: str
    symbol: str
    market: str
    name: str
    asset_type: str = "index"


@dataclass(slots=True)
class SymbolConfig:
    symbol: str
    market: str
    name: str
    group: str
    asset_type: str = "equity"
    benchmark: str | None = None
    benchmark_label: str | None = None
    benchmark_name: str | None = None
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
class Event:
    code: str
    polarity: str
    title: str
    weight: int
    detail: str


@dataclass(slots=True)
class AnalysisResult:
    config: SymbolConfig
    as_of: date
    source: str
    data_quality: str
    fetched_at: datetime | None
    indicators: dict[str, Any]
    indicator_scores: dict[str, int]
    events: list[Event]
    display_events: list[Event]
    score: int
    confidence: str
    state: str
    price: float
    sparkline: list[float] = field(default_factory=list)
    benchmark_available: bool = False
