"""Abstract exporter interface for future AutoCAD Plant 3D integration.

IMPORTANT: nothing in this file talks to Plant 3D. There is no real
`PLANTREGISTERCUSTOMSCRIPTS` call, no Plant 3D Python module import, and no
invented decorator or class from the Plant 3D SDK. This is intentionally a
placeholder that defines *the shape* of a future exporter so the rest of
the app (components, geometry, JSON export) can already depend on a stable
interface.

Planned pipeline (not implemented yet):

    ElbowParameters -> ComponentExporter.export() -> Plant 3D CustomScript (.py)
        -> PLANTREGISTERCUSTOMSCRIPTS -> Catalog -> Spec -> AutoCAD Plant 3D

Each step above will be built and validated against real Plant 3D
documentation/behavior in a later stage of this project, not guessed here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from core.models.elbow import ElbowParameters


class ComponentExporter(ABC):
    """Base class a future Plant3DCustomScriptExporter would implement."""

    @abstractmethod
    def export(self, params: ElbowParameters, output_path: Path) -> Path:
        """Writes a Plant 3D-compatible artifact for params and returns its path.

        Not implemented in V0.1 — raise NotImplementedError from any
        concrete subclass added before the Plant 3D integration stage
        actually begins, rather than emitting fabricated script content.
        """
        raise NotImplementedError(
            "Plant 3D export is a future project stage; no exporter is implemented yet."
        )
