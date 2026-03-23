from __future__ import annotations

from collections.abc import Iterable

from watchlist_signal_bot.models import SymbolConfig
from watchlist_signal_bot.settings import load_yaml_file


def normalize_symbol(raw_symbol: str) -> str:
    symbol = str(raw_symbol).strip()
    if symbol.isdigit() and len(symbol) <= 6:
        return symbol.zfill(6)
    return symbol.upper()


def infer_market(symbol: str) -> str:
    return "KR" if symbol.isdigit() and len(symbol) == 6 else "US"


def load_watchlist(path) -> list[SymbolConfig]:
    raw = load_yaml_file(path)
    metadata = raw.get("metadata", {})
    universe: list[SymbolConfig] = []
    for group_name, symbols in raw.get("groups", {}).items():
        for item in symbols:
            payload = {"symbol": item} if not isinstance(item, dict) else item.copy()
            symbol = normalize_symbol(str(payload["symbol"]))
            meta = dict(metadata.get(symbol, {}))
            market = str(
                payload.get("market") or meta.get("market") or infer_market(symbol)
            ).upper()
            universe.append(
                SymbolConfig(
                    symbol=symbol,
                    market=market,
                    name=str(payload.get("name") or meta.get("name") or symbol),
                    group=str(group_name),
                    asset_type=str(payload.get("asset_type") or meta.get("asset_type") or "equity"),
                    active=bool(meta.get("active", True)) and not bool(meta.get("dormant", False)),
                    currency=meta.get("currency"),
                    thresholds=dict(meta.get("thresholds", {})),
                )
            )
    return universe


def filter_universe(
    universe: Iterable[SymbolConfig],
    *,
    symbols: set[str] | None = None,
    groups: set[str] | None = None,
    market: str | None = None,
    include_inactive: bool = False,
) -> list[SymbolConfig]:
    filtered: list[SymbolConfig] = []
    for config in universe:
        if not include_inactive and not config.active:
            continue
        if symbols and config.symbol not in symbols:
            continue
        if groups and config.group not in groups:
            continue
        if market and config.market != market:
            continue
        filtered.append(config)
    return filtered
