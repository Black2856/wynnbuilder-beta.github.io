from __future__ import annotations

import pytest

from search.scoring import check_conditions, score_stat_map


# ---------------------------------------------------------------------------
# score_stat_map
# ---------------------------------------------------------------------------


def test_score_maximize_single():
    score, breakdown = score_stat_map({"hp": 1000}, {"maximize": {"hp": 2}})
    assert score == 2000.0
    assert breakdown == {"maximize.hp": 2000.0}


def test_score_minimize_single():
    score, breakdown = score_stat_map({"spRaw1": 10}, {"minimize": {"spRaw1": 1}})
    assert score == -10.0
    assert breakdown == {"minimize.spRaw1": -10.0}


def test_score_maximize_and_minimize():
    stat_map = {"hp": 500, "sdRaw": 100, "spRaw1": 20}
    scoring = {"maximize": {"hp": 1, "sdRaw": 2}, "minimize": {"spRaw1": 1}}
    score, breakdown = score_stat_map(stat_map, scoring)
    assert score == 500 + 200 - 20
    assert breakdown["maximize.hp"] == 500.0
    assert breakdown["maximize.sdRaw"] == 200.0
    assert breakdown["minimize.spRaw1"] == -20.0


def test_score_missing_key_treated_as_zero():
    score, breakdown = score_stat_map({}, {"maximize": {"hp": 1}})
    assert score == 0.0
    assert breakdown == {"maximize.hp": 0.0}


def test_score_empty_scoring():
    score, breakdown = score_stat_map({"hp": 1000}, {})
    assert score == 0.0
    assert breakdown == {}


def test_score_none_sections_ignored():
    score, breakdown = score_stat_map({"hp": 100}, {"maximize": None, "minimize": None})
    assert score == 0.0
    assert breakdown == {}


def test_score_breakdown_keys_prefixed():
    _, breakdown = score_stat_map({"hp": 1, "sdRaw": 1}, {"maximize": {"hp": 1}, "minimize": {"sdRaw": 1}})
    assert "maximize.hp" in breakdown
    assert "minimize.sdRaw" in breakdown


def test_score_fractional_weight():
    score, _ = score_stat_map({"hp": 100}, {"maximize": {"hp": 0.5}})
    assert score == 50.0


# ---------------------------------------------------------------------------
# check_conditions
# ---------------------------------------------------------------------------


def test_condition_gte_pass():
    assert check_conditions({"hp": 500}, [{"key": "hp", "op": ">=", "value": 500}]) is True
    assert check_conditions({"hp": 600}, [{"key": "hp", "op": ">=", "value": 500}]) is True


def test_condition_gte_fail():
    assert check_conditions({"hp": 499}, [{"key": "hp", "op": ">=", "value": 500}]) is False


def test_condition_lte_pass():
    assert check_conditions({"spRaw1": 5}, [{"key": "spRaw1", "op": "<=", "value": 5}]) is True
    assert check_conditions({"spRaw1": 3}, [{"key": "spRaw1", "op": "<=", "value": 5}]) is True


def test_condition_lte_fail():
    assert check_conditions({"spRaw1": 6}, [{"key": "spRaw1", "op": "<=", "value": 5}]) is False


def test_condition_multiple_and_all_pass():
    stat_map = {"hp": 1000, "sdRaw": 200}
    conditions = [
        {"key": "hp", "op": ">=", "value": 500},
        {"key": "sdRaw", "op": ">=", "value": 100},
    ]
    assert check_conditions(stat_map, conditions) is True


def test_condition_multiple_and_one_fails():
    stat_map = {"hp": 1000, "sdRaw": 50}
    conditions = [
        {"key": "hp", "op": ">=", "value": 500},
        {"key": "sdRaw", "op": ">=", "value": 100},
    ]
    assert check_conditions(stat_map, conditions) is False


def test_condition_unknown_key_treated_as_zero():
    # unknown key → actual = 0, so >= 0 passes, >= 1 fails
    assert check_conditions({}, [{"key": "nonexistent", "op": ">=", "value": 0}]) is True
    assert check_conditions({}, [{"key": "nonexistent", "op": ">=", "value": 1}]) is False


def test_condition_empty_list_always_passes():
    assert check_conditions({}, []) is True
    assert check_conditions({"hp": 999999}, []) is True


def test_condition_unknown_operator_raises():
    with pytest.raises(ValueError, match="Unknown condition operator"):
        check_conditions({"hp": 100}, [{"key": "hp", "op": "==", "value": 100}])


def test_condition_negative_stat_lte():
    # spRaw1 は負の値が良い (コスト削減)
    assert check_conditions({"spRaw1": -5}, [{"key": "spRaw1", "op": "<=", "value": -3}]) is True
    assert check_conditions({"spRaw1": -2}, [{"key": "spRaw1", "op": "<=", "value": -3}]) is False
