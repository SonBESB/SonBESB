"""Builds the interactive 3D Plotly figure for the segmented elbow preview.

Consumes core/geometry/tube_mesh.py (pure numpy, no cadquery) so the 3D
preview works even when the optional CAD backend is not installed. Kept
separate from ui/app_streamlit.py for the same reason as ui/plotly_view.py
(the 2D preview, unchanged from V0.1): plotting logic is not widget glue.
"""

from __future__ import annotations

from typing import List

import numpy as np
import plotly.graph_objects as go

from core.geometry.segmented_elbow import ElbowSegment, SegmentedElbowGeometry
from core.geometry.tube_mesh import DEFAULT_ANGULAR_SAMPLES, build_piece_meshes
from core.models.elbow import ElbowParameters

GAJO_COLOR = "rgb(120, 170, 220)"
STUB_COLOR = "rgb(180, 190, 200)"
CENTERLINE_COLOR = "rgb(180, 60, 60)"
PORT_COLOR = "rgb(10, 120, 10)"
CUT_PLANE_COLOR = "rgba(40, 40, 40, 0.6)"
LABEL_COLOR = "rgb(20, 20, 20)"


def _perpendicular_frame(direction: np.ndarray):
    world_up = np.array([0.0, 0.0, 1.0])
    if abs(np.dot(direction, world_up)) > 0.999:
        world_up = np.array([1.0, 0.0, 0.0])
    v = np.cross(direction, world_up)
    v = v / np.linalg.norm(v)
    u = np.cross(v, direction)
    u = u / np.linalg.norm(u)
    return u, v


def _add_mesh_traces(fig: go.Figure, geometry: SegmentedElbowGeometry, od_mm: float, id_mm: float, samples: int) -> None:
    for mesh in build_piece_meshes(geometry, od_mm=od_mm, id_mm=id_mm, samples=samples):
        color = GAJO_COLOR if mesh.is_gajo else STUB_COLOR
        fig.add_trace(
            go.Mesh3d(
                x=mesh.vertices[:, 0],
                y=mesh.vertices[:, 1],
                z=mesh.vertices[:, 2],
                i=mesh.triangles[:, 0],
                j=mesh.triangles[:, 1],
                k=mesh.triangles[:, 2],
                color=color,
                flatshading=True,
                lighting=dict(ambient=0.55, diffuse=0.7, specular=0.15, roughness=0.6),
                name=mesh.label,
                hovertext=mesh.label,
                hoverinfo="text",
                showscale=False,
            )
        )


def _add_centerline_trace(fig: go.Figure, geometry: SegmentedElbowGeometry) -> None:
    points = [geometry.all_pieces[0].axis_start]
    for piece in geometry.all_pieces:
        points.append(piece.axis_end)
    xs, ys, zs = zip(*points)
    fig.add_trace(
        go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode="lines",
            line=dict(color=CENTERLINE_COLOR, width=5, dash="dash"),
            name="Eje / centerline",
        )
    )


def _add_port_traces(fig: go.Figure, geometry: SegmentedElbowGeometry) -> None:
    for port in geometry.ports:
        fig.add_trace(
            go.Scatter3d(
                x=[port.position_mm[0]], y=[port.position_mm[1]], z=[port.position_mm[2]],
                mode="markers+text",
                marker=dict(color=PORT_COLOR, size=7, symbol="circle"),
                text=[port.id],
                textposition="top center",
                name=port.id,
            )
        )


def _plane_loop(point, normal, half_size: float) -> List[np.ndarray]:
    u, v = _perpendicular_frame(np.array(normal))
    point = np.array(point)
    corners = [point + half_size * (s1 * u + s2 * v) for s1, s2 in ((1, 1), (-1, 1), (-1, -1), (1, -1), (1, 1))]
    return corners


def _add_cut_plane_traces(fig: go.Figure, geometry: SegmentedElbowGeometry, od_mm: float) -> None:
    interior_planes = []
    pieces = geometry.all_pieces
    for a, b in zip(pieces[:-1], pieces[1:]):
        interior_planes.append((a.cut_plane_end.point, a.cut_plane_end.normal))
    half_size = od_mm * 0.65
    for i, (point, normal) in enumerate(interior_planes):
        corners = _plane_loop(point, normal, half_size)
        xs, ys, zs = zip(*[c.tolist() for c in corners])
        fig.add_trace(
            go.Scatter3d(
                x=xs, y=ys, z=zs,
                mode="lines",
                line=dict(color=CUT_PLANE_COLOR, width=2),
                name="Planos de union" if i == 0 else None,
                showlegend=(i == 0),
                hoverinfo="skip",
            )
        )


def _add_segment_label_traces(fig: go.Figure, geometry: SegmentedElbowGeometry, od_mm: float) -> None:
    gajos = geometry.segments or []
    if not gajos:
        return
    xs, ys, zs, texts = [], [], [], []
    for segment in gajos:
        direction = np.array(segment.direction)
        u, _ = _perpendicular_frame(direction)
        midpoint = np.array([(a + b) / 2 for a, b in zip(segment.axis_start, segment.axis_end)])
        label_point = midpoint + u * (od_mm / 2 * 1.4)
        xs.append(label_point[0])
        ys.append(label_point[1])
        zs.append(label_point[2])
        texts.append(str(segment.index))
    fig.add_trace(
        go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode="text",
            text=texts,
            textfont=dict(color=LABEL_COLOR, size=16),
            name="Numeros de gajo",
        )
    )


def build_elbow_figure_3d(
    geometry: SegmentedElbowGeometry,
    params: ElbowParameters,
    title: str,
    show_centerline: bool = True,
    show_ports: bool = True,
    show_cut_planes: bool = False,
    show_segment_labels: bool = True,
    samples: int = DEFAULT_ANGULAR_SAMPLES,
) -> go.Figure:
    fig = go.Figure()
    _add_mesh_traces(fig, geometry, params.od_mm, params.inside_diameter_mm, samples)
    if show_centerline:
        _add_centerline_trace(fig, geometry)
    if show_ports:
        _add_port_traces(fig, geometry)
    if show_cut_planes:
        _add_cut_plane_traces(fig, geometry, params.od_mm)
    if show_segment_labels:
        _add_segment_label_traces(fig, geometry, params.od_mm)

    fig.update_layout(
        title=title,
        scene=dict(
            xaxis_title="mm",
            yaxis_title="mm",
            zaxis_title="mm",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        showlegend=True,
    )
    return fig
