# My Watchlist Signal Bot

## Language

- [한국어](./README.md)
- English

A rule-based signal bot that collects OHLCV data for KR/US stocks and ETFs, calculates explainable technical signals, and publishes Telegram and HTML reports.

## Overview

- Collects daily OHLCV data for a user-managed watchlist.
- Computes explainable signals based on moving averages, breakouts, RSI, volume, and relative strength.
- Writes outputs as `CSV`, `JSON`, `HTML`, and `Telegram text`.
- Uses `FinanceDataReader` as the unified price source and falls back to cached prices when live fetches fail.

## Fork Setup

If you want to run this from your own fork, set up these items first.

1. Update [`config/watchlist.yml`](./config/watchlist.yml) with your own symbols.
2. Update [`config/github_actions.yml`](./config/github_actions.yml) for your schedule and workflow defaults.
3. Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` under `Settings > Secrets and variables > Actions`.
4. In `Settings > Pages`, set GitHub Pages to use the `gh-pages` branch and `/ (root)`.
5. If needed, set `GITHUB_PAGES_URL` to pin the report link shown in Telegram.

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
- `metadata`: market, display name, benchmark, and asset type per symbol
- For 6-digit KR tickers, keep them quoted as strings.
  Example: `"005930"`, `"069500"`

Current default universe:

- US M6: `AAPL`, `MSFT`, `NVDA`, `AMZN`, `META`, `GOOGL`
- KR large caps: `"005930"` Samsung Electronics, `"000660"` SK hynix, `"005380"` Hyundai Motor

Example:

```yaml
groups:
  core_kr:
    - "005930"
    - "000660"
    - "005380"
  core_us:
    - AAPL
    - MSFT
    - NVDA
    - AMZN
    - META
    - GOOGL
```

### `config/thresholds.yml`

Defines signal calculation parameters.

- lookback window: `lookback_days`
- moving averages: `moving_average`
- breakout windows: `breakout`
- volume spike threshold: `volume.spike_ratio`
- RSI period and bounds: `rsi`
- scoring weights: `score_weights`

The default market-data source is `FinanceDataReader`.

### `config/benchmarks.yml`

Defines default benchmarks and benchmark symbol mappings.

- `default`: default benchmark label per market
- `symbols`: lookup symbol, market, and name for each benchmark label

Included examples:

- `KOSPI -> KS11`
- `KOSDAQ -> KQ11`
- `SPY -> SPY`
- `QQQ -> QQQ`
- `SOXX -> SOXX`

### `config/github_actions.yml`

Defines GitHub Actions settings.

- `daily.schedule`: cron schedules for recurring runs
- `daily.options`: default options for the daily workflow
- `manual.options`: default options for the manual workflow

Important:

- GitHub Actions cannot load `schedule` dynamically from a config file at runtime.
- Because of that, this project uses [`config/github_actions.yml`](./config/github_actions.yml) as the source of truth and keeps [`.github/workflows/`](./.github/workflows/) YAML files as generated outputs.
- This file is intentionally limited to user-facing customization values such as cron entries and workflow option defaults.
- Developer-facing values such as runner type, permissions, artifact paths, and Python/uv versions are kept inside the generator as internal defaults.
- The workflow builds a `public/` bundle and pushes it to the dedicated `gh-pages` branch for GitHub Pages hosting.
- After changing the config, regenerate the workflow files.

```bash
make render-workflows
make check-workflows
```

## Signal Components

The Telegram summary no longer relies on one combined score line. Instead, it renders each category below as natural-language explanations per symbol.

### Moving Average

- `close > SMA20`, `close > SMA60`, `close > SMA120`
- alignment check for `SMA20 > SMA60 > SMA120`
- `GOLDEN_CROSS`, `DEAD_CROSS`
- long-term average breakdown check

This category measures whether the trend structure is healthy and aligned.

### Breakout / Breakdown

- `BREAKOUT_20D`
- `BREAKOUT_60D`
- `120-day high breakout`
- `WATCH_NEAR_BREAKOUT`
- `BREAKDOWN_20D`

This category measures whether price is pushing through recent ranges or losing support.

### RSI

- Uses `RSI(14)`.
- The `45~70` zone is treated as constructive.
- Overheated conditions are penalized through `RSI_OVERHEATED`.

This category measures balance between strength and overheating.

### Volume

- `volume / 20-day average volume`
- accumulation on up days
- `VOLUME_CONFIRMED_BREAKOUT`
- `HIGH_VOLUME_SELLING`

This category checks whether price action is confirmed by volume or pressured by selling.

### Relative Strength

- `relative_return_20d`
- `relative_return_60d`
- `RS_GT_BENCHMARK`
- `RS_WEAKENING`

This category measures whether the symbol is outperforming or weakening versus its benchmark.

### Momentum

- `20-day`, `60-day`, and `120-day` returns
- `MOMENTUM_ACCELERATING`

This category measures whether upside speed and mid-term momentum are still improving.

### How To Read Telegram Output

- The output is split into `[강세]`, `[중립]`, and `[약세]` sections.
- Each symbol is described with separate natural-language lines for moving averages, breakouts, RSI, volume, relative strength, and momentum.
- Example: `Price is below the 120-day moving average.`, `A dead cross occurred.`, `RSI is 41.2.`
- Fetch-status labels such as `fresh`, `fallback`, and `stale` are not shown in Telegram.
- The default watchlist contains 9 symbols: US M6 plus 3 KR large caps.

## Environment Variables

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

If they are not set, Telegram delivery is skipped and only local artifacts are generated.

## Main Outputs

- `artifacts/signals_daily.csv`
- `artifacts/signal_history.csv`
- `artifacts/report.json`
- `artifacts/report.html`
- `artifacts/telegram.txt`

## Development Commands

```bash
make sync
make lint
make test
make dry-run
make render-workflows
make check-workflows
```
