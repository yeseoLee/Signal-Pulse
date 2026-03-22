from __future__ import annotations

import argparse
import json
from pathlib import Path

from watchlist_signal_bot.pipeline import analyze_symbol, fetch_with_fallback
from watchlist_signal_bot.reports.html import render_html_report
from watchlist_signal_bot.reports.telegram import render_telegram_summary, send_telegram_message
from watchlist_signal_bot.settings import AppSettings, load_yaml_file
from watchlist_signal_bot.storage import HistoryStore, ParquetStore
from watchlist_signal_bot.universe import (
    build_benchmark_universe,
    filter_universe,
    load_benchmarks,
    load_watchlist,
    normalize_symbol,
)
from watchlist_signal_bot.utils.dates import build_window, resolve_end_date
from watchlist_signal_bot.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="시그널 봇")
    parser.add_argument("--root-dir", default=".", help="Project root directory")
    parser.add_argument("--watchlist", help="Path to watchlist.yml")
    parser.add_argument("--thresholds", help="Path to thresholds.yml")
    parser.add_argument("--benchmarks", help="Path to benchmarks.yml")
    parser.add_argument("--market", choices=["KR", "US"], help="Filter by market")
    parser.add_argument("--group", action="append", help="Filter by watchlist group")
    parser.add_argument("--symbol", action="append", help="Filter by symbol")
    parser.add_argument("--end-date", help="Override end date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Skip Telegram delivery")
    parser.add_argument("--skip-html", action="store_true", help="Skip HTML output")
    parser.add_argument("--skip-telegram", action="store_true", help="Skip Telegram delivery")
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include inactive symbols from watchlist metadata",
    )
    return parser


def main() -> int:
    configure_logging()
    args = build_parser().parse_args()
    root_dir = Path(args.root_dir).resolve()
    settings = AppSettings.build(
        root_dir=root_dir,
        watchlist_path=Path(args.watchlist).resolve() if args.watchlist else None,
        thresholds_path=Path(args.thresholds).resolve() if args.thresholds else None,
        benchmarks_path=Path(args.benchmarks).resolve() if args.benchmarks else None,
    )
    settings.ensure_directories()

    thresholds = load_yaml_file(settings.thresholds_path)
    benchmark_defaults, benchmark_catalog = load_benchmarks(settings.benchmarks_path)
    universe = load_watchlist(
        settings.watchlist_path,
        default_benchmarks=benchmark_defaults,
        benchmark_catalog=benchmark_catalog,
    )
    selected_symbols = {normalize_symbol(symbol) for symbol in args.symbol} if args.symbol else None
    selected_groups = set(args.group) if args.group else None
    filtered = filter_universe(
        universe,
        symbols=selected_symbols,
        groups=selected_groups,
        market=args.market,
        include_inactive=args.include_inactive,
    )
    if not filtered:
        raise SystemExit("No symbols selected from watchlist")

    end_date = resolve_end_date(args.end_date)
    start_date, end_date = build_window(lookback_days=settings.lookback_days, end_date=end_date)
    price_store = ParquetStore(settings.prices_dir)
    benchmark_store = ParquetStore(settings.cache_dir)
    history_store = HistoryStore(
        daily_csv=settings.daily_csv_path,
        history_csv=settings.history_csv_path,
        report_json=settings.report_json_path,
    )

    benchmark_requests = build_benchmark_universe(filtered, benchmark_catalog)
    benchmark_frames = {}
    benchmark_failures = {}
    for benchmark_symbol, benchmark_config in benchmark_requests.items():
        try:
            outcome = fetch_with_fallback(
                benchmark_config,
                start=start_date,
                end=end_date,
                store=benchmark_store,
            )
            benchmark_frames[benchmark_symbol] = outcome.frame
        except Exception as exc:  # noqa: BLE001
            benchmark_failures[benchmark_symbol] = str(exc)
            logger.warning("Benchmark fetch failed for %s: %s", benchmark_symbol, exc)

    analyses = []
    failures = {}
    for symbol_config in filtered:
        try:
            price_outcome = fetch_with_fallback(
                symbol_config,
                start=start_date,
                end=end_date,
                store=price_store,
            )
            benchmark_frame = (
                benchmark_frames.get(symbol_config.benchmark) if symbol_config.benchmark else None
            )
            analyses.append(
                analyze_symbol(
                    symbol_config,
                    price_outcome=price_outcome,
                    thresholds=thresholds,
                    benchmark_frame=benchmark_frame,
                )
            )
        except Exception as exc:  # noqa: BLE001
            failures[symbol_config.symbol] = str(exc)
            logger.exception("Symbol processing failed for %s", symbol_config.symbol)

    if not analyses:
        logger.error("No symbols completed successfully")
        return 1

    daily_frame = history_store.write_daily_signals(analyses)
    history_frame = history_store.append_history(daily_frame)

    report_payload = build_report_payload(
        analyses=analyses,
        failures=failures,
        benchmark_failures=benchmark_failures,
        history_frame=history_frame,
    )
    history_store.write_report_json(report_payload)

    telegram_text = render_telegram_summary(
        analyses,
        failures=failures,
        benchmark_failures=benchmark_failures,
        github_pages_url=settings.github_pages_url,
    )
    settings.telegram_path.write_text(telegram_text, encoding="utf-8")

    if not args.skip_html:
        html = render_html_report(
            analyses,
            failures=failures,
            benchmark_failures=benchmark_failures,
            history_frame=history_frame,
        )
        settings.html_path.write_text(html, encoding="utf-8")

    if not args.dry_run and not args.skip_telegram:
        send_telegram_message(
            telegram_text,
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
        )

    logger.info("Completed %s symbols with %s failures", len(analyses), len(failures))
    return 0


def build_report_payload(*, analyses, failures, benchmark_failures, history_frame):
    return {
        "summary": {
            "success_count": len(analyses),
            "failure_count": len(failures),
            "benchmark_failure_count": len(benchmark_failures),
        },
        "failures": failures,
        "benchmark_failures": benchmark_failures,
        "signals": [
            {
                "symbol": item.config.symbol,
                "name": item.config.name,
                "market": item.config.market,
                "group": item.config.group,
                "state": item.state,
                "score": item.score,
                "indicator_scores": item.indicator_scores,
                "confidence": item.confidence,
                "source": item.source,
                "data_quality": item.data_quality,
                "events": [event.code for event in item.display_events],
                "indicators": item.indicators,
            }
            for item in sorted(analyses, key=lambda result: result.score, reverse=True)
        ],
        "history_tail": json.loads(history_frame.tail(50).to_json(orient="records")),
    }


if __name__ == "__main__":
    raise SystemExit(main())
