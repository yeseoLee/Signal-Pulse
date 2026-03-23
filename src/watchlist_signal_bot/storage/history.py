from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from watchlist_signal_bot.models import AnalysisResult, PriceZone
from watchlist_signal_bot.signals import format_zone, normalize_output_price
from watchlist_signal_bot.utils.sorting import asset_priority


class HistoryStore:
    def __init__(self, *, daily_csv: Path, history_csv: Path, report_json: Path):
        self.daily_csv = daily_csv
        self.history_csv = history_csv
        self.report_json = report_json

    def write_daily_signals(self, results: list[AnalysisResult]) -> pd.DataFrame:
        daily_frame = pd.DataFrame([self._result_row(result) for result in results]).sort_values(
            by=["asset_priority", "trend_score", "symbol"],
            ascending=[True, False, True],
        )
        daily_frame.to_csv(self.daily_csv, index=False)
        return daily_frame

    def append_history(self, daily_frame: pd.DataFrame) -> pd.DataFrame:
        if self.history_csv.exists():
            history = pd.read_csv(self.history_csv)
            combined = pd.concat([history, daily_frame], ignore_index=True)
        else:
            combined = daily_frame.copy()

        if "asset_type" not in combined.columns:
            combined["asset_type"] = "equity"
        combined["asset_type"] = combined["asset_type"].fillna("equity")

        if "asset_priority" not in combined.columns:
            combined["asset_priority"] = combined["asset_type"].map(asset_priority)
        combined["asset_priority"] = (
            combined["asset_priority"]
            .fillna(combined["asset_type"].map(asset_priority))
            .astype(int)
        )

        combined = combined.drop_duplicates(subset=["as_of", "symbol"], keep="last")
        combined = combined.sort_values(
            by=["as_of", "asset_priority", "symbol"]
        ).reset_index(drop=True)
        combined["previous_trend_label"] = (
            combined.groupby("symbol")["trend_label"].shift(1).fillna("")
        )
        combined["trend_change"] = combined.apply(_find_trend_change, axis=1)
        combined.to_csv(self.history_csv, index=False)
        return combined

    def write_report_json(self, payload: dict[str, Any]) -> None:
        with self.report_json.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    @staticmethod
    def _result_row(result: AnalysisResult) -> dict[str, Any]:
        return {
            "as_of": result.as_of.isoformat(),
            "symbol": result.config.symbol,
            "name": result.config.name,
            "market": result.config.market,
            "group": result.config.group,
            "asset_type": result.config.asset_type,
            "asset_priority": asset_priority(result.config.asset_type),
            "price": normalize_output_price(result.price, market=result.config.market),
            "short_trend_label": result.short_trend_label,
            "medium_trend_label": result.medium_trend_label,
            "long_trend_label": result.long_trend_label,
            "trend_label": result.trend_label,
            "trend_score": result.trend_score,
            "return_20d": result.indicators.get("return_20d"),
            "return_60d": result.indicators.get("return_60d"),
            "return_120d": result.indicators.get("return_120d"),
            "supports": ";".join(
                _zone_label(
                    result.support_zones,
                    market=result.config.market,
                    asset_type=result.config.asset_type,
                )
            ),
            "resistances": ";".join(
                _zone_label(
                    result.resistance_zones,
                    market=result.config.market,
                    asset_type=result.config.asset_type,
                )
            ),
            "trend_summary": result.trend_summary,
            "support_summary": result.support_summary,
            "resistance_summary": result.resistance_summary,
            "source": result.source,
            "data_quality": result.data_quality,
            "fetched_at": result.fetched_at.isoformat() if result.fetched_at else "",
        }


def _find_trend_change(row: pd.Series) -> str:
    previous = str(row.get("previous_trend_label", "")).strip()
    current = str(row.get("trend_label", "")).strip()
    if not previous or previous == current:
        return ""
    return f"{previous} -> {current}"


def _zone_label(zones: list[PriceZone], *, market: str, asset_type: str) -> list[str]:
    return [format_zone(zone, market=market, asset_type=asset_type) for zone in zones]
