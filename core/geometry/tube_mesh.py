"""Pure-numpy hollow-pipe triangle mesh, built directly from the math model.

Deliberately independent of cadquery: this is what feeds the interactive
Plotly 3D preview in ui/, so the preview keeps working even in an
environment where the (optional, heavy) CAD backend is not installed. The
"real" CAD solid for STEP/STL export is built separately by
cad/backends/cadquery_backend.py from the same SegmentedElbowGeometry.

Each piece (Le stub or gajo) is a section of an infinite cylinder, cut by
its own two miter/end planes. For a given angular sample around the pipe,
the point on the cylinder wall is found by intersecting the axis-parallel
line at that angle with each bounding plane — i.e. each piece is meshed as
a ruled surface between two (generally elliptical, at a miter) rings, not
as a perpendicular-capped cylinder.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from core.geometry.segmented_elbow import ElbowSegment, SegmentedElbowGeometry

DEFAULT_ANGULAR_SAMPLES = 32


@dataclass(frozen=True)
class PieceMesh:
    label: str
    piece_index: int
    is_gajo: bool
    vertices: np.ndarray  # (N, 3)
    triangles: np.ndarray  # (M, 3) int indices into vertices
    midpoint: Tuple[float, float, float]


def _perpendicular_frame(direction: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Returns (u, v): an orthonormal basis for the plane perpendicular to
    direction. Valid for any planar-elbow direction produced by
    segmented_elbow.py (all of which have zero z-component), since (0,0,1)
    is then always perpendicular to it.
    """
    world_up = np.array([0.0, 0.0, 1.0])
    if abs(np.dot(direction, world_up)) > 0.999:
        world_up = np.array([1.0, 0.0, 0.0])
    v = np.cross(direction, world_up)
    v = v / np.linalg.norm(v)
    u = np.cross(v, direction)
    u = u / np.linalg.norm(u)
    return u, v


def _ring_at_plane(
    reference_point: np.ndarray,
    direction: np.ndarray,
    radius: float,
    plane_point: np.ndarray,
    plane_normal: np.ndarray,
    angles_rad: np.ndarray,
    u: np.ndarray,
    v: np.ndarray,
) -> np.ndarray:
    """Intersects the `radius`-offset generatrix lines with one bounding plane."""
    radial = np.outer(np.cos(angles_rad), u) + np.outer(np.sin(angles_rad), v)
    radial *= radius
    base = reference_point + radial  # (N, 3): a point on each generatrix line
    denom = np.dot(plane_normal, direction)
    s = np.dot(plane_point - base, plane_normal) / denom  # (N,)
    return base + s[:, None] * direction


def _quad_strip_triangles(n: int, start_index: int, reverse: bool = False) -> np.ndarray:
    """Triangle indices joining ring A (indices start_index..) to ring B
    (indices start_index+n..), both of length n, wrapped circularly."""
    tris = []
    for m in range(n):
        m_next = (m + 1) % n
        a0, a1 = start_index + m, start_index + m_next
        b0, b1 = start_index + n + m, start_index + n + m_next
        if reverse:
            tris.append((a0, b0, b1))
            tris.append((a0, b1, a1))
        else:
            tris.append((a0, a1, b1))
            tris.append((a0, b1, b0))
    return np.array(tris, dtype=int)


def _build_piece_mesh(
    piece: ElbowSegment,
    od_mm: float,
    id_mm: float,
    samples: int,
    include_start_cap: bool,
    include_end_cap: bool,
) -> PieceMesh:
    direction = np.array(piece.direction)
    axis_start = np.array(piece.axis_start)
    axis_end = np.array(piece.axis_end)
    reference_point = (axis_start + axis_end) / 2
    u, v = _perpendicular_frame(direction)
    angles = np.linspace(0, 2 * np.pi, samples, endpoint=False)

    plane_start_point = np.array(piece.cut_plane_start.point)
    plane_start_normal = np.array(piece.cut_plane_start.normal)
    plane_end_point = np.array(piece.cut_plane_end.point)
    plane_end_normal = np.array(piece.cut_plane_end.normal)

    outer_start = _ring_at_plane(reference_point, direction, od_mm / 2, plane_start_point, plane_start_normal, angles, u, v)
    outer_end = _ring_at_plane(reference_point, direction, od_mm / 2, plane_end_point, plane_end_normal, angles, u, v)
    inner_start = _ring_at_plane(reference_point, direction, id_mm / 2, plane_start_point, plane_start_normal, angles, u, v)
    inner_end = _ring_at_plane(reference_point, direction, id_mm / 2, plane_end_point, plane_end_normal, angles, u, v)

    vertex_blocks = [outer_start, outer_end, inner_start, inner_end]
    offsets = np.cumsum([0] + [len(b) for b in vertex_blocks[:-1]])
    vertices = np.concatenate(vertex_blocks, axis=0)

    triangles = [
        _quad_strip_triangles(samples, offsets[0]),  # outer wall (outer_start -> outer_end)
        _quad_strip_triangles(samples, offsets[2], reverse=True),  # inner wall
    ]
    if include_start_cap:
        # Annulus at the open P1 end: outer_start <-> inner_start.
        cap = []
        for m in range(samples):
            m_next = (m + 1) % samples
            o0, o1 = offsets[0] + m, offsets[0] + m_next
            i0, i1 = offsets[2] + m, offsets[2] + m_next
            cap.append((o0, i1, i0))
            cap.append((o0, o1, i1))
        triangles.append(np.array(cap, dtype=int))
    if include_end_cap:
        cap = []
        start = offsets[1]
        istart = offsets[3]
        for m in range(samples):
            m_next = (m + 1) % samples
            o0, o1 = start + m, start + m_next
            i0, i1 = istart + m, istart + m_next
            cap.append((o0, i0, i1))
            cap.append((o0, i1, o1))
        triangles.append(np.array(cap, dtype=int))

    all_triangles = np.concatenate(triangles, axis=0)
    midpoint = tuple(((axis_start + axis_end) / 2).tolist())

    return PieceMesh(
        label=piece.label,
        piece_index=piece.index,
        is_gajo=piece.angle_deg > 0,
        vertices=vertices,
        triangles=all_triangles,
        midpoint=midpoint,
    )


def build_piece_meshes(
    geometry: SegmentedElbowGeometry,
    od_mm: float,
    id_mm: float,
    samples: int = DEFAULT_ANGULAR_SAMPLES,
) -> List[PieceMesh]:
    """One mesh per physical piece (Le stubs + gajos when available).

    Open-end caps are only added at the very first (P1) and very last (P2)
    piece — every other joint is an internal miter weld, not an open pipe
    end, so it is left unmeshed (the two adjoining pieces' walls already
    reach that joint's cut plane exactly).
    """
    pieces = geometry.all_pieces
    meshes = []
    for i, piece in enumerate(pieces):
        meshes.append(
            _build_piece_mesh(
                piece,
                od_mm=od_mm,
                id_mm=id_mm,
                samples=samples,
                include_start_cap=(i == 0),
                include_end_cap=(i == len(pieces) - 1),
            )
        )
    return meshes
