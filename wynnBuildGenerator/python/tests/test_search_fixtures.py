"""Precision and accuracy tests using fixtures from docs/search_fixtures/.

Tests are parameterized over fixture files and run the full search pipeline
(beam search + final evaluation) to verify correctness guarantees.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from wynn_builder_compat.data import WynnData, prepare_item_from_clean
from search.item_index import ItemIndex, SLOT_NAMES
from search.numpy_evaluator import NumpyEvaluator
from search.beam_search import beam_search
from search.final_evaluator import evaluate_single, BuildResult

# ---------------------------------------------------------------------------
# Shared fixtures (pytest fixtures, not search fixtures)
# ---------------------------------------------------------------------------

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "docs" / "search_fixtures"


@pytest.fixture(scope="module")
def wynn() -> WynnData:
    return WynnData.from_root()


@pytest.fixture(scope="module")
def item_index(wynn: WynnData) -> ItemIndex:
    return ItemIndex(wynn)


@pytest.fixture(scope="module")
def evaluator(wynn: WynnData) -> NumpyEvaluator:
    all_prepared = [prepare_item_from_clean(item) for item in wynn.items]
    return NumpyEvaluator(all_prepared)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_search(
    inp: dict[str, Any],
    wynn: WynnData,
    item_index: ItemIndex,
    evaluator: NumpyEvaluator,
) -> list[BuildResult]:
    """Run beam search + final evaluation from a fixture input dict."""
    class_ = inp["class"]
    level = int(inp["level"])
    conditions = inp.get("conditions", [])
    scoring = inp.get("scoring", {})
    fixed_items_names = inp.get("fixed_items", {})
    params = inp.get("search_params", {})

    beam_width = int(params.get("beam_width", 50))
    max_per_slot = int(params.get("max_candidates_per_slot", 40))
    result_limit = int(params.get("result_limit", 10))

    # Resolve fixed items to slot indices
    fixed_slot_idx: dict[int, str | None] = {}
    for slot_name, item_name in fixed_items_names.items():
        if slot_name in SLOT_NAMES:
            fixed_slot_idx[SLOT_NAMES.index(slot_name)] = item_name

    # Build slot candidates
    slot_candidates: list[list[dict[str, Any]]] = []
    for slot_idx in range(9):
        fixed_name = fixed_slot_idx.get(slot_idx, ...)
        if fixed_name is ...:
            candidates = item_index.candidates_for_slot(slot_idx, class_, level)[:max_per_slot]
        else:
            candidates = item_index.candidates_for_slot(slot_idx, class_, level, fixed_name=fixed_name)
        slot_candidates.append(candidates)

    # Beam search
    beam_results = beam_search(slot_candidates, fixed_slot_idx, beam_width, evaluator, scoring, conditions)

    # Final evaluation
    results: list[BuildResult] = []
    for item_names in beam_results[:result_limit * 3]:
        try:
            r = evaluate_single(item_names, level, wynn, scoring, conditions)
            if r.conditions_met:
                results.append(r)
        except Exception:
            pass

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:result_limit]


def _check_expect(results: list[BuildResult], expect: dict[str, Any], inp: dict[str, Any]) -> None:
    min_results = expect.get("min_results")
    max_results = expect.get("max_results")

    if min_results is not None:
        assert len(results) >= min_results, (
            f"Expected at least {min_results} results, got {len(results)}"
        )

    if max_results is not None:
        assert len(results) <= max_results, (
            f"Expected at most {max_results} results, got {len(results)}"
        )

    if expect.get("score_descending") and len(results) > 1:
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score, (
                f"Score not descending at index {i}: {results[i].score} < {results[i+1].score}"
            )

    if expect.get("conditions_satisfied"):
        conditions = inp.get("conditions", [])
        if conditions:
            for r in results:
                assert r.conditions_met, (
                    f"Build does not satisfy conditions: {r.equipment_names}"
                )

    # Stat constraint check
    stat_constraint = expect.get("stat_constraint", {})
    for stat_key, constraint in stat_constraint.items():
        op = constraint["op"]
        threshold = float(constraint["value"])
        for r in results:
            actual = float(r.stat_map.get(stat_key, 0))
            if op == ">=":
                assert actual >= threshold, (
                    f"stat {stat_key}={actual} does not satisfy >= {threshold} "
                    f"for build {r.equipment_names}"
                )
            elif op == "<=":
                assert actual <= threshold, (
                    f"stat {stat_key}={actual} does not satisfy <= {threshold} "
                    f"for build {r.equipment_names}"
                )

    # Required builds (slot-specific checks)
    for req in expect.get("required_builds", []):
        n = req.get("must_appear_in_top_n", 10)
        top_n = results[:n]
        matched = False
        for r in top_n:
            build_ok = True
            for key, value in req.items():
                if key.startswith("equipment_slot_"):
                    slot_idx = int(key.split("_")[-1])
                    if slot_idx < 8:
                        if r.equipment_names[slot_idx] != value:
                            build_ok = False
                            break
                    elif slot_idx == 8:
                        if r.weapon_name != value:
                            build_ok = False
                            break
                elif key == "equipment":
                    eq_list = [v for v in value if v is not None]
                    for eq_item in eq_list:
                        if eq_item not in r.equipment_names:
                            build_ok = False
                            break
            if build_ok:
                matched = True
                break
        assert matched, (
            f"Required build {req} not found in top {n} results. "
            f"Got: {[(r.equipment_names, r.weapon_name) for r in top_n]}"
        )


# ---------------------------------------------------------------------------
# Parameterized tests by fixture file
# ---------------------------------------------------------------------------

def _load_single_fixture(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("fixture_path", sorted(_FIXTURE_DIR.glob("zero_guard_*.json")))
def test_zero_guard(fixture_path: Path, wynn, item_index, evaluator):
    data = _load_single_fixture(fixture_path)
    if "test_cases" in data:
        for tc in data["test_cases"]:
            results = _run_search(tc["input"], wynn, item_index, evaluator)
            _check_expect(results, tc["expect"], tc["input"])
    else:
        results = _run_search(data["input"], wynn, item_index, evaluator)
        _check_expect(results, data["expect"], data["input"])


@pytest.mark.parametrize("fixture_path", sorted(_FIXTURE_DIR.glob("false_negative_*.json")))
def test_false_negative(fixture_path: Path, wynn, item_index, evaluator):
    data = _load_single_fixture(fixture_path)
    results = _run_search(data["input"], wynn, item_index, evaluator)
    _check_expect(results, data["expect"], data["input"])


@pytest.mark.parametrize("fixture_path", sorted(_FIXTURE_DIR.glob("condition_accuracy_*.json")))
def test_condition_accuracy(fixture_path: Path, wynn, item_index, evaluator):
    data = _load_single_fixture(fixture_path)
    results = _run_search(data["input"], wynn, item_index, evaluator)
    _check_expect(results, data["expect"], data["input"])


@pytest.mark.parametrize("fixture_path", sorted(_FIXTURE_DIR.glob("score_order_*.json")))
def test_score_order(fixture_path: Path, wynn, item_index, evaluator):
    data = _load_single_fixture(fixture_path)
    results = _run_search(data["input"], wynn, item_index, evaluator)
    _check_expect(results, data["expect"], data["input"])


@pytest.mark.parametrize("fixture_path", sorted(_FIXTURE_DIR.glob("score_monotonicity_*.json")))
def test_score_monotonicity(fixture_path: Path, wynn, item_index, evaluator):
    data = _load_single_fixture(fixture_path)
    base = data["input_base"]
    param_steps = data["param_steps"]

    top_scores: list[float] = []
    for step in param_steps:
        inp = {**base, "search_params": step}
        results = _run_search(inp, wynn, item_index, evaluator)
        if results:
            top_scores.append(results[0].score)
        else:
            top_scores.append(0.0)

    if data.get("expect", {}).get("top_score_monotone"):
        for i in range(len(top_scores) - 1):
            assert top_scores[i + 1] >= top_scores[i], (
                f"score_monotonicity violated at step {i+1}: "
                f"top_score={top_scores[i+1]} < prev={top_scores[i]}"
            )


@pytest.mark.parametrize("fixture_path", sorted(_FIXTURE_DIR.glob("edge_case_*.json")))
def test_edge_case(fixture_path: Path, wynn, item_index, evaluator):
    data = _load_single_fixture(fixture_path)
    results = _run_search(data["input"], wynn, item_index, evaluator)
    _check_expect(results, data["expect"], data["input"])
