"""Python port targets for crafted item preview logic from js/craft.js."""

from __future__ import annotations

import math
from typing import Any

GRID_ROWS = 3
GRID_COLS = 2
MATERIAL_TIER_MULTIPLIERS = (0, 1, 1.25, 1.4)
SKP_ORDER = ("str", "dex", "int", "def", "agi")
SKP_ELEMENTS = ("e", "t", "w", "f", "a")
ARMOR_TYPES = {"helmet", "chestplate", "leggings", "boots"}
WEAPON_TYPES = {"wand", "spear", "bow", "dagger", "relik"}
ACCESSORY_TYPES = {"ring", "bracelet", "necklace"}
CONSUMABLE_TYPES = {"potion", "scroll", "food"}
DEFAULT_ROLLED_IDS = ("rawSpellDamage", "rawHealth", "str", "dex", "int", "def", "agi")


def material_multiplier(material_amounts: list[float], material_tiers: list[int]) -> float:
    """Weighted material tier multiplier from js/craft.js."""
    if len(material_amounts) != len(material_tiers):
        raise ValueError("material_amounts and material_tiers must have the same length")
    total_amount = sum(material_amounts)
    if total_amount == 0:
        return 1.0
    weighted = 0.0
    for amount, tier in zip(material_amounts, material_tiers, strict=True):
        weighted += amount * MATERIAL_TIER_MULTIPLIERS[tier]
    return weighted / total_amount


def ingredient_effectiveness_grid(position_modifiers: list[dict[str, float]]) -> list[list[float]]:
    """Port of js/craft.js ingredient effectiveness grid calculation.

    The crafting grid is 3 rows by 2 columns. Input order is the same flattened
    order used by Wynnbuilder: row-major, six ingredient slots maximum.
    """
    if len(position_modifiers) > GRID_ROWS * GRID_COLS:
        raise ValueError("at most six ingredient position modifier maps are supported")

    eff = [[100.0, 100.0], [100.0, 100.0], [100.0, 100.0]]
    for n, pos_mods in enumerate(position_modifiers):
        row = n // GRID_COLS
        col = n % GRID_COLS
        for key, value in pos_mods.items():
            if value == 0:
                continue
            if key == "above":
                for target_row in range(row - 1, -1, -1):
                    eff[target_row][col] += value
            elif key == "under":
                for target_row in range(row + 1, GRID_ROWS):
                    eff[target_row][col] += value
            elif key == "left":
                if col == 1:
                    eff[row][col - 1] += value
            elif key == "right":
                if col == 0:
                    eff[row][col + 1] += value
            elif key == "touching":
                for target_row in range(GRID_ROWS):
                    for target_col in range(GRID_COLS):
                        if (
                            abs(target_row - row) == 1
                            and abs(target_col - col) == 0
                        ) or (
                            abs(target_row - row) == 0
                            and abs(target_col - col) == 1
                        ):
                            eff[target_row][target_col] += value
            elif key == "notTouching":
                for target_row in range(GRID_ROWS):
                    for target_col in range(GRID_COLS):
                        if (
                            abs(target_row - row) > 1
                            or (
                                abs(target_row - row) == 1
                                and abs(target_col - col) == 1
                            )
                        ):
                            eff[target_row][target_col] += value
            else:
                raise ValueError(f"unknown position modifier: {key}")
    return eff


def ingredient_effectiveness_flat(position_modifiers: list[dict[str, float]]) -> list[float]:
    """Return the row-major flattened effectiveness used as ingredEffectiveness."""
    return [value for row in ingredient_effectiveness_grid(position_modifiers) for value in row]


def js_round(value: float) -> int:
    """Match JavaScript Math.round for craft formulas."""
    return math.floor(value + 0.5)


def js_to_fixed_number(value: float, digits: int) -> float:
    """Return a numeric value after JavaScript-style toFixed(digits)."""
    return float(f"{value:.{digits}f}")


def apply_item_ids(
    stat_values: dict[str, float],
    durability: list[float],
    item_ids_by_ingredient: list[dict[str, float]],
    effectiveness_flat: list[float],
    *,
    item_is_powder: list[bool] | None = None,
    is_consumable: bool = False,
) -> tuple[dict[str, float], list[float]]:
    """Port the itemIDs application block from js/craft.js.

    Non-durability itemIDs are affected by ingredient effectiveness unless the
    ingredient is a powder. `dura` modifies durability directly and is not
    affected by effectiveness. Consumables never receive item requirements.
    """
    values = dict(stat_values)
    durability_values = list(durability)
    powder_flags = item_is_powder or [False] * len(item_ids_by_ingredient)
    for index, item_ids in enumerate(item_ids_by_ingredient):
        eff_mult = js_to_fixed_number(effectiveness_flat[index] / 100, 2)
        is_powder = powder_flags[index] if index < len(powder_flags) else False
        for key, value in item_ids.items():
            if key != "dura" and not is_consumable:
                current = values.get(key, 0)
                if not is_powder:
                    values[key] = js_round(current + value * eff_mult)
                else:
                    values[key] = js_round(current + value)
            else:
                durability_values = [entry + value for entry in durability_values]
    return values, durability_values


def apply_rolled_ids(
    min_rolls: dict[str, float],
    max_rolls: dict[str, float],
    rolled_ids_by_ingredient: list[dict[str, tuple[float, float]]],
    effectiveness_flat: list[float],
) -> tuple[dict[str, int], dict[str, int]]:
    """Port the rolled ID application block from js/craft.js.

    Each ingredient supplies min/max rolls. Both are multiplied by the
    effectiveness multiplier rounded via `toFixed(2)`, floored, sorted, then
    accumulated into output minRolls/maxRolls.
    """
    mins = dict(min_rolls)
    maxes = dict(max_rolls)
    for index, rolled_ids in enumerate(rolled_ids_by_ingredient):
        eff_mult = js_to_fixed_number(effectiveness_flat[index] / 100, 2)
        for key, (min_value, max_value) in rolled_ids.items():
            if not max_value:
                continue
            rolls = sorted((math.floor(min_value * eff_mult), math.floor(max_value * eff_mult)))
            mins[key] = mins.get(key, 0) + rolls[0]
            maxes[key] = maxes.get(key, 0) + rolls[1]
    return mins, maxes


def apply_consumable_ids(
    stat_values: dict[str, Any],
    consumable_ids_by_ingredient: list[dict[str, float]],
) -> dict[str, Any]:
    """Port the consumableIDs application block from js/craft.js.

    The JS code applies this block for every crafted item category. A `dura`
    consumable ID modifies `duration`; other IDs are set from `charges + value`.
    """
    values = dict(stat_values)
    for consumable_ids in consumable_ids_by_ingredient:
        for key, value in consumable_ids.items():
            if key == "dura":
                values["duration"] = [entry + value for entry in values["duration"]]
            else:
                values[key] = values.get("charges", 0) + value
    return values


def finalize_durability(durability: list[float]) -> tuple[list[int], float | None]:
    """Port final durability floor/missingDurability behavior from js/craft.js."""
    values: list[int] = []
    missing = None
    for entry in durability:
        if entry < 1:
            missing = entry
            values.append(0)
        else:
            values.append(math.floor(entry))
    return values, missing


def apply_weapon_base_damage(stat_map: dict[str, Any], low: float, high: float, matmult: float, attack_speed: str) -> None:
    """Port the weapon damage base section from js/craft.js.

    Powder-as-ingredient conversion is intentionally not included yet because the
    corresponding JS block is commented out in the current source.
    """
    ratio = 2.05
    if attack_speed == "SLOW":
        ratio /= 1.5
    elif attack_speed == "NORMAL":
        ratio = 1
    elif attack_speed == "FAST":
        ratio /= 2.5

    n_dam_base_low = math.floor(low * matmult)
    n_dam_base_high = math.floor(high * matmult)
    n_dam_base_low = math.floor(n_dam_base_low * ratio)
    n_dam_base_high = math.floor(n_dam_base_high * ratio)
    elem_dam_base_low = [0, 0, 0, 0, 0]
    elem_dam_base_high = [0, 0, 0, 0, 0]

    stat_map["ingredPowders"] = []

    low1 = math.floor(n_dam_base_low * 0.9)
    low2 = math.floor(n_dam_base_low * 1.1)
    high1 = math.floor(n_dam_base_high * 0.9)
    high2 = math.floor(n_dam_base_high * 1.1)
    stat_map["nDamBaseLow"] = n_dam_base_low
    stat_map["nDamBaseHigh"] = n_dam_base_high
    stat_map["nDamLow"] = f"{low1}-{low2}"
    stat_map["nDam"] = f"{high1}-{high2}"

    for index, element in enumerate(SKP_ELEMENTS):
        stat_map[f"{element}DamBaseLow"] = elem_dam_base_low[index]
        stat_map[f"{element}DamBaseHigh"] = elem_dam_base_high[index]
        low1 = math.floor(elem_dam_base_low[index] * 0.9)
        low2 = math.floor(elem_dam_base_low[index] * 1.1)
        high1 = math.floor(elem_dam_base_high[index] * 0.9)
        high2 = math.floor(elem_dam_base_high[index] * 1.1)
        stat_map[f"{element}DamLow"] = f"{low1}-{low2}"
        stat_map[f"{element}Dam"] = f"{high1}-{high2}"


def preview_craft(
    recipe: dict[str, Any],
    material_tiers: list[int],
    ingredients: list[dict[str, Any]],
    *,
    attack_speed: str = "NORMAL",
    craft_hash: str = "mock",
    rolled_ids: tuple[str, ...] = DEFAULT_ROLLED_IDS,
) -> dict[str, Any]:
    """Partial port of js/craft.js::Craft statMap construction.

    This currently covers armor/accessory/weapon mock fixtures without powder
    mechanics. Unsupported branches raise NotImplementedError instead of
    silently diverging from Wynnbuilder.
    """
    craft_type = str(recipe["type"]).lower()
    stat_map: dict[str, Any] = {
        "minRolls": {},
        "maxRolls": {},
        "name": f"CR-{craft_hash}",
        "displayName": f"CR-{craft_hash}",
        "tier": "Crafted",
        "type": craft_type,
        "duration": list(recipe.get("duration", [0, 0])),
        "durability": list(recipe.get("durability", [0, 0])),
        "lvl": recipe["lvl"][1],
        "lvlLow": recipe["lvl"][0],
        "nDam": 0,
        "hp": 0,
        "hpLow": 0,
        "powders": [],
        "hash": f"CR-{craft_hash}",
    }
    for element in SKP_ELEMENTS:
        stat_map[f"{element}Dam"] = "0-0"
        stat_map[f"{element}Def"] = 0
    for skill in SKP_ORDER:
        stat_map[f"{skill}Req"] = 0
        stat_map[skill] = 0

    if craft_type in ARMOR_TYPES or craft_type in WEAPON_TYPES:
        stat_map["category"] = "weapon"
        low_level = recipe["lvl"][0]
        stat_map["slots"] = 1 if low_level < 30 else 2 if low_level < 70 else 3
    else:
        stat_map["slots"] = 0

    if craft_type in CONSUMABLE_TYPES:
        raise NotImplementedError("consumable craft preview is not ported yet")
    stat_map["charges"] = 0

    if craft_type in ARMOR_TYPES:
        stat_map["hp"] = "-".join(str(value) for value in recipe["healthOrDamage"])
        stat_map["category"] = "armor"
    elif craft_type in WEAPON_TYPES:
        stat_map["nDam"] = "-".join(str(value) for value in recipe["healthOrDamage"])
        for element in SKP_ELEMENTS:
            stat_map[f"{element}Dam"] = "0-0"
            stat_map[f"{element}DamLow"] = "0-0"
        stat_map["category"] = "weapon"
        stat_map["atkSpd"] = attack_speed
    elif craft_type in ACCESSORY_TYPES:
        stat_map["category"] = "accessory"

    amounts = [material["amount"] for material in recipe["materials"]]
    matmult = material_multiplier(amounts, material_tiers)
    low, high = recipe["healthOrDamage"]

    if stat_map["category"] == "armor":
        stat_map["durability"] = [js_round(value * matmult) for value in stat_map["durability"]]
        low = math.floor(low * matmult)
        high = math.floor(high * matmult)
        stat_map["hp"] = high
        stat_map["hpLow"] = low
    elif stat_map["category"] == "weapon":
        stat_map["durability"] = [js_round(value * matmult) for value in stat_map["durability"]]
        apply_weapon_base_damage(stat_map, low, high, matmult, attack_speed)
    elif stat_map["category"] == "accessory":
        stat_map["durability"] = [js_round(value * matmult) for value in stat_map["durability"]]

    position_modifiers = [ingredient.get("posMods", {}) for ingredient in ingredients]
    effectiveness = ingredient_effectiveness_flat(position_modifiers)
    stat_map["ingredEffectiveness"] = effectiveness

    item_ids = [ingredient.get("itemIDs", {}) for ingredient in ingredients]
    is_powder = [bool(ingredient.get("isPowder", False)) for ingredient in ingredients]
    item_values, durability = apply_item_ids(
        {key: value for key, value in stat_map.items() if isinstance(value, (int, float))},
        stat_map["durability"],
        item_ids,
        effectiveness,
        item_is_powder=is_powder,
        is_consumable=craft_type in CONSUMABLE_TYPES,
    )
    for key, value in item_values.items():
        stat_map[key] = value
    stat_map["durability"] = durability

    consumable_ids = [ingredient.get("consumableIDs", {}) for ingredient in ingredients]
    stat_map.update(apply_consumable_ids(stat_map, consumable_ids))

    rolled_by_ingredient = [
        {
            key: tuple(value)
            for key, value in ingredient.get("rolledIDs", {}).items()
        }
        for ingredient in ingredients
    ]
    min_rolls, max_rolls = apply_rolled_ids(stat_map["minRolls"], stat_map["maxRolls"], rolled_by_ingredient, effectiveness)
    stat_map["minRolls"] = min_rolls
    stat_map["maxRolls"] = max_rolls

    stat_map["durability"], missing_durability = finalize_durability(stat_map["durability"])
    if missing_durability is not None:
        stat_map["missingDurability"] = missing_durability

    if "charges" in stat_map and stat_map["charges"] < 1:
        stat_map["charges"] = 1

    stat_map["reqs"] = [0, 0, 0, 0, 0]
    stat_map["skillpoints"] = [0, 0, 0, 0, 0]
    for index, skill in enumerate(SKP_ORDER):
        value = stat_map["maxRolls"].get(skill, 0)
        stat_map[skill] = value
        stat_map["skillpoints"][index] = value
        stat_map["reqs"][index] = stat_map.get(f"{skill}Req", 0) if craft_type not in CONSUMABLE_TYPES else 0

    for rolled_id in rolled_ids:
        stat_map["minRolls"].setdefault(rolled_id, 0)
        stat_map["maxRolls"].setdefault(rolled_id, 0)

    stat_map["crafted"] = True
    return stat_map
