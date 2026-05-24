from wynn_builder_compat.build_utils import (
    level_to_hp_base,
    level_to_skill_points,
    skill_points_to_percentage,
)


def test_level_to_skill_points_matches_js_edges():
    assert level_to_skill_points(0) == 0
    assert level_to_skill_points(1) == 0
    assert level_to_skill_points(2) == 2
    assert level_to_skill_points(100) == 198
    assert level_to_skill_points(101) == 200
    assert level_to_skill_points(121) == 200


def test_level_to_hp_base_matches_js_edges():
    assert level_to_hp_base(1) == 10
    assert level_to_hp_base(106) == 535
    assert level_to_hp_base(121) == 610
    assert level_to_hp_base(122) == 610


def test_skill_points_to_percentage_matches_js_edges():
    assert skill_points_to_percentage(0) == 0.0
    assert skill_points_to_percentage(-1) == 0.0
    assert skill_points_to_percentage(151) == skill_points_to_percentage(150)

