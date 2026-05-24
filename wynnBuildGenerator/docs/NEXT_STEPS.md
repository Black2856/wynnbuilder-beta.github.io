# 次にやること

最終更新: 2026-05-24

## Phase 1: Python 評価 adapter の接続確認 ✅ 実質完了

`wynn_builder_compat` の完成により、DOM 依存なしの Build 評価は Python 側で解決済み。

確認済みの内容:

- `build_stat_map()` + `calculate_skillpoints()` で固定 build を評価できる (parity 済み)。
- `display_keys.py` で表示順・数値表記を Builder と一致させられる。
- `encoding.py` で build hash の生成・解析ができる。

残作業:

- `scoring.py` に条件式 / スコア式の評価関数を実装する (Phase 5.5 と並行)。
- `build_stat_map()` の出力から条件・スコアを計算する小さな wrapper を作る。

## Phase 2: Basic item search

1. スロット別 item index を作る。
2. class、level、固定 item、tier でフィルタする。
3. beam search を実装する。
4. 最終候補だけ正式評価する。
5. 結果一覧と詳細 UI を作る。
6. 各結果に「Builder で開く」リンクを付ける。

完了条件:

- weapon を含む 9 スロットの build 候補を返せる。
- 条件式とスコア式を UI から追加できる。
- 検索中も UI の入力操作が止まらない (Python バックエンドを非同期で呼び出す)。
- 生成結果を既存 Wynnbuilder ページで開ける (Python `encoding.py` で build hash を生成)。

## Phase 3: Wynnbuilder 導線

1. Builder sidebar または Builder ページ内に Generator へのリンクを追加する。
2. Generator から Builder へ戻る URL 形式を確定する。
3. build hash 生成ができる場合は `encodeBuild()` 互換にする。
4. hash 生成が難しい場合は、一時的に Generator result import 用 hash を Builder 側に追加する。

完了条件:

- Builder から Generator に移動できる。
- Generator の結果から Builder に戻り、同じ装備を閲覧できる。
- 未対応要素がある場合、Generator 結果画面で明示される。

## Phase 4: 精度保証と性能評価

**優先順位: 速度より精度を優先する。**

正しい候補が返ってこない不具合は、速度不足より致命的であるため、精度テストを先に固め、その上で性能を測定する。

### 4-1. 精度テスト corpus の構築

以下のカテゴリを網羅した JSON fixture を `docs/search_fixtures/` に作成する。

**Fixture フォーマット**

各 fixture は `入力` と `期待検証内容` を持つ JSON ファイル。

```json
{
  "case_id": "warrior-lv106-hp-zero-guard",
  "category": "zero_guard",
  "description": "HP 条件あり lv106 warrior で 0 件にならないことを確認",
  "input": {
    "class": "warrior",
    "level": 106,
    "conditions": [{ "key": "hp", "op": ">=", "value": 30000 }],
    "scoring": { "maximize": { "hp": 1 } },
    "fixed_items": {},
    "search_params": { "beam_width": 50, "max_candidates_per_slot": 40, "result_limit": 10 }
  },
  "expect": {
    "min_results": 1,
    "conditions_satisfied": true,
    "score_descending": true,
    "required_builds": []
  }
}
```

`required_builds` には既知の良いビルドを指定し、上位 N 件に含まれることを検証する。

```json
"required_builds": [
  {
    "equipment": ["Helmet A", "Chest B", "Legs C", "Boots D", "Ring E", "Ring F", "Brace G", "Neck H"],
    "weapon": "Weapon X",
    "must_appear_in_top_n": 10
  }
]
```

カテゴリ一覧:

| カテゴリ | 確認内容 |
|---|---|
| `zero_guard` | `min_results >= 1` — 有効な条件で 0 件にならない |
| `false_negative` | `required_builds` の既知ビルドが上位 N 件に含まれる |
| `condition_accuracy` | 返却候補が全て条件式を満たしている |
| `score_order` | スコアが降順になっている |
| `skill_req` | スキル要求を満たせないビルドが含まれない |
| `score_monotonicity` | 探索幅を広げたとき top score が下がらない |
| `edge_case` | 全スロット空き・固定アイテム・極端な条件など |

**ゼロ件ガード (存在する組み合わせが 0 件にならないことを確認)**

- 1 件以上の有効ビルドが必ず存在する緩い条件を与え、結果が 0 件にならないことを確認する。
- class / level の有効な組み合わせすべてで最低 1 件返ること。
- 固定アイテム (lock) を指定した場合、そのアイテムを含む候補が返ること。
- 同じリングを 2 スロットに指定した場合に正しく扱われること。

**False Negative ガード (既知のビルドが候補から落ちないことを確認)**

- 既知の有効ビルドを答えとして持つ検索条件を用意し、そのビルドが上位に出ること。
- pruning evaluator を有効にしたときと無効にしたときで、最終候補セットが一致すること (または無効時の上位 N 件が有効時にも含まれること)。
- beam 幅を変えても既知ビルドが消えないこと。

**スコア・条件の正確性**

- 条件式 `hp >= X` を満たさないビルドが返ってこないこと。
- 複数条件の AND 評価が正しく動くこと (A を満たして B を満たさないビルドは除外される)。
- スコア降順が保たれること (上位結果の score が下位を下回らない)。
- スコアの内訳が statMap の値と一致すること。

**スキル要求の正確性**

- `calculate_skillpoints()` が失敗する装備構成 (スキル要求を満たせない) が返ってこないこと。
- スキル要求のギリギリを満たすビルドが正しく通ること。

**エッジケース**

- 全スロット空き (weapon のみ指定) での検索が動くこと。
- 存在しないアイテム名を固定指定したときに適切にエラーを返すこと。
- 極端に厳しい条件 (現実的に 0 件が正解) で 0 件が返ること、かつフリーズしないこと。
- 候補数が beam 幅を下回るスロットがある場合に動くこと。
- 同一アイテムを複数スロットに使う場合 (ring 以外は不可、ring は可) の制約が守られること。

**`score_monotonicity` fixture の形式**

同一の検索条件に対して、探索パラメータを段階的に広げたとき top score が単調に改善 (または維持) されることを確認する。

```json
{
  "case_id": "warrior-lv106-monotonicity",
  "category": "score_monotonicity",
  "description": "beam_width / max_candidates_per_slot を広げると top score が下がらないことを確認",
  "input_base": {
    "class": "warrior",
    "level": 106,
    "conditions": [],
    "scoring": { "maximize": { "hp": 1, "sdRaw": 2 } }
  },
  "param_steps": [
    { "beam_width": 20, "max_candidates_per_slot": 20 },
    { "beam_width": 50, "max_candidates_per_slot": 40 },
    { "beam_width": 100, "max_candidates_per_slot": 80 }
  ],
  "expect": {
    "top_score_monotone": true
  }
}
```

`top_score_monotone: true` は「各ステップの top score が前ステップを下回らない」ことを意味する。旧実装で実際に発生した問題 (候補数を増やすと beam pruning で良い候補が落ちてスコアが下がる) を regression として検出するためのカテゴリ。

### 4-2. Pruning Evaluator の精度保証

NumPy pruning evaluator を導入した場合、以下を regression テストとして維持する。

- `pruning_miss_rate`: pruning で棄却した候補の中に、final evaluator で上位 N 件に入るものがないこと。
  - 許容値: 上位 10 件への miss は 0 件。
- `pruning_false_zero`: pruning が全候補を棄却して結果が 0 件になるケースがないこと。
- beam 幅・候補数 cap を変えた場合の上位スコアが単調に改善すること (広げると悪化しない)。

### 4-3. 性能計測

精度テストが全パスした後に実施する。

1. 代表的な検索条件を JSON fixture として保存する。
2. 候補生成・beam 展開・最終評価・全体の時間を分けて記録する。
3. 遅い条件と候補数を `docs/search_fixtures/BENCHMARK_NOTES.md` に追記する。

完了条件:

- 4-1 の全カテゴリを網羅した fixture が存在し、自動テストで再現できる。
- pruning evaluator の精度保証テスト (上位 10 件 miss 0 件) が CI で維持される。
- 代表検索の runtime と top score を再現できる。
- pruning / beam 変更時に精度劣化を自動検出できる。

## Phase 5: Python 互換エンジン ✅ 完了

`wynn_builder_compat` として実装済み。Priority A / B のすべてのロジックが parity 済み。

完了した内容:

- item / ingredient / recipe data loader (`data.py`)
- skill requirement logic (`skillpoints.py`) — parity 済み
- build stat aggregation (`build.py`) — set bonus loop 含む parity 済み
- craft preview と ingredient effectiveness (`craft.py`) — parity 済み
- display key order and formatted values (`display_keys.py`) — unit test 済み
- build encode/decode (`encoding.py`) — JS fixture + parity 済み
- JS fixture exporter 群 (`tools/export_js_fixtures/`)
- parity test suite 34 テスト全パス

残作業 (Priority C):

- `damage.py`: base/spell damage 未実装 (`js/damage_calc.js`)
- craft encode/decode 未実装

## Phase 5.5: 探索エンジン性能基盤

Python 互換エンジンを探索に使うための性能レイヤーを実装する。

1. NumPy item matrix を構築する (`python/search/` に `numpy_evaluator.py` として追加)。
   - 全アイテムの stat を `np.ndarray (N_items × N_stats)` にキャッシュ。
   - `partial_stat_sum(indices)` — 選択 item の stat を `item_matrix[indices].sum(axis=0)` で返す。
   - 条件評価 (`stat >= threshold`) とスコア (weighted dot product) をベクトル演算で実装。
2. CPU multiprocessing wrapper を実装する。
   - `ProcessPoolExecutor` で最終候補の `build_stat_map()` + `calculate_skillpoints()` を並列実行。
   - worker 数デフォルト `os.cpu_count()`、上限設定可能。
3. 二層評価のベンチマークを作る (`benchmarks.py` に追加)。
   - pruning evaluator vs final evaluator の結果を比較し、棄却ミスを記録。

完了条件:

- NumPy evaluator が pruning フェーズで dict ベースより高速であることを benchmark で確認。
- multiprocessing wrapper が正式評価フェーズで CPU コア数に応じてスケールすることを確認。
- top score が pruning evaluator の近似によって最終候補から落ちていないことを benchmark で検証。

## Phase 6: 拡張判断

以下は basic search と Python 互換エンジンの土台が安定してから判断する。

- Tome 対応 → skillpointに関するguild tomeのみ対応する
- Powder 対応 → 対応なし
- Ability Tree / Aspect 対応 → 対応なし
- FastAPI など backend の再導入
- learned ranker による soft ordering

backend を入れる場合は、静的版で使う Wynnbuilder JS 評価との一致テストを先に作る。

## Crafted Search 調査項目

crafted 対応に入る前に、次を fixture 化する。

1. ingredient pool size、candidate cap、recipe 数を増やしても top score が下がらないか。
2. `-150%` booster などの負の effectiveness で、負 stat が正方向に反転・増幅されるケース。
3. condition を悪化させるが score を大きく伸ばす素材を含むケース。
4. durability 補助素材を入れないと成立しない high-score craft。
5. 同じ素材 6 個、relevant + booster mix、distinct 6 素材の配置コスト比較。

これらが再現できるまで、crafted search は「完全探索」ではなく限定対応として扱う。
