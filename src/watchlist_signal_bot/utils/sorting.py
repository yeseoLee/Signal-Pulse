from __future__ import annotations


def asset_priority(asset_type: str | None) -> int:
    normalized = str(asset_type or "").strip().lower()
    if normalized == "index":
        return 0
    if normalized == "equity":
        return 1
    return 2
