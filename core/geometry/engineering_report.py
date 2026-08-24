"""Fabrication/engineering report for a segmented elbow — V0.2.1.

This module does NOT introduce any new geometric hypothesis. It only
*reads out* dimensions from an already-built SegmentedElbowGeometry, using
formulas kept deliberately independent from the ones used to build that
geometry in the first place (see the module docstring of
core/geometry/segmented_elbow.py and docs/GEOMETRY_VALIDATION_REFERENCE.md
for which parts are Excel data, which are equations, and which are
modeling hypotheses still awaiting comparison against a physical/CAD
reference).

Nothing here talks to Streamlit, Plotly or cadquery.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

from core.geometry.segmented_elbow import ElbowSegment, SegmentedElbowGeometry
from core.geometry.tube_mesh import build_piece_meshes
from core.models.elbow import ElbowParameters

Vector3 = Tuple[float, float, float]


def _dist(a: Vector3, b: Vector3) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _midpoint(a: Vector3, b: Vector3) -> Vector3:
    return tuple((x + y) / 2 for x, y in zip(a, b))


def _add(a: Vector3, b: Vector3, scale: float = 1.0) -> Vector3:
    return tuple(x + y * scale for x, y in zip(a, b))


def _sub(a: Vector3, b: Vector3) -> Vector3:
    return tuple(x - y for x, y in zip(a, b))


def _dot(a: Vector3, b: Vector3) -> float:
    return sum(x * y for x, y in zip(a, b))


def _angle_between_deg(a: Vector3, b: Vector3) -> float:
    na, nb = math.sqrt(_dot(a, a)), math.sqrt(_dot(b, b))
    cos_angle = max(-1.0, min(1.0, _dot(a, b) / (na * nb)))
    return math.degrees(math.acos(cos_angle))


def _in_plane_perpendicular(direction: Vector3) -> Vector3:
    """A 90-degree in-plane rotation of `direction` (both assumed z=0,
    valid for every direction this planar-elbow engine produces)."""
    return (-direction[1], direction[0], 0.0)


def _extrados_direction(piece: ElbowSegment, arc_center: Vector3) -> Vector3:
    """Unit vector, perpendicular to the piece's own axis, pointing away
    from arc_center (the "long side" of a miter cut on a curving pipe)."""
    perp = _in_plane_perpendicular(piece.direction)
    midpoint = _midpoint(piece.axis_start, piece.axis_end)
    plus = _add(midpoint, perp)
    minus = _add(midpoint, perp, -1.0)
    chosen = perp if _dist(plus, arc_center) > _dist(minus, arc_center) else tuple(-c for c in perp)
    norm = math.sqrt(_dot(chosen, chosen))
    return tuple(c / norm for c in chosen)


def _line_plane_intersection(point_on_line: Vector3, direction: Vector3, plane_point: Vector3, plane_normal: Vector3) -> Vector3:
    denom = _dot(plane_normal, direction)
    t = _dot(_sub(plane_point, point_on_line), plane_normal) / denom
    return _add(point_on_line, direction, t)


def _generatrix_length(piece: ElbowSegment, radial_dir: Vector3, radius_mm: float) -> float:
    """Length of the straight wall line at angular position `radial_dir`,
    trimmed between the piece's own two cut planes — i.e. the real
    fabrication length a pipefitter would mark on that side of the pipe."""
    reference = _midpoint(piece.axis_start, piece.axis_end)
    base = _add(reference, radial_dir, radius_mm)
    p_start = _line_plane_intersection(base, piece.direction, piece.cut_plane_start.point, piece.cut_plane_start.normal)
    p_end = _line_plane_intersection(base, piece.direction, piece.cut_plane_end.point, piece.cut_plane_end.normal)
    return _dist(p_start, p_end)


def _cut_plane_angle_deg(piece: ElbowSegment, which: str) -> float:
    """Deviation of a cut plane from a square (perpendicular-to-axis) cut.

    0 degrees = square cut (only true at the open P1/P2 ends). Computed as
    the angle between the piece's own axis and the plane's normal.
    """
    plane = piece.cut_plane_start if which == "start" else piece.cut_plane_end
    angle = _angle_between_deg(piece.direction, plane.normal)
    return min(angle, 180.0 - angle)


@dataclass(frozen=True)
class GajoFabricationRow:
    gajo: str
    angle_deg: float
    cumulative_angle_deg: float
    axis_length_mm: float
    outer_length_approx_mm: float
    inner_length_approx_mm: float
    start_point_mm: Vector3
    end_point_mm: Vector3
    direction: Vector3
    start_cut_plane_angle_deg: float
    end_cut_plane_angle_deg: float


@dataclass(frozen=True)
class UnionRow:
    label: str
    position_mm: Vector3
    distance_to_next_mm: float


@dataclass(frozen=True)
class OverallDimensions:
    width_mm: float  # X extent of the whole solid envelope
    height_mm: float  # Z extent (out-of-plane; exactly OD for a planar elbow)
    length_mm: float  # Y extent of the whole solid envelope
    p1_p2_distance_mm: float
    p1_to_vertex_mm: float
    p2_to_vertex_mm: float
    radius_used_mm: float
    z_resultant_mm: float


def build_fabrication_table(params: ElbowParameters, geometry: SegmentedElbowGeometry) -> List[GajoFabricationRow]:
    """One row per gajo. Empty when the source doesn't itemize segments
    (e.g. 30 degrees) — never fabricates rows for an unknown breakdown."""
    if not geometry.segments:
        return []

    rows = []
    for segment in geometry.segments:
        extrados_dir = _extrados_direction(segment, geometry.arc_center)
        intrados_dir = tuple(-c for c in extrados_dir)
        outer_length = _generatrix_length(segment, extrados_dir, params.od_mm / 2)
        inner_length = _generatrix_length(segment, intrados_dir, params.od_mm / 2)
        rows.append(
            GajoFabricationRow(
                gajo=segment.label,
                angle_deg=segment.angle_deg,
                cumulative_angle_deg=segment.cumulative_angle_deg,
                axis_length_mm=segment.length_mm,
                outer_length_approx_mm=outer_length,
                inner_length_approx_mm=inner_length,
                start_point_mm=segment.axis_start,
                end_point_mm=segment.axis_end,
                direction=segment.direction,
                start_cut_plane_angle_deg=_cut_plane_angle_deg(segment, "start"),
                end_cut_plane_angle_deg=_cut_plane_angle_deg(segment, "end"),
            )
        )
    return rows


def build_union_table(geometry: SegmentedElbowGeometry) -> List[UnionRow]:
    """Every weld/miter joint, T1 through T2 — the stub-to-gajo joints
    included, the open P1/P2 ends excluded (those are ports, not unions).
    Empty when segments are unavailable (no interior joints exist)."""
    if not geometry.segments:
        return []

    points: List[Tuple[str, Vector3]] = [("T1 (union tramo recto - Gajo 1)", geometry.tangent_point_1)]
    for i in range(len(geometry.segments) - 1):
        points.append((f"Union Gajo {i + 1} - Gajo {i + 2}", geometry.segments[i].axis_end))
    points.append((f"T2 (union Gajo {len(geometry.segments)} - tramo recto)", geometry.tangent_point_2))

    rows = []
    for i, (label, position) in enumerate(points):
        distance_to_next = _dist(position, points[i + 1][1]) if i + 1 < len(points) else 0.0
        rows.append(UnionRow(label=label, position_mm=position, distance_to_next_mm=distance_to_next))
    return rows


def build_overall_dimensions(params: ElbowParameters, geometry: SegmentedElbowGeometry) -> OverallDimensions:
    meshes = build_piece_meshes(geometry, od_mm=params.od_mm, id_mm=params.inside_diameter_mm, samples=48)
    all_vertices = [v for mesh in meshes for v in mesh.vertices.tolist()]
    xs = [v[0] for v in all_vertices]
    ys = [v[1] for v in all_vertices]
    zs = [v[2] for v in all_vertices]

    return OverallDimensions(
        width_mm=max(xs) - min(xs),
        height_mm=max(zs) - min(zs),
        length_mm=max(ys) - min(ys),
        p1_p2_distance_mm=_dist(geometry.p1_face, geometry.p2_face),
        p1_to_vertex_mm=_dist(geometry.vertex, geometry.p1_face),
        p2_to_vertex_mm=_dist(geometry.vertex, geometry.p2_face),
        radius_used_mm=geometry.radius_mm,
        z_resultant_mm=geometry.z_mm,
    )
