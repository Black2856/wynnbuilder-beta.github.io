"""Python port targets for js/builder/build.js."""

from __future__ import annotations

from typing import Any

from .build_utils import SKP_ORDER, level_to_hp_base, level_to_skill_points

# From js/builder/build.js::Build.initBuildStats (BUILD_STATIC_IDS)
STATIC_IDS: tuple[str, ...] = (
    "hp", "eDef", "tDef", "wDef", "fDef", "aDef",
    "str", "dex", "int", "def", "agi",
    "damMobs", "defMobs",
)
_STATIC_IDS_SET: frozenset[str] = frozenset(STATIC_IDS)

# From js/builder/build.js::Build.initBuildStats (BUILD_MUST_IDS)
MUST_IDS: tuple[str, ...] = (
    "eMdPct", "eMdRaw", "eSdPct", "eSdRaw", "eDamPct", "eDamRaw", "eDamAddMin", "eDamAddMax",
    "tMdPct", "tMdRaw", "tSdPct", "tSdRaw", "tDamPct", "tDamRaw", "tDamAddMin", "tDamAddMax",
    "wMdPct", "wMdRaw", "wSdPct", "wSdRaw", "wDamPct", "wDamRaw", "wDamAddMin", "wDamAddMax",
    "fMdPct", "fMdRaw", "fSdPct", "fSdRaw", "fDamPct", "fDamRaw", "fDamAddMin", "fDamAddMax",
    "aMdPct", "aMdRaw", "aSdPct", "aSdRaw", "aDamPct", "aDamRaw", "aDamAddMin", "aDamAddMax",
    "nMdPct", "nMdRaw", "nSdPct", "nSdRaw", "nDamPct", "nDamRaw", "nDamAddMin", "nDamAddMax",
    "mdPct", "mdRaw", "sdPct", "sdRaw", "damPct", "damRaw", "damAddMin", "damAddMax",
    "rMdPct", "rMdRaw", "rSdPct", "rSdRaw", "rDamPct", "rDamRaw", "rDamAddMin", "rDamAddMax",
    "healPct", "critDamPct",
)

CLASS_DEFENSE_MULTIPLIERS = {
    "relik": 0.60,
    "bow": 0.70,
    "wand": 0.80,
    "dagger": 1.0,
    "spear": 1.0,
}


def clamp_level(level: int) -> int:
    if level < 1:
        return 1
    if level > 121:
        return 121
    return level


def initial_stat_map(level: int) -> dict[str, Any]:
    """Initial stat map values from js/builder/build.js::Build.initBuildStats."""
    stat_map: dict[str, Any] = {k: 0 for k in STATIC_IDS}
    stat_map.update({k: 0 for k in MUST_IDS})
    stat_map["hp"] = level_to_hp_base(level)
    stat_map["agiDef"] = 90
    stat_map["damMult"] = {"tome": 0}
    stat_map["defMult"] = {"tome": 0}
    stat_map["activeMajorIDs"] = set()
    stat_map["poisonPct"] = 0
    stat_map["healMult"] = {"item": 0}
    return stat_map


def build_stat_map(
    equipment: list[dict[str, Any]],
    weapon: dict[str, Any],
    level: int,
    active_set_counts: dict[str, int] | None = None,
    sets_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Port of js/builder/build.js::Build.initBuildStats.

    Accepts lists of expand_item() results (equipment + weapon) and aggregates stats.
    active_set_counts comes from calculate_skillpoints() result[4].
    """
    stat_map: dict[str, Any] = {k: 0 for k in STATIC_IDS}
    stat_map.update({k: 0 for k in MUST_IDS})
    stat_map["hp"] = level_to_hp_base(level)
    stat_map["agiDef"] = 90

    major_ids: set[str] = set()
    all_items = list(equipment) + [weapon]

    for item_stats in all_items:
        max_rolls: dict[str, Any] = item_stats.get("maxRolls") or {}
        for stat_id, value in max_rolls.items():
            if stat_id in _STATIC_IDS_SET:
                continue
            stat_map[stat_id] = (stat_map.get(stat_id) or 0) + value
        for static_id in STATIC_IDS:
            v = item_stats.get(static_id)
            if v:
                stat_map[static_id] = stat_map[static_id] + v
        item_major_ids = item_stats.get("majorIds")
        if item_major_ids:
            for mid in item_major_ids:
                major_ids.add(mid)

    stat_map["damMult"] = {"tome": stat_map.get("damMobs", 0)}
    stat_map["defMult"] = {"tome": stat_map.get("defMobs", 0)}
    stat_map["activeMajorIDs"] = major_ids

    if active_set_counts and sets_data:
        for set_name, count in active_set_counts.items():
            set_def = sets_data.get(set_name)
            if not set_def:
                continue
            bonuses = set_def.get("bonuses", [])
            if count < 1 or count > len(bonuses):
                continue
            bonus = bonuses[count - 1]
            for stat_id, value in bonus.items():
                if stat_id in SKP_ORDER:
                    continue
                stat_map[stat_id] = (stat_map.get(stat_id) or 0) + value

    stat_map["poisonPct"] = 0
    stat_map["healMult"] = {"item": stat_map.get("healPct", 0)}
    return stat_map


def available_skillpoints(level: int) -> int:
    return level_to_skill_points(clamp_level(level))

