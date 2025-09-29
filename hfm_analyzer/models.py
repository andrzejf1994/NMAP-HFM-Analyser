"""Dataclasses used across the HFM Analyzer application."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict


@dataclass(slots=True)
class FoundFile:
    """Descriptor for a backup XML file discovered on disk."""

    machine: str
    dt: datetime
    path: str


@dataclass(slots=True)
class ParamSnapshot:
    """Single snapshot of parameters extracted from a backup file."""

    dt: datetime
    machine: str
    program: str
    table: str
    pin: str
    step: int
    values: Dict[str, float | None]
    included: Dict[str, bool]
    modes: Dict[str, str]
    path: str


@dataclass(slots=True)
class IndexSnapshot:
    """Snapshot of table index parameters extracted from a backup file."""

    dt: datetime
    machine: str
    program: str
    table: str
    step: int
    values: Dict[str, float]
    included: Dict[str, bool]
    modes: Dict[str, str]
    override: float | None
    path: str


@dataclass(slots=True)
class GripSnapshot:
    """Snapshot describing HP grip configuration for a specific pin."""

    dt: datetime
    machine: str
    program: str
    pin: str
    values: Dict[str, str]
    path: str


@dataclass(slots=True)
class NestSnapshot:
    """Snapshot describing nest configuration for a specific pin."""

    dt: datetime
    machine: str
    program: str
    pin: str
    values: Dict[str, str]
    path: str


@dataclass(slots=True)
class HairpinSnapshot:
    """Snapshot describing hairpin manager configuration for a specific pin."""

    dt: datetime
    machine: str
    program: str
    pin: str
    values: Dict[str, str]
    path: str


__all__ = [
    "FoundFile",
    "ParamSnapshot",
    "IndexSnapshot",
    "GripSnapshot",
    "NestSnapshot",
    "HairpinSnapshot",
]
