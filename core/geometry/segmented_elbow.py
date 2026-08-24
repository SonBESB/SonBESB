"""3D mathematical model of a segmented (mitred) HDPE elbow.

This module builds the actual straight-cylinder-and-miter-cut geometry of
a segmented elbow, as opposed to core/geometry/elbow_geometry.py (kept
unchanged from V0.1), which only draws a smooth 2D arc approximation for
dimensional preview. Nothing here imports cadquery, Plotly or Streamlit —
see core/geometry/tube_mesh.py for the pure-numpy triangle mesh consumed
by the UI, and cad/backends/ for the optional CAD solid backend.

Construction (see docs/SEGMENTED_ELBOW_GEOMETRY.md for the full write-up):

  - Reuses the same vertex/tangent-point/arc-centre relations as
    core/geometry/elbow_geometry.py (dir1 fixed at 180°, dir2 at
    angle_deg, tangent length t = R*tan(angle/2)), embedded in the local
    XY plane (z=0) of a 3D frame.
  - Each catalog "Configuracion" entry (e.g. 15-30-30-15 for 90°) is
    interpreted as the arc span, in degrees, that one gajo (segment)
    occupies on the same R-radius circle already used for the tangent
    points. The segment joints are therefore points ON that circle, at
    cumulative angular offsets — which makes the first and last joints
    coincide exactly with the existing tangent points T1/T2. This is the
    most literal reading of numbers that sum exactly to the total angle;
    no pipefitting convention beyond that is assumed (see DATA_NOTES.md
    / SEGMENTED_ELBOW_GEOMETRY.md for the explicit call-out).
  - The two Le tangent runs are modelled as extra zero-angle "segments"
    (leg1_stub / leg2_stub) so every piece of the fitting — including the
    open ends at P1/P2 — is cut using the same miter-plane formula: the
    cutting plane at any joint bisects the direction of the two pieces
    that meet there (a symmetric miter join guarantees the two abutting
    cylinders' elliptical cut faces coincide). At P1/P2 there is only one
    piece, so the "bisector" degenerates to a plane perpendicular to that
    piece's own axis, i.e. a normal (non-mitred) open end.
  - When the source configuration is not itemized (30° in the supplied
    workbook), segments is None and no gajo geometry is produced — the
    two stubs are still returned (Le/T1/T2 are tabulated), leaving a
    visible, honest gap instead of guessed segmentation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from core.models.common import EndType, Port, Vector3
from core.models.elbow import ElbowParameters

ARC_START_ANGLE_DEG = -90.0  # same convention as core/geometry/elbow_geometry.py


def _vec3(x: float, y: float, z: float = 0.0) -> Vector3:
    return (x, y, z)


def _add(a: Vector3, b: Vector3, scale: float = 1.0) -> Vector3:
    return (a[0] + b[0] * scale, a[1] + b[1] * scale, a[2] + b[2] * scale)


def _sub(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: Vector3, b: Vector3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a: Vector3) -> float:
    return math.sqrt(_dot(a, a))


def _normalize(a: Vector3) -> Vector3:
    n = _norm(a)
    if n < 1e-12:
        raise ValueError("Cannot normalize a zero-length vector.")
    return (a[0] / n, a[1] / n, a[2] / n)


def _unit_xy(angle_deg: float) -> Vector3:
    rad = math.radians(angle_deg)
    return (math.cos(rad), math.sin(rad), 0.0)


def _bisector_normal(direction_before: Vector3, direction_after: Vector3) -> Vector3:
    """Miter-plane normal for two pieces meeting end-to-end.

    Degenerates cleanly to a perpendicular (non-mitred) cut when the two
    directions are identical, which is exactly what P1/P2's open ends
    need (see module docstring).
    """
    summed = _add(direction_before, direction_after)
    if _norm(summed) < 1e-9:
        raise ValueError("Cannot build a miter plane for two opposite directions (180 degree local turn).")
    return _normalize(summed)


@dataclass(frozen=True)
class Plane:
    point: Vector3
    normal: Vector3  # unit vector


@dataclass(frozen=True)
class ElbowSegment:
    """One physical straight piece of the fitting: a Le stub or a gajo."""

    index: int
    label: str
    angle_deg: float
    cumulative_angle_deg: float
    axis_start: Vector3
    axis_end: Vector3
    direction: Vector3
    cut_plane_start: Plane
    cut_plane_end: Plane

    @property
    def length_mm(self) -> float:
        return _norm(_sub(self.axis_end, self.axis_start))


@dataclass(frozen=True)
class SegmentedElbowGeometry:
    vertex: Vector3
    p1_face: Vector3
    p2_face: Vector3
    p1_direction: Vector3
    p2_direction: Vector3
    tangent_point_1: Vector3
    tangent_point_2: Vector3
    arc_center: Vector3
    radius_mm: float
    z_mm: float
    leg1_stub: ElbowSegment
    leg2_stub: ElbowSegment
    segments: Optional[List[ElbowSegment]]
    segments_available: bool
    unavailable_reason: Optional[str]
    ports: List[Port] = field(default_factory=list)

    @property
    def all_pieces(self) -> List[ElbowSegment]:
        """Every physical piece in P1->P2 order, gajos included when available."""
        middle = self.segments or []
        return [self.leg1_stub, *middle, self.leg2_stub]


def build_segmented_elbow_geometry(params: ElbowParameters) -> SegmentedElbowGeometry:
    angle_deg = params.angle_deg
    radius_mm = params.radius_mm
    le_mm = params.le_mm

    tangent_len = radius_mm * math.tan(math.radians(angle_deg) / 2)
    if params.z_mm is not None:
        z_mm = params.z_mm
    else:
        z_mm = le_mm + tangent_len

    vertex = _vec3(0.0, 0.0)
    dir1 = _unit_xy(180.0)
    dir2 = _unit_xy(angle_deg)

    p1_face = _add(vertex, dir1, z_mm)
    p2_face = _add(vertex, dir2, z_mm)
    t1 = _add(vertex, dir1, tangent_len)
    t2 = _add(vertex, dir2, tangent_len)
    arc_center = _vec3(t1[0], t1[1] + radius_mm)

    config = params.segment_configuration
    segments: Optional[List[ElbowSegment]] = None
    segments_available = False
    unavailable_reason = None

    joint_points: List[Vector3] = [t1, t2]
    gajo_directions: List[Vector3] = []

    if config and config.is_itemized and config.segment_angles_deg:
        offsets = [0.0]
        for a in config.segment_angles_deg:
            offsets.append(offsets[-1] + a)
        joint_points = [
            _add(arc_center, _unit_xy(ARC_START_ANGLE_DEG + off), radius_mm) for off in offsets
        ]
        gajo_directions = [
            _normalize(_sub(joint_points[i + 1], joint_points[i])) for i in range(len(config.segment_angles_deg))
        ]
        segments_available = True
    else:
        unavailable_reason = (
            config.source_text if config else "No hay configuracion de segmentos disponible para este angulo."
        )

    # Build the full ordered direction sequence (stub, gajos..., stub),
    # every entry in the *same* axis_start->axis_end ("flow", P1->P2)
    # sense that gajo_directions already uses — NOT the outward,
    # away-from-vertex sense of dir1 (that convention is only correct for
    # leg2_stub, since t2->p2_face happens to point along +dir2; leg1_stub
    # goes p1_face->t1, which points along -dir1). Mixing the two
    # conventions would make _bisector_normal average two direction
    # vectors that face opposite ways, producing a miter plane
    # perpendicular to the correct one instead of bisecting it.
    leg1_flow_direction = _normalize(_sub(t1, p1_face))
    leg2_flow_direction = _normalize(_sub(p2_face, t2))
    piece_directions = [leg1_flow_direction, *gajo_directions, leg2_flow_direction]
    # Pad with the sequence's own first/last entries (not dir1/dir2) so the
    # P1/P2 end-cut bisector is self-paired (bisector(d, d) = d), giving a
    # plane perpendicular to that piece's own axis regardless of sign.
    padded_directions = [piece_directions[0], *piece_directions, piece_directions[-1]]
    cut_planes: List[Plane] = []
    piece_points = [p1_face, t1, *joint_points[1:-1], t2, p2_face]
    for k in range(len(piece_directions) + 1):
        normal = _bisector_normal(padded_directions[k], padded_directions[k + 1])
        cut_planes.append(Plane(point=piece_points[k], normal=normal))

    leg1_stub = ElbowSegment(
        index=0,
        label="Tramo recto Le (lado P1)",
        angle_deg=0.0,
        cumulative_angle_deg=0.0,
        axis_start=p1_face,
        axis_end=t1,
        direction=leg1_flow_direction,
        cut_plane_start=cut_planes[0],
        cut_plane_end=cut_planes[1],
    )

    if segments_available:
        offsets_deg = [0.0]
        for a in config.segment_angles_deg:
            offsets_deg.append(offsets_deg[-1] + a)
        segments = []
        for i, a in enumerate(config.segment_angles_deg):
            segments.append(
                ElbowSegment(
                    index=i + 1,
                    label=f"Gajo {i + 1}",
                    angle_deg=a,
                    cumulative_angle_deg=offsets_deg[i + 1],
                    axis_start=joint_points[i],
                    axis_end=joint_points[i + 1],
                    direction=gajo_directions[i],
                    cut_plane_start=cut_planes[i + 1],
                    cut_plane_end=cut_planes[i + 2],
                )
            )

    leg2_index = len(piece_directions) - 1  # 0-based index of the last piece
    leg2_stub = ElbowSegment(
        index=leg2_index,
        label="Tramo recto Le (lado P2)",
        angle_deg=0.0,
        cumulative_angle_deg=angle_deg,
        axis_start=t2,
        axis_end=p2_face,
        direction=leg2_flow_direction,
        cut_plane_start=cut_planes[leg2_index],
        cut_plane_end=cut_planes[leg2_index + 1],
    )

    ports = [
        Port(
            id="P1",
            position_mm=p1_face,
            direction=dir1,
            nominal_diameter_mm=params.dn_mm,
            outside_diameter_mm=params.od_mm,
            end_type=params.end_type,
        ),
        Port(
            id="P2",
            position_mm=p2_face,
            direction=dir2,
            nominal_diameter_mm=params.dn_mm,
            outside_diameter_mm=params.od_mm,
            end_type=params.end_type,
        ),
    ]

    return SegmentedElbowGeometry(
        vertex=vertex,
        p1_face=p1_face,
        p2_face=p2_face,
        p1_direction=dir1,
        p2_direction=dir2,
        tangent_point_1=t1,
        tangent_point_2=t2,
        arc_center=arc_center,
        radius_mm=radius_mm,
        z_mm=z_mm,
        leg1_stub=leg1_stub,
        leg2_stub=leg2_stub,
        segments=segments,
        segments_available=segments_available,
        unavailable_reason=unavailable_reason,
        ports=ports,
    )
