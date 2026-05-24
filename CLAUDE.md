# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WynnBuilder is a **client-side static site** for the MMORPG Wynncraft. No build step, no package manager, no server. Everything runs directly in the browser. The site consists of several tools:

- **WynnBuilder** (`builder/`) — Equipment build calculator with damage, skillpoints, ability tree, tomes, and aspects
- **WynnCrafter** (`crafter/`) — Crafted item recipe calculator
- **WynnAtlas** (`items/`, `items_adv/`) — Item search with filters
- **WynnCustom** (`custom/`) — Custom item creator
- **WynnGPS** (`map/`) — In-game map with location search

## Development Workflow

Since there is no dev server or build process, open HTML files directly in a browser or serve from a local static file server:

```
python -m http.server 8080
```

Then visit `http://localhost:8080/builder/` etc.

The `builder/index.html` is minified — the **readable source is `builder/index_full.html`**. Edit `index_full.html` and then minify into `index.html` when shipping.

## Data Update Workflow

Game data lives in `data/<version>/` (e.g. `data/2.0.2.3/`). To update for a new Wynncraft patch:

1. Run `py_script/v3_process_items.py` (from `py_script/`) to regenerate `items`, `tomes`, `ingreds` JSON.
2. Optionally run `py_script/process_recipes.py` for crafting recipes.
3. Copy generated files into the new version folder and update the compressed root files (`*compress.json`).
4. Run `py_script/get_aspects.py` to check for new/changed aspects and update manually.
5. Update `js/builder/atree_constants.json` and `js/builder/major_ids_clean.json` if the ability tree changed.
6. From `js/builder/`, run `python3 ../../py_script/atree-generateID.py` to compile/minify atree and major IDs. Copy the resulting `*_min/*.json` / `*_clean.json` files into `data/<ver>/`.
7. Run `py_script/research/plot_dps.py` to regenerate DPS data.
8. Run `py_script/encoding_gen_const.py <ver>` to preview encoding constants, then add `--write` to write `data/<ver>/encoding_consts.json`.

**Never edit `atree.json` or `major_ids_clean.json` directly in `data/`** — those are generated outputs. Edit only `js/builder/atree_constants.json` and `js/builder/major_ids_clean.json`.

## Architecture

### Data Loading (`js/loader.js`, `js/load_*.js`)

All game data (items, ingredients, tomes, aspects) flows through the `Loader` base class pattern:

- **Remote path** → fetches compressed JSON, writes to IndexedDB
- **Local path** → reads from IndexedDB (cached from prior visit)
- **Old version path** → loads a historical data version directly (no IndexedDB caching)

After loading, each loader calls `init_maps()` to populate in-memory lookup maps (`itemMap`, `idMap`, `tomeIDMap`, etc.).

Data versioning: `js/load_item.js` contains `wynn_version_names` (array mapping integer version IDs to folder names like `"2.0.2.3"`). `WYNN_VERSION_LATEST` points to the current version. Build hashes encode which version they were built with; loading an old hash triggers `loadOlderVersion()` which offers an upgrade prompt.

### Computation Graph (`js/computation_graph.js`)

The builder page uses a **reactive computation graph** instead of imperative recalculation. `ComputeNode` instances declare their inputs; when a node is marked dirty it propagates dirtiness to children and recalculates lazily. The graph is wired up in `js/builder/builder_graph.js`. When touching build logic, you need to understand which nodes depend on each other.

### Build Encoding (`ENCODING.md`, `js/builder/build_encode_decode.js`)

Builds are stored as compact Base64 strings in the URL hash. The current binary format is **V12**. Key points:

- IDs are stable across versions; the bit-width of each ID field is dynamically determined per-version from `data/<ver>/encoding_consts.json`.
- The first 6 bits determine legacy vs binary decoding (≤11 = legacy).
- Crafted items and custom items have their own self-contained sub-encodings embedded in the build hash.
- `py_script/encoding_gen_const.py` generates `encoding_consts.json` and validates backward compatibility.

### Build Calculation

- `js/builder/build.js` — `Build` class: aggregates items into a `statMap`, handles skillpoint calculation and equip order.
- `js/damage_calc.js` — spell and melee damage formulas.
- `js/build_utils.js` — helper formulas: `skillPointsToPercentage`, `levelToSkillPoints`, element/damage constants.
- `js/skillpoints.js` — skillpoint assignment solver (equip order permutation logic).
- `js/builder/atree.js` — ability tree rendering and state.
- `js/builder/aspects.js` — aspect slot logic.

### Item Data Format

Items are processed from Wynncraft API format by `py_script/v3_process_items.py` into a normalized schema. `js/load_item.js:clean_item()` applies post-load normalization. Stat IDs use Wynncraft's internal key names (e.g. `sdPct`, `mdRaw`, `eDamPct`, `hprRaw`). Element prefix convention: `e`=Earth, `t`=Thunder, `w`=Water, `f`=Fire, `a`=Air.

### Frontend

No frameworks — vanilla JS with Bootstrap 5 for layout and autoComplete.js for item search inputs. CSS is split by page and viewport width (`*-narrow.css` / `*-wide.css`). The `thirdparty/` directory contains vendored libraries (Bootstrap, autoComplete, Macy.js for masonry layout).
