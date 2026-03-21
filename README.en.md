# My Watchlist Signal Bot

## Language

- [한국어](./README.md)
- English

A rule-based signal bot that collects OHLCV data for KR/US stocks and ETFs, calculates explainable technical signals, and publishes Telegram and HTML reports.

## Overview

- Collects daily OHLCV data for a user-managed watchlist.
- Computes explainable signals based on moving averages, breakouts, RSI, volume, and relative strength.
- Writes outputs as `CSV`, `JSON`, `HTML`, and `Telegram text`.
- Prefers fallback data sources and cached prices when live fetches fail.

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

- US mega caps: `AAPL`, `MSFT`, `NVDA`, `AMZN`, `META`, `GOOGL`, `TSLA`
- US ETFs: `QQQ`, `SPY`
- KR large caps: `"005930"` Samsung Electronics, `"000660"` SK hynix, `"005380"` Hyundai Motor
- KR ETFs: `"069500"` KODEX 200, `"229200"` KODEX KOSDAQ150

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
    - TSLA
  etf_us:
    - QQQ
    - SPY
  etf_kr:
    - "069500"
    - "229200"
```

### `config/thresholds.yml`

Defines signal calculation parameters.

- lookback window: `lookback_days`
- moving averages: `moving_average`
- breakout windows: `breakout`
- volume spike threshold: `volume.spike_ratio`
- RSI period and bounds: `rsi`
- scoring weights: `score_weights`

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

- `shared`: Python/uv versions, runner, permissions, and shared environment variables
- `workflows.daily.schedule`: cron schedules for recurring runs
- `workflows.*.dispatch_inputs`: manual workflow input definitions
- `workflows.*.runtime_artifact`: uploaded artifact names and paths
- `workflows.*.pages`: GitHub Pages bundle files and deploy conditions

Important:

- GitHub Actions cannot load `schedule` dynamically from a config file at runtime.
- Because of that, this project uses [`config/github_actions.yml`](./config/github_actions.yml) as the source of truth and keeps [`.github/workflows/`](./.github/workflows/) YAML files as generated outputs.
- After changing the config, regenerate the workflow files.

```bash
make render-workflows
make check-workflows
```

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
