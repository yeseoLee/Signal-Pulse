from __future__ import annotations

from typing import Any

import pandas as pd

from watchlist_signal_bot.models import Event, SymbolConfig


def _event(code: str, polarity: str, title: str, weight: int, detail: str) -> Event:
    return Event(code=code, polarity=polarity, title=title, weight=weight, detail=detail)


def _truthy(value: Any) -> bool:
    return bool(value) if pd.notna(value) else False


def select_display_events(events: list[Event]) -> list[Event]:
    if not events:
        return []
    ordered = sorted(events, key=lambda item: abs(item.weight), reverse=True)
    primary = ordered[0]
    display: list[Event] = [primary]

    confirmations = [
        event
        for event in ordered[1:]
        if event.polarity == primary.polarity and event.weight > 0 and event.code != primary.code
    ]
    if confirmations:
        display.append(confirmations[0])

    risks = [
        event
        for event in ordered[1:]
        if event.polarity == "negative" and event.code != primary.code
    ]
    if primary.polarity == "negative":
        risks = [event for event in ordered[1:] if event.weight < 0 and event.code != primary.code]
    if risks:
        display.append(risks[0])

    seen: set[str] = set()
    deduped: list[Event] = []
    for event in display:
        if event.code in seen:
            continue
        seen.add(event.code)
        deduped.append(event)
    return deduped[:3]


def evaluate_signals(
    frame: pd.DataFrame,
    *,
    symbol: SymbolConfig,
    thresholds: dict[str, Any],
) -> tuple[list[Event], list[Event], dict[str, Any]]:
    latest = frame.iloc[-1]
    volume_threshold = float(thresholds["volume"]["spike_ratio"])
    near_breakout_buffer = float(thresholds["breakout"].get("near_breakout_buffer", 0.98))
    overbought = float(thresholds["rsi"]["overbought"])
    events: list[Event] = []

    if _truthy(latest.get("breakout_60d")):
        events.append(
            _event(
                "BREAKOUT_60D",
                "positive",
                "Breakout 60D",
                20,
                "종가가 직전 60일 고점을 상향 돌파했습니다.",
            )
        )
    elif _truthy(latest.get("breakout_20d")):
        events.append(
            _event(
                "BREAKOUT_20D",
                "positive",
                "Breakout 20D",
                10,
                "종가가 직전 20일 고점을 상향 돌파했습니다.",
            )
        )

    if _truthy(latest.get("golden_cross")):
        events.append(
            _event(
                "GOLDEN_CROSS",
                "positive",
                "Golden Cross",
                15,
                "SMA20이 SMA60을 상향 돌파했습니다.",
            )
        )

    if _truthy(latest.get("rs_positive")):
        events.append(
            _event(
                "RS_GT_BENCHMARK",
                "positive",
                "Relative Strength Positive",
                15,
                "60일 상대강도가 벤치마크보다 우위입니다.",
            )
        )

    if _truthy(latest.get("momentum_accelerating")) and latest.get("return_20d", 0) > 0:
        events.append(
            _event(
                "MOMENTUM_ACCELERATING",
                "positive",
                "Momentum Accelerating",
                10,
                "20일 수익률이 최근 60일 흐름 대비 가속 중입니다.",
            )
        )

    if _truthy(latest.get("volume_ratio_20")) and latest["volume_ratio_20"] >= volume_threshold:
        if _truthy(latest.get("breakout_20d")) or _truthy(latest.get("breakout_60d")):
            events.append(
                _event(
                    "VOLUME_CONFIRMED_BREAKOUT",
                    "positive",
                    "Volume Confirmed Breakout",
                    10,
                    f"거래량이 20일 평균 대비 {latest['volume_ratio_20']:.1f}배입니다.",
                )
            )

    prior_high = latest.get("prior_high_20d")
    if pd.notna(prior_high) and latest["close"] >= prior_high * near_breakout_buffer:
        if not _truthy(latest.get("breakout_20d")):
            events.append(
                _event(
                    "WATCH_NEAR_BREAKOUT",
                    "neutral",
                    "Watch Near Breakout",
                    6,
                    "20일 고점 근처까지 접근했습니다.",
                )
            )

    if _truthy(latest.get("squeeze")):
        events.append(
            _event(
                "RANGE_COMPRESSION",
                "neutral",
                "Range Compression",
                5,
                "볼린저 밴드 폭이 축소되어 방향성 대기 구간입니다.",
            )
        )

    if (
        _truthy(latest.get("above_sma120"))
        and _truthy(latest.get("sma20_gt_sma60"))
        and latest["close"] < latest.get("sma_short", latest["close"])
        and latest["close"] > latest.get("sma_medium", latest["close"])
    ):
        events.append(
            _event(
                "PULLBACK_IN_UPTREND",
                "neutral",
                "Pullback In Uptrend",
                7,
                "상승 추세 안에서 단기 눌림 구간입니다.",
            )
        )

    if _truthy(latest.get("dead_cross")):
        events.append(
            _event(
                "DEAD_CROSS",
                "negative",
                "Dead Cross",
                -20,
                "SMA20이 SMA60 아래로 내려왔습니다.",
            )
        )

    if _truthy(latest.get("breakdown_20d")):
        events.append(
            _event(
                "BREAKDOWN_20D",
                "negative",
                "Breakdown 20D",
                -15,
                "종가가 직전 20일 저점을 이탈했습니다.",
            )
        )

    if (
        _truthy(latest.get("down_on_volume"))
        and latest.get("volume_ratio_20", 0) >= volume_threshold
    ):
        events.append(
            _event(
                "HIGH_VOLUME_SELLING",
                "negative",
                "High Volume Selling",
                -10,
                f"하락과 함께 거래량이 {latest['volume_ratio_20']:.1f}배로 증가했습니다.",
            )
        )

    if _truthy(latest.get("rs_weakening")):
        events.append(
            _event(
                "RS_WEAKENING",
                "negative",
                "RS Weakening",
                -10,
                "상대강도 비율이 약해지고 있습니다.",
            )
        )

    if pd.notna(latest.get("sma_long")) and latest["close"] < latest["sma_long"]:
        events.append(
            _event(
                "CLOSE_BELOW_SMA120",
                "negative",
                "Close Below SMA120",
                -10,
                "종가가 장기 이동평균 아래에 있습니다.",
            )
        )

    if pd.notna(latest.get("rsi_14")) and latest["rsi_14"] >= overbought:
        events.append(
            _event(
                "RSI_OVERHEATED",
                "negative",
                "RSI Overheated",
                -5,
                f"RSI가 {latest['rsi_14']:.1f}로 과열권입니다.",
            )
        )

    snapshot = {
        "close": float(latest["close"]),
        "sma20": _maybe_float(latest.get("sma_short")),
        "sma60": _maybe_float(latest.get("sma_medium")),
        "sma120": _maybe_float(latest.get("sma_long")),
        "return_20d": _maybe_percent(latest.get("return_20d")),
        "return_60d": _maybe_percent(latest.get("return_60d")),
        "return_120d": _maybe_percent(latest.get("return_120d")),
        "return_252d": _maybe_percent(latest.get("return_252d")),
        "rsi14": _maybe_float(latest.get("rsi_14")),
        "roc20": _maybe_float(latest.get("roc_20")),
        "stoch_k": _maybe_float(latest.get("stoch_k")),
        "stoch_d": _maybe_float(latest.get("stoch_d")),
        "volume_ratio_20": _maybe_float(latest.get("volume_ratio_20")),
        "atr14": _maybe_float(latest.get("atr_14")),
        "daily_volatility_20": _maybe_float(latest.get("daily_volatility_20")),
        "range_percentile_20d": _maybe_float(latest.get("range_percentile_20d")),
        "distance_from_52w_high": _maybe_float(latest.get("distance_from_52w_high")),
        "distance_from_52w_low": _maybe_float(latest.get("distance_from_52w_low")),
        "relative_return_60d": _maybe_percent(latest.get("relative_return_60d")),
        "relative_return_20d": _maybe_percent(latest.get("relative_return_20d")),
        "data_points": int(frame["close"].count()),
    }
    return events, select_display_events(events), snapshot


def _maybe_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _maybe_percent(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value) * 100.0
