from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class AppSettings:
    root_dir: Path
    watchlist_path: Path
    thresholds_path: Path
    benchmarks_path: Path
    prices_dir: Path
    cache_dir: Path
    metadata_dir: Path
    artifacts_dir: Path
    html_path: Path
    telegram_path: Path
    report_json_path: Path
    daily_csv_path: Path
    history_csv_path: Path
    lookback_days: int = 420
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    @classmethod
    def build(
        cls,
        *,
        root_dir: Path,
        watchlist_path: Path | None = None,
        thresholds_path: Path | None = None,
        benchmarks_path: Path | None = None,
        prices_dir: Path | None = None,
        artifacts_dir: Path | None = None,
    ) -> AppSettings:
        watchlist = watchlist_path or root_dir / "config" / "watchlist.yml"
        thresholds = thresholds_path or root_dir / "config" / "thresholds.yml"
        benchmarks = benchmarks_path or root_dir / "config" / "benchmarks.yml"
        prices = prices_dir or root_dir / "data" / "prices"
        artifacts = artifacts_dir or root_dir / "artifacts"
        cache_dir = root_dir / "data" / "cache"
        metadata_dir = root_dir / "data" / "metadata"
        threshold_config = load_yaml_file(thresholds)
        lookback_days = int(threshold_config.get("lookback_days", 420))
        return cls(
            root_dir=root_dir,
            watchlist_path=watchlist,
            thresholds_path=thresholds,
            benchmarks_path=benchmarks,
            prices_dir=prices,
            cache_dir=cache_dir,
            metadata_dir=metadata_dir,
            artifacts_dir=artifacts,
            html_path=artifacts / "report.html",
            telegram_path=artifacts / "telegram.txt",
            report_json_path=artifacts / "report.json",
            daily_csv_path=artifacts / "signals_daily.csv",
            history_csv_path=artifacts / "signal_history.csv",
            lookback_days=lookback_days,
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
        )

    def ensure_directories(self) -> None:
        for path in (
            self.prices_dir,
            self.cache_dir,
            self.metadata_dir,
            self.artifacts_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def load_yaml_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return data
