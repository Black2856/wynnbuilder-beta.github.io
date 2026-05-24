# Benchmark Notes

最終更新: 2026-05-24

## 測定方法

`python/search/benchmarks.py` で各フェーズの時間を計測する。

測定対象:
1. 候補生成 (`candidates_for_slot` × 9 スロット)
2. Beam 展開 (`beam_search`)
3. 最終評価 (`evaluate_single` × 上位 N 件)
4. 全体 (`/api/search` 応答時間)

## 実測値 (2026-05-24, warrior lv106, HP + sdRaw maximize)

| beam_width | max_candidates_per_slot | API 応答時間 (ms) | top_score |
|-----------|------------------------|-----------------|-----------|
| 20        | 20                      | ~50             | 23721.0   |
| 50        | 40                      | ~170            | 27231.0   |
| 100       | 80                      | ~600            | 28346.0   |

環境: Windows 11, Python 3.11

## 注意事項

- 初回アクセス時はデータロードで追加時間が発生する (以降はキャッシュ済み)。
- `ProcessPoolExecutor` による最終評価の並列化は Windows spawn context の制約により、
  現状はシーケンシャルフォールバックが動作している。
- NumPy pruning evaluator (beam search 中の近似スコア) は final evaluator に比べ大幅に高速。
  set bonus・skillpoints を除外しているため、上位候補の一部が final evaluator で
  SP不足になる場合がある。

## 精度保証上の注意

- `score_monotonicity` fixture のとおり、beam_width/max_candidates を増やすとスコアは改善する。
  これは beam search の greedy 性質によるもので期待通りの動作。
- 上位 10 件の pruning miss rate は 0 件を維持すること (Phase 4-2 要件)。
  beam_width を大幅に縮小した場合、良い候補が落ちる可能性がある。
