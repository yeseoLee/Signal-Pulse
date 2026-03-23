# Watchlist Signal Bot

## Language

- 한국어
- [English](./README.en.md)

관심종목을 대상으로 **5일/20일/60일/120일 이동평균선 기반 추세**, **pivot 기반 지지/저항 가격대**, **20일/60일/120일 수익률**을 자동 계산해 Telegram과 HTML 리포트로 만드는 봇입니다.

## 개요

- 추세는 `MA5`, `MA20`, `MA60`, `MA120`을 사용해 `단기`, `중단기`, `중장기`, `장기`로 나눠 제공합니다.
- 보고서의 기준 추세는 `중장기(20일/60일선)` 기준으로 분류합니다.
- 지지/저항은 최근 고점·저점을 pivot으로 찾고, 비슷한 가격대를 병합해 zone 형태로 보여줍니다.
- 수익률은 `20일`, `60일`, `120일` 기준으로 함께 제공합니다.
- 결과는 `CSV`, `JSON`, `HTML`, `Telegram text`로 저장합니다.
- 가격 데이터는 `FinanceDataReader`로 수집하고, 실패 시 저장된 캐시를 재사용합니다.

## Fork 후 설정

이 저장소를 Fork해서 쓰려면 아래만 먼저 맞추면 됩니다.

1. [`config/watchlist.yml`](./config/watchlist.yml)에서 관심종목을 본인 기준으로 수정합니다.
2. [`config/thresholds.yml`](./config/thresholds.yml)에서 pivot window, 병합 tolerance, zone 폭을 수정합니다.
3. [`config/github_actions.yml`](./config/github_actions.yml)에서 실행 주기와 기본 옵션을 수정합니다.
4. GitHub 저장소 `Settings > Secrets and variables > Actions`에 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`를 등록합니다.
5. GitHub 저장소 `Settings > Pages`에서 `gh-pages` 브랜치 `/ (root)`를 Pages 소스로 지정합니다.
6. 필요하면 `GITHUB_PAGES_URL` 환경변수에 본인 Pages 주소를 넣어 텔레그램 링크를 고정할 수 있습니다.

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
- `metadata`: 종목별 시장, 이름, 자산 유형
- KR 6자리 숫자 티커는 문자열로 감싸는 것을 권장합니다.
  예: `"005930"`

현재 기본 구성은 다음과 같습니다.

- US: `AAPL`, `NVDA`, `GOOGL`, `"S&P500"`
- KR: `"005930"` 삼성전자, `"000660"` SK하이닉스, `"005380"` 현대차, `KOSPI`

### `config/thresholds.yml`

기술적 분석 규칙의 핵심 파라미터를 정의합니다.

- `moving_average.fast`: 기본 5일 이동평균
- `moving_average.short`: 기본 20일 이동평균
- `moving_average.medium`: 기본 60일 이동평균
- `moving_average.long`: 기본 120일 이동평균
- `returns.windows`: 기본 수익률 구간
- `levels.lookback_days`: 지지/저항 탐지에 사용하는 최근 일봉 길이
- `levels.pivot_window`: pivot high / low 탐지 창 크기
- `levels.merge_tolerance`: 가격대 병합 허용 오차
- `levels.zone_width_ratio`: 지지/저항 zone 폭
- `levels.max_supports`, `levels.max_resistances`: 출력 개수

### `config/github_actions.yml`

GitHub Actions 관련 설정을 관리합니다.

- `daily.schedule`: 정기 실행 cron
- `daily.options`: daily workflow 기본 옵션
- `manual.options`: manual workflow 기본 옵션

중요:

- GitHub Actions의 `schedule`은 런타임에 설정 파일을 읽을 수 없습니다.
- 그래서 이 프로젝트는 [`config/github_actions.yml`](./config/github_actions.yml)을 소스로 사용하고, [`.github/workflows/`](./.github/workflows/) 아래 YAML은 생성물로 관리합니다.
- 리포트 HTML은 workflow가 `public/` 번들을 만든 뒤 `gh-pages` 전용 브랜치로 푸시합니다.
- 설정 변경 후 아래 명령으로 워크플로를 다시 생성해야 합니다.

```bash
make render-workflows
make check-workflows
```

## 리포트 구조

현재 리포트는 아래 4가지를 중심으로 작성됩니다.

### 1. 추세

- 단기 추세: `close > MA5` 이면 `상승 추세`, `close < MA5` 이면 `하락 추세`, 나머지는 `횡보`
- 중단기 추세: `close > MA5 > MA20` 이면 `상승 추세`, `close < MA5 < MA20` 이면 `하락 추세`, 나머지는 `횡보`
- 중장기 추세: `close > MA20 > MA60` 이면 `상승 추세`, `close < MA20 < MA60` 이면 `하락 추세`, 나머지는 `횡보`
- 장기 추세: `close > MA60 > MA120` 이면 `상승 추세`, `close < MA60 < MA120` 이면 `하락 추세`, 나머지는 `횡보`
- 보고서 섹션과 추세 변화 추적은 `중장기 추세`를 기준값으로 사용합니다.

### 2. 수익률

리포트에는 항상 아래 수익률이 함께 나갑니다.

- `20일 수익률`
- `60일 수익률`
- `120일 수익률`

### 3. 지지/저항

- 최근 일봉에서 `pivot high`, `pivot low`를 찾습니다.
- 비슷한 가격대는 tolerance 기준으로 병합합니다.
- 현재가 아래는 지지, 위는 저항으로 나눕니다.
- 가까운 zone 2개씩 선택합니다.

표현 예시:

- `98,000원 부근`
- `99,000~101,000원`

### 4. 문장 요약

각 종목마다 아래 문장을 자동 생성합니다.

- 추세 설명 1문장
- 지지 설명 1문장
- 저항 설명 1문장

## 산출물 형식

### Telegram

- `상승 추세`, `횡보`, `하락 추세` 섹션으로 나눕니다.
- 종목별로 `현재가`, `추세 해석`, `20/60/120일 수익률`만 보여줍니다.
- 하단에 GitHub Pages 리포트 링크를 함께 붙입니다.

### HTML

- 추세 분포 요약
- 최근 추세 변화
- 종목별 카드와 `단기/중단기/중장기/장기` 추세 배지
- 지지/저항 zone
- 실패 종목 목록

## 환경 변수

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `GITHUB_PAGES_URL`

둘 다 없으면 Telegram 전송은 건너뛰고 파일만 생성합니다.

## 주요 산출물

- `artifacts/signals_daily.csv`
- `artifacts/signal_history.csv`
- `artifacts/report.json`
- `artifacts/report.html`
- `artifacts/telegram.txt`

## 개발자 문서

- 구현 함수와 시그널 구조: [`docs/signals.md`](./docs/signals.md)

## 개발 명령

```bash
make sync
make lint
make test
make dry-run
make render-workflows
make check-workflows
```
