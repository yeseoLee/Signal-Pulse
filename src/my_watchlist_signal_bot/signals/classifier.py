from __future__ import annotations


def classify_state(score: int) -> str:
    if score >= 80:
        return "Strong Uptrend"
    if score >= 60:
        return "Uptrend"
    if score >= 40:
        return "Neutral"
    if score >= 20:
        return "Weak"
    return "Breakdown Risk"
