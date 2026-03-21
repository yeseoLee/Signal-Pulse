from __future__ import annotations

from pathlib import Path

import pandas as pd


def _safe_symbol(symbol: str) -> str:
    return symbol.replace("/", "_").replace("^", "_").replace("=", "_")


class ParquetStore:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, symbol: str) -> Path:
        return self.root_dir / f"{_safe_symbol(symbol)}.parquet"

    def load(self, symbol: str) -> pd.DataFrame | None:
        path = self.path_for(symbol)
        if not path.exists():
            return None
        frame = pd.read_parquet(path)
        frame.index = pd.to_datetime(frame.index)
        return frame.sort_index()

    def write(self, symbol: str, frame: pd.DataFrame) -> Path:
        clean = frame.copy()
        clean = clean[~clean.index.duplicated(keep="last")].sort_index()
        path = self.path_for(symbol)
        clean.to_parquet(path)
        return path
