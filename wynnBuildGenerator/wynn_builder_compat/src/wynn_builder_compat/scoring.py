"""Search condition and score helpers for Python candidate generation."""

from __future__ import annotations

from typing import Any


def score_stat_map(stat_map: dict[str, float], scoring: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """Weighted score over Wynnbuilder statMap keys."""
    score = 0.0
    breakdown: dict[str, float] = {}
    for key, weight in (scoring.get("maximize") or {}).items():
        contribution = float(stat_map.get(key, 0.0)) * float(weight)
        score += contribution
        breakdown[f"maximize.{key}"] = contribution
    for key, weight in (scoring.get("minimize") or {}).items():
        contribution = -float(stat_map.get(key, 0.0)) * float(weight)
        score += contribution
        breakdown[f"minimize.{key}"] = contribution
    return score, breakdown

