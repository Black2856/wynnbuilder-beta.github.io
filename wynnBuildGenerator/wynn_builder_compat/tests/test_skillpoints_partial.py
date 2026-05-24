from types import SimpleNamespace

from wynn_builder_compat.skillpoints import apply_to_fit, can_equip, vadd5


def test_vadd5_matches_js_behavior():
    assert vadd5([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]) == [6, 6, 6, 6, 6]


def test_can_equip_uses_positive_requirements_only():
    item = SimpleNamespace(reqs=[0, -5, 10, 20, 30])
    assert can_equip([0, 0, 10, 20, 30], item)
    assert not can_equip([0, 0, 9, 20, 30], item)


def test_apply_to_fit_mutates_skillpoints_and_returns_delta():
    item = SimpleNamespace(reqs=[0, 5, 10, 0, 1])
    skillpoints = [0, 1, 10, 0, 0]
    assert apply_to_fit(skillpoints, item) == [0, 4, 0, 0, 1]
    assert skillpoints == [0, 5, 10, 0, 1]

