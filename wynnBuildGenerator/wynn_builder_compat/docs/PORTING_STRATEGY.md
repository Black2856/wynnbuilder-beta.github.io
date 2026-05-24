# Python Porting Strategy

最終更新: 2026-05-23

## 目的

crafted search の精度と速度を上げるため、Wynnbuilder の必要な計算ロジックを Python に移植する。Python 側は高速探索、並列処理、将来的な GPU / vectorized evaluation を担当する。ただし正しさの基準は常に Wynnbuilder JavaScript とし、Python 実装は JS parity test に合格することを必須条件にする。

## 採用理由

crafted search は ingredient combination、重複あり 6 素材、2x3 配置、positive / negative booster、durability、condition と score のトレードオフにより、静的 JS だけでは探索改善が難しい可能性が高い。Python に移植した互換計算モジュールを持てば、candidate generation、lane selection、benchmark、parallel search を高速に実験できる。

## 基本方針

- Python 実装は Wynnbuilder JS の互換実装とする。
- Python 側を独自仕様の正にしない。
- 移植対象は検索に必要なロジックから段階的に増やす。
- すべての移植ロジックに JS/Python 一致テストを用意する。
- AI は移植と保守を補助してよいが、採用判断は parity test 結果で行う。

## 移植対象の優先順位

1. item / ingredient data loading and normalization
2. skill requirement logic: `js/skillpoints.js`
3. build stat aggregation: `js/builder/build.js`
4. condition / scoring stat extraction
5. display-compatible stat key order and labels
6. damage calculation: `js/damage_calc.js`
7. craft preview formula and ingredient effectiveness
8. build encode/decode compatibility

crafted search の初期改善では、damage 全体よりも craft preview、ingredient effectiveness、durability、condition / score に必要な stat を優先する。

## 想定構成

```text
wynnBuildGenerator/
  python/
  wynn_builder_compat/
    src/
      wynn_builder_compat/
        data.py
        skillpoints.py
        build.py
        scoring.py
        craft.py
        damage.py
        display_keys.py
    tests/
    docs/
    search/
      crafted_candidates.py
      lanes.py
      benchmarks.py
  tools/
    export_js_fixtures/
    compare_python_js/
  tests/
    parity/
```

## Formula Map

移植時は、対応関係を `FORMULA_MAP.md` に必ず記録する。

例:

- `js/skillpoints.js::calculate_skillpoints` -> `wynn_builder_compat/src/wynn_builder_compat/skillpoints.py::calculate_skillpoints`
- `js/builder/build.js::Build.initBuildStats` -> `wynn_builder_compat/src/wynn_builder_compat/build.py::build_stat_map`
- `js/display.js::displayFixedID` -> `wynn_builder_compat/src/wynn_builder_compat/display_keys.py`
- `js/craft.js` / crafter logic -> `wynn_builder_compat/src/wynn_builder_compat/craft.py`

メンテナンス時は `MAINTENANCE_PROMPT.md` を AI に読み込ませ、この対応表と parity test を基準に更新する。

## Crafted Search 方針

Python crafted search は全探索を前提にしない。まず candidate generator として機能させる。

- recipe lane
- direct score lane
- condition lane
- score high / condition bad lane
- positive booster lane
- negative booster lane
- durability lane
- mixed synergy lane

各 lane は個別 quota を持つ。ingredient pool size や candidate cap を増やしたときに top score が下がる場合は、探索幅の問題ではなく pruning instability として扱う。

## 正式評価

Python 側で上位候補を生成したあと、最終候補は JS parity 済み Python evaluator で評価する。重要なリリース前や parity が不安な領域では、Wynnbuilder JS fixture exporter でも再評価する。

将来的に Python 実装が十分に parity test を満たす場合、検索中の正式評価を Python のみに寄せてもよい。ただし新しい Wynnbuilder 更新が入った場合は、再度 JS fixture による一致確認を行う。
