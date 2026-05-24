# Repository Guidelines

## Project Structure & Module Organization

This repository is a client-side Wynncraft utility site. Entry pages live at the root and in feature directories such as `builder/`, `crafter/`, `atlas/`, `items/`, `ingredients/`, `map/`, and `wynnfo/`. Shared browser code is in `js/`, with builder-specific logic in `js/builder/`. Styles are in `css/`; images, icons, audio, and PDFs are in `media/` and `wynnfo/pdfs/`. Large game data files are stored at the root and under `data/`. Python data/update helpers live in `py_script/`, while exploratory scripts are in `testing/`. `wynnBuildGenerator_old/` is an archived Python implementation; do not treat it as active unless explicitly restoring it.

## Build, Test, and Development Commands

No package manager build is required for the main site. Serve the repository locally when browser module loading or relative paths matter:

```powershell
python -m http.server 8000
```

Open `http://localhost:8000/builder/` or another feature path. Validate JSON before committing data changes:

```powershell
python -m json.tool clean.json > $null
python py_script/validate.py clean.json
```

For data refreshes, follow `py_script/README.md`; examples include `python py_script/v3_process_items.py`, `python py_script/process_recipes.py`, and `python py_script/encoding_gen_const.py <version> --write`.

## Coding Style & Naming Conventions

Use plain JavaScript, HTML, CSS, JSON, and Python consistent with nearby files. JavaScript identifiers are generally `camelCase`; Python files and functions use `snake_case`; constants use `UPPER_SNAKE_CASE`. Keep indentation consistent with the edited file, commonly 4 spaces in Python and 2-4 spaces in frontend files. Prefer existing helpers in `js/utils.js`, `js/display.js`, and `js/builder/` before adding new global utilities.

## Testing Guidelines

There is no unified automated test suite for the static site. For UI changes, manually test the affected page through a local HTTP server and check the browser console. For data changes, run JSON validation and relevant scripts under `py_script/` or `testing/`. Name new Python tests `test_*.py` if introducing pytest-based coverage.

## Commit & Pull Request Guidelines

Recent history uses short, descriptive messages, often lowercase summaries such as `tether fix + t4 amps` or data update notes like `gen data for 2.2.0_31`. Keep commits focused and mention affected features or data versions. Pull requests should include a concise summary, validation commands run, linked issues when applicable, and screenshots for visible UI changes.

## Data & Configuration Notes

Large generated JSON files are part of the runtime surface; avoid hand-editing them without documenting the source and regeneration path. Do not commit local server artifacts, caches, or temporary analysis output.
