from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from wynn_builder_compat.craft import (
    apply_consumable_ids,
    apply_item_ids,
    apply_rolled_ids,
    ingredient_effectiveness_flat,
    ingredient_effectiveness_grid,
    material_multiplier,
)

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "tools" / "export_js_fixtures" / "craft_effectiveness_fixture.mjs"


def load_js_fixture() -> dict:
    if shutil.which("node") is None:
        pytest.skip("Node.js is required for JS/Python parity fixture export")
    completed = subprocess.run(
        ["node", str(EXPORTER)],
        cwd=ROOT.parent,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def test_craft_material_multiplier_js_python_parity():
    fixture = load_js_fixture()
    for case in fixture["materialMultipliers"]:
        assert material_multiplier(case["amounts"], case["tiers"]) == pytest.approx(case["output"], abs=1e-12)


def test_craft_effectiveness_grid_js_python_parity():
    fixture = load_js_fixture()
    for case in fixture["effectiveness"]:
        assert ingredient_effectiveness_grid(case["positionModifiers"]) == case["output"], case["caseId"]
        assert ingredient_effectiveness_flat(case["positionModifiers"]) == case["flat"], case["caseId"]


def test_craft_item_id_application_js_python_parity():
    fixture = load_js_fixture()
    for case in fixture["itemIdApplication"]:
        values, durability = apply_item_ids(
            case["statValues"],
            case["durability"],
            case["itemIdsByIngredient"],
            case["effectivenessFlat"],
            item_is_powder=case["itemIsPowder"],
            is_consumable=case["isConsumable"],
        )
        assert {"values": values, "durability": durability} == case["output"], case["caseId"]


def test_craft_rolled_id_application_js_python_parity():
    fixture = load_js_fixture()
    for case in fixture["rolledIdApplication"]:
        min_rolls, max_rolls = apply_rolled_ids(
            case["minRolls"],
            case["maxRolls"],
            [
                {
                    key: tuple(value)
                    for key, value in rolled_ids.items()
                }
                for rolled_ids in case["rolledIdsByIngredient"]
            ],
            case["effectivenessFlat"],
        )
        assert {"minRolls": min_rolls, "maxRolls": max_rolls} == case["output"], case["caseId"]


def test_craft_consumable_id_application_matches_js_duration_behavior():
    result = apply_consumable_ids(
        {"duration": [0, 0], "charges": 1},
        [{"dura": 120}, {"charges": 2}],
    )
    assert result["duration"] == [120, 120]
    assert result["charges"] == 3
