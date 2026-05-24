"""Shared data models for the Python compatibility layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CompatItem:
    """Small Python stand-in for a Wynnbuilder Item.statMap-like object."""

    name: str
    stat_map: dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.stat_map.get(key, default)


@dataclass
class CraftPreview:
    """Result shape for a crafted item preview."""

    requirements: dict[str, float] = field(default_factory=dict)
    identifications: dict[str, float] = field(default_factory=dict)
    base: dict[str, Any] = field(default_factory=dict)
    durability: float = 0.0
    duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

