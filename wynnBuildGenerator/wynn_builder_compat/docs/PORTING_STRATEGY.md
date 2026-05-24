# Python Porting Strategy

最終更新: 2026-05-24

## 目的

crafted search の精度と速度を上げるため、Wynnbuilder の必要な計算ロジックを Python に移植する。Python 側は高速探索、並列処理、将来的な GPU / vectorized evaluation を担当する。ただし正しさの基準は常に Wynnbuilder JavaScript とし、Python 実装は JS parity test に合格することを必須条件にする。

## 採用理由

crafted search は ingredient combination、重複あり 6 素材、2x3 配置、positive / negative booster、durability、condition と score のトレードオフにより、静的 JS だけでは探索改善が難しい可能性が高い。Python に移植した互換計算モジュールを持てば、candidate generation、lane selection、benchmark、parallel search を高速に実験できる。

## wynn_builder_compat の責務

`wynn_builder_compat` は **Wynnbuilder JavaScript ロジックの Python 移植のみ** を担う。

- 対応する JS ソース関数が存在しないコードはここに置かない。
- Generator 固有のロジック (スコア計算、条件式評価、beam search、NumPy evaluator など) は `wynnBuildGenerator/python/search/` に置く。
- `FORMULA_MAP.md` に JS source が記載されていないものは `wynn_builder_compat` に追加しない。

この境界を守ることで、Wynnbuilder 更新時の影響範囲を `wynn_builder_compat` に限定できる。

## 基本方針

- Python 実装は Wynnbuilder JS の互換実装とする。
- Python 側を独自仕様の正にしない。
- 移植対象は検索に必要なロジックから段階的に増やす。
- すべての移植ロジックに JS/Python 一致テストを用意する。
- AI は移植と保守を補助してよいが、採用判断は parity test 結果で行う。

## 移植対象の優先順位

1. item / ingredient data loading and normalization ✅ (`data.py`)
2. skill requirement logic: `js/skillpoints.js` ✅ (`skillpoints.py`)
3. build stat aggregation: `js/builder/build.js` ✅ (`build.py`)
4. display-compatible stat key order and labels ✅ (`display_keys.py`)
5. build encode/decode compatibility ✅ (`encoding.py`)
6. craft preview formula and ingredient effectiveness ✅ (`craft.py`)
7. damage calculation: `js/damage_calc.js` (部分実装 — parity test なし。crafted search 本格対応時に完成させる)

Priority A〜B はすべて parity 済み。Priority C (damage, craft encode/decode) は crafted search 本格対応時に実装する。

条件式評価・スコア計算 (`scoring.py`) は Generator 固有ロジックのため `wynnBuildGenerator/python/search/` に置く。`wynn_builder_compat` には含めない。

## 実際の構成

```text
wynnBuildGenerator/
  python/
    search/
      scoring.py            # Generator 固有: スコア計算・条件式評価
      numpy_evaluator.py    # Generator 固有: NumPy pruning evaluator (未実装)
      lanes.py              # crafted candidate lane 定義
      crafted_candidates.py # crafted candidate generator (未実装)
      benchmarks.py         # benchmark helpers
    tests/
      test_scoring.py
  wynn_builder_compat/
    src/
      wynn_builder_compat/
        data.py
        skillpoints.py
        build.py
        build_utils.py
        craft.py
        damage.py           # 部分実装 (parity test なし)
        encoding.py
        display_keys.py
        models.py
    tests/
      test_*.py             # 全テスト parity 済み
    tools/
      export_js_fixtures/
        *.mjs               # JS fixture exporter 群
    docs/
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

## 探索への接続

`wynn_builder_compat` の parity 済み実装は、`wynnBuildGenerator/python/search/` の探索エンジンから直接利用する。

評価器は二層に分かれる:

- **Pruning evaluator** (`numpy_evaluator.py`): NumPy 行列演算による高速近似。Beam 展開中の候補絞り込みに使う。set bonus・skillpoints は反映しない。
- **Final evaluator** (`wynn_builder_compat`): parity 済みの `build_stat_map()` + `calculate_skillpoints()` パイプライン。最終候補の確定評価に使う。`ProcessPoolExecutor` で並列実行する。

二層の評価結果が食い違う場合は final evaluator の結果を正とする。pruning evaluator が候補を過剰に棄却していないか benchmark で定期確認する。

## 正式評価

Python 側で上位候補を生成したあと、最終候補は JS parity 済み Python evaluator で評価する。重要なリリース前や parity が不安な領域では、Wynnbuilder JS fixture exporter でも再評価する。

将来的に Python 実装が十分に parity test を満たす場合、検索中の正式評価を Python のみに寄せてもよい。ただし新しい Wynnbuilder 更新が入った場合は、再度 JS fixture による一致確認を行う。
