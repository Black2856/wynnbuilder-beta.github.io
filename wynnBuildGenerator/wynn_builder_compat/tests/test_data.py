from __future__ import annotations

from wynn_builder_compat.data import (
    DEFAULT_DATA_ROOT,
    WynnData,
    item_requirements,
    item_skillpoints,
    minmax_pair,
    normalize_item_for_skillpoints,
    normalize_recipe,
)


def test_minmax_pair_normalizes_wynnbuilder_ranges():
    assert minmax_pair({"minimum": 103, "maximum": 105}) == [103, 105]
    assert minmax_pair([1, 3]) == [1, 3]


def test_normalize_recipe_preview_shape():
    recipe = {
        "type": "RING",
        "lvl": {"minimum": 103, "maximum": 105},
        "healthOrDamage": {"minimum": 0, "maximum": 0},
        "durability": {"minimum": 80, "maximum": 100},
        "materials": [{"item": "Refined Gem", "amount": 1}],
    }
    assert normalize_recipe(recipe)["lvl"] == [103, 105]
    assert normalize_recipe(recipe)["durability"] == [80, 100]


def test_wynn_data_real_dataset_lookup():
    data = WynnData.from_root(DEFAULT_DATA_ROOT)

    item = data.item("Alstroemania")
    assert item["type"] == "leggings"
    assert data.item(item["id"])["displayName"] == "Alstroemania"
    assert item_requirements(item) == [65, 80, 0, 0, 0]
    assert item_skillpoints(item) == [0, 0, 12, 0, 0]
    assert normalize_item_for_skillpoints(item)["name"] == "Alstroemania"

    ingredient = data.ingredient("Voidtossed Memory")
    assert "ids" in ingredient
    assert data.ingredient(ingredient["id"])["displayName"] == "Voidtossed Memory"

    recipe = data.recipe("Ring-103-105", normalized=True)
    assert recipe["type"] == "RING"
    assert recipe["lvl"] == [103, 105]

    assert any(entry["displayName"] == "Alstroemania" for entry in data.items_for_slot("leggings"))
    assert any(entry["name"] == "Ring-103-105" for entry in data.recipes_for_type("ring"))
    assert any(entry["displayName"] == "Voidtossed Memory" for entry in data.ingredients_for_skill("ARMOURING"))
