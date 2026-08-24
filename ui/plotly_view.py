"""Builds the Plotly figure for the elbow preview.

Kept separate from app_streamlit.py so the plotting logic is not tangled
with Streamlit widget code, and could be reused (e.g. by a future 3D view
built on the same ElbowGeometry2D-style data) without touching the UI glue.
"""

from __future__ import annotations

import plotly.graph_objects as go

from core.geometry.elbow_geometry import ElbowGeometry2D

OUTER_FILL_COLOR = "rgba(120, 170, 220, 0.35)"
OUTER_LINE_COLOR = "rgb(40, 90, 150)"
CENTERLINE_COLOR = "rgb(180, 60, 60)"
WELD_MARKER_COLOR = "rgb(20, 20, 20)"
PORT_MARKER_COLOR = "rgb(10, 120, 10)"


def build_elbow_figure(geometry: ElbowGeometry2D, title: str) -> go.Figure:
    fig = go.Figure()

    pipe_polygon = geometry.outer_boundary + list(reversed(geometry.inner_boundary))
    if pipe_polygon:
        pipe_polygon = pipe_polygon + [pipe_polygon[0]]
        xs, ys = zip(*pipe_polygon)
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                fill="toself",
                fillcolor=OUTER_FILL_COLOR,
                line=dict(color=OUTER_LINE_COLOR, width=2),
                name="Cuerpo del codo (OD)",
                hoverinfo="skip",
            )
        )

    if geometry.centerline:
        cx, cy = zip(*geometry.centerline)
        fig.add_trace(
            go.Scatter(
                x=cx,
                y=cy,
                mode="lines",
                line=dict(color=CENTERLINE_COLOR, width=1.5, dash="dash"),
                name="Eje / linea de centro",
                hoverinfo="skip",
            )
        )

    if geometry.weld_markers:
        wx, wy = zip(*geometry.weld_markers)
        fig.add_trace(
            go.Scatter(
                x=wx,
                y=wy,
                mode="markers",
                marker=dict(color=WELD_MARKER_COLOR, size=9, symbol="line-ns-open", line=dict(width=2)),
                name="Uniones entre segmentos",
            )
        )

    for port in geometry.ports:
        fig.add_trace(
            go.Scatter(
                x=[port.position_mm[0]],
                y=[port.position_mm[1]],
                mode="markers+text",
                marker=dict(color=PORT_MARKER_COLOR, size=11, symbol="circle"),
                text=[port.id],
                textposition="top center",
                name=port.id,
            )
        )

    fig.add_trace(
        go.Scatter(
            x=[geometry.vertex[0]],
            y=[geometry.vertex[1]],
            mode="markers",
            marker=dict(color="gray", size=6, symbol="x"),
            name="Vertice teorico",
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="mm",
        yaxis_title="mm",
        showlegend=True,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig
