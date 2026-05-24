"""Final build evaluator using full skillpoint resolution and set bonuses."""

from __future__ import annotations

import concurrent.futures
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from wynn_builder_compat.build import build_stat_map
from wynn_builder_compat.build_utils import level_to_skill_points
from wynn_builder_compat.data import WynnData, prepare_item_from_clean
from wynn_builder_compat.encoding import encode_build
from wynn_builder_compat.skillpoints import calculate_skillpoints

from .scoring import check_conditions, score_stat_map


@dataclass
class BuildResult:
    """Result of a fully evaluated build candidate."""

    equipment_names: list[str | None]  # length 8
    weapon_name: str | None
    score: float
    score_breakdown: dict[str, float]
    conditions_met: bool
    skillpoints_valid: bool
    stat_map: dict[str, Any]
    build_hash: str | None
    level: int


def _resolve_items(
    item_names: list[str | None],
    wynn: WynnData,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Resolve item names to prepare_item_from_clean dicts.

    Returns (equipment_list_of_8, weapon_item_or_None).
    Missing items (name not found, or None) are represented as a minimal empty item.
    """
    equipment: list[dict[str, Any]] = []
    weapon: dict[str, Any] | None = None

    def _empty_item() -> dict[str, Any]:
        return prepare_item_from_clean(
            {"displayName": "", "type": "", "lvl": 0, "tier": "Normal"}
        )

    for i, name in enumerate(item_names[:8]):
        if name is None:
            equipment.append(_empty_item())
        else:
            try:
                raw = wynn.item(name)
                equipment.append(prepare_item_from_clean(raw))
            except KeyError:
                equipment.append(_empty_item())

    weapon_name = item_names[8] if len(item_names) > 8 else None
    if weapon_name is not None:
        try:
            raw = wynn.item(weapon_name)
            weapon = prepare_item_from_clean(raw)
        except KeyError:
            weapon = _empty_item()
    else:
        weapon = _empty_item()

    return equipment, weapon


def evaluate_single(
    item_names: list[str | None],
    level: int,
    wynn: WynnData,
    scoring: dict[str, Any],
    conditions: list[dict[str, Any]],
) -> BuildResult:
    """Evaluate one build candidate with full skillpoint resolution and set bonuses.

    Args:
        item_names: length-9 list [equipment[0..7], weapon].
        level: build level.
        wynn: loaded WynnData.
        scoring: scoring dict.
        conditions: condition list.

    Returns:
        BuildResult with all fields populated.
    """
    equipment_names = list(item_names[:8])
    weapon_name = item_names[8] if len(item_names) > 8 else None

    equipment, weapon = _resolve_items(item_names, wynn)

    # Calculate skillpoints to get equip order and set counts
    try:
        (
            _best_order,
            best_skillpoints,
            _final_skillpoints,
            best_total,
            best_active_set_counts,
            _total_item_skillpoints,
        ) = calculate_skillpoints(equipment, weapon, sets_data=wynn.sets_data)
    except Exception:
        best_total = float("inf")
        best_active_set_counts = {}

    # Determine if skillpoint budget is satisfied
    sp_budget = level_to_skill_points(level)
    skillpoints_valid = best_total <= sp_budget

    # Build stat map with set bonuses applied
    stat_map = build_stat_map(
        equipment,
        weapon,
        level,
        active_set_counts=best_active_set_counts,
        sets_data=wynn.sets_data,
    )

    # Score and check conditions
    score, score_breakdown = score_stat_map(stat_map, scoring)
    conditions_met = check_conditions(stat_map, conditions)

    # Encode build hash (best-effort: None on failure)
    build_hash: str | None = None
    try:
        build_hash = encode_build(equipment_names, weapon_name, level, wynn)
    except Exception:
        build_hash = None

    return BuildResult(
        equipment_names=equipment_names,
        weapon_name=weapon_name,
        score=score,
        score_breakdown=score_breakdown,
        conditions_met=conditions_met,
        skillpoints_valid=skillpoints_valid,
        stat_map=stat_map,
        build_hash=build_hash,
        level=level,
    )


def _worker_evaluate(
    args: tuple[list[str | None], int, str | Path, dict[str, Any], list[dict[str, Any]]],
) -> BuildResult:
    """Worker function for ProcessPoolExecutor.

    Loads WynnData independently (no shared memory).
    """
    item_names, level, data_root, scoring, conditions = args
    wynn = WynnData.from_root(data_root)
    return evaluate_single(item_names, level, wynn, scoring, conditions)


def evaluate_batch(
    candidates: list[list[str | None]],
    level: int,
    wynn: WynnData,
    scoring: dict[str, Any],
    conditions: list[dict[str, Any]],
    max_workers: int | None = None,
) -> list[BuildResult]:
    """Evaluate multiple build candidates, returning only those meeting all conditions.

    Attempts parallel evaluation via ProcessPoolExecutor. Falls back to sequential
    evaluation if multiprocessing is unavailable (e.g., spawn context issues).

    Args:
        candidates: list of item_names lists (each length 9).
        level: build level.
        wynn: WynnData instance (used directly for sequential fallback; workers
              reload independently).
        scoring: scoring dict.
        conditions: condition list.
        max_workers: number of worker processes. None = CPU count.

    Returns:
        List of BuildResult where conditions_met is True, in no particular order.
    """
    if not candidates:
        return []

    results: list[BuildResult] = []

    # Determine data root for worker re-loading
    from wynn_builder_compat.data import DEFAULT_DATA_ROOT
    data_root = str(DEFAULT_DATA_ROOT)

    # Try parallel evaluation; fall back to sequential on any error
    try:
        worker_args = [
            (item_names, level, data_root, scoring, conditions)
            for item_names in candidates
        ]
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_worker_evaluate, arg) for arg in worker_args]
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if result.conditions_met:
                        results.append(result)
                except Exception:
                    # Skip failed evaluations
                    pass
    except Exception:
        # Sequential fallback
        for item_names in candidates:
            try:
                result = evaluate_single(item_names, level, wynn, scoring, conditions)
                if result.conditions_met:
                    results.append(result)
            except Exception:
                pass

    return results
