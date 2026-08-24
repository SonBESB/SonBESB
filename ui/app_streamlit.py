"""Streamlit UI for the Piping Component Generator — HDPE segmented elbow.

This module only wires widgets to the domain layer
(components/elbows/hdpe_segmented_elbow.py) and renders the result. It
never computes geometry or reads the Excel file directly.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import streamlit as st

# Allow running via `streamlit run ui/app_streamlit.py` directly, where the
# repo root would otherwise not be on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cad.backends.base_backend import CadBackendUnavailableError
from cad.backends.cadquery_backend import CADQUERY_AVAILABLE, CadQueryElbowBackend
from components.elbows.hdpe_segmented_elbow import build_custom, build_normalized
from core.geometry.elbow_geometry import build_elbow_geometry
from core.geometry.geometry_validation import GeometryValidationError, validate_segmented_elbow_geometry
from core.geometry.segmented_elbow import build_segmented_elbow_geometry
from core.models.common import DataAvailability, EndType
from core.serialization.json_export import elbow_to_dict
from core.validation.elbow_validation import Severity, has_blocking_errors
from data.repository import ElbowRepository
from ui.plotly_view import build_elbow_figure
from ui.plotly_view3d import build_elbow_figure_3d
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

    st.subheader("Vista previa 3D (segmentada)")
    geometry_3d = build_segmented_elbow_geometry(params)
    try:
        validate_segmented_elbow_geometry(params, geometry_3d)
        validation_ok = True
    except GeometryValidationError as exc:
        validation_ok = False
        st.error("GEOMETRY_VALIDATION_ERROR — no se muestra la geometria 3D ni se incluye en el JSON.")
        for failure in exc.failures:
            st.code(
                f"{failure.code}: esperado={failure.expected!r} obtenido={failure.found!r} "
                f"diferencia={failure.difference!r}\n{failure.message}",
                language="text",
            )

    if not geometry_3d.segments_available:
        st.warning(
            "Configuracion de segmentos NO DISPONIBLE para este angulo: "
            f"{geometry_3d.unavailable_reason} No se genera geometria de gajos "
            "(se muestran solo los tramos rectos Le, con un vacio real entre ellos)."
        )

    if validation_ok:
        col_a, col_b, col_c, col_d = st.columns(4)
        show_centerline = col_a.checkbox("Mostrar centerline", value=True, key=f"{key_prefix}_show_centerline")
        show_ports = col_b.checkbox("Mostrar puertos", value=True, key=f"{key_prefix}_show_ports")
        show_cut_planes = col_c.checkbox("Mostrar planos de union", value=False, key=f"{key_prefix}_show_planes")
        show_labels = col_d.checkbox("Mostrar numeros de gajo", value=True, key=f"{key_prefix}_show_labels")

        fig3d = build_elbow_figure_3d(
            geometry_3d,
            params,
            title=title,
            show_centerline=show_centerline,
            show_ports=show_ports,
            show_cut_planes=show_cut_planes,
            show_segment_labels=show_labels,
        )
        st.plotly_chart(fig3d, use_container_width=True, key=f"{key_prefix}_chart3d")

        render_cad_export(geometry_3d, params, key_prefix)

    st.subheader("Exportar componente (JSON)")
    component_json = elbow_to_dict(params, geometry=geometry_3d if validation_ok else None)
    st.json(component_json)
    st.download_button(
        "Descargar JSON",
        data=json.dumps(component_json, indent=2, ensure_ascii=False),
        file_name=f"{key_prefix}_hdpe_segmented_elbow.json",
        mime="application/json",
        key=f"{key_prefix}_download",
    )


def render_cad_export(geometry_3d, params, key_prefix: str) -> None:
    st.subheader("Exportar CAD (experimental — STEP / STL)")
    st.caption(
        "Solido generado con CadQuery/OpenCASCADE solo para validar la geometria. "
        "No es todavia el mecanismo de importacion a AutoCAD Plant 3D."
    )
    if not CADQUERY_AVAILABLE:
        st.info("cadquery no esta instalado en este entorno: la exportacion STEP/STL esta deshabilitada.")
        return

    if st.button("Generar solido CAD", key=f"{key_prefix}_build_cad"):
        backend = CadQueryElbowBackend()
        try:
            with st.spinner("Construyendo solido (tubos huecos + cortes a inglete + union booleana)..."):
                solid = backend.build_solid(geometry_3d, od_mm=params.od_mm, id_mm=params.inside_diameter_mm)
                tmp_dir = Path(tempfile.mkdtemp(prefix="piping_cad_"))
                step_path = backend.export_step(solid, tmp_dir / f"{key_prefix}_elbow.step")
                stl_path = backend.export_stl(solid, tmp_dir / f"{key_prefix}_elbow.stl")
        except CadBackendUnavailableError as exc:
            st.error(str(exc))
            return
        st.session_state[f"{key_prefix}_step_bytes"] = step_path.read_bytes()
        st.session_state[f"{key_prefix}_stl_bytes"] = stl_path.read_bytes()
        st.success("Solido generado.")

    step_bytes = st.session_state.get(f"{key_prefix}_step_bytes")
    stl_bytes = st.session_state.get(f"{key_prefix}_stl_bytes")
    if step_bytes and stl_bytes:
        col1, col2 = st.columns(2)
        col1.download_button(
            "Descargar STEP", data=step_bytes, file_name=f"{key_prefix}_elbow.step",
            mime="application/step", key=f"{key_prefix}_download_step",
        )
        col2.download_button(
            "Descargar STL", data=stl_bytes, file_name=f"{key_prefix}_elbow.stl",
            mime="model/stl", key=f"{key_prefix}_download_stl",
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
    st.title("Piping Component Generator — V0.2")
    st.caption(
        "Codo HDPE segmentado PE100 (DIN 16963), con motor geometrico 3D real "
        "(gajos + planos a inglete). Independiente de AutoCAD Plant 3D."
    )

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
