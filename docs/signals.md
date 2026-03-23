# 기술적 분석 구현 문서

이 문서는 현재 `watchlist_signal_bot`이 사용하는 **추세 / 지지·저항 / 수익률 보고서 구조**를 구현 관점에서 정리한 문서입니다.

사용자 문서는 루트 [`README.md`](../README.md)를 보고, 여기서는 실제 구현 함수와 데이터 흐름을 기준으로 설명합니다.

## 목표

현재 리포트는 아래 3가지를 핵심으로 합니다.

1. 5일/20일/60일 이동평균선 기반 단기/중기/장기 추세 판정
2. pivot 기반 지지/저항 가격대 탐지
3. 20일 / 60일 / 120일 수익률 제공

복잡한 이벤트 조합보다, 주간 자동 보고서에 적합한 **설명 가능한 규칙**을 우선합니다.

## 전체 흐름

진입점은 [`analyze_symbol`](../src/watchlist_signal_bot/pipeline.py) 입니다.

1. [`fetch_with_fallback`](../src/watchlist_signal_bot/pipeline.py)
   `FinanceDataReader` 또는 캐시에서 가격 데이터를 읽습니다.
2. [`build_indicator_frame`](../src/watchlist_signal_bot/pipeline.py)
   이동평균과 수익률 컬럼을 추가합니다.
3. [`detect_trend`](../src/watchlist_signal_bot/signals/technical_report.py)
   `MA5`, `MA20`, `MA60`, `120일 수익률`을 기준으로 단기/중기/장기 추세와 기준 추세를 계산합니다.
4. [`detect_support_resistance`](../src/watchlist_signal_bot/signals/technical_report.py)
   pivot high / low를 찾고 병합해 지지/저항 zone을 계산합니다.
5. [`summarize_trend`](../src/watchlist_signal_bot/signals/technical_report.py)
   추세 설명 문장을 생성합니다.
6. [`summarize_levels`](../src/watchlist_signal_bot/signals/technical_report.py)
   지지/저항 설명 문장을 생성합니다.

## 설정 파일

핵심 파라미터는 [`config/thresholds.yml`](../config/thresholds.yml)에서 읽습니다.

### 이동평균

- `moving_average.fast`
- `moving_average.short`
- `moving_average.medium`

### 수익률

- `returns.windows`

현재 기본값은 `20`, `60`, `120` 입니다.

### 지지/저항

- `levels.lookback_days`
- `levels.pivot_window`
- `levels.merge_tolerance`
- `levels.zone_width_ratio`
- `levels.max_supports`
- `levels.max_resistances`

## 지표 생성 함수

### 이동평균

구현 위치: [`add_moving_averages`](../src/watchlist_signal_bot/indicators/trend.py)

주요 출력 컬럼:

- `sma_fast`
- `sma_short`
- `sma_medium`
- `above_sma5`
- `above_sma20`
- `above_sma60`
- `sma5_gt_sma20`
- `sma20_gt_sma60`

### 수익률

구현 위치: [`add_return_indicators`](../src/watchlist_signal_bot/indicators/momentum.py)

주요 출력 컬럼:

- `return_20d`
- `return_60d`
- `return_120d`

## 추세 판정 함수

구현 위치: [`detect_trend`](../src/watchlist_signal_bot/signals/technical_report.py)

입력:

- 최신 `close`
- 최신 `sma_fast` (`MA5`)
- 최신 `sma_short` (`MA20`)
- 최신 `sma_medium` (`MA60`)
- 최신 `return_120d`

### 단기 추세 규칙

- `close > MA5 > MA20` => `상승 추세`
- `close < MA5 < MA20` => `하락 추세`
- 나머지 => `횡보`

### 중기 추세 규칙

- `close > MA20 > MA60` => `상승 추세`
- `close < MA20 < MA60` => `하락 추세`
- 나머지 => `횡보`

### 장기 추세 규칙

- `close > MA60` 이고 `120일 수익률 > 0` => `상승 추세`
- `close < MA60` 이고 `120일 수익률 < 0` => `하락 추세`
- 나머지 => `횡보`

### 기준 추세와 내부 점수

- 기준 추세(`trend_label`)는 `중기 추세`를 그대로 사용합니다.
- 내부 `trend_score`는 `단기/중기/장기`를 각각 `상승=+1`, `횡보=0`, `하락=-1`로 환산해 합산합니다.
- 점수 범위는 `-3~3` 입니다.

## 지지/저항 함수

### Pivot High 탐지

구현 위치: [`find_pivot_highs`](../src/watchlist_signal_bot/signals/technical_report.py)

규칙:

- 어떤 날의 `high`가 앞뒤 `window`일의 high보다 모두 높으면 pivot high로 간주합니다.

### Pivot Low 탐지

구현 위치: [`find_pivot_lows`](../src/watchlist_signal_bot/signals/technical_report.py)

규칙:

- 어떤 날의 `low`가 앞뒤 `window`일의 low보다 모두 낮으면 pivot low로 간주합니다.

### 가격대 병합

구현 위치: [`merge_price_levels`](../src/watchlist_signal_bot/signals/technical_report.py)

입력:

- pivot 가격 목록
- `merge_tolerance`
- `zone_width_ratio`

동작:

- 가격 차이가 tolerance 이내면 같은 레벨로 병합합니다.
- 병합된 레벨의 대표값은 평균 가격으로 계산합니다.
- zone은 `center ± zone_width_ratio` 로 생성합니다.

### 지지/저항 분리

구현 위치: [`detect_support_resistance`](../src/watchlist_signal_bot/signals/technical_report.py)

규칙:

- 현재가 아래의 병합된 pivot low => 지지
- 현재가 위의 병합된 pivot high => 저항
- 현재가와 가까운 순으로 `max_supports`, `max_resistances`만 남깁니다.

## 요약 문장 함수

### 추세 문장

구현 위치: [`summarize_trend`](../src/watchlist_signal_bot/signals/technical_report.py)

예시:

- `단기부터 장기까지 상승 구조가 비교적 고르게 정렬돼 있습니다.`
- `장기 구조는 양호하지만 중기 기준으로는 아직 횡보 구간입니다.`

### 지지/저항 문장

구현 위치: [`summarize_levels`](../src/watchlist_signal_bot/signals/technical_report.py)

예시:

- `하단에서는 98,000~101,000원 구간이 1차 지지로 해석됩니다.`
- `상단에서는 103,000~105,000원 구간이 1차 저항으로 보입니다.`

## AnalysisResult 구조

핵심 결과는 [`AnalysisResult`](../src/watchlist_signal_bot/models.py)에 저장됩니다.

주요 필드:

- `short_trend_label`
- `medium_trend_label`
- `long_trend_label`
- `trend_label`
- `trend_score`
- `trend_summary`
- `support_zones`
- `resistance_zones`
- `support_summary`
- `resistance_summary`
- `indicators`

`indicators`에는 아래 값이 저장됩니다.

- `close`
- `sma5`
- `sma20`
- `sma60`
- `return_20d`
- `return_60d`
- `return_120d`
- `data_points`

## 히스토리 저장

구현 위치: [`HistoryStore`](../src/watchlist_signal_bot/storage/history.py)

현재 히스토리에는 아래가 저장됩니다.

- 날짜
- 종목
- 추세 라벨
- 추세 점수
- 20/60/120일 수익률
- 지지 zone 문자열
- 저항 zone 문자열

추가로 직전 값과 비교해 `trend_change`를 생성합니다.

예시:

- `상승 추세 -> 횡보`
- `횡보 -> 하락 추세`

## 리포트 출력

### Telegram

구현 위치: [`render_telegram_summary`](../src/watchlist_signal_bot/reports/telegram.py)

구성:

- 리포트 기준일
- 추세별 종목 수
- 종목별 단기/중기/장기 추세
- 20/60/120일 수익률
- 지지/저항 zone
- GitHub Pages 링크

### HTML

구현 위치:

- [`render_html_report`](../src/watchlist_signal_bot/reports/html.py)
- [`report.html.j2`](../src/watchlist_signal_bot/reports/templates/report.html.j2)

구성:

- 추세 분포 요약
- 최근 추세 변화
- 종목별 카드와 단기/중기/장기 추세 배지
- 지지/저항 zone
- 실패 종목

## 새 규칙 추가 체크리스트

새 추세 규칙이나 가격대 로직을 추가할 때는 보통 아래 파일을 같이 봅니다.

1. [`config/thresholds.yml`](../config/thresholds.yml)
2. [`src/watchlist_signal_bot/indicators/trend.py`](../src/watchlist_signal_bot/indicators/trend.py)
3. [`src/watchlist_signal_bot/indicators/momentum.py`](../src/watchlist_signal_bot/indicators/momentum.py)
4. [`src/watchlist_signal_bot/signals/technical_report.py`](../src/watchlist_signal_bot/signals/technical_report.py)
5. [`src/watchlist_signal_bot/pipeline.py`](../src/watchlist_signal_bot/pipeline.py)
6. [`src/watchlist_signal_bot/reports/telegram.py`](../src/watchlist_signal_bot/reports/telegram.py)
7. [`src/watchlist_signal_bot/reports/html.py`](../src/watchlist_signal_bot/reports/html.py)
8. [`tests/`](../tests/)
