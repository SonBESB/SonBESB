"""Streamlit UI for the Piping Component Generator — V0.1 (HDPE segmented elbow).

This module only wires widgets to the domain layer
(components/elbows/hdpe_segmented_elbow.py) and renders the result. It
never computes geometry or reads the Excel file directly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

# Allow running via `streamlit run ui/app_streamlit.py` directly, where the
# repo root would otherwise not be on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.elbows.hdpe_segmented_elbow import build_custom, build_normalized
from core.geometry.elbow_geometry import build_elbow_geometry
from core.models.common import DataAvailability, EndType
from core.serialization.json_export import elbow_to_dict
from core.validation.elbow_validation import Severity, has_blocking_errors
from data.repository import ElbowRepository
from ui.plotly_view import build_elbow_figure
from ui.results_view import build_result_rows

st.set_page_config(page_title="Piping Component Generator", layout="wide")


@st.cache_resource
def get_repository() -> ElbowRepository:
    return ElbowRepository.from_excel()


def render_notes(notes: list[str], as_error: bool = False) -> None:
    for note in notes:
        if as_error:
            st.error(note)
        else:
            st.info(note)


def render_component(params, missing_fields, key_prefix: str, extra_notes=None) -> None:
    geometry = build_elbow_geometry(params)
    # Port positions/directions/diameters only exist once a coordinate
    # system has been built; fill them in from geometry before the table
    # and JSON export below are rendered, so both reflect real values
    # instead of the placeholder ports the data/facade layers set.
    params.ports = geometry.ports

    st.subheader("Parametros del componente")
    rows = build_result_rows(params, missing_fields)
    st.table({"Parametro": [r[0] for r in rows], "Valor": [r[1] for r in rows]})

    if params.notes:
        render_notes(params.notes)
    if extra_notes:
        render_notes(extra_notes)

    st.subheader("Vista previa geometrica")
    title = (
        f"Codo HDPE segmentado DN{int(params.dn_mm)} {params.pn} {params.angle_deg:g}°"
        if params.dn_mm
        else f"Codo HDPE segmentado personalizado {params.angle_deg:g}°"
    )
    fig = build_elbow_figure(geometry, title)
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_chart")

    st.subheader("Exportar componente (JSON)")
    component_json = elbow_to_dict(params)
    st.json(component_json)
    st.download_button(
        "Descargar JSON",
        data=json.dumps(component_json, indent=2, ensure_ascii=False),
        file_name=f"{key_prefix}_hdpe_segmented_elbow.json",
        mime="application/json",
        key=f"{key_prefix}_download",
    )


def render_normalized_tab(repository: ElbowRepository) -> None:
    st.markdown("El componente se busca directamente en la base de datos del catalogo. "
                "Ningun valor faltante se inventa.")

    dn_options = repository.available_dn_mm()
    pn_options = repository.available_pn_labels()
    angle_options = repository.available_angles_deg()

    col1, col2, col3 = st.columns(3)
    dn_mm = col1.selectbox("DN (mm)", dn_options, index=dn_options.index(315) if 315 in dn_options else 0)
    pn_label = col2.selectbox("PN", pn_options, index=pn_options.index("PN10") if "PN10" in pn_options else 0)
    angle_deg = col3.selectbox("Angulo", angle_options, index=angle_options.index(90) if 90 in angle_options else 0)

    result = build_normalized(repository, dn_mm=dn_mm, pn_label=pn_label, angle_deg=angle_deg)

    if result.status is DataAvailability.NOT_AVAILABLE:
        st.error(f"Combinacion NO DISPONIBLE: DN {dn_mm} mm / {pn_label} / {angle_deg}°.")
        render_notes(result.notes)
        return

    if result.status is DataAvailability.INCOMPLETE:
        st.warning("Combinacion DISPONIBLE con informacion INCOMPLETA en la fuente.")
    else:
        st.success("Combinacion DISPONIBLE.")

    render_component(result.elbow, result.missing_fields, key_prefix="normalized")


def render_custom_tab() -> None:
    st.markdown("**COMPONENTE PERSONALIZADO** — no se declara cumplimiento con DIN 16963. "
                "Se validan reglas geometricas basicas.")

    col1, col2, col3 = st.columns(3)
    od_mm = col1.number_input("OD (mm)", min_value=0.0, value=630.0, step=1.0)
    thickness_mm = col2.number_input("Espesor (mm)", min_value=0.0, value=37.4, step=0.1)
    angle_deg = col3.number_input("Angulo (deg)", min_value=0.0, max_value=180.0, value=73.0, step=1.0)

    col4, col5, col6 = st.columns(3)
    radius_mm = col4.number_input("Radio R (mm)", min_value=0.0, value=900.0, step=1.0)
    le_mm = col5.number_input("Le (mm)", min_value=0.0, value=350.0, step=1.0)
    z_manual = col6.checkbox("Definir Z manualmente")
    z_mm = col6.number_input("Z (mm)", min_value=0.0, value=0.0, step=1.0, disabled=not z_manual) if z_manual else None

    end_type = st.selectbox("Tipo de union (EndType)", list(EndType), format_func=lambda e: e.value)

    segments_text = st.text_input(
        "Configuracion de segmentos (opcional, grados separados por coma, ej: 15,30,30,15)",
        value="",
    )
    segment_angles_deg = None
    if segments_text.strip():
        try:
            segment_angles_deg = [float(v.replace(",", ".")) for v in segments_text.split(",") if v.strip()]
        except ValueError:
            st.error("Configuracion de segmentos invalida: use numeros separados por coma.")

    params, issues = build_custom(
        od_mm=od_mm,
        thickness_mm=thickness_mm,
        angle_deg=angle_deg,
        radius_mm=radius_mm,
        le_mm=le_mm,
        z_mm=z_mm,
        segment_angles_deg=segment_angles_deg,
        end_type=end_type,
    )

    errors = [i for i in issues if i.severity is Severity.ERROR]
    warnings = [i for i in issues if i.severity is Severity.WARNING]

    for issue in errors:
        st.error(f"{issue.field}: {issue.message}")
    for issue in warnings:
        st.warning(f"{issue.field}: {issue.message}")

    if has_blocking_errors(issues):
        return

    render_component(params, missing_fields=[], key_prefix="custom")


def main() -> None:
    st.title("Piping Component Generator — V0.1")
    st.caption("Codo HDPE segmentado PE100 (DIN 16963). Independiente de AutoCAD Plant 3D.")

    repository = get_repository()

    tab_normalized, tab_custom, tab_engineering = st.tabs(
        ["Modo A — Normalizado", "Modo B — Personalizado", "Modo C — Ingenieria"]
    )
    with tab_normalized:
        render_normalized_tab(repository)
    with tab_custom:
        render_custom_tab()
    with tab_engineering:
        st.info(
            "Modo Ingenieria: arquitectura reservada para una version futura "
            "(edicion avanzada por segmento, puertos y propiedades Plant 3D). "
            "No implementado en V0.1."
        )


if __name__ == "__main__":
    main()
