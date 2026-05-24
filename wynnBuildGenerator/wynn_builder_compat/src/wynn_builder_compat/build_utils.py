"""Ports of low-risk constants and helpers from js/build_utils.js."""

from __future__ import annotations

import math
from typing import Any

SKP_ORDER = ("str", "dex", "int", "def", "agi")
SKILL_NAMES = ("Strength", "Dexterity", "Intelligence", "Defense", "Agility")
SKP_ELEMENTS = ("e", "t", "w", "f", "a")
DAMAGE_CLASSES = ("Neutral", "Earth", "Thunder", "Water", "Fire", "Air")
ATTACK_SPEEDS = (
    "SUPER_SLOW",
    "VERY_SLOW",
    "SLOW",
    "NORMAL",
    "FAST",
    "VERY_FAST",
    "SUPER_FAST",
)
BASE_DAMAGE_MULTIPLIER = (0.51, 0.83, 1.5, 2.05, 2.5, 3.1, 4.3)
SKILLPOINT_DAMAGE_MULT = (1, 1, 1, 0.867, 0.951)


def skill_points_to_percentage(skp: float) -> float:
    """Port of js/build_utils.js::skillPointsToPercentage."""
    if skp <= 0:
        return 0.0
    if skp >= 150:
        skp = 150
    r = 0.9908
    return (r / (1 - r) * (1 - math.pow(r, skp))) / 100.0


SKILLPOINT_FINAL_MULT = (
    1,
    1,
    0.5 / skill_points_to_percentage(150),
    0.867,
    0.951,
)


def level_to_skill_points(level: int) -> int:
    """Port of js/build_utils.js::levelToSkillPoints."""
    if level < 1:
        return 0
    if level >= 101:
        return 200
    return (level - 1) * 2


def level_to_hp_base(level: int) -> int:
    """Port of js/build_utils.js::levelToHPBase."""
    if level < 1:
        return level_to_hp_base(1)
    if level > 121:
        return level_to_hp_base(121)
    return 5 * level + 5


# IDs whose values are NOT rolled (copied directly from item into expanded map).
NON_ROLLED_IDS: tuple[str, ...] = (
    "name", "lore", "displayName", "tier", "set", "slots", "type", "material",
    "drop", "quest", "restrict", "nDam", "fDam", "wDam", "aDam", "tDam", "eDam",
    "atkSpd", "hp", "fDef", "wDef", "aDef", "tDef", "eDef", "lvl", "classReq",
    "strReq", "dexReq", "intReq", "defReq", "agiReq", "str", "dex", "int", "agi", "def",
    "fixID", "category", "id", "skillpoints", "reqs",
    "nDam_", "fDam_", "wDam_", "aDam_", "tDam_", "eDam_",
    "majorIds", "damMobs", "defMobs",
)

# IDs with min/max rolls in expandItem (comments stripped; wynn2 duplicates excluded).
ROLLED_IDS: tuple[str, ...] = (
    "hprPct", "mr", "sdPct", "mdPct", "ls", "ms", "xpb", "lb", "ref",
    "thorns", "expd", "spd", "atkTier", "poison", "hpBonus", "spRegen", "eSteal",
    "hprRaw", "sdRaw", "mdRaw",
    "fDamPct", "wDamPct", "aDamPct", "tDamPct", "eDamPct",
    "fDefPct", "wDefPct", "aDefPct", "tDefPct", "eDefPct",
    "spPct1", "spRaw1", "spPct2", "spRaw2", "spPct3", "spRaw3", "spPct4", "spRaw4",
    "rSdRaw", "sprint", "sprintReg", "jh", "lq", "gXp", "gSpd",
    # wynn2 (eDamPct/tDamPct/wDamPct/fDamPct/aDamPct/mdPct/mdRaw/sdPct/sdRaw/rSdRaw already above)
    "eMdPct", "eMdRaw", "eSdPct", "eSdRaw", "eDamRaw", "eDamAddMin", "eDamAddMax",
    "tMdPct", "tMdRaw", "tSdPct", "tSdRaw", "tDamRaw", "tDamAddMin", "tDamAddMax",
    "wMdPct", "wMdRaw", "wSdPct", "wSdRaw", "wDamRaw", "wDamAddMin", "wDamAddMax",
    "fMdPct", "fMdRaw", "fSdPct", "fSdRaw", "fDamRaw", "fDamAddMin", "fDamAddMax",
    "aMdPct", "aMdRaw", "aSdPct", "aSdRaw", "aDamRaw", "aDamAddMin", "aDamAddMax",
    "nMdPct", "nMdRaw", "nSdPct", "nSdRaw", "nDamPct", "nDamRaw", "nDamAddMin", "nDamAddMax",
    "damPct", "damRaw", "damAddMin", "damAddMax",
    "rMdPct", "rMdRaw", "rSdPct", "rDamPct", "rDamRaw", "rDamAddMin", "rDamAddMax",
    "critDamPct",
    "spPct1Final", "spPct2Final", "spPct3Final", "spPct4Final",
    "healPct", "kb", "weakenEnemy", "slowEnemy", "rDefPct", "maxMana",
    "mainAttackRange",
)

# Spell cost IDs where a negative value is beneficial (inverts the positive/negative roll direction).
REVERSED_IDS: frozenset[str] = frozenset(
    ("spPct1", "spRaw1", "spPct2", "spRaw2", "spPct3", "spRaw3", "spPct4", "spRaw4")
)


def id_round(val: float) -> int:
    """Port of js/build_utils.js::idRound.

    Uses floor(val + 0.5) to match JS Math.round (rounds half toward +inf, not banker's rounding).
    Returns sign(val) instead of 0 to preserve direction for tiny non-zero values.
    """
    r = math.floor(val + 0.5)
    if r == 0:
        return int(math.copysign(1, val)) if val != 0 else 0
    return r


def expand_item(item: dict[str, Any]) -> dict[str, Any]:
    """Port of js/build_utils.js::expandItem.

    Converts a raw clean.json item dict into an expanded map with minRolls/maxRolls dicts.
    The item should have skillpoints/reqs/majorIds pre-populated (see prepare_item_from_clean).
    """
    min_rolls: dict[str, int] = {}
    max_rolls: dict[str, int] = {}
    expanded: dict[str, Any] = {}

    if item.get("fixID"):
        expanded["fixID"] = True
        for stat_id in ROLLED_IDS:
            val = item.get(stat_id) or 0
            min_rolls[stat_id] = val
            max_rolls[stat_id] = val
    else:
        for stat_id in ROLLED_IDS:
            val = item.get(stat_id) or 0
            if isinstance(val, dict) and val.get("static"):
                max_rolls[stat_id] = val["raw"]
                min_rolls[stat_id] = val["raw"]
            elif val == 0:
                max_rolls[stat_id] = 0
                min_rolls[stat_id] = 0
            elif (val > 0) != (stat_id in REVERSED_IDS):
                max_rolls[stat_id] = id_round(val * 1.3)
                min_rolls[stat_id] = id_round(val * 0.3)
            else:
                max_rolls[stat_id] = id_round(val * 0.7)
                min_rolls[stat_id] = id_round(val * 1.3)

    for stat_id in NON_ROLLED_IDS:
        expanded[stat_id] = item.get(stat_id)

    expanded["minRolls"] = min_rolls
    expanded["maxRolls"] = max_rolls
    return expanded

