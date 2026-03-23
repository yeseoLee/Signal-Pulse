# Watchlist Signal Bot

## Language

- [한국어](./README.md)
- English

This bot generates Telegram and HTML reports from a watchlist using **5-day / 20-day / 60-day / 120-day moving-average trend detection**, **pivot-based support and resistance zones**, and **20-day / 60-day / 120-day returns**.

## Overview

- Trend is split into `short-term`, `short-to-mid-term`, `mid-to-long-term`, and `long-term` states using `MA5`, `MA20`, `MA60`, and `MA120`.
- The report uses the `mid-to-long-term (20/60)` trend as the primary section label.
- Support and resistance are derived from pivot highs and lows, then merged into simple price zones.
- The report always includes `20-day`, `60-day`, and `120-day` returns.
- Outputs are written as `CSV`, `JSON`, `HTML`, and `Telegram text`.
- Price data is fetched with `FinanceDataReader`, with cached fallback when live fetches fail.

## Fork Setup

If you want to run this from your own fork, set up these items first.

1. Update [`config/watchlist.yml`](./config/watchlist.yml) with your own symbols.
2. Update [`config/thresholds.yml`](./config/thresholds.yml) for pivot window, merge tolerance, and zone width.
3. Update [`config/github_actions.yml`](./config/github_actions.yml) for your schedule and workflow defaults.
4. Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` under `Settings > Secrets and variables > Actions`.
5. In `Settings > Pages`, set GitHub Pages to use the `gh-pages` branch and `/ (root)`.
6. If needed, set `GITHUB_PAGES_URL` to pin the report link shown in Telegram.

## Quick Start

```bash
uv sync --group dev
uv run python -m watchlist_signal_bot.main --dry-run
```

You can also run a narrower scenario.

```bash
uv run python -m watchlist_signal_bot.main --dry-run --market US
uv run python -m watchlist_signal_bot.main --dry-run --symbol AAPL
```

## Config

All configuration files live under [`config/`](./config/).

### `config/watchlist.yml`

Defines the watchlist universe and per-symbol metadata.

- `groups`: symbol groups
- `metadata`: market, display name, and asset type per symbol
- For 6-digit KR tickers, keep them quoted as strings.

### `config/thresholds.yml`

Defines the core technical-report parameters.

- `moving_average.fast`: default 5-day average
- `moving_average.short`: default 20-day average
- `moving_average.medium`: default 60-day average
- `moving_average.long`: default 120-day average
- `returns.windows`: default return windows
- `levels.lookback_days`: trailing candles used for support/resistance detection
- `levels.pivot_window`: pivot high/low window
- `levels.merge_tolerance`: price-level merge tolerance
- `levels.zone_width_ratio`: width of each support/resistance zone
- `levels.max_supports`, `levels.max_resistances`: number of zones to show

### `config/github_actions.yml`

Defines the user-facing GitHub Actions settings.

- `daily.schedule`: recurring cron entries
- `daily.options`: defaults for scheduled runs
- `manual.options`: defaults for manual runs

After changing this config, regenerate the workflow files.

```bash
make render-workflows
make check-workflows
```

## Report Structure

### 1. Trend

- Short-term: `close > MA5` => `uptrend`, `close < MA5` => `downtrend`, otherwise `sideways`
- Short-to-mid-term: `close > MA5 > MA20` => `uptrend`, `close < MA5 < MA20` => `downtrend`, otherwise `sideways`
- Mid-to-long-term: `close > MA20 > MA60` => `uptrend`, `close < MA20 < MA60` => `downtrend`, otherwise `sideways`
- Long-term: `close > MA60 > MA120` => `uptrend`, `close < MA60 < MA120` => `downtrend`, otherwise `sideways`
- The primary report label and trend-change tracking use the mid-to-long-term trend.

### 2. Returns

Each report includes:

- `20-day return`
- `60-day return`
- `120-day return`

### 3. Support / Resistance

- Detect `pivot highs` and `pivot lows`
- Merge nearby prices into zones
- Levels below price become support
- Levels above price become resistance
- Show the nearest two zones on each side

### 4. Generated Text

Each symbol gets:

- one trend sentence
- one support sentence
- one resistance sentence

## Output Format

### Telegram

- Split into `uptrend`, `sideways`, and `downtrend` sections
- Show only the current price, trend summary, and 20/60/120-day returns per symbol
- Append the GitHub Pages report link at the bottom

### HTML

- Trend distribution summary
- Recent trend changes
- Per-symbol cards with short/short-mid/mid-long/long trend badges
- Support/resistance zones
- Failed symbols section

## Environment Variables

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `GITHUB_PAGES_URL`

If Telegram credentials are missing, the app only writes local artifacts.

## Main Outputs

- `artifacts/signals_daily.csv`
- `artifacts/signal_history.csv`
- `artifacts/report.json`
- `artifacts/report.html`
- `artifacts/telegram.txt`

## Developer Docs

- Signal and function map: [`docs/signals.md`](./docs/signals.md)

## Development Commands

```bash
make sync
make lint
make test
make dry-run
make render-workflows
make check-workflows
```
