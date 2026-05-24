from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from wynn_builder_compat.skillpoints import calculate_skillpoints

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "tools" / "export_js_fixtures" / "skillpoints_fixture.mjs"


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


def test_calculate_skillpoints_js_python_parity():
    fixture = load_js_fixture()
    assert {case["caseId"] for case in fixture["cases"]} == {
        "base-nine-equipment",
        "crafted-skillpoints-deferred",
        "real-clean-json-equipment",
    }
    for case in fixture["cases"]:
        result = calculate_skillpoints(case["input"]["equipment"], case["input"]["weapon"])
        python_result = {
            "bestOrder": [item["name"] for item in result[0]],
            "bestSkillpoints": result[1],
            "finalSkillpoints": result[2],
            "bestTotal": result[3],
            "bestActiveSetCounts": result[4],
            "totalItemSkillpoints": result[5],
        }
        assert python_result == case["result"], case["caseId"]
