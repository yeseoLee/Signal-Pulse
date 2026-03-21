# My Watchlist Signal Bot

Rule-based watchlist signal bot for KR and US equities and ETFs.

## Quick Start

```bash
uv sync --group dev
uv run python -m my_watchlist_signal_bot.main --dry-run
```

## Environment Variables

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Main Outputs

- `artifacts/signals_daily.csv`
- `artifacts/signal_history.csv`
- `artifacts/report.json`
- `artifacts/report.html`
- `artifacts/telegram.txt`
