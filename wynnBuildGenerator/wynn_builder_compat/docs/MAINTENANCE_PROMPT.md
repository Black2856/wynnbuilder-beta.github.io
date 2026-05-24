# Maintenance Prompt

最終更新: 2026-05-24

## 目的

この文書は、AI に Python 互換エンジンの移植・更新・保守を依頼するときに最初に読み込ませるプロンプトである。Wynnbuilder JavaScript と Python 実装の parity を守ることを最優先にする。

## Prompt

You are maintaining `wynnBuildGenerator`, a Python-compatible search engine for Wynnbuilder.

Read these documents first:

1. `wynnBuildGenerator/docs/REQUIREMENTS.md`
2. `wynnBuildGenerator/docs/ARCHITECTURE.md`
3. `wynnBuildGenerator/wynn_builder_compat/docs/PORTING_STRATEGY.md`
4. `wynnBuildGenerator/wynn_builder_compat/docs/PARITY_TESTING.md`
5. `wynnBuildGenerator/wynn_builder_compat/docs/FORMULA_MAP.md`
6. `wynnBuildGenerator/docs/OLD_IMPLEMENTATION_NOTES.md`

Hard requirements:

- Wynnbuilder JavaScript is the source of truth.
- Python code must not become an independent formula source.
- `wynn_builder_compat` is strictly for porting Wynnbuilder JS logic. Every file here must have a corresponding JS source function listed in `FORMULA_MAP.md`. Generator-specific logic (scoring, condition evaluation, beam search, NumPy evaluator) belongs in `wynnBuildGenerator/python/search/`, not here.
- Every ported formula needs JS/Python parity coverage.
- Do not optimize by changing behavior unless parity tests prove the output is unchanged.
- For crafted search, preserve edge cases involving positive boosters, negative boosters, durability, and condition/score tradeoffs.
- If a JS behavior is unclear, add a fixture exporter case before changing Python logic.
- If parity fails, fix Python to match JS unless the user explicitly decides to change Wynnbuilder itself.

Maintenance workflow:

1. Identify the JS source function from `FORMULA_MAP.md`.
2. Read the exact JS implementation.
3. Locate or create the Python target function.
4. Add or update a fixture that exercises the behavior.
5. Run parity tests.
6. Fix Python until parity passes.
7. Only then update search or optimization code.
8. Document new findings in `docs/`.

For crafted search changes:

- Never rely on one global top-N ingredient list.
- Preserve separate lanes for direct score, condition, score-high/condition-bad, positive booster, negative booster, durability, and mixed synergy.
- Increasing ingredient pool size, candidate cap, or recipe count must not lower the representative top score in regression fixtures.
- Negative effectiveness can invert negative stats into positive contribution; include these cases in tests.
- A material that worsens a condition may still be required for the best score; do not prune it only because it hurts one condition.

For performance changes:

- Measure candidate generation, placement optimization, build evaluation, and parity validation separately.
- Prefer cache, vectorization, batch evaluation, and lane stability before hard pruning.
- Hard pruning is allowed only when a benchmark corpus proves it does not remove expected top candidates.
- The search engine uses a two-layer evaluator: NumPy vectorized pruning (approximate, no set bonus/skillpoints) and the parity-tested final evaluator (`build_stat_map()` + `calculate_skillpoints()`). Do not merge these layers.
- NumPy pruning evaluator lives in `wynnBuildGenerator/python/search/numpy_evaluator.py`. Final evaluator uses `wynn_builder_compat` directly.
- Final evaluation is parallelized with `ProcessPoolExecutor`. Worker count defaults to `os.cpu_count()`. Do not apply multiprocessing to the beam expansion loop itself.
- After changing the pruning evaluator, run benchmarks to confirm that top candidates are not dropped compared to final evaluator results.

Expected final response after maintenance:

- Summary of changed files.
- Which JS source functions were matched.
- Which parity fixtures were added or updated.
- Test commands run and results.
- Any remaining parity gaps or unimplemented formula areas.

## Short Version

Use this shorter prompt when context is limited:

```text
Maintain wynnBuildGenerator's Python compatibility engine. Wynnbuilder JS is the source of truth. Read wynn_builder_compat/docs/PORTING_STRATEGY.md, wynn_builder_compat/docs/PARITY_TESTING.md, and wynn_builder_compat/docs/FORMULA_MAP.md. Port only the required JS logic into wynn_builder_compat/ (every file must have a JS source in FORMULA_MAP.md). Generator-specific logic (scoring, conditions, beam search, NumPy evaluator) belongs in python/search/, not wynn_builder_compat/. Add JS/Python parity fixtures and fix Python until parity passes. For crafted search, preserve positive booster, negative booster, durability, and condition/score tradeoff cases. Do not let larger candidate caps lower benchmark top scores. Document findings in docs/.
```
