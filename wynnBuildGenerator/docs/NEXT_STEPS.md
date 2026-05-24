# 次にやること

最終更新: 2026-05-23

## Phase 1: 調査と薄い評価 adapter

1. Builder ページで 1 build を評価する最小経路を特定する。
2. DOM 依存なしで item list から `Build` 相当を作れるか確認する。
3. statMap から条件式とスコア式を評価する小さな関数を作る。
4. `displayBuildStats()` / `displayFixedID()` と同じ表示順・数値表記を再利用する方法を確認する。
5. 既存 Builder の表示結果と adapter 評価結果が一致する fixture を用意する。

完了条件:

- 固定 1 build を入力し、Health、Skill Point、主要 damage 系 stat が Builder と一致する。
- 表示名、数値表記、表示順が Builder と一致する。
- build hash または Builder 入力へ戻せる。

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
- 検索中も UI が固まらない。
- 生成結果を既存 Wynnbuilder ページで開ける。

## Phase 3: Wynnbuilder 導線

1. Builder sidebar または Builder ページ内に Generator へのリンクを追加する。
2. Generator から Builder へ戻る URL 形式を確定する。
3. build hash 生成ができる場合は `encodeBuild()` 互換にする。
4. hash 生成が難しい場合は、一時的に Generator result import 用 hash を Builder 側に追加する。

完了条件:

- Builder から Generator に移動できる。
- Generator の結果から Builder に戻り、同じ装備を閲覧できる。
- 未対応要素がある場合、Generator 結果画面で明示される。

## Phase 4: 性能評価

1. 代表的な検索条件を JSON fixture として保存する。
2. 候補数を増やしたときに top score が不自然に下がらないか確認する。
3. `performance.now()` で候補生成、beam、正式評価の時間を分けて記録する。
4. 遅い条件を `docs/` に追記する。

完了条件:

- 代表検索の runtime と top score を再現できる。
- pruning 変更時に品質劣化を検出できる。

## Phase 5: Python 互換エンジン

crafted search の精度と速度を上げるため、Python 互換エンジンを作る。

1. `wynn_builder_compat/docs/PORTING_STRATEGY.md` の Formula Map を作る。
2. JS fixture exporter の最小版を作る。
3. Python 側に item / ingredient loader を作る。
4. craft preview と ingredient effectiveness を移植する。
5. negative booster、durability、condition / score tradeoff の parity fixture を作る。
6. crafted candidate lane generator を作る。

完了条件:

- crafted search に必要な主要 stat が JS と Python で一致する。
- fixture 化した crafted edge case が再現できる。
- ingredient pool size / candidate cap / recipe 数を増やしたときの top score regression を検出できる。

## Phase 6: 拡張判断

以下は basic search と Python 互換エンジンの土台が安定してから判断する。

- Tome 対応
- Powder 対応
- Ability Tree / Aspect 対応
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
