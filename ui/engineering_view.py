"""Vista de ingenieria: extends the V0.2 3D preview with the overlays a
dimensional audit needs — the theoretical R circle, every weld/miter
union point, and the main "cotas" (Z, R, Le) — so the modeling hypothesis
(gajo joints inscribed on the R circle, see
docs/GEOMETRY_VALIDATION_REFERENCE.md) is something the viewer can see,
not just trust.

Builds on top of ui/plotly_view3d.py's figure instead of duplicating its
mesh/centerline/port/label code.
"""

from __future__ import annotations

import math
from typing import List, Tuple

import plotly.graph_objects as go

from core.geometry.segmented_elbow import SegmentedElbowGeometry
from core.models.elbow import ElbowParameters
from ui.plotly_view3d import build_elbow_figure_3d

R_CIRCLE_COLOR = "rgba(90, 90, 90, 0.5)"
UNION_COLOR = "rgb(160, 30, 30)"
COTA_COLOR = "rgb(30, 30, 30)"
COTA_LINE_COLOR = "rgba(30, 30, 30, 0.5)"


def _add_r_circle_trace(fig: go.Figure, geometry: SegmentedElbowGeometry, samples: int = 96) -> None:
    center = geometry.arc_center
    radius = geometry.radius_mm
    xs, ys, zs = [], [], []
    for i in range(samples + 1):
        theta = 2 * math.pi * i / samples
        xs.append(center[0] + radius * math.cos(theta))
        ys.append(center[1] + radius * math.sin(theta))
        zs.append(center[2])
    fig.add_trace(
        go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode="lines",
            line=dict(color=R_CIRCLE_COLOR, width=3, dash="dot"),
            name=f"Circunferencia teorica R={radius:g}mm",
            hoverinfo="name",
        )
    )


def _union_points(geometry: SegmentedElbowGeometry) -> List[Tuple[float, float, float]]:
    if not geometry.segments:
        return []
    points = [geometry.tangent_point_1]
    for segment in geometry.segments[:-1]:
        points.append(segment.axis_end)
    points.append(geometry.tangent_point_2)
    return points


def _add_union_traces(fig: go.Figure, geometry: SegmentedElbowGeometry) -> None:
    points = _union_points(geometry)
    if not points:
        return
    xs, ys, zs = zip(*points)
    fig.add_trace(
        go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode="markers",
            marker=dict(color=UNION_COLOR, size=6, symbol="diamond"),
            name="Puntos de union",
        )
    )


def _cota_text_trace(point, text: str, offset=(0.0, 0.0, 0.0)):
    return go.Scatter3d(
        x=[point[0] + offset[0]], y=[point[1] + offset[1]], z=[point[2] + offset[2]],
        mode="text",
        text=[text],
        textfont=dict(color=COTA_COLOR, size=13),
        showlegend=False,
        hoverinfo="skip",
    )


def _add_cota_traces(fig: go.Figure, geometry: SegmentedElbowGeometry, params: ElbowParameters) -> None:
    od = params.od_mm
    # Z: vertex -> P1 face (and symmetric label on the P2 side).
    z_mid_p1 = tuple((a + b) / 2 for a, b in zip(geometry.vertex, geometry.p1_face))
    fig.add_trace(_cota_text_trace(z_mid_p1, f"Z = {geometry.z_mm:g} mm", offset=(0, 0, od * 0.6)))

    # R: arc_center -> tangent_point_1.
    r_mid = tuple((a + b) / 2 for a, b in zip(geometry.arc_center, geometry.tangent_point_1))
    fig.add_trace(
        go.Scatter3d(
            x=[geometry.arc_center[0], geometry.tangent_point_1[0]],
            y=[geometry.arc_center[1], geometry.tangent_point_1[1]],
            z=[geometry.arc_center[2], geometry.tangent_point_1[2]],
            mode="lines",
            line=dict(color=COTA_LINE_COLOR, width=2, dash="dash"),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(_cota_text_trace(r_mid, f"R = {geometry.radius_mm:g} mm", offset=(0, 0, od * 0.5)))

    # Le: leg1_stub midpoint.
    le_mid = tuple((a + b) / 2 for a, b in zip(geometry.leg1_stub.axis_start, geometry.leg1_stub.axis_end))
    fig.add_trace(_cota_text_trace(le_mid, f"Le = {geometry.leg1_stub.length_mm:g} mm", offset=(0, 0, -od * 0.6)))


def build_engineering_figure(
    geometry: SegmentedElbowGeometry,
    params: ElbowParameters,
    title: str,
    show_r_circle: bool = True,
    show_unions: bool = True,
    show_cotas: bool = True,
) -> go.Figure:
    fig = build_elbow_figure_3d(
        geometry,
        params,
        title=title,
        show_centerline=True,
        show_ports=True,
        show_cut_planes=True,
        show_segment_labels=True,
    )
    if show_r_circle:
        _add_r_circle_trace(fig, geometry)
    if show_unions:
        _add_union_traces(fig, geometry)
    if show_cotas:
        _add_cota_traces(fig, geometry, params)
    return fig
