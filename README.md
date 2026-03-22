# Watchlist Signal Bot

## Language

- 한국어
- [English](./README.en.md)

한국/미국 주식과 ETF를 대상으로 OHLCV를 수집하고, 설명 가능한 규칙 기반 시그널을 생성해 Telegram과 HTML 리포트로 출력하는 봇입니다.

## 개요

- 관심종목 목록 기준으로 일봉 데이터를 수집합니다.
- 이동평균, 돌파, RSI, 거래량, 상대강도 기반 신호를 계산합니다.
- 결과를 `CSV`, `JSON`, `HTML`, `Telegram text` 형태로 저장합니다.
- 가격 데이터는 `FinanceDataReader`로 수집하고, 실패 시 저장된 캐시를 재사용합니다.

## 빠른 시작

```bash
uv sync --group dev
uv run python -m watchlist_signal_bot.main --dry-run
```

특정 시장 또는 종목만 테스트할 수도 있습니다.

```bash
uv run python -m watchlist_signal_bot.main --dry-run --market US
uv run python -m watchlist_signal_bot.main --dry-run --symbol AAPL
```

## Config

설정 파일은 모두 [`config/`](./config/) 아래에 있습니다.

### `config/watchlist.yml`

관심종목 유니버스와 종목 메타데이터를 정의합니다.

- `groups`: 종목 그룹 목록
- `metadata`: 종목별 시장, 이름, 벤치마크, 자산 유형
- KR 6자리 숫자 티커는 문자열로 감싸는 것을 권장합니다.
  예: `"005930"`, `"069500"`

현재 기본 구성은 다음과 같습니다.

- US M6: `AAPL`, `MSFT`, `NVDA`, `AMZN`, `META`, `GOOGL`
- KR 대형주: `"005930"` 삼성전자, `"000660"` SK하이닉스, `"005380"` 현대차

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
```

### `config/thresholds.yml`

시그널 계산 파라미터를 정의합니다.

- 조회 기간: `lookback_days`
- 이동평균: `moving_average`
- 돌파 윈도우: `breakout`
- 거래량 급증 임계값: `volume.spike_ratio`
- RSI 기간/과열/과매도: `rsi`
- 점수 가중치: `score_weights`

현재 기본 데이터 소스는 `FinanceDataReader` 하나로 통합되어 있습니다.

### `config/benchmarks.yml`

시장 기본 벤치마크와 벤치마크 심볼 매핑을 정의합니다.

- `default`: 시장별 기본 벤치마크
- `symbols`: 벤치마크 라벨과 실제 조회 심볼

현재 예시는 아래를 포함합니다.

- `KOSPI -> KS11`
- `KOSDAQ -> KQ11`
- `SPY -> SPY`
- `QQQ -> QQQ`
- `SOXX -> SOXX`

### `config/github_actions.yml`

GitHub Actions 관련 설정을 관리합니다.

- `daily.schedule`: 정기 실행 cron
- `daily.options`: daily workflow 기본 옵션
- `manual.options`: manual workflow 기본 옵션

중요:

- GitHub Actions의 `schedule`은 런타임에 설정 파일을 읽을 수 없습니다.
- 그래서 이 프로젝트는 [`config/github_actions.yml`](./config/github_actions.yml)을 소스로 사용하고, [`.github/workflows/`](./.github/workflows/) 아래 YAML은 생성물로 관리합니다.
- 이 파일에는 사용자가 바꿔도 되는 값만 둡니다. 예를 들어 `cron`, `market 기본값`, `dry_run 기본값`, `publish_pages 기본값` 같은 항목입니다.
- runner, permissions, artifact 경로, Python/uv 버전 같은 개발자용 값은 생성기 내부 기본값으로 관리합니다.
- 리포트 HTML은 workflow가 `public/` 번들을 만든 뒤 `gh-pages` 전용 브랜치로 푸시합니다.
- 설정 변경 후 아래 명령으로 워크플로를 다시 생성해야 합니다.

```bash
make render-workflows
make check-workflows
```

## 신호 계산 항목

텔레그램 요약은 종합 점수 한 줄로 판단하지 않습니다. 각 종목에 대해 아래 항목을 자연어 문장으로 풀어서 보여줍니다.

### 이동평균

- `close > SMA20`, `close > SMA60`, `close > SMA120`
- `SMA20 > SMA60 > SMA120` 정배열 여부
- `골든크로스`, `데드크로스`
- 장기선 하회 여부

이 항목은 추세의 방향과 이동평균 구조가 건강한지 판단합니다.

### 돌파 / 이탈

- `20일 돌파`
- `60일 돌파`
- `120일 고점 돌파`
- `돌파 임박`
- `20일 저점 이탈`

이 항목은 가격이 최근 박스 상단을 돌파하는지, 또는 반대로 지지 구간을 이탈하는지 판단합니다.

### RSI

- `RSI(14)`를 사용합니다.
- 일반적으로 `45~70` 구간은 우호적으로 봅니다.
- 과열 구간은 `RSI 과열`로 감점합니다.

이 항목은 추세 안의 과열 여부와 강도의 균형을 봅니다.

### 거래량

- `volume / 20일 평균 거래량`
- 상승일 거래량 증가 여부
- `거래량 동반 돌파`
- `거래량 동반 하락`

이 항목은 가격 움직임이 거래량으로 확인되는지, 혹은 매도 압력이 커지는지 판단합니다.

### 상대강도

- `relative_return_20d`
- `relative_return_60d`
- `상대강도 우위`
- `상대강도 약화`

이 항목은 종목이 벤치마크보다 강한지, 약해지고 있는지를 판단합니다.

### 모멘텀

- `20일`, `60일`, `120일` 수익률
- `모멘텀 가속`

이 항목은 상승 속도가 유지되는지, 중기 흐름이 가속되는지 판단합니다.

### 텔레그램 해석 방법

- 출력은 `[강세]`, `[중립]`, `[약세]` 세 영역으로 나뉩니다.
- 종목별로 `이동평균`, `돌파`, `RSI`, `거래량`, `상대강도`, `모멘텀`을 각각 자연어 문장으로 설명합니다.
- 예: `120일 이동평균선 아래에 있습니다.`, `데드크로스가 발생했습니다.`, `RSI는 41.2입니다.`
- 텔레그램에는 `신규 수집`, `대체 소스`, `캐시 재사용` 같은 데이터 상태 라벨을 노출하지 않습니다.
- 기본 watchlist는 미국 M6와 한국 3종목, 총 9종목입니다.

## 환경 변수

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

둘 다 없으면 Telegram 전송은 건너뛰고 파일만 생성합니다.

## 주요 산출물

- `artifacts/signals_daily.csv`
- `artifacts/signal_history.csv`
- `artifacts/report.json`
- `artifacts/report.html`
- `artifacts/telegram.txt`

## 개발 명령

```bash
make sync
make lint
make test
make dry-run
make render-workflows
make check-workflows
```
