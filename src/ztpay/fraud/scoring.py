from __future__ import annotations


def noisy_or(severities: list[float]) -> float:
    p = 1.0
    for s in severities:
        s = min(max(float(s), 0.0), 1.0)
        p *= 1.0 - s
    return round(1.0 - p, 4)


def decide(findings: list[dict]) -> tuple[str, float]:
    if not findings:
        return "allow", 0.0
    score = noisy_or([f["severity"] for f in findings])
    if score >= 0.80 or len(findings) >= 2:
        return "hold", score
    if score >= 0.45:
        return "hold", score
    return "allow", score
