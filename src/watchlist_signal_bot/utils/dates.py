from __future__ import annotations

from datetime import UTC, date, datetime, timedelta


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def resolve_end_date(raw_end: str | None = None) -> date:
    if raw_end:
        return date.fromisoformat(raw_end)
    return utc_now().date()


def build_window(*, lookback_days: int, end_date: date) -> tuple[date, date]:
    return end_date - timedelta(days=lookback_days * 2), end_date
