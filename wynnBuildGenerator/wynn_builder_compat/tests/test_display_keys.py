from __future__ import annotations

from wynn_builder_compat.display_keys import (
    BUILD_DETAILED_DISPLAY_COMMANDS,
    SQ2_ITEM_DISPLAY_COMMANDS,
    format_stat,
    format_stat_map,
)


def test_format_stat_numeric_nonzero():
    assert format_stat("hp", 500) == "Health : 500"
    assert format_stat("sdPct", 15) == "Spell Damage %: 15%"
    assert format_stat("mr", 3) == "Mana Regen: 3/5s"
    assert format_stat("atkTier", 2) == "Attack Speed Bonus: 2 tier"


def test_format_stat_numeric_zero_returns_none():
    assert format_stat("hp", 0) is None
    assert format_stat("sdPct", 0) is None
    assert format_stat("mr", 0) is None


def test_format_stat_string_nonempty():
    assert format_stat("displayName", "Excision of Trust") == "Excision of Trust"
    assert format_stat("atkSpd", "NORMAL") == "Attack Speed: NORMAL"
    assert format_stat("set", "Boundless") == "Set: Boundless set."


def test_format_stat_string_empty_returns_none():
    assert format_stat("displayName", "") is None
    assert format_stat("atkSpd", "") is None


def test_format_stat_unknown_id_returns_none():
    assert format_stat("unknown_stat", 100) is None
    assert format_stat("activeMajorIDs", 1) is None


def test_format_stat_none_value_returns_none():
    assert format_stat("hp", None) is None


def test_format_stat_map_basic():
    stat_map = {"hp": 500, "sdPct": 15, "mr": 0}
    lines = format_stat_map(stat_map, ["hp", "sdPct", "mr"])
    assert lines == ["Health : 500", "Spell Damage %: 15%"]


def test_format_stat_map_skips_directives():
    stat_map = {"hp": 500}
    lines = format_stat_map(stat_map, ["!spacer", "#defense-stats", "hp", "!elemental"])
    assert lines == ["Health : 500"]


def test_format_stat_map_missing_key_skipped():
    stat_map = {"sdPct": 10}
    lines = format_stat_map(stat_map, ["hp", "sdPct"])
    assert lines == ["Spell Damage %: 10%"]


def test_format_stat_map_default_order():
    stat_map = {"displayName": "Test Item", "hp": 100, "sdPct": 5}
    lines = format_stat_map(stat_map)
    assert "Test Item" in lines
    assert "Health : 100" in lines
    assert "Spell Damage %: 5%" in lines
    # Verify displayName comes before hp in SQ2_ITEM_DISPLAY_COMMANDS order
    assert lines.index("Test Item") < lines.index("Health : 100")


def test_build_detailed_display_commands_structure():
    # Ensure no stat IDs are repeated in the display command list
    stat_ids = [k for k in BUILD_DETAILED_DISPLAY_COMMANDS if not k.startswith("!") and not k.startswith("#")]
    assert len(stat_ids) == len(set(stat_ids)), "Duplicate stat IDs in BUILD_DETAILED_DISPLAY_COMMANDS"


def test_sq2_item_display_commands_structure():
    stat_ids = [k for k in SQ2_ITEM_DISPLAY_COMMANDS if not k.startswith("!") and not k.startswith("#")]
    assert len(stat_ids) == len(set(stat_ids)), "Duplicate stat IDs in SQ2_ITEM_DISPLAY_COMMANDS"
