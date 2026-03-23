from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class AppSettings:
    root_dir: Path
    watchlist_path: Path
    thresholds_path: Path
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
    github_pages_url: str | None = None

    @classmethod
    def build(
        cls,
        *,
        root_dir: Path,
        watchlist_path: Path | None = None,
        thresholds_path: Path | None = None,
        prices_dir: Path | None = None,
        artifacts_dir: Path | None = None,
    ) -> AppSettings:
        watchlist = watchlist_path or root_dir / "config" / "watchlist.yml"
        thresholds = thresholds_path or root_dir / "config" / "thresholds.yml"
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
            github_pages_url=_resolve_github_pages_url(root_dir),
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


def _resolve_github_pages_url(root_dir: Path) -> str | None:
    env_url = os.getenv("GITHUB_PAGES_URL")
    if env_url:
        return env_url.rstrip("/") + "/"

    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=root_dir,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:  # noqa: BLE001
        return None

    remote = result.stdout.strip()
    if remote.startswith("git@github.com:"):
        remote = remote.replace("git@github.com:", "https://github.com/")
    if not remote.startswith("https://github.com/"):
        return None

    path = remote.removeprefix("https://github.com/").removesuffix(".git").strip("/")
    if "/" not in path:
        return None
    owner, repo = path.split("/", 1)
    return f"https://{owner.lower()}.github.io/{repo}/"
