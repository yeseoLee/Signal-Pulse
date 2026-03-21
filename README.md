# My Watchlist Signal Bot

한국어: 한국/미국 주식과 ETF를 대상으로 OHLCV를 수집하고, 설명 가능한 규칙 기반 시그널을 생성해 Telegram과 HTML 리포트로 출력하는 봇입니다.

English: A rule-based signal bot that collects OHLCV data for KR/US stocks and ETFs, calculates explainable technical signals, and publishes Telegram and HTML reports.

## 한국어

### 개요

- 관심종목 목록 기준으로 일봉 데이터를 수집합니다.
- 이동평균, 돌파, RSI, 거래량, 상대강도 기반 신호를 계산합니다.
- 결과를 `CSV`, `JSON`, `HTML`, `Telegram text` 형태로 저장합니다.
- 라이브 데이터 수집 실패 시 소스 폴백과 캐시 재사용을 우선합니다.

### 빠른 시작

```bash
uv sync --group dev
uv run python -m watchlist_signal_bot.main --dry-run
```

특정 시장 또는 종목만 테스트할 수도 있습니다.

```bash
uv run python -m watchlist_signal_bot.main --dry-run --market US
uv run python -m watchlist_signal_bot.main --dry-run --symbol AAPL
```

### Config

설정 파일은 모두 [`config/`](/home/lys74/DEV/Signal-Pulse/config) 아래에 있습니다.

#### `config/watchlist.yml`

관심종목 유니버스와 종목 메타데이터를 정의합니다.

- `groups`: 종목 그룹 목록
- `metadata`: 종목별 시장, 이름, 벤치마크, 자산 유형
- KR 6자리 숫자 티커는 반드시 문자열로 감싸는 것을 권장합니다.
  예: `"005930"`, `"069500"`

현재 기본 구성은 다음과 같습니다.

- US 대형주: `AAPL`, `MSFT`, `NVDA`, `AMZN`, `META`, `GOOGL`, `TSLA`
- US ETF: `QQQ`, `SPY`
- KR 대형주: `"005930"` 삼성전자, `"000660"` SK하이닉스, `"005380"` 현대차
- KR ETF: `"069500"` KODEX 200, `"229200"` KODEX 코스닥150

예시:

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

#### `config/thresholds.yml`

시그널 계산 파라미터를 정의합니다.

- 조회 기간: `lookback_days`
- 이동평균: `moving_average`
- 돌파 윈도우: `breakout`
- 거래량 급증 임계값: `volume.spike_ratio`
- RSI 기간/과열/과매도: `rsi`
- 점수 가중치: `score_weights`

#### `config/benchmarks.yml`

시장 기본 벤치마크와 벤치마크 심볼 매핑을 정의합니다.

- `default`: 시장별 기본 벤치마크
- `symbols`: 벤치마크 라벨과 실제 조회 심볼

현재 예시는 아래를 포함합니다.

- `KOSPI -> KS11`
- `KOSDAQ -> KQ11`
- `SPY -> SPY`
- `QQQ -> QQQ`
- `SOXX -> SOXX`

#### `config/github_actions.yml`

GitHub Actions 관련 설정을 관리합니다.

- `shared`: Python/uv 버전, runner, permissions, 공통 환경 변수
- `workflows.daily.schedule`: 정기 실행 cron
- `workflows.*.dispatch_inputs`: 수동 실행 입력값 정의
- `workflows.*.runtime_artifact`: 업로드할 artifact 이름과 경로
- `workflows.*.pages`: GitHub Pages 번들 파일과 배포 조건

중요:

- GitHub Actions의 `schedule`은 런타임에 설정 파일을 읽을 수 없습니다.
- 그래서 이 프로젝트는 `config/github_actions.yml`을 소스로 사용하고, `.github/workflows/*.yml`은 생성물로 관리합니다.
- 설정 변경 후 아래 명령으로 워크플로를 다시 생성해야 합니다.

```bash
make render-workflows
make check-workflows
```

### 환경 변수

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

둘 다 없으면 Telegram 전송은 건너뛰고 파일만 생성합니다.

### 주요 산출물

- `artifacts/signals_daily.csv`
- `artifacts/signal_history.csv`
- `artifacts/report.json`
- `artifacts/report.html`
- `artifacts/telegram.txt`

### 개발 명령

```bash
make sync
make lint
make test
make dry-run
make render-workflows
make check-workflows
```

## English

### Overview

- Collects daily OHLCV data for a user-managed watchlist.
- Computes explainable signals based on moving averages, breakouts, RSI, volume, and relative strength.
- Writes outputs as `CSV`, `JSON`, `HTML`, and `Telegram text`.
- Prefers fallback data sources and cached prices when live fetches fail.

### Quick Start

```bash
uv sync --group dev
uv run python -m watchlist_signal_bot.main --dry-run
```

You can also run a narrower scenario.

```bash
uv run python -m watchlist_signal_bot.main --dry-run --market US
uv run python -m watchlist_signal_bot.main --dry-run --symbol AAPL
```

### Config

All configuration files live under [`config/`](/home/lys74/DEV/Signal-Pulse/config).

#### `config/watchlist.yml`

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

#### `config/thresholds.yml`

Defines signal calculation parameters.

- lookback window: `lookback_days`
- moving averages: `moving_average`
- breakout windows: `breakout`
- volume spike threshold: `volume.spike_ratio`
- RSI period and bounds: `rsi`
- scoring weights: `score_weights`

#### `config/benchmarks.yml`

Defines default benchmarks and benchmark symbol mappings.

- `default`: default benchmark label per market
- `symbols`: lookup symbol, market, and name for each benchmark label

Included examples:

- `KOSPI -> KS11`
- `KOSDAQ -> KQ11`
- `SPY -> SPY`
- `QQQ -> QQQ`
- `SOXX -> SOXX`

#### `config/github_actions.yml`

Defines GitHub Actions settings.

- `shared`: Python/uv versions, runner, permissions, and shared environment variables
- `workflows.daily.schedule`: cron schedules for recurring runs
- `workflows.*.dispatch_inputs`: manual workflow input definitions
- `workflows.*.runtime_artifact`: uploaded artifact names and paths
- `workflows.*.pages`: GitHub Pages bundle files and deploy conditions

Important:

- GitHub Actions cannot load `schedule` dynamically from a config file at runtime.
- Because of that, this project treats `config/github_actions.yml` as the source of truth and keeps `.github/workflows/*.yml` as generated files.
- After changing the config, regenerate the workflow files.

```bash
make render-workflows
make check-workflows
```

### Environment Variables

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

If they are not set, Telegram delivery is skipped and only local artifacts are generated.

### Main Outputs

- `artifacts/signals_daily.csv`
- `artifacts/signal_history.csv`
- `artifacts/report.json`
- `artifacts/report.html`
- `artifacts/telegram.txt`

### Development Commands

```bash
make sync
make lint
make test
make dry-run
make render-workflows
make check-workflows
```
