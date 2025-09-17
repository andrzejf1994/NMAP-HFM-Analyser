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
    values: Dict[str, float]
    path: str


__all__ = ["FoundFile", "ParamSnapshot"]
