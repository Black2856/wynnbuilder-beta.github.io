"""Slot-based item index for wynnBuildGenerator search."""

from __future__ import annotations

from typing import Any

from wynn_builder_compat.data import WynnData, prepare_item_from_clean

SLOT_NAMES = ["helmet", "chestplate", "leggings", "boots", "ring1", "ring2", "bracelet", "necklace", "weapon"]
SLOT_TYPES = ["helmet", "chestplate", "leggings", "boots", "ring", "ring", "bracelet", "necklace", None]

CLASS_WEAPON_MAP: dict[str, str] = {
    "warrior": "spear",
    "fallen": "spear",
    "archer": "bow",
    "skyseer": "bow",
    "mage": "wand",
    "darkwizard": "wand",
    "assassin": "dagger",
    "ninja": "dagger",
    "shaman": "relik",
    "ritualist": "relik",
}


class ItemIndex:
    """Slot-aware item index that pre-categorizes items for fast candidate lookup."""

    def __init__(self, wynn: WynnData) -> None:
        self._wynn = wynn
        # Pre-build slot buckets: maps type_string -> list of prepared items
        # We keep both the raw item and the prepared version to avoid re-expanding each lookup
        self._by_type: dict[str, list[dict[str, Any]]] = {}
        for item in wynn.items:
            item_type = str(item.get("type", "")).lower()
            if item_type not in self._by_type:
                self._by_type[item_type] = []
            self._by_type[item_type].append(item)

        # Build prepared cache keyed by displayName for fast lookup
        self._prepared_cache: dict[str, dict[str, Any]] = {}

    def _get_prepared(self, raw: dict[str, Any]) -> dict[str, Any]:
        name = raw.get("displayName") or raw.get("name", "")
        if name not in self._prepared_cache:
            self._prepared_cache[name] = prepare_item_from_clean(raw)
        return self._prepared_cache[name]

    def candidates_for_slot(
        self,
        slot_idx: int,
        class_: str,
        level: int,
        tier_filter: list[str] | None = None,
        fixed_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return prepare_item_from_clean results for valid items in the given slot.

        Args:
            slot_idx: 0-8 index into SLOT_NAMES.
            class_: player class string (e.g. "warrior").
            level: build level; items with lvl > level are excluded.
            tier_filter: if provided, only items whose tier is in this list are returned.
            fixed_name: if provided, return only the single named item.

        Returns:
            List of prepare_item_from_clean() results.
        """
        if slot_idx < 0 or slot_idx >= len(SLOT_NAMES):
            raise ValueError(f"slot_idx must be 0-8, got {slot_idx}")

        class_lower = class_.lower()

        # Handle fixed item
        if fixed_name is not None:
            try:
                raw = self._wynn.item(fixed_name)
            except KeyError:
                return []
            return [self._get_prepared(raw)]

        slot_type = SLOT_TYPES[slot_idx]

        # Weapon slot: type depends on class
        if slot_type is None:
            weapon_type = CLASS_WEAPON_MAP.get(class_lower)
            if weapon_type is None:
                return []
            raw_items = self._by_type.get(weapon_type, [])
            result: list[dict[str, Any]] = []
            for raw in raw_items:
                if (raw.get("lvl") or 0) > level:
                    continue
                # Verify classReq matches the resolved weapon type
                class_req = str(raw.get("classReq", "") or "").lower()
                if class_req and class_req != class_lower:
                    # Allow subclasses: warrior/fallen both use spear
                    # CLASS_WEAPON_MAP maps both sub and base class to weapon type
                    # so filter by whether classReq is in CLASS_WEAPON_MAP for any key
                    # pointing to the same weapon type
                    valid_classes = {k for k, v in CLASS_WEAPON_MAP.items() if v == weapon_type}
                    if class_req not in valid_classes:
                        continue
                if tier_filter is not None and raw.get("tier") not in tier_filter:
                    continue
                result.append(self._get_prepared(raw))
            return result

        # Armor/accessory slot
        raw_items = self._by_type.get(slot_type, [])
        result = []
        for raw in raw_items:
            if (raw.get("lvl") or 0) > level:
                continue
            if tier_filter is not None and raw.get("tier") not in tier_filter:
                continue
            result.append(self._get_prepared(raw))
        return result
