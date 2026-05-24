# アーキテクチャ検討

最終更新: 2026-05-24

## 推奨構成

検索エンジンは Python で実装する。UI は静的ページとして置き、Python バックエンドを呼び出す構成とする。

```text
wynnBuildGenerator/
  index.html
  styles.css
  app.js
  docs/
  python/
    search/
      scoring.py          # スコア計算・条件式評価 (Generator 固有ロジック)
      numpy_evaluator.py  # NumPy vectorized pruning evaluator
      benchmarks.py       # benchmark helpers
      lanes.py            # crafted candidate lane 定義
      crafted_candidates.py
  wynn_builder_compat/    # Wynnbuilder JS ロジックの Python 移植のみ
    src/wynn_builder_compat/
      data.py, skillpoints.py, build.py, craft.py,
      encoding.py, display_keys.py, build_utils.py, ...
```

**モジュール責務の境界**:

- `wynn_builder_compat/` — Wynnbuilder JS の移植のみ。対応 JS ソースが `FORMULA_MAP.md` に記載されているものだけを置く。
- `python/search/` — Generator 固有のロジック。スコア計算、条件式評価、beam search、NumPy evaluator、benchmark などはすべてここ。

この境界を守ることで、Wynnbuilder 更新時の影響範囲を `wynn_builder_compat/` に限定できる。

## 既存 Wynnbuilder から参照する候補

主な参照先:

- `clean.json`, `items_compress.json`, `ingreds_compress.json`, `recipes_compress.json`
- `js/load_item.js`, `js/loader.js`
- `js/builder/build.js`
- `js/builder/builder_graph.js`
- `js/damage_calc.js`
- `js/build_utils.js`
- `js/skillpoints.js`
- `js/display_constants.js`, `js/display.js`
- `js/builder/build_encode_decode.js`

特に `Build` は装備、スキルポイント、セットボーナス、statMap 集計の中心である。スキル要求は `js/skillpoints.js` の `calculate_skillpoints()` が既存の正とするロジックで、Generator はこれを利用する。ダメージ系は `calculateSpellDamage()` など既存関数を使う。URL 共有は `encodeBuild()` 系を利用する。

表示面では `js/display.js` の `displayBuildStats()`、`displayFixedID()`、`displayExpandedItem()` と、`js/display_constants.js` の ID 定義・表示 command を基準にする。Generator 側で同じ stat を別の順番や丸めで表示しない。

## 実装上の注意

現在の Builder ロジックは DOM とグローバル変数に依存する箇所がある。検索 Worker から直接使えない場合は、まず既存関数を壊さずに薄い adapter を作る。

例:

- アイテム名から `Item` を作る adapter
- DOM 更新を伴わず `Build` 相当の評価だけを返す adapter
- statMap から条件式・スコア式を評価する adapter
- Builder と同じ表示順・表記で stat summary を作る adapter

adapter は新規計算式を持たず、既存関数の呼び出しとデータ整形だけに限定する。

## ページ間連携

Wynnbuilder から Generator への入口は、既存の sidebar または Builder ページの操作エリアに追加する。遷移先は `../wynnBuildGenerator/` を基本とする。将来的に検索条件を持ち込む場合は query string または hash に JSON を圧縮して渡す。

Generator から Builder への戻りは、既存の build encode 仕様を使う。

```text
wynnBuildGenerator result
  -> equipment item names / ids
  -> Build adapter
  -> encodeBuild(...)
  -> ../builder/#<encoded-build>
```

初期版では `encodeBuild()` を直接呼べない可能性があるため、次のどちらかで実装する。

1. Builder と同じグローバル初期化を Generator ページでも読み込み、結果 item set から build hash を生成する。
2. Generator 側では item set を query/hash に持たせ、Builder 側に「Generator result import」処理を追加して decode する。

優先は 1。Builder 既存の共有 URL と互換にでき、生成結果を通常の Wynnbuilder build として扱えるため。

## 検索エンジン案

候補生成:

1. スロット別にアイテムを分類する。
2. class、level、tier、固定アイテムで事前フィルタする。
3. 単品 stat の近似値で候補を並べる。
4. 各スロットの候補数を制限する。

組み合わせ探索:

- 初期版は beam search を使う。
- 各 partial build を軽量評価し、条件進捗とスコアで beam を残す。
- 最終候補だけ Wynnbuilder の正式 Build 評価 (parity 済み) に通す。
- `resultLimit` が満たされた後も、上位に入り得る候補だけ検証する。

**精度保証の原則 (速度より優先)**:

- pruning (beam 絞り込み) は近似でよいが、**条件式の最終判定と返却候補の確定は必ず parity 済み final evaluator で行う**。
- pruning が原因で有効な候補を取りこぼしていないか、regression fixture で継続検証する。
  - 上位 10 件への miss 0 件を維持する。
- 0 件ガード: 有効ビルドが存在する条件で 0 件を返してはならない。pruning が全棄却した場合は beam 幅を緊急拡大するフォールバックを入れる。
- False Negative ガード: 既知ビルドが beam から落ちないことを `docs/search_fixtures/` の fixture で自動検証する。
- 返却時の条件式チェックは pruning evaluator の値ではなく final evaluator の値で行う。

旧実装で有効だった考え方:

- スキル要求の正式判定は Wynnbuilder の `calculate_skillpoints()` / `Build` に委譲し、返却候補中心に行う。
- candidate count を増やしたときに上位スコアが下がらないかを benchmark する。
- ML/DL は hard filter ではなく soft ordering に留める。

**探索幅拡大時のスコア単調性 (必須)**:

beam_width や max_candidates_per_slot を大きくしたとき、top score が下がる場合は探索バグとして扱う。候補空間を広げるほど探索精度が上がるべきであり、下がる場合は beam pruning が良い候補を誤棄却している。`score_monotonicity` fixture でパラメータを段階的に変えて top score の単調性を regression テストとして維持する。

## Crafted Search 方針

crafted item は basic item と同じ候補リストに直接混ぜる前に、専用 candidate generator で slot 別の少数候補へ圧縮する。ただし単純な top-N では不十分。ingredient には booster、負の booster、durability 補助、condition 悪化と score 改善を同時に起こす素材があるため、複数 lane を保持する。

候補 lane の例:

- score lane
- condition lane
- score high / condition bad lane
- positive booster lane
- negative booster lane
- durability lane
- mixed synergy lane

ingredient pool size、recipe 数、candidate cap を増やしたときに top score が下がる場合は、探索空間の拡大ではなく pruning の不安定さとして扱う。benchmark では「cap を増やしても代表 top score が下がらない」ことを regression 条件にする。

負の booster は、単体素材の符号だけでは評価できない。配置後に `-25` が `+37.5` 相当へ反転するようなケースを拾うため、ingredient 単体評価ではなく「素材ペア / booster 対象 / 配置方向」の簡易評価を candidate generator に入れる。

## 評価器の二層構造

探索パイプラインは評価コストの異なる二層の evaluator で構成する。

```
[Pruning evaluator]  NumPy vectorized
  - 入力: slot × item_index の選択
  - 処理: item_matrix[indices].sum(axis=0) → 条件チェック + スコア
  - 用途: Beam 展開時の候補絞り込み
  - 正確度: 近似 (set bonus・skillpoints は意図的に無視。精度影響は regression fixture で監視)

[Final evaluator]    wynn_builder_compat (parity 済み)
  - 入力: 最終候補 build
  - 処理: build_stat_map() + calculate_skillpoints()
  - 用途: 返却候補の確定と表示
  - 正確度: Wynnbuilder JS と parity 保証済み
```

二層の結果が食い違う場合は pruning evaluator の過推定として扱い、final evaluator の結果を正とする。set bonus を無視する pruning が上位候補を過剰棄却していないか、`docs/search_fixtures/` の `false_negative` カテゴリ fixture で継続検証する。

### NumPy item matrix の構築

```python
# 起動時に一度だけ構築
stat_keys: list[str]          # 固定順の stat ID リスト
item_matrix: np.ndarray       # shape (N_items, N_stats), dtype float32
item_index: dict[str, int]    # item name → row index
```

- `WynnData` の全アイテムを走査して行列化する。
- set bonus・skillpoint bonus は pruning では無視し、final evaluator に委ねる (意図的な設計)。
- スロット別の候補 index 配列を事前に生成し、Beam 展開で再利用する。

### CPU multiprocessing による最終評価の並列化

```python
with ProcessPoolExecutor(max_workers=os.cpu_count()) as pool:
    futures = [pool.submit(evaluate_final, build) for build in final_candidates]
    results = [f.result() for f in futures]
```

- `evaluate_final(build)` は worker プロセス内で `WynnData.from_root()` をロードする。
- pickle 可能な plain dict / dataclass のみを worker 間でやり取りする。
- Beam 展開ループ自体は並列化せず逐次のまま維持する。

## Python 互換エンジン案

crafted search の精度と速度改善を必須目標とするため、Wynnbuilder JS の必要ロジックを Python に移植した互換エンジンを採用候補ではなく正式方針として扱う。詳細は `wynn_builder_compat/docs/PORTING_STRATEGY.md` と `wynn_builder_compat/docs/PARITY_TESTING.md` に従う。

Python 側は crafted candidate generation、lane selection、benchmark、parallel search、将来的な vectorized / GPU evaluation を担当する。JS 側は正しさの基準であり、Python 実装は parity test により JS と一致させる。

初期実装では JS Worker で basic search を進めてもよいが、crafted search に入る前に Python 互換エンジンと parity fixture の土台を作る。

## バックエンド案

FastAPI + uv は旧実装で動作実績があるが、初期版では採用しない。採用判断の条件:

- Web Worker でも代表的検索が実用速度に届かない。
- ブラウザメモリや single-thread 制約が問題になる。
- Python の最適化実装を持つ利益が、計算式二重管理のリスクを上回る。

採用する場合でも、最終値の検証は Wynnbuilder JS と比較する regression fixture を必須にする。
