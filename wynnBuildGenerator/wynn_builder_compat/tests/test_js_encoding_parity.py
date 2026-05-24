from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from wynn_builder_compat.data import WynnData
from wynn_builder_compat.encoding import decode_build, encode_build

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "tools" / "export_js_fixtures" / "encode_decode_fixture.mjs"


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


def test_decode_js_encoded_build():
    """Python decode of a JS-encoded hash matches expected equipment, weapon, and level."""
    fixture = load_js_fixture()
    wynn = WynnData.from_root()

    for case in fixture["cases"]:
        inp = case["input"]
        result = decode_build(case["hash"], wynn)

        assert result["equipment"] == inp["equipment"], (
            f"{case['caseId']}: equipment mismatch\n"
            f"  python={result['equipment']}\n"
            f"  js    ={inp['equipment']}"
        )
        assert result["weapon"] == inp["weapon"], (
            f"{case['caseId']}: weapon mismatch: python={result['weapon']!r} js={inp['weapon']!r}"
        )
        assert result["level"] == inp["level"], (
            f"{case['caseId']}: level mismatch: python={result['level']} js={inp['level']}"
        )


def test_python_encode_decode_roundtrip():
    """Python encode → decode round trip preserves equipment, weapon, and level."""
    wynn = WynnData.from_root()

    equipment = [
        "Counterfeit Coronet",
        "Coal Fire",
        "Alstroemania",
        "Bleeding Soles",
        "Burning Brand",
        "Cannon Coin",
        "Excision of Trust",
        "Arbiter of Iridescence",
    ]
    weapon = "Amalgamation"
    level = 105

    hash_str = encode_build(equipment, weapon, level, wynn)
    result = decode_build(hash_str, wynn)

    assert result["equipment"] == equipment
    assert result["weapon"] == weapon
    assert result["level"] == level


def test_python_encode_decode_roundtrip_max_level():
    """Round trip at MAX_LEVEL uses the compact MAX flag and decodes correctly."""
    wynn = WynnData.from_root()

    equipment = [None] * 8
    weapon = "Amalgamation"
    level = 121  # MAX_LEVEL for version 2.2.0.31

    hash_str = encode_build(equipment, weapon, level, wynn)
    result = decode_build(hash_str, wynn)

    assert result["equipment"] == equipment
    assert result["weapon"] == weapon
    assert result["level"] == level


def test_python_encode_decode_roundtrip_partial_nulls():
    """Round trip preserves None slots (empty equipment) correctly."""
    wynn = WynnData.from_root()

    equipment = ["Counterfeit Coronet", None, None, "Bleeding Soles", None, None, None, None]
    weapon = "Amalgamation"
    level = 50

    hash_str = encode_build(equipment, weapon, level, wynn)
    result = decode_build(hash_str, wynn)

    assert result["equipment"] == equipment
    assert result["weapon"] == weapon
    assert result["level"] == level
