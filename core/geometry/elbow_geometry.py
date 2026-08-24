"""2D schematic geometry for a segmented HDPE elbow preview.

Construction (all in a local XY plane, vertex at the origin):

  - Leg 1 (towards P1) runs along the fixed direction (-1, 0).
  - Leg 2 (towards P2) runs along (cos(angle), sin(angle)).
  - The bend is a circular arc of the given radius, tangent to both legs.
    Its tangent length from the vertex is t = R * tan(angle/2), a standard
    mitred/segmented-bend relation, and (as a consequence) Z = Le + t —
    the same formula this project's Excel BUSCADOR sheet demonstrates.
  - The arc's central angle always equals the elbow's deflection angle,
    which is what lets the whole construction stay a closed-form
    calculation instead of an iterative solve.

This module only computes points; it knows nothing about Plotly, Streamlit
or matplotlib — see ui/app_streamlit.py for rendering.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from core.models.common import EndType, Port
from core.models.elbow import ElbowParameters

Point2D = Tuple[float, float]

DEFAULT_ARC_SAMPLES = 48


def calculate_z_mm(le_mm: float, radius_mm: float, angle_deg: float) -> float:
    """Z = Le + R * tan(angle / 2), verified against the source workbook."""
    return le_mm + radius_mm * math.tan(math.radians(angle_deg) / 2)


@dataclass(frozen=True)
class ElbowGeometry2D:
    vertex: Point2D
    p1_face: Point2D
    p2_face: Point2D
    tangent_point_1: Point2D
    tangent_point_2: Point2D
    arc_center: Point2D
    centerline: List[Point2D]
    outer_boundary: List[Point2D]
    inner_boundary: List[Point2D]
    weld_markers: List[Point2D]
    ports: List[Port] = field(default_factory=list)


def _unit(angle_deg: float) -> Point2D:
    rad = math.radians(angle_deg)
    return (math.cos(rad), math.sin(rad))


def _add(a: Point2D, b: Point2D, scale: float = 1.0) -> Point2D:
    return (a[0] + b[0] * scale, a[1] + b[1] * scale)


def _arc_points(center: Point2D, radius: float, theta_start_deg: float, theta_end_deg: float, samples: int) -> List[Point2D]:
    if radius <= 0:
        return []
    points = []
    for i in range(samples + 1):
        t = theta_start_deg + (theta_end_deg - theta_start_deg) * i / samples
        rad = math.radians(t)
        points.append((center[0] + radius * math.cos(rad), center[1] + radius * math.sin(rad)))
    return points


def build_elbow_geometry(
    params: ElbowParameters,
    arc_samples: int = DEFAULT_ARC_SAMPLES,
) -> ElbowGeometry2D:
    """Builds the 2D preview geometry for one ElbowParameters instance."""
    angle_deg = params.angle_deg
    radius_mm = params.radius_mm
    le_mm = params.le_mm
    half_od = params.od_mm / 2
    half_id = params.inside_diameter_mm / 2

    tangent_len = radius_mm * math.tan(math.radians(angle_deg) / 2)
    z_mm = params.z_mm if params.z_mm is not None else calculate_z_mm(le_mm, radius_mm, angle_deg)

    vertex: Point2D = (0.0, 0.0)
    dir1 = _unit(180.0)
    dir2 = _unit(angle_deg)

    p1_face = _add(vertex, dir1, z_mm)
    p2_face = _add(vertex, dir2, z_mm)
    t1 = _add(vertex, dir1, tangent_len)
    t2 = _add(vertex, dir2, tangent_len)
    arc_center = (t1[0], t1[1] + radius_mm)  # valid because dir1 is fixed at (-1, 0)

    theta_start = -90.0
    theta_end = -90.0 + angle_deg
    arc_pts = _arc_points(arc_center, radius_mm, theta_start, theta_end, arc_samples)

    centerline = [p1_face, t1, *arc_pts[1:-1], t2, p2_face]

    # Extrados (far side from arc_center) / intrados (near side) offset directions
    # for the straight legs, chosen so they connect smoothly with the arc offset.
    ext_dir1 = (0.0, -1.0)
    ext_dir2 = _unit(math.degrees(math.atan2(t2[1] - arc_center[1], t2[0] - arc_center[0])))

    def offset_leg_and_arc(radial_offset: float) -> List[Point2D]:
        # ext_dir1/ext_dir2 point outward (extrados); a negative radial_offset
        # (intrados) simply flips the direction, since _add scales by it.
        r = max(radius_mm + radial_offset, 0.0)
        arc = _arc_points(arc_center, r, theta_start, theta_end, arc_samples)
        leg1_start = _add(p1_face, ext_dir1, radial_offset)
        leg1_end = _add(t1, ext_dir1, radial_offset)
        leg2_start = _add(t2, ext_dir2, radial_offset)
        leg2_end = _add(p2_face, ext_dir2, radial_offset)
        return [leg1_start, leg1_end, *arc[1:-1], leg2_start, leg2_end]

    outer_boundary = offset_leg_and_arc(half_od)
    inner_boundary = offset_leg_and_arc(-half_od)

    weld_markers: List[Point2D] = []
    config = params.segment_configuration
    if config and config.segment_angles_deg:
        cumulative = 0.0
        for segment_angle in config.segment_angles_deg[:-1]:
            cumulative += segment_angle
            theta = theta_start + cumulative
            rad = math.radians(theta)
            weld_markers.append((arc_center[0] + radius_mm * math.cos(rad), arc_center[1] + radius_mm * math.sin(rad)))

    ports = [
        Port(
            id="P1",
            position_mm=(p1_face[0], p1_face[1], 0.0),
            direction=(dir1[0], dir1[1], 0.0),
            nominal_diameter_mm=params.dn_mm,
            outside_diameter_mm=params.od_mm,
            end_type=params.end_type,
        ),
        Port(
            id="P2",
            position_mm=(p2_face[0], p2_face[1], 0.0),
            direction=(dir2[0], dir2[1], 0.0),
            nominal_diameter_mm=params.dn_mm,
            outside_diameter_mm=params.od_mm,
            end_type=params.end_type,
        ),
    ]

    return ElbowGeometry2D(
        vertex=vertex,
        p1_face=p1_face,
        p2_face=p2_face,
        tangent_point_1=t1,
        tangent_point_2=t2,
        arc_center=arc_center,
        centerline=centerline,
        outer_boundary=outer_boundary,
        inner_boundary=inner_boundary,
        weld_markers=weld_markers,
        ports=ports,
    )
