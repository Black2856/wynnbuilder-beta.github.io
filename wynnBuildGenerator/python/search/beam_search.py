"""Beam search algorithm for wynnBuildGenerator build exploration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .numpy_evaluator import NumpyEvaluator


@dataclass
class PartialBuild:
    """Partial build state during beam search expansion."""

    item_names: list[str | None]
    approx_score: float = 0.0


def beam_search(
    slot_candidates: list[list[dict[str, Any]]],
    fixed_items: dict[int, str | None],
    beam_width: int,
    evaluator: NumpyEvaluator,
    scoring: dict[str, Any],
    conditions: list[dict[str, Any]],
) -> list[list[str | None]]:
    """Greedy beam search over 9 equipment slots.

    Expands one slot at a time. At each step, keeps only the top beam_width
    partial builds ranked by approx_score. Fixed slots are expanded with their
    single fixed item only.

    Args:
        slot_candidates: 9-element list; each element is a list of
            prepare_item_from_clean dicts for that slot.
        fixed_items: mapping of slot_idx -> fixed item name (or None for empty).
        beam_width: maximum number of partial builds to retain per step.
        evaluator: NumpyEvaluator for approximate scoring.
        scoring: scoring dict {"maximize": {...}, "minimize": {...}}.
        conditions: list of condition dicts (used for pruning in approx check).

    Returns:
        List of up to beam_width complete item_names lists (length 9).
    """
    num_slots = len(slot_candidates)
    if num_slots == 0:
        return []

    # Seed beam with one empty partial build
    beam: list[PartialBuild] = [PartialBuild(item_names=[], approx_score=0.0)]

    for slot_idx in range(num_slots):
        next_beam: list[PartialBuild] = []

        # Build candidates for this slot
        if slot_idx in fixed_items:
            # Fixed slot: one candidate (the fixed item, possibly None = empty)
            fixed_name = fixed_items[slot_idx]
            slot_options: list[str | None] = [fixed_name]
        else:
            candidates = slot_candidates[slot_idx]
            if candidates:
                slot_options = [
                    (item.get("displayName") or item.get("name"))
                    for item in candidates
                ]
            else:
                # No candidates: treat as empty slot
                slot_options = [None]

        for partial in beam:
            for name in slot_options:
                new_names = partial.item_names + [name]
                score = evaluator.approx_score(new_names, scoring)
                next_beam.append(PartialBuild(item_names=new_names, approx_score=score))

        # Prune: keep only top beam_width by approx_score
        next_beam.sort(key=lambda pb: pb.approx_score, reverse=True)
        beam = next_beam[:beam_width]

    return [pb.item_names for pb in beam]
