"""Abstract CAD solid backend interface.

Deliberately generic: SegmentedElbowGeometry -> some opaque "solid" object
-> STEP/STL bytes on disk. cad/backends/cadquery_backend.py is the only
concrete implementation right now; keeping this interface separate from it
is what lets core/geometry stay free of the cadquery dependency (see
core/geometry/segmented_elbow.py docstring) and leaves room for a
different backend later without touching callers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from core.geometry.segmented_elbow import SegmentedElbowGeometry


class CadBackendUnavailableError(Exception):
    """Raised when the concrete backend's dependency (e.g. cadquery) is not installed."""


class SolidCadBackend(ABC):
    @abstractmethod
    def build_solid(self, geometry: SegmentedElbowGeometry, od_mm: float, id_mm: float) -> Any:
        """Builds an opaque solid object for the given geometry."""

    @abstractmethod
    def export_step(self, solid: Any, output_path: Path) -> Path:
        ...

    @abstractmethod
    def export_stl(self, solid: Any, output_path: Path) -> Path:
        ...
