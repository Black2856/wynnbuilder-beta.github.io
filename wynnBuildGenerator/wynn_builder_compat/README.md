# wynn_builder_compat

`wynn_builder_compat` は、Wynnbuilder JavaScript の計算ロジックを Python で再現するための互換レイヤーです。Wynnbuilder JS を仕様の正とし、Python 側は探索高速化のために使います。

## Layout

```text
wynn_builder_compat/
  src/wynn_builder_compat/   Python compatibility modules
  tests/                     pytest unit and parity tests
  tools/export_js_fixtures/  Node.js fixture exporters
  docs/                      porting and maintenance notes
```

## Implemented Areas

- `build_utils.py`: level and skill point helper parity
- `craft.py`: crafted equipment preview parity for all equipment categories
- `data.py`: `clean.json`, `ingreds_clean.json`, `recipes_clean.json` loader and lookup facade
- `skillpoints.py`: low-level helpers and `calculate_skillpoints()` parity for synthetic and real `clean.json` item builds

Current JS fixture exporters:

- `build_utils_fixture.mjs`
- `craft_effectiveness_fixture.mjs`
- `craft_preview_fixture.mjs`
- `skillpoints_fixture.mjs`

## Maintenance Workflow

1. Read `docs/MAINTENANCE_PROMPT.md`.
2. Check the relevant source mapping in `docs/FORMULA_MAP.md`.
3. Read the current Wynnbuilder JS implementation.
4. Add or update a JS fixture exporter that captures the expected behavior.
5. Update Python code under `src/wynn_builder_compat/`.
6. Run parity tests and fix Python until JS/Python outputs match.
7. Update docs with newly covered or still-missing behavior.

Do not change Python formulas by intuition. Capture the JS behavior first, then port it.

## Running Tests

Run from `wynnBuildGenerator/`:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest -p no:cacheprovider
```

Node.js is required for JS/Python parity tests. If Node.js is unavailable, those tests are skipped.

## Data Access Example

```python
from wynn_builder_compat.data import WynnData

data = WynnData.from_root("..")
item = data.item("Alstroemania")
recipe = data.recipe("Ring-103-105", normalized=True)
ingredients = data.ingredients_for_skill("ARMOURING")
```

## Remaining Work

See `docs/REMAINING_WORK.md` for the detailed handoff list.

- Add decoded Wynnbuilder URL/build fixtures for `calculate_skillpoints()`.
- Port full build stat aggregation.
- Port condition and score evaluators from `wynnBuildGenerator_old` while keeping Wynnbuilder stat semantics.
- Add parity for powder ingredient and consumable craft branches if they become search targets.
- Add display key and numeric formatting parity.
