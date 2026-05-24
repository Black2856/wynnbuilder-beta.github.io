"""Score and condition evaluation for wynnBuildGenerator search.

This module is wynnBuildGenerator-specific logic. It operates on statMap dicts
produced by wynn_builder_compat.build.build_stat_map(), but is NOT a port of any
Wynnbuilder JS function.
"""

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


def check_conditions(stat_map: dict[str, float], conditions: list[dict[str, Any]]) -> bool:
    """Return True if stat_map satisfies all conditions (AND evaluation).

    Each condition: {"key": str, "op": ">=" | "<=", "value": float}
    Unknown keys are treated as 0. Unknown operators raise ValueError.
    """
    for cond in conditions:
        key = cond["key"]
        op = cond["op"]
        threshold = float(cond["value"])
        actual = float(stat_map.get(key, 0.0))
        if op == ">=":
            if not (actual >= threshold):
                return False
        elif op == "<=":
            if not (actual <= threshold):
                return False
        else:
            raise ValueError(f"Unknown condition operator: {op!r}")
    return True
