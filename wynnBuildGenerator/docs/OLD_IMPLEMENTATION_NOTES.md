# 旧実装から引き継ぐ仕様と保留点

最終更新: 2026-05-23

## 参照元

旧実装は `wynnBuildGenerator_old/` にある。特に次の資料が有用。

- `docs/REQUIREMENTS.md`
- `docs/DETAILED_DESIGN.md`
- `docs/INVESTIGATION.md`
- `docs/search_optimization_report.md`
- `docs/craft_optimization_report.md`
- `docs/REMAINING_WORK.md`

## 引き継ぐ仕様

- 9 装備スロットを対象にする。
- 条件式は AND で評価する。
- 条件式とスコア式は複数 key を扱う。
- 固定アイテム lock を持つ。
- 同じリングを 2 つ使える。
- 検索結果には score、条件一致、候補統計、警告を含める。
- skill requirement は最終候補で Wynnbuilder 既存ロジックにより検証する。
- 検索は正確性を優先し、近似だけで結果を確定しない。

## 捨てる・置き換える部分

旧実装の Python 側 normalized item、total_stats、damage formula、craft formula はそのまま移植しない。理由は Wynnbuilder 本体と式やデータ解釈がずれるリスクが高いため。

置き換え方:

- Python loader ではなく Wynnbuilder の loader/data を参照する。
- Python `total_stats.py` ではなく `Build.statMap` と既存表示ロジックを参照する。
- Python damage/craft formula ではなく `js/damage_calc.js` と Builder/Crafter 側ロジックを参照する。
- FastAPI endpoint ではなく、静的ページ内の関数または Worker message API に置き換える。

## 旧実装の重要な知見

検索の主なボトルネックはスキル要求の exact equip-order validation だった。旧実装では Python 側に独自 DP を持っていたが、新実装ではその solver は移植しない。Wynnbuilder には `js/skillpoints.js` の `calculate_skillpoints()` と `Build` 経由の装備順序・必要割り振り計算があるため、正式判定はそれを使う。

旧実装から引き継ぐべき知見は、正式なスキル要求判定を全組み合わせに対して行うと重い可能性があること。検索中は軽量な近似や候補順序付けを使ってよいが、返却候補は必ず Wynnbuilder 既存ロジックで再評価する。

basic search の代表ケースでは `maxCandidatesPerSlot=40` が約 71 秒から約 6.9 秒まで改善している。これは「計算式を変えずに探索順序と検証タイミングを改善する」方向が有効であることを示す。

crafted search は branching factor と formula parity の両方が難しい。初期版では basic item search を優先し、crafted は後続に回す。

## 旧 crafted search の処理

旧実装の crafted search は、9 枠探索中に ingredient を直接展開するのではなく、先に `generate_crafted_candidates_by_slot()` で crafted 装備候補を slot 別に作ってから通常検索へ渡していた。

処理順:

1. condition と scoring から `relevant_stat_keys()` を作る。
2. slot、class weapon type、level で recipe を絞る。
3. recipe の profession と level に合う ingredient を `ingreds_clean` 相当のデータから選ぶ。
4. relevant ID、condition 別 ranking、booster potential、durability を混ぜて ingredient pool を小さくする。
5. `stratified_ingredient_groups()` で、同一 ingredient、relevant + booster mix、fallback の順に重複あり組み合わせを生成する。
6. 各 group を `optimize_ingredient_order()` に渡し、2x3 配置の distinct permutation を評価する。
7. durability などの条件を満たした preview を crafted item 風の `NormalizedItem` に変換する。
8. slot ごとに scoring / condition progress で代表候補だけ残す。
9. basic item 候補と merge し、通常の 9 枠 beam search に渡す。

この構成は「craft 候補を先に作ってから build search へ入る」という方向性としては正しい。ただし旧実装は Python 側に craft formula、total stat、skill requirement を持っていたため、Wynnbuilder との式ズレが起きやすい。新実装ではこの流れを参考にしつつ、craft preview と最終評価は Wynnbuilder / Crafter 側のロジックに寄せる。

旧 crafted search の弱点:

- ingredient pool に入らない素材は絶対に探索されない。
- booster ingredient は単体 stat で価値を測れないため heuristic 依存になる。
- 6 ingredient で distinct ingredient が多いと配置 permutation が重い。
- recipe 数、ingredient pool、候補 cap の値で結果品質が大きく変わる。
- ingredient pool size、candidate cap、recipe 数を大きくしたときに、探索結果の top score が下がる問題があった。候補空間を広げるほど良くなるとは限らず、beam pruning や代表候補選択で良い候補が落ちることが原因になり得る。
- `-150%` booster のような負の effectiveness により、負の stat が反転・増幅されるケースがある。例として score 上は `-25` の素材が配置次第で `+37.5` 相当になる可能性があり、単体 stat ranking では評価できない。
- condition を悪化させる素材でも、score を大きく伸ばす場合がある。condition ranking だけ、または score ranking だけでは候補を落としやすい。
- Python 独自 formula の parity 確認が必要だった。

新方針では crafted item は basic search と別モジュールの candidate generator として扱う。Generator は condition / score に効きそうな crafted 候補を先に作り、十分に絞った後で 9 枠 build search に渡す。

crafted search で「ベスト」を狙う場合、単純な top-N ingredient 選択では不十分。少なくとも次の候補 lane を分けて保持する必要がある。

- score を直接伸ばす素材
- condition 達成に寄与する素材
- condition を悪化させるが score を伸ばす素材
- 正の booster
- 負の booster
- durability を補う素材
- 低単体評価だが booster と組み合わせると反転・増幅する素材

探索幅を増やしたときの score 低下を防ぐには、candidate cap を単一リストで切るのではなく、lane ごとに quota を持たせるか、過去の小さい cap の候補集合を protected lane として残す必要がある。これは旧 basic search で有効だった protected candidate lanes と同じ考え方だが、craft では recipe / ingredient / placement の各段階に適用する必要がある。

## 未解決の論点

- Wynnbuilder の既存 JS を Worker でどこまで直接 import できるか。
- DOM 依存の強い処理をどこまで adapter 化すべきか。
- stat key の UI 表示名と内部 ID の対応表をどこから取るか。
- Ability Tree、Aspect、Powder、Tome をどの段階で探索条件に含めるか。
- candidate benchmark corpus をどの形式で保存するか。
