"""FastAPI server for wynnBuildGenerator build search."""

from __future__ import annotations

import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

# Ensure wynn_builder_compat and python/search are importable
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE / "wynn_builder_compat" / "src"))
sys.path.insert(0, str(_HERE / "python"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from wynn_builder_compat.data import WynnData
from search.item_index import ItemIndex, SLOT_NAMES
from search.numpy_evaluator import NumpyEvaluator, STAT_KEYS
from search.beam_search import beam_search
from search.final_evaluator import evaluate_batch, evaluate_single


@asynccontextmanager
async def _lifespan(application: FastAPI):
    _get_wynn()
    _get_item_index()
    _get_evaluator()
    yield


app = FastAPI(title="wynnBuildGenerator API", version="0.1.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global state: load data once at startup ---

_wynn: WynnData | None = None
_item_index: ItemIndex | None = None
_evaluator: NumpyEvaluator | None = None


def _get_wynn() -> WynnData:
    global _wynn
    if _wynn is None:
        _wynn = WynnData.from_root()
    return _wynn


def _get_item_index() -> ItemIndex:
    global _item_index
    if _item_index is None:
        _item_index = ItemIndex(_get_wynn())
    return _item_index


def _get_evaluator() -> NumpyEvaluator:
    global _evaluator
    if _evaluator is None:
        wynn = _get_wynn()
        from wynn_builder_compat.data import prepare_item_from_clean
        all_prepared = [prepare_item_from_clean(item) for item in wynn.items]
        _evaluator = NumpyEvaluator(all_prepared)
    return _evaluator


# --- Request / Response models ---

class SearchRequest(BaseModel):
    class_: str = Field(alias="class")
    level: int
    conditions: list[dict[str, Any]] = []
    scoring: dict[str, Any] = Field(
        default_factory=lambda: {"maximize": {}, "minimize": {}}
    )
    fixed_items: dict[str, str | None] = {}
    search_params: dict[str, Any] = {}

    model_config = {"populate_by_name": True}


class SearchResponse(BaseModel):
    results: list[dict[str, Any]]
    elapsed_ms: float
    total_candidates_evaluated: int


# --- Endpoints ---

@app.post("/api/search", response_model=SearchResponse)
def search_builds(req: SearchRequest) -> SearchResponse:
    t0 = time.perf_counter()

    params = req.search_params or {}
    beam_width: int = int(params.get("beam_width", 50))
    max_candidates_per_slot: int = int(params.get("max_candidates_per_slot", 40))
    result_limit: int = int(params.get("result_limit", 10))

    wynn = _get_wynn()
    item_index = _get_item_index()
    evaluator = _get_evaluator()

    # Convert fixed_items from slot_name -> item_name to slot_idx -> item_name
    fixed_slot_idx: dict[int, str | None] = {}
    for slot_name, item_name in req.fixed_items.items():
        if slot_name in SLOT_NAMES:
            fixed_slot_idx[SLOT_NAMES.index(slot_name)] = item_name

    # Build slot candidates
    slot_candidates: list[list[dict[str, Any]]] = []
    for slot_idx in range(9):
        fixed_name = fixed_slot_idx.get(slot_idx, ...)  # sentinel for "not fixed"
        if fixed_name is ...:
            candidates = item_index.candidates_for_slot(
                slot_idx,
                req.class_,
                req.level,
            )
            # Limit candidates per slot
            if max_candidates_per_slot > 0:
                candidates = candidates[:max_candidates_per_slot]
        else:
            # Fixed slot: pass through to beam_search as fixed
            candidates = item_index.candidates_for_slot(
                slot_idx,
                req.class_,
                req.level,
                fixed_name=fixed_name,
            )
        slot_candidates.append(candidates)

    # Beam search
    max_retries = 2
    current_beam_width = beam_width
    beam_results: list[list[str | None]] = []

    for attempt in range(max_retries + 1):
        beam_results = beam_search(
            slot_candidates=slot_candidates,
            fixed_items=fixed_slot_idx,
            beam_width=current_beam_width,
            evaluator=evaluator,
            scoring=req.scoring,
            conditions=req.conditions,
        )

        # Final evaluation on top candidates
        eval_limit = result_limit * 3
        top_candidates = beam_results[:eval_limit]

        final_results = []
        for item_names in top_candidates:
            try:
                result = evaluate_single(item_names, req.level, wynn, req.scoring, req.conditions)
                if result.conditions_met:
                    final_results.append(result)
            except Exception:
                pass

        if len(final_results) >= result_limit or attempt >= max_retries:
            break

        # Retry with doubled beam width
        current_beam_width *= 2

    # Sort by score descending, take top result_limit
    final_results.sort(key=lambda r: r.score, reverse=True)
    final_results = final_results[:result_limit]

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    serialized = []
    for r in final_results:
        # Convert stat_map: filter out non-serializable values (sets, dicts)
        stat_map_clean: dict[str, Any] = {}
        for k, v in r.stat_map.items():
            if isinstance(v, (int, float, str, bool)):
                stat_map_clean[k] = v
            elif isinstance(v, set):
                stat_map_clean[k] = list(v)
            elif isinstance(v, dict):
                stat_map_clean[k] = v

        serialized.append({
            "equipment": r.equipment_names,
            "weapon": r.weapon_name,
            "score": r.score,
            "score_breakdown": r.score_breakdown,
            "conditions_met": r.conditions_met,
            "skillpoints_valid": r.skillpoints_valid,
            "build_hash": r.build_hash,
            "level": r.level,
            "stat_map": stat_map_clean,
        })

    return SearchResponse(
        results=serialized,
        elapsed_ms=elapsed_ms,
        total_candidates_evaluated=len(top_candidates),
    )


@app.get("/api/items")
def list_items(q: str = "", limit: int = 50) -> dict[str, Any]:
    """Return item names for autocomplete. Optionally filter by query substring."""
    wynn = _get_wynn()
    names = [
        item.get("displayName") or item.get("name", "")
        for item in wynn.items
        if item.get("displayName") or item.get("name")
    ]
    if q:
        q_lower = q.lower()
        names = [n for n in names if q_lower in n.lower()]
    return {"items": names[:limit]}


@app.get("/api/stat_keys")
def list_stat_keys() -> dict[str, Any]:
    """Return all available stat keys for scoring/condition configuration."""
    return {"stat_keys": STAT_KEYS}


# Serve static files from the wynnBuildGenerator directory (index.html etc.)
_static_dir = _HERE
if (_static_dir / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
