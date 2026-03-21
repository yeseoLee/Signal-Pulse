from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from watchlist_signal_bot.models import AnalysisResult


class HistoryStore:
    def __init__(self, *, daily_csv: Path, history_csv: Path, report_json: Path):
        self.daily_csv = daily_csv
        self.history_csv = history_csv
        self.report_json = report_json

    def write_daily_signals(self, results: list[AnalysisResult]) -> pd.DataFrame:
        daily_frame = pd.DataFrame([self._result_row(result) for result in results]).sort_values(
            by=["score", "symbol"], ascending=[False, True]
        )
        daily_frame.to_csv(self.daily_csv, index=False)
        return daily_frame

    def append_history(self, daily_frame: pd.DataFrame) -> pd.DataFrame:
        if self.history_csv.exists():
            history = pd.read_csv(self.history_csv)
            combined = pd.concat([history, daily_frame], ignore_index=True)
        else:
            combined = daily_frame.copy()

        combined = combined.drop_duplicates(subset=["as_of", "symbol"], keep="last")
        combined = combined.sort_values(by=["as_of", "symbol"]).reset_index(drop=True)

        combined["previous_events"] = combined.groupby("symbol")["event_codes"].shift(1).fillna("")
        combined["new_events"] = combined.apply(_find_new_events, axis=1)
        combined.to_csv(self.history_csv, index=False)
        return combined

    def write_report_json(self, payload: dict[str, Any]) -> None:
        with self.report_json.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    @staticmethod
    def _result_row(result: AnalysisResult) -> dict[str, Any]:
        events = [event.code for event in result.display_events]
        return {
            "as_of": result.as_of.isoformat(),
            "symbol": result.config.symbol,
            "name": result.config.name,
            "market": result.config.market,
            "group": result.config.group,
            "benchmark": result.config.benchmark_label or result.config.benchmark,
            "price": round(result.price, 4),
            "score": result.score,
            "confidence": result.confidence,
            "state": result.state,
            "source": result.source,
            "data_quality": result.data_quality,
            "event_codes": ";".join(events),
            "fetched_at": result.fetched_at.isoformat() if result.fetched_at else "",
        }


def _find_new_events(row: pd.Series) -> str:
    current = {item for item in str(row["event_codes"]).split(";") if item}
    previous = {item for item in str(row["previous_events"]).split(";") if item}
    return ";".join(sorted(current - previous))
