from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from wynn_builder_compat.build_utils import (
    ATTACK_SPEEDS,
    BASE_DAMAGE_MULTIPLIER,
    SKILLPOINT_DAMAGE_MULT,
    SKILLPOINT_FINAL_MULT,
    SKP_ELEMENTS,
    SKP_ORDER,
    level_to_hp_base,
    level_to_skill_points,
    skill_points_to_percentage,
)

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "tools" / "export_js_fixtures" / "build_utils_fixture.mjs"


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


def test_build_utils_js_python_parity():
    fixture = load_js_fixture()

    for case in fixture["levelToSkillPoints"]:
        assert level_to_skill_points(case["input"]) == case["output"]

    for case in fixture["levelToHPBase"]:
        assert level_to_hp_base(case["input"]) == case["output"]

    for case in fixture["skillPointsToPercentage"]:
        assert skill_points_to_percentage(case["input"]) == pytest.approx(case["output"], abs=1e-12)

    constants = fixture["constants"]
    assert list(SKP_ORDER) == constants["skpOrder"]
    assert list(SKP_ELEMENTS) == constants["skpElements"]
    assert list(ATTACK_SPEEDS) == constants["attackSpeeds"]
    assert list(BASE_DAMAGE_MULTIPLIER) == constants["baseDamageMultiplier"]
    assert list(SKILLPOINT_DAMAGE_MULT) == constants["skillpointDamageMult"]
    assert list(SKILLPOINT_FINAL_MULT) == pytest.approx(constants["skillpointFinalMult"], abs=1e-12)
