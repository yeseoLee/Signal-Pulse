from __future__ import annotations

from collections.abc import Iterable

from watchlist_signal_bot.models import BenchmarkConfig, SymbolConfig
from watchlist_signal_bot.settings import load_yaml_file


def normalize_symbol(raw_symbol: str) -> str:
    symbol = str(raw_symbol).strip()
    if symbol.isdigit() and len(symbol) <= 6:
        return symbol.zfill(6)
    return symbol.upper()


def infer_market(symbol: str) -> str:
    return "KR" if symbol.isdigit() and len(symbol) == 6 else "US"


def load_benchmarks(
    path,
) -> tuple[dict[str, str], dict[str, BenchmarkConfig]]:
    raw = load_yaml_file(path)
    defaults = {str(market).upper(): str(label) for market, label in raw.get("default", {}).items()}
    catalog: dict[str, BenchmarkConfig] = {}
    for label, payload in raw.get("symbols", {}).items():
        catalog[str(label)] = BenchmarkConfig(
            label=str(label),
            symbol=normalize_symbol(payload["symbol"]),
            market=str(payload.get("market", infer_market(str(payload["symbol"])))).upper(),
            name=str(payload.get("name", label)),
            asset_type=str(payload.get("asset_type", "index")),
        )
    return defaults, catalog


def load_watchlist(path, *, default_benchmarks, benchmark_catalog) -> list[SymbolConfig]:
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
            benchmark_label = (
                str(
                    payload.get("benchmark")
                    or meta.get("benchmark")
                    or default_benchmarks.get(market, "")
                ).strip()
                or None
            )
            benchmark_cfg = benchmark_catalog.get(benchmark_label) if benchmark_label else None
            universe.append(
                SymbolConfig(
                    symbol=symbol,
                    market=market,
                    name=str(payload.get("name") or meta.get("name") or symbol),
                    group=str(group_name),
                    asset_type=str(payload.get("asset_type") or meta.get("asset_type") or "equity"),
                    benchmark=benchmark_cfg.symbol if benchmark_cfg else benchmark_label,
                    benchmark_label=benchmark_label,
                    benchmark_name=benchmark_cfg.name if benchmark_cfg else benchmark_label,
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


def build_benchmark_universe(
    universe: Iterable[SymbolConfig],
    benchmark_catalog: dict[str, BenchmarkConfig],
) -> dict[str, SymbolConfig]:
    configs: dict[str, SymbolConfig] = {}
    for symbol in universe:
        if not symbol.benchmark:
            continue
        if symbol.benchmark_label and symbol.benchmark_label in benchmark_catalog:
            benchmark = benchmark_catalog[symbol.benchmark_label]
            configs[benchmark.symbol] = SymbolConfig(
                symbol=benchmark.symbol,
                market=benchmark.market,
                name=benchmark.name,
                group="benchmarks",
                asset_type=benchmark.asset_type,
                benchmark=benchmark.symbol,
                benchmark_label=benchmark.label,
                benchmark_name=benchmark.name,
            )
            continue
        configs[symbol.benchmark] = SymbolConfig(
            symbol=normalize_symbol(symbol.benchmark),
            market=symbol.market,
            name=symbol.benchmark_name or symbol.benchmark,
            group="benchmarks",
            asset_type="index",
            benchmark=symbol.benchmark,
            benchmark_label=symbol.benchmark_label or symbol.benchmark,
            benchmark_name=symbol.benchmark_name or symbol.benchmark,
        )
    return configs
