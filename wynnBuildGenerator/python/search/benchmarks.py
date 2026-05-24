"""Benchmark helpers for search experiments."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkResult:
    case_id: str
    elapsed_ms: float
    top_score: float | None
    candidate_count: int

