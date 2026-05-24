# JS / Python Parity Testing

最終更新: 2026-05-24

## 目的

Python に移植した計算ロジックが Wynnbuilder JavaScript と一致することを保証する。crafted search では Python 側の評価値を探索に使うため、parity test は必須とする。

## 方針

同じ入力 build / craft / ingredient set を JS と Python に渡し、出力 JSON を比較する。JS 側を正とし、Python 側は既存 Wynnbuilder の挙動に合わせる。

主な比較対象:

- skill point helper と level helper ✅
- ingredient effectiveness grid ✅
- material tier multiplier ✅
- itemIDs / rolled IDs の effectiveness 適用 ✅
- crafted item の `statMap` ✅
- skill requirement / skillpoints ✅
- build statMap aggregation (set bonus 含む) ✅
- build encode/decode ✅
- display key order and formatted values ✅
- durability / missingDurability
- weapon base damage

## Fixture Exporter

Node.js の `vm` で既存 JS を実行し、fixture JSON を標準出力する。

実装済み:

- `tools/export_js_fixtures/build_utils_fixture.mjs` → `tests/test_js_build_utils_parity.py` ✅
- `tools/export_js_fixtures/craft_effectiveness_fixture.mjs` → `tests/test_js_craft_effectiveness_parity.py` ✅
- `tools/export_js_fixtures/craft_preview_fixture.mjs` → `tests/test_js_craft_preview_parity.py` ✅
- `tools/export_js_fixtures/skillpoints_fixture.mjs` → `tests/test_js_skillpoints_parity.py` ✅
- `tools/export_js_fixtures/build_fixture.mjs` → `tests/test_js_build_parity.py` ✅
- `tools/export_js_fixtures/encode_decode_fixture.mjs` → `tests/test_js_encoding_parity.py` ✅

`craft_preview_fixture.mjs` は `js/build_utils.js` と `js/craft.js` を読み込み、`Craft` が生成する `statMap` を Python `preview_craft()` と完全一致で比較する。現在の fixture は mock armor / mock weapon に加え、`recipes_clean.json` と `ingreds_clean.json` から実データの全装備カテゴリを使う。

実データ fixture:

- armor: `Helmet-103-105`, `Chestplate-103-105`, `Leggings-103-105`, `Boots-103-105`
- weapon: `Wand-103-105`, `Spear-103-105`, `Bow-103-105`, `Dagger-103-105`, `Relik-103-105`
- accessory: `Ring-103-105`, `Bracelet-103-105`, `Necklace-103-105`

## Comparison Rules

- integer stats: exact match
- strings, booleans, arrays, object keys: exact match
- crafted `statMap`: full dict equality
- floating derived values: 原則 JS と同じ丸め処理を移植して exact match
- 表示文字列: Wynnbuilder の formatter と一致させる

例外的に tolerance が必要な場合は、理由と対象関数をこの文書に追記する。

## Required Crafted Fixtures

crafted search に入る前に、最低限次の fixture を増やす。

1. 同じ素材 6 個
2. positive booster を含む craft
3. `-150%` negative booster を含む craft
4. condition 要求値は悪化するが score が大きく伸びる素材
5. durability が成立しない high-score craft
6. ingredient placement permutation が score を変える craft
7. ingredient pool size / candidate cap / recipe 数を増やしても top score が下がらない regression case
8. powder ingredient branch
9. consumable craft branch

## Failure Report

parity test failure は次を確認する。

- `caseId`
- compared key path
- JS value
- Python value
- related JS source file / function
- related Python source file / function

AI メンテナンス時は、まず JS の現在挙動を fixture で固定し、Python 実装を合わせてから探索側で使う。

## Acceptance Criteria

移植済み領域は、対応する parity test が全て通るまで search engine の正式評価に使わない。pruning や lightweight ranking に暫定利用する場合も、最終候補は parity 済み evaluator で再評価する。
