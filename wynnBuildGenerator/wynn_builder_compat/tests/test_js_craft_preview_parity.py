from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from wynn_builder_compat.craft import preview_craft

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "tools" / "export_js_fixtures" / "craft_preview_fixture.mjs"
EXPECTED_CASE_IDS = {
    "mock-chestplate",
    "mock-wand-fast",
    "real-helmet-103-105-boosters",
    "real-chestplate-103-105-boosters",
    "real-leggings-103-105-boosters",
    "real-boots-103-105-boosters",
    "real-wand-103-105-boosters",
    "real-spear-103-105-boosters",
    "real-bow-103-105-boosters",
    "real-dagger-103-105-boosters",
    "real-relik-103-105-boosters",
    "real-ring-103-105-boosters",
    "real-bracelet-103-105-boosters",
    "real-necklace-103-105-boosters",
}


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


def test_craft_preview_js_python_parity():
    fixture = load_js_fixture()
    assert {case["caseId"] for case in fixture["cases"]} == EXPECTED_CASE_IDS
    for case in fixture["cases"]:
        python_stat_map = preview_craft(
            case["input"]["recipe"],
            case["input"]["materialTiers"],
            case["input"]["ingredients"],
            attack_speed=case["input"]["attackSpeed"],
            craft_hash=case["input"]["hash"],
            rolled_ids=tuple(case["input"]["rolledIDs"]),
        )
        assert python_stat_map == case["statMap"], case["caseId"]
