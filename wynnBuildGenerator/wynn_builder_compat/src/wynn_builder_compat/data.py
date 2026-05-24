"""Data loading helpers for Wynnbuilder JSON datasets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .build_utils import expand_item


DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[4]
SKP_ORDER = ("str", "dex", "int", "def", "agi")
REQ_ORDER = ("strReq", "dexReq", "intReq", "defReq", "agiReq")


def load_json(path: str | Path) -> Any:
    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def _as_sequence(payload: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        payload = payload.get(key, [])
    if not isinstance(payload, list):
        raise ValueError(f"expected {key} data to be a list or object containing {key}")
    return payload


def load_items(path: str | Path) -> list[dict[str, Any]]:
    """Load `clean.json` item entries."""
    return _as_sequence(load_json(path), "items")


def load_ingredients(path: str | Path) -> list[dict[str, Any]]:
    """Load `ingreds_clean.json` ingredient entries."""
    return _as_sequence(load_json(path), "ingredients")


def load_recipes(path: str | Path) -> list[dict[str, Any]]:
    """Load `recipes_clean.json` recipe entries."""
    return _as_sequence(load_json(path), "recipes")


def load_sets(path: str | Path) -> dict[str, Any]:
    """Load `clean.json` sets dict."""
    payload = load_json(path)
    if isinstance(payload, dict):
        return payload.get("sets") or {}
    return {}


def minmax_pair(value: Any) -> list[Any]:
    """Normalize Wynnbuilder `{minimum, maximum}` values to `[min, max]`."""
    if isinstance(value, dict) and "minimum" in value and "maximum" in value:
        return [value["minimum"], value["maximum"]]
    if isinstance(value, list):
        return value
    raise ValueError(f"expected min/max object or list, got {value!r}")


def normalize_recipe(recipe: dict[str, Any]) -> dict[str, Any]:
    """Return a recipe shape accepted by `craft.preview_craft()`."""
    normalized = dict(recipe)
    for key in ("duration", "durability", "lvl", "healthOrDamage"):
        if key in normalized:
            normalized[key] = minmax_pair(normalized[key])
    return normalized


def item_skillpoints(item: dict[str, Any]) -> list[Any]:
    """Return an item skillpoint array in Wynnbuilder `str,dex,int,def,agi` order."""
    return [item.get(key, 0) or 0 for key in SKP_ORDER]


def item_requirements(item: dict[str, Any]) -> list[Any]:
    """Return an item requirement array in Wynnbuilder `str,dex,int,def,agi` order."""
    return [item.get(key, 0) or 0 for key in REQ_ORDER]


def normalize_item_for_skillpoints(item: dict[str, Any]) -> dict[str, Any]:
    """Return a compact item shape accepted by `skillpoints.calculate_skillpoints()`."""
    return {
        "name": item.get("displayName") or item.get("name"),
        "reqs": item_requirements(item),
        "skillpoints": item_skillpoints(item),
        "crafted": bool(item.get("crafted", False)),
        "set": item.get("set"),
    }


def prepare_item_from_clean(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a clean.json item dict and expand it for use in build_stat_map.

    Mirrors build_fixture.mjs::prepareItem: sets skillpoints/reqs/majorIds defaults
    then calls expand_item().
    """
    item: dict[str, Any] = dict(raw)
    if not item.get("displayName"):
        item["displayName"] = item.get("name", "")
    item["skillpoints"] = item_skillpoints(item)
    item["reqs"] = item_requirements(item)
    if not item.get("majorIds"):
        item["majorIds"] = []
    return expand_item(item)


def _index_by(entries: Iterable[dict[str, Any]], key: str) -> dict[Any, dict[str, Any]]:
    index: dict[Any, dict[str, Any]] = {}
    for entry in entries:
        if key in entry:
            index[entry[key]] = entry
    return index


@dataclass(frozen=True)
class WynnData:
    """Lookup facade around clean/ingredient/recipe JSON files."""

    items: list[dict[str, Any]]
    ingredients: list[dict[str, Any]]
    recipes: list[dict[str, Any]]
    sets_data: dict[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "_items_by_name", _index_by(self.items, "displayName"))
        object.__setattr__(self, "_items_by_internal_name", _index_by(self.items, "name"))
        object.__setattr__(self, "_items_by_id", _index_by(self.items, "id"))
        object.__setattr__(self, "_ingredients_by_name", _index_by(self.ingredients, "displayName"))
        object.__setattr__(self, "_ingredients_by_internal_name", _index_by(self.ingredients, "name"))
        object.__setattr__(self, "_ingredients_by_id", _index_by(self.ingredients, "id"))
        object.__setattr__(self, "_recipes_by_name", _index_by(self.recipes, "name"))
        object.__setattr__(self, "_recipes_by_id", _index_by(self.recipes, "id"))
        # Mirror load_item.js: remapID items redirect old IDs to new ones during URL decode.
        redirect_map: dict[int, int] = {
            item["id"]: item["remapID"]
            for item in self.items
            if item.get("remapID") is not None
        }
        object.__setattr__(self, "_redirect_map", redirect_map)
        # Mirror load_item.js: assign item.set from sets data (items lack set field in JSON)
        items_by_name: dict[str, dict[str, Any]] = self._items_by_name  # type: ignore[attr-defined]
        for set_name, set_def in self.sets_data.items():
            for item_name in set_def.get("items", []):
                item = items_by_name.get(item_name)
                if item is not None:
                    item["set"] = set_name

    @classmethod
    def from_root(cls, root: str | Path = DEFAULT_DATA_ROOT) -> "WynnData":
        root_path = Path(root)
        return cls(
            items=load_items(root_path / "clean.json"),
            ingredients=load_ingredients(root_path / "ingreds_clean.json"),
            recipes=load_recipes(root_path / "recipes_clean.json"),
            sets_data=load_sets(root_path / "clean.json"),
        )

    def item(self, name_or_id: str | int) -> dict[str, Any]:
        if isinstance(name_or_id, int):
            return self._items_by_id[name_or_id]
        return self._items_by_name.get(name_or_id) or self._items_by_internal_name[name_or_id]

    def ingredient(self, name_or_id: str | int) -> dict[str, Any]:
        if isinstance(name_or_id, int):
            return self._ingredients_by_id[name_or_id]
        return self._ingredients_by_name.get(name_or_id) or self._ingredients_by_internal_name[name_or_id]

    def recipe(self, name_or_id: str | int, *, normalized: bool = False) -> dict[str, Any]:
        if isinstance(name_or_id, int):
            recipe = self._recipes_by_id[name_or_id]
        else:
            recipe = self._recipes_by_name[name_or_id]
        return normalize_recipe(recipe) if normalized else recipe

    def items_for_slot(self, slot: str) -> list[dict[str, Any]]:
        slot_value = slot.lower()
        return [item for item in self.items if str(item.get("type", "")).lower() == slot_value]

    def items_for_category(self, category: str) -> list[dict[str, Any]]:
        category_value = category.lower()
        return [item for item in self.items if str(item.get("category", "")).lower() == category_value]

    def recipes_for_type(self, recipe_type: str) -> list[dict[str, Any]]:
        type_value = recipe_type.upper()
        return [recipe for recipe in self.recipes if str(recipe.get("type", "")).upper() == type_value]

    def ingredients_for_skill(self, skill: str) -> list[dict[str, Any]]:
        skill_value = skill.upper()
        return [entry for entry in self.ingredients if skill_value in entry.get("skills", [])]
