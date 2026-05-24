# Formula Map

最終更新: 2026-05-24

## Purpose

Wynnbuilder JavaScript から Python へ移植する計算ロジックの対応表。JS が仕様の正であり、Python 実装は parity fixture で一致を確認してから探索に使う。

## Priority A: Crafted Search Core

| JS source | JS symbol / area | Python target | Status |
| --- | --- | --- | --- |
| `js/craft.js` | `Craft.statMap` | `craft.py::preview_craft()` | 装備カテゴリは parity 済み |
| `js/craft.js` | material tier multiplier | `craft.py::material_multiplier()` | parity 済み |
| `js/craft.js` | position modifier grid | `craft.py::ingredient_effectiveness_grid()` | parity 済み |
| `js/craft.js` | itemIDs application | `craft.py::apply_item_ids()` | parity 済み |
| `js/craft.js` | rolled IDs application | `craft.py::apply_rolled_ids()` | parity 済み |
| `js/craft.js` | consumable IDs application | `craft.py::apply_consumable_ids()` | 部分実装 |
| `clean.json` | item data | `data.py::WynnData.item()` | 実データ lookup 済み |
| `ingreds_clean.json` | ingredient data | `data.py::WynnData.ingredient()` | 実データ lookup 済み |
| `recipes_clean.json` | recipe data | `data.py::WynnData.recipe()` | 実データ lookup 済み |

## Priority B: Build Evaluation

| JS source | JS symbol / area | Python target | Status |
| --- | --- | --- | --- |
| `js/skillpoints.js` | `vadd5()` | `skillpoints.py::vadd5()` | parity 済み |
| `js/skillpoints.js` | `can_equip()` | `skillpoints.py::can_equip()` | parity 済み |
| `js/skillpoints.js` | `apply_to_fit()` | `skillpoints.py::apply_to_fit()` | parity 済み |
| `js/skillpoints.js` | `apply_skillpoints()` | `skillpoints.py::apply_skillpoints()` | fixture build parity 済み |
| `js/skillpoints.js` | `fix_should_pop()` | `skillpoints.py::fix_should_pop()` | fixture build parity 済み |
| `js/skillpoints.js` | `calculate_skillpoints()` | `skillpoints.py::calculate_skillpoints()` | synthetic + real `clean.json` fixture parity 済み |
| `js/build_utils.js` | `idRound()` | `build_utils.py::id_round()` | parity 済み (Math.round vs banker's rounding 差分対応済) |
| `js/build_utils.js` | `expandItem()` | `build_utils.py::expand_item()` | build statMap parity fixture で検証済み |
| `js/builder/build.js` | `Build.initBuildStats()` | `build.py::build_stat_map()` | set bonus loop 含む parity 済み |
| `js/load_item.js` | item.set 付与ロジック | `data.py::WynnData.__post_init__` | sets_data から item["set"] 付与 済み |

## Priority C: Damage, Display, Encoding

| JS source | JS symbol / area | Python target | Status |
| --- | --- | --- | --- |
| `js/build_utils.js` | `levelToSkillPoints()` | `build_utils.py::level_to_skill_points()` | parity 済み |
| `js/build_utils.js` | `levelToHPBase()` | `build_utils.py::level_to_hp_base()` | parity 済み |
| `js/build_utils.js` | `skillPointsToPercentage()` | `build_utils.py::skill_points_to_percentage()` | parity 済み |
| `js/damage_calc.js` | base/spell damage | `damage.py` | 未実装 |
| `js/display.js` / `js/display_constants.js` | display rows and formatting | `display_keys.py` | 未実装 |
| `js/builder/build_encode_decode.js` | build URL/hash encoding | `encoding.py` | JS fixture + parity 済み |
| `js/display_constants.js` | `idPrefixes`, `idSuffixes`, display command lists | `display_keys.py` | 定数移植 + unit test 済み |
| `js/craft.js` | craft encode/decode | `encoding.py` | 未実装 |

## Rules

- JS fixture を先に追加し、その出力に Python を合わせる。
- 正式評価に使う関数は parity test 済みにする。
- pruning 用の近似評価と最終評価を分ける場合、最終候補は parity 済み evaluator で再評価する。
- 未対応 branch は silent zero にせず、必要なら `NotImplementedError` で止める。
