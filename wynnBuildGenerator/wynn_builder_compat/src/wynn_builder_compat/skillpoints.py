"""Python ports for js/skillpoints.js."""

from __future__ import annotations

from collections.abc import Iterable, MutableSequence, Sequence
from typing import Any

SKILL_COUNT = 5
SKP_ORDER = ("str", "dex", "int", "def", "agi")
REQ_ORDER = ("strReq", "dexReq", "intReq", "defReq", "agiReq")


def _get(item: Any, key: str, default: Any = None) -> Any:
    if hasattr(item, "get"):
        return item.get(key, default)
    return getattr(item, key, default)


def _skillpoints(item: Any) -> list[float]:
    values = _get(item, "skillpoints")
    if values is not None:
        return list(values)
    return [_get(item, key, 0) or 0 for key in SKP_ORDER]


def _reqs(item: Any) -> list[float]:
    values = _get(item, "reqs")
    if values is not None:
        return list(values)
    return [_get(item, key, 0) or 0 for key in REQ_ORDER]


def _prepared_item(item: Any) -> dict[str, Any]:
    return {
        "source": item,
        "skillpoints": _skillpoints(item),
        "reqs": _reqs(item),
        "set": _get(item, "set"),
        "crafted": bool(_get(item, "crafted", False)),
    }


def vadd5(left: tuple[float, ...] | list[float], right: tuple[float, ...] | list[float]) -> list[float]:
    """Port of js/skillpoints.js::vadd5."""
    return [left[i] + right[i] for i in range(SKILL_COUNT)]


def can_equip(skillpoints: tuple[float, ...] | list[float], item: Any) -> bool:
    """Port of js/skillpoints.js::can_equip for item-like objects with reqs."""
    reqs = _reqs(item)
    for i in range(SKILL_COUNT):
        if reqs[i] <= 0:
            continue
        if reqs[i] > skillpoints[i]:
            return False
    return True


def apply_skillpoints(skillpoints: MutableSequence[float], item: Any, set_counts: dict[str, int]) -> None:
    """Port of js/skillpoints.js::apply_skillpoints set counting behavior."""
    item_skillpoints = _skillpoints(item)
    for i in range(SKILL_COUNT):
        skillpoints[i] += item_skillpoints[i]

    set_name = _get(item, "set")
    if set_name:
        set_counts[set_name] = set_counts.get(set_name, 0) + 1


def fix_should_pop(skillpoints: MutableSequence[float], item: Any) -> list[float]:
    """Port of js/skillpoints.js::fix_should_pop."""
    reqs = _reqs(item)
    item_skillpoints = _skillpoints(item)
    crafted = bool(_get(item, "crafted", False))
    applied = [0, 0, 0, 0, 0]
    for i in range(SKILL_COUNT):
        if reqs[i] <= 0:
            continue
        req = reqs[i] if crafted else reqs[i] + item_skillpoints[i]
        cur = skillpoints[i]
        if req > cur:
            diff = req - cur
            applied[i] += diff
            skillpoints[i] += diff
    return applied


def check_under_100(skillpoints: Sequence[float]) -> bool:
    """Port of js/skillpoints.js::check_under_100."""
    return all(value <= 100 for value in skillpoints)


def apply_to_fit(skillpoints: MutableSequence[float], item: Any) -> list[float]:
    """Port of js/skillpoints.js::apply_to_fit."""
    reqs = _reqs(item)
    applied = [0, 0, 0, 0, 0]
    for i in range(SKILL_COUNT):
        if reqs[i] <= 0:
            continue
        cur = skillpoints[i]
        if reqs[i] > cur:
            diff = reqs[i] - cur
            applied[i] += diff
            skillpoints[i] += diff
    return applied


def calculate_skillpoints(
    equipment: Iterable[Any],
    weapon: Any,
    *,
    sets_data: dict[str, Any] | None = None,
) -> tuple[list[Any], list[float], list[float], float, dict[str, int], list[float]]:
    """Port of js/skillpoints.js::calculate_skillpoints.

    Returns `[best_order, best_skillpoints, final_skillpoints, best_total,
    best_active_set_counts, total_item_skillpoints]` as a Python tuple.
    """
    equipment_items = [_prepared_item(item) for item in equipment]
    weapon_item = _prepared_item(weapon)
    crafted_items = [item for item in equipment_items if item["crafted"]]
    total_item_skillpoints = [0, 0, 0, 0, 0]

    for i in range(SKILL_COUNT):
        total_item_skillpoints[i] += weapon_item["skillpoints"][i]
    for item in equipment_items:
        for i in range(SKILL_COUNT):
            total_item_skillpoints[i] += item["skillpoints"][i]

    best_order = list(equipment_items)
    best_skillpoints = [0, 0, 0, 0, 0]
    final_skillpoints = [0, 0, 0, 0, 0]
    best_total = float("inf")
    best_under_100 = False
    best_active_set_counts: dict[str, int] = {}

    def recurse_check(
        applied_so_far: list[float],
        skp_totals: list[float],
        active_sets: dict[str, int],
        total_applied_so_far: float,
        skipped_states: list[list[float]],
        prior_skipped: list[int],
        equipped_indices: list[int],
        remains_in_order: list[int],
    ) -> None:
        nonlocal best_order
        nonlocal best_skillpoints
        nonlocal final_skillpoints
        nonlocal best_total
        nonlocal best_under_100
        nonlocal best_active_set_counts

        if len(remains_in_order) == 1:
            item = equipment_items[remains_in_order[0]]
            skillpoints = list(skp_totals)

            deltas1 = apply_to_fit(skillpoints, item)
            sets = dict(active_sets)
            if not item["crafted"]:
                apply_skillpoints(skillpoints, item, sets)
            deltas2 = apply_to_fit(skillpoints, weapon_item)
            deltas = vadd5(deltas1, deltas2)

            for equipped_item in equipment_items:
                deltas = vadd5(deltas, fix_should_pop(skillpoints, equipped_item))

            for index, skipped_index in enumerate(prior_skipped):
                sim_skillpoints = vadd5(skipped_states[index], deltas)
                if can_equip(sim_skillpoints, equipment_items[skipped_index]):
                    return

            applied = vadd5(applied_so_far, deltas)
            total_applied = total_applied_so_far + sum(deltas)
            solution_under_100 = check_under_100(applied)
            if best_under_100 and not solution_under_100:
                return
            if total_applied < best_total or (solution_under_100 and not best_under_100):
                for crafted in crafted_items:
                    apply_skillpoints(skillpoints, crafted, sets)
                apply_skillpoints(skillpoints, weapon_item, sets)

                final_skillpoints = skillpoints
                best_skillpoints = applied
                best_total = total_applied
                best_active_set_counts = sets
                best_order = [equipment_items[index] for index in equipped_indices + [remains_in_order[0]]]
                best_under_100 = solution_under_100
            return

        for i, item_index in enumerate(remains_in_order):
            head = remains_in_order[:i]
            skipped = prior_skipped + head
            skillpoints = list(skp_totals)
            item = equipment_items[item_index]
            deltas = apply_to_fit(skillpoints, item)
            sim_states: list[list[float]] = []

            rejected = False
            for j, skipped_index in enumerate(prior_skipped):
                sim_skillpoints = vadd5(skipped_states[j], deltas)
                if can_equip(sim_skillpoints, equipment_items[skipped_index]):
                    rejected = True
                    break
                sim_states.append(sim_skillpoints)
            if rejected:
                continue

            for head_index in head:
                if can_equip(skillpoints, equipment_items[head_index]):
                    rejected = True
                    break
                sim_states.append(skillpoints)
            if rejected:
                continue

            mod_skillpoints = list(skillpoints)
            sets = dict(active_sets)
            if not item["crafted"]:
                apply_skillpoints(mod_skillpoints, item, sets)
            applied = vadd5(applied_so_far, deltas)
            total_applied = total_applied_so_far + sum(deltas)
            tail = remains_in_order[i + 1 :]
            remains = tail + head

            recurse_check(
                applied,
                mod_skillpoints,
                sets,
                total_applied,
                sim_states,
                skipped,
                equipped_indices + [item_index],
                remains,
            )

    recurse_check(
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        {},
        0,
        [],
        [],
        [],
        list(range(len(equipment_items))),
    )

    if sets_data:
        for set_name, count in best_active_set_counts.items():
            bonus = sets_data.get(set_name, {}).get("bonuses", [])[count - 1]
            for i, skill in enumerate(SKP_ORDER):
                delta = bonus.get(skill, 0)
                final_skillpoints[i] += delta
                total_item_skillpoints[i] += delta

    return (
        [item["source"] for item in best_order],
        best_skillpoints,
        final_skillpoints,
        best_total,
        best_active_set_counts,
        total_item_skillpoints,
    )
