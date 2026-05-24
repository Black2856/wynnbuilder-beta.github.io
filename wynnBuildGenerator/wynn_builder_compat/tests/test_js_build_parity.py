from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from wynn_builder_compat.build import build_stat_map
from wynn_builder_compat.data import WynnData, prepare_item_from_clean
from wynn_builder_compat.skillpoints import calculate_skillpoints

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "tools" / "export_js_fixtures" / "build_fixture.mjs"


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


def test_build_stat_map_js_python_parity():
    fixture = load_js_fixture()
    wynn = WynnData.from_root()

    for case in fixture["cases"]:
        inp = case["input"]
        level: int = inp["level"]
        equipment_items = [prepare_item_from_clean(wynn.item(name)) for name in inp["equipment"]]
        weapon_item = prepare_item_from_clean(wynn.item(inp["weapon"]))

        # calculate_skillpoints provides active_set_counts for set bonus application.
        # Skillpoints parity is already covered by test_js_skillpoints_parity.py.
        skp_result = calculate_skillpoints(equipment_items, weapon_item)
        active_set_counts: dict[str, int] = skp_result[4]

        stat_map = build_stat_map(equipment_items, weapon_item, level, active_set_counts, wynn.sets_data)

        js_stat = case["result"]["statMap"]
        for stat_id, js_val in js_stat.items():
            if stat_id == "atkSpd":
                py_val = weapon_item.get("atkSpd") or ""
            else:
                py_val = stat_map.get(stat_id, 0)
            assert py_val == js_val, (
                f"{case['caseId']} statMap[{stat_id!r}]: python={py_val!r} js={js_val!r}"
            )
