"""Python port targets for js/damage_calc.js."""

from __future__ import annotations

from typing import Any

from .build_utils import ATTACK_SPEEDS, BASE_DAMAGE_MULTIPLIER

DAMAGE_KEYS = ("nDam", "eDam", "tDam", "wDam", "fDam", "aDam")


def get_base_dps(item: Any) -> float | list[float]:
    """Partial port of js/damage_calc.js::get_base_dps."""
    atk_spd = item.get("atkSpd")
    attack_speed_mult = BASE_DAMAGE_MULTIPLIER[ATTACK_SPEEDS.index(atk_spd)]
    if item.get("tier") != "Crafted":
        total_damage = 0
        for damage_key in DAMAGE_KEYS:
            damages = item.get(damage_key)
            total_damage += damages[0] + damages[1]
        return total_damage * attack_speed_mult / 2

    total_damage_min = 0
    total_damage_max = 0
    for damage_key in DAMAGE_KEYS:
        damages = item.get(damage_key)
        total_damage_min += damages[0][0] + damages[0][1]
        total_damage_max += damages[1][0] + damages[1][1]
    return [attack_speed_mult * total_damage_min / 2, attack_speed_mult * total_damage_max / 2]


def calculate_spell_damage(*_args: Any, **_kwargs: Any) -> Any:
    """Placeholder for js/damage_calc.js::calculateSpellDamage."""
    raise NotImplementedError("calculate_spell_damage requires damage parity fixtures before implementation")

