"""NumPy matrix-based pruning evaluator for wynnBuildGenerator search."""

from __future__ import annotations

from typing import Any

import numpy as np

from wynn_builder_compat.build import STATIC_IDS, MUST_IDS

# All stat IDs that can appear in a stat_map, sorted for stable indexing.
# STATIC_IDS covers static fields (hp, eDef, ..., damMobs, defMobs).
# MUST_IDS covers the always-present roll fields.
# ROLLED_IDS from build_utils covers all rolled stat fields.
# We union them all for a comprehensive stat key list.
_STATIC_SET: frozenset[str] = frozenset(STATIC_IDS)

# Import rolled IDs from build_utils to build the full key list
from wynn_builder_compat.build_utils import ROLLED_IDS as _ROLLED_IDS

STAT_KEYS: list[str] = sorted(set(STATIC_IDS) | set(MUST_IDS) | set(_ROLLED_IDS))


def _item_stat_vector(item: dict[str, Any], stat_keys: list[str]) -> np.ndarray:
    """Build a float32 vector for one item using maxRolls + static stats."""
    vec = np.zeros(len(stat_keys), dtype=np.float32)
    key_index = {k: i for i, k in enumerate(stat_keys)}

    # maxRolls contains rolled stat values at their best possible roll
    max_rolls: dict[str, Any] = item.get("maxRolls") or {}
    for stat_id, value in max_rolls.items():
        if stat_id in key_index:
            vec[key_index[stat_id]] += float(value or 0)

    # Static IDs are stored directly on the item (not in maxRolls)
    for stat_id in STATIC_IDS:
        if stat_id in key_index:
            v = item.get(stat_id)
            if v:
                vec[key_index[stat_id]] += float(v)

    return vec


class NumpyEvaluator:
    """Pruning-only evaluator using NumPy matrix operations.

    Does NOT include set bonus or skillpoint resolution. Designed for fast
    approximate scoring during beam search candidate pruning.
    """

    def __init__(
        self,
        all_items: list[dict[str, Any]],
        stat_keys: list[str] | None = None,
    ) -> None:
        self.stat_keys: list[str] = stat_keys if stat_keys is not None else STAT_KEYS
        self._key_index: dict[str, int] = {k: i for i, k in enumerate(self.stat_keys)}

        # Build item matrix: shape (N, len(stat_keys))
        self.item_name_to_idx: dict[str, int] = {}
        rows: list[np.ndarray] = []

        for item in all_items:
            name = item.get("displayName") or item.get("name") or ""
            if not name:
                continue
            idx = len(rows)
            self.item_name_to_idx[name] = idx
            rows.append(_item_stat_vector(item, self.stat_keys))

        if rows:
            self.item_matrix: np.ndarray = np.stack(rows, axis=0).astype(np.float32)
        else:
            self.item_matrix = np.zeros((0, len(self.stat_keys)), dtype=np.float32)

        # Cached zero vector for None slots
        self._zero_vec: np.ndarray = np.zeros(len(self.stat_keys), dtype=np.float32)

    def _get_row(self, name: str | None) -> np.ndarray:
        if name is None:
            return self._zero_vec
        idx = self.item_name_to_idx.get(name)
        if idx is None:
            return self._zero_vec
        return self.item_matrix[idx]

    def approx_stat_sum(self, item_names: list[str | None]) -> np.ndarray:
        """Sum stat vectors for the given item names. None treated as zero vector.

        Returns:
            np.ndarray of shape (len(stat_keys),).
        """
        total = np.zeros(len(self.stat_keys), dtype=np.float32)
        for name in item_names:
            total += self._get_row(name)
        return total

    def approx_score(self, item_names: list[str | None], scoring: dict[str, Any]) -> float:
        """Compute weighted dot product score from stat sum.

        scoring: {"maximize": {key: weight, ...}, "minimize": {key: weight, ...}}
        """
        stat_sum = self.approx_stat_sum(item_names)
        score = 0.0

        for key, weight in (scoring.get("maximize") or {}).items():
            idx = self._key_index.get(key)
            if idx is not None:
                score += float(stat_sum[idx]) * float(weight)

        for key, weight in (scoring.get("minimize") or {}).items():
            idx = self._key_index.get(key)
            if idx is not None:
                score -= float(stat_sum[idx]) * float(weight)

        return score

    def approx_check_conditions(
        self,
        item_names: list[str | None],
        conditions: list[dict[str, Any]],
    ) -> bool:
        """Approximate AND evaluation of all conditions against stat sum.

        Set bonuses are NOT included; this is a conservative estimate.
        """
        if not conditions:
            return True

        stat_sum = self.approx_stat_sum(item_names)

        for cond in conditions:
            key = cond["key"]
            op = cond["op"]
            threshold = float(cond["value"])
            idx = self._key_index.get(key)
            actual = float(stat_sum[idx]) if idx is not None else 0.0

            if op == ">=":
                if actual < threshold:
                    return False
            elif op == "<=":
                if actual > threshold:
                    return False
            else:
                raise ValueError(f"Unknown condition operator: {op!r}")

        return True
