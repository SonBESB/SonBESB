"""CadQuery (OpenCASCADE) solid backend — experimental STEP/STL export only.

This is NOT the interactive preview path (see core/geometry/tube_mesh.py +
ui/plotly_view3d.py for that, which works without this module). This
backend exists solely so V0.2 can produce a real B-rep solid to validate
the segmented-elbow geometry and export it for external CAD inspection.

Import of cadquery is guarded: if it is not installed, CADQUERY_AVAILABLE
is False and build_solid() raises CadBackendUnavailableError with a clear
message, instead of the app failing to start.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cad.backends.base_backend import CadBackendUnavailableError, SolidCadBackend
from core.geometry.segmented_elbow import ElbowSegment, SegmentedElbowGeometry

try:
    import cadquery as cq

    CADQUERY_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when cadquery is absent
    cq = None
    CADQUERY_AVAILABLE = False

# How far a piece's hollow-cylinder stock overshoots its own two cut
# planes before being trimmed, as a multiple of OD. Generous margin keeps
# the trim solid valid even for the widest miter angles in this catalog.
_OVERSHOOT_OD_MULTIPLE = 3.0


def _require_cadquery() -> None:
    if not CADQUERY_AVAILABLE:
        raise CadBackendUnavailableError(
            "cadquery no esta instalado en este entorno. La exportacion STEP/STL "
            "es experimental y opcional; el resto de la aplicacion (incluida la "
            "vista previa 3D) no depende de cadquery. Instala con: pip install cadquery"
        )


def _build_piece_solid(piece: ElbowSegment, od_mm: float, id_mm: float) -> "cq.Workplane":
    reference_point = tuple((a + b) / 2 for a, b in zip(piece.axis_start, piece.axis_end))
    half_length = piece.length_mm / 2 + od_mm * _OVERSHOOT_OD_MULTIPLE

    plane = cq.Plane(origin=reference_point, normal=piece.direction)
    tube = cq.Workplane(plane).circle(od_mm / 2).circle(id_mm / 2).extrude(half_length, both=True)

    # Every cut_plane normal in a SegmentedElbowGeometry points in the same
    # overall P1->P2 flow sense (see segmented_elbow.py). So at a piece's
    # *start* plane the material to discard (the stock's overshoot before
    # this piece begins) lies on the -normal side, while at its *end*
    # plane the overshoot-to-discard lies on the +normal side. cadquery's
    # Workplane.extrude(distance) builds in the +normal direction of the
    # given plane, so the two cuts need opposite-signed extrude distances.
    cutter_size = od_mm * _OVERSHOOT_OD_MULTIPLE * 4
    for cut_plane, extrude_distance in (
        (piece.cut_plane_start, -cutter_size),
        (piece.cut_plane_end, cutter_size),
    ):
        cutter = (
            cq.Workplane(cq.Plane(origin=cut_plane.point, normal=cut_plane.normal))
            .rect(cutter_size, cutter_size)
            .extrude(extrude_distance)
        )
        tube = tube.cut(cutter)

    return tube


class CadQueryElbowBackend(SolidCadBackend):
    def build_solid(self, geometry: SegmentedElbowGeometry, od_mm: float, id_mm: float) -> Any:
        _require_cadquery()
        pieces = geometry.all_pieces
        solid = _build_piece_solid(pieces[0], od_mm, id_mm)
        for piece in pieces[1:]:
            solid = solid.union(_build_piece_solid(piece, od_mm, id_mm))
        return solid

    def export_step(self, solid: Any, output_path: Path) -> Path:
        _require_cadquery()
        solid.val().exportStep(str(output_path))
        return output_path

    def export_stl(self, solid: Any, output_path: Path) -> Path:
        _require_cadquery()
        solid.val().exportStl(str(output_path))
        return output_path
