"""Streamlit UI for the BESB Piping — HDPE segmented elbow.

This module only wires widgets to the domain layer
(components/elbows/hdpe_segmented_elbow.py) and renders the result. It
never computes geometry or reads the Excel file directly.
"""

from __future__ import annotations

import json
import shutil
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
from core.geometry.engineering_report import (
    build_fabrication_table,
    build_overall_dimensions,
    build_union_table,
)
from core.geometry.geometry_validation import GeometryValidationError, validate_segmented_elbow_geometry
from core.geometry.segmented_elbow import build_segmented_elbow_geometry
from core.compatibility.engine import check_compatibility
from core.library.component_family import COMPONENT_FAMILIES
from core.library.elbow_registration import ComponentRegistration, register_hdpe_segmented_elbow
from core.library.materials import MATERIALS_REGISTRY
from core.library.standards import STANDARDS_REGISTRY
from core.models.common import DataAvailability, EndType
from core.serialization.json_export import elbow_to_dict
from core.validation.elbow_validation import Severity, has_blocking_errors
from core.validation.reference_comparison import (
    ComparisonStatus,
    ReferenceMeasurement,
    compare_gajo_lengths,
    compare_overall_dimensions,
    has_any_reference_value,
)
from data.repository import ElbowRepository
from data_sources.registry import REGISTERED_SOURCES
from plant3d.deployment.package_builder import build_deployment_package
from plant3d.environment.detector import detect_plant3d_environment
from plant3d.generators.custom_script_generator import generate_custom_script
from ui.engineering_view import build_engineering_figure
from ui.plotly_view import build_elbow_figure
from ui.plotly_view3d import build_elbow_figure_3d
from ui.pump_operating_view import render_pump_operating_point_tab
from ui.results_view import build_result_rows

st.set_page_config(page_title="BESB Piping", layout="wide")


@st.cache_resource
def get_repository() -> ElbowRepository:
    return ElbowRepository.from_excel()


def render_notes(notes: list[str], as_error: bool = False) -> None:
    for note in notes:
        if as_error:
            st.error(note)
        else:
            st.info(note)


def render_library_header(registration: ComponentRegistration) -> None:
    standard = registration.standard
    standard_label = standard.code if standard.organization.value == standard.code else f"{standard.organization.value} {standard.code}"
    if standard.part:
        standard_label += f" Parte {standard.part}"
    material_label = registration.material.grade or registration.material.key

    col1, col2, col3, col4 = st.columns(4)
    for col, label, value in (
        (col1, "Categoria", registration.family.category.value.title()),
        (col2, "Familia", registration.family.display_name),
        (col3, "Norma", standard_label),
        (col4, "Material", f"{registration.material.family.value} {material_label}"),
    ):
        col.caption(label)
        col.markdown(f"**{value}**")
    st.caption(f"Estado de cumplimiento: {registration.compliance_status.value}")


def render_available_libraries() -> None:
    with st.expander("Bibliotecas disponibles / futuras"):
        st.caption(
            "Registrar una norma, material o familia aqui no significa que sus tablas ya "
            "esten cargadas — solo que el nombre existe en la arquitectura. Ver "
            "docs/STANDARDS_ARCHITECTURE.md y docs/MATERIALS_ARCHITECTURE.md."
        )

        st.markdown("**Familias de componentes**")
        st.dataframe(
            {
                "Familia": [f.display_name for f in COMPONENT_FAMILIES.values()],
                "Categoria": [f.category.value for f in COMPONENT_FAMILIES.values()],
                "Implementada": ["Si" if f.implemented else "No" for f in COMPONENT_FAMILIES.values()],
            },
            use_container_width=True, hide_index=True,
        )

        st.markdown("**Normas**")
        st.dataframe(
            {
                "Norma": [f"{s.organization.value} {s.code}" + (f" Parte {s.part}" if s.part else "") for s in STANDARDS_REGISTRY.values()],
                "Estado de datos": [s.data_status.value for s in STANDARDS_REGISTRY.values()],
            },
            use_container_width=True, hide_index=True,
        )

        st.markdown("**Materiales**")
        st.dataframe(
            {
                "Material": [m.key for m in MATERIALS_REGISTRY.values()],
                "Familia": [m.family.value for m in MATERIALS_REGISTRY.values()],
                "Especificacion / Grado": [
                    " / ".join(filter(None, [m.specification, m.grade])) or "—" for m in MATERIALS_REGISTRY.values()
                ],
            },
            use_container_width=True, hide_index=True,
        )

        st.markdown("**Fuentes documentales registradas**")
        st.dataframe(
            {
                "Documento": [s.name for s in REGISTERED_SOURCES],
                "Tipo": [s.document_type for s in REGISTERED_SOURCES],
                "Estado": [s.status.value for s in REGISTERED_SOURCES],
            },
            use_container_width=True, hide_index=True,
        )

        compatibility = check_compatibility("HDPE_SEGMENTED_ELBOW", "ASME_B16_9", "PE100")
        st.markdown("**Ejemplo del motor de compatibilidad**")
        st.code(
            "HDPE_SEGMENTED_ELBOW + ASME_B16_9 + PE100\n"
            f"=> {compatibility.status.value}\n"
            f"({compatibility.message})",
            language="text",
        )


def render_component(params, missing_fields, key_prefix: str, extra_notes=None) -> None:
    geometry = build_elbow_geometry(params)

    # Built early (before any display) so the library header and the rest
    # of the 3D-dependent sections all share one computation.
    geometry_3d = build_segmented_elbow_geometry(params)
    try:
        validate_segmented_elbow_geometry(params, geometry_3d)
        validation_ok = True
    except GeometryValidationError as exc:
        validation_ok = False
        geometry_validation_failures = exc.failures

    registration = register_hdpe_segmented_elbow(params, geometry_3d if validation_ok else None)
    render_library_header(registration)

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
    if not validation_ok:
        st.error("GEOMETRY_VALIDATION_ERROR — no se muestra la geometria 3D ni se incluye en el JSON.")
        for failure in geometry_validation_failures:
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
        render_engineering_validation(params, geometry_3d, title, key_prefix)

    st.subheader("Exportar componente (JSON)")
    component_json = elbow_to_dict(
        params, geometry=geometry_3d if validation_ok else None, registration=registration
    )
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


TOLERANCE_PRESETS = {"±1 mm": 1.0, "±2 mm": 2.0, "±5 mm": 5.0, "Personalizada": None}


def _status_badge(status: ComparisonStatus) -> str:
    return "PASS" if status is ComparisonStatus.PASS else "FAIL"


def render_engineering_validation(params, geometry_3d, title: str, key_prefix: str) -> None:
    st.subheader("Validacion de ingenieria")
    st.warning(
        "MODELO MATEMATICO — PENDIENTE DE VALIDACION CONTRA REFERENCIA FISICA/CAD. "
        "La geometria generada es una HIPOTESIS DE MODELADO (que los puntos de union de "
        "los gajos estan inscritos en el circulo de radio R, ver "
        "docs/GEOMETRY_VALIDATION_REFERENCE.md), no un hecho confirmado. Que Z, el radio "
        "o el cierre geometrico coincidan con el catalogo NO confirma esta hipotesis por "
        "si solo — para eso es esta seccion."
    )

    st.markdown("**Vista de ingenieria**")
    col_a, col_b, col_c = st.columns(3)
    show_r_circle = col_a.checkbox("Mostrar circunferencia teorica R", value=True, key=f"{key_prefix}_eng_r")
    show_unions = col_b.checkbox("Mostrar puntos de union", value=True, key=f"{key_prefix}_eng_unions")
    show_cotas = col_c.checkbox("Mostrar cotas principales", value=True, key=f"{key_prefix}_eng_cotas")

    fig_eng = build_engineering_figure(
        geometry_3d, params, title=title,
        show_r_circle=show_r_circle, show_unions=show_unions, show_cotas=show_cotas,
    )
    st.plotly_chart(fig_eng, use_container_width=True, key=f"{key_prefix}_eng_chart")

    fabrication_rows = build_fabrication_table(params, geometry_3d)
    if fabrication_rows:
        st.markdown("**Tabla de fabricacion / modelado por gajo**")
        st.dataframe(
            {
                "Gajo": [r.gajo for r in fabrication_rows],
                "Angulo (deg)": [r.angle_deg for r in fabrication_rows],
                "Angulo acumulado (deg)": [r.cumulative_angle_deg for r in fabrication_rows],
                "Long. eje (mm)": [round(r.axis_length_mm, 2) for r in fabrication_rows],
                "Long. exterior aprox. (mm)": [round(r.outer_length_approx_mm, 2) for r in fabrication_rows],
                "Long. interior aprox. (mm)": [round(r.inner_length_approx_mm, 2) for r in fabrication_rows],
                "Inicio XYZ (mm)": [tuple(round(c, 2) for c in r.start_point_mm) for r in fabrication_rows],
                "Termino XYZ (mm)": [tuple(round(c, 2) for c in r.end_point_mm) for r in fabrication_rows],
                "Direccion eje": [tuple(round(c, 4) for c in r.direction) for r in fabrication_rows],
                "Plano corte inicial (deg)": [round(r.start_cut_plane_angle_deg, 3) for r in fabrication_rows],
                "Plano corte final (deg)": [round(r.end_cut_plane_angle_deg, 3) for r in fabrication_rows],
            },
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "Sin desglose de gajos disponible para este angulo: no se genera tabla de "
            "fabricacion (ver aviso de configuracion de segmentos arriba)."
        )

    union_rows = build_union_table(geometry_3d)
    if union_rows:
        st.markdown("**Uniones (planos de inglete) y distancias**")
        st.dataframe(
            {
                "Union": [u.label for u in union_rows],
                "Posicion XYZ (mm)": [tuple(round(c, 2) for c in u.position_mm) for u in union_rows],
                "Distancia a la siguiente (mm)": [
                    round(u.distance_to_next_mm, 2) if i < len(union_rows) - 1 else "—"
                    for i, u in enumerate(union_rows)
                ],
            },
            use_container_width=True,
            hide_index=True,
        )

    overall = build_overall_dimensions(params, geometry_3d)
    st.markdown("**Dimensiones generales del solido**")
    st.table(
        {
            "Dimension": [
                "Ancho total", "Alto total", "Largo total", "Distancia P1-P2",
                "Distancia P1 - vertice teorico", "Distancia P2 - vertice teorico",
                "R utilizado", "Z resultante",
            ],
            "Valor (mm)": [
                round(overall.width_mm, 2), round(overall.height_mm, 2), round(overall.length_mm, 2),
                round(overall.p1_p2_distance_mm, 2), round(overall.p1_to_vertex_mm, 2),
                round(overall.p2_to_vertex_mm, 2), round(overall.radius_used_mm, 2),
                round(overall.z_resultant_mm, 2),
            ],
        }
    )

    st.markdown("**Comparacion: MODELO PARAMETRICO vs MODELO DE REFERENCIA**")
    st.caption(
        "Ingresa las medidas reales obtenidas del modelo de referencia (CAD/fisico). "
        "Deja en 0 los campos que aun no tengas — se omiten de la comparacion, nunca se "
        "asume un valor. La geometria nunca se ajusta automaticamente para coincidir."
    )

    tolerance_label = st.selectbox(
        "Tolerancia", list(TOLERANCE_PRESETS.keys()), index=0, key=f"{key_prefix}_tolerance_preset"
    )
    if TOLERANCE_PRESETS[tolerance_label] is None:
        tolerance_mm = st.number_input(
            "Tolerancia personalizada (mm)", min_value=0.0, value=1.0, step=0.1, key=f"{key_prefix}_tolerance_custom"
        )
    else:
        tolerance_mm = TOLERANCE_PRESETS[tolerance_label]

    ref_col1, ref_col2, ref_col3, ref_col4 = st.columns(4)
    ref_width = ref_col1.number_input("Ancho total ref. (mm)", min_value=0.0, value=0.0, key=f"{key_prefix}_ref_width")
    ref_height = ref_col2.number_input("Alto total ref. (mm)", min_value=0.0, value=0.0, key=f"{key_prefix}_ref_height")
    ref_length = ref_col3.number_input("Largo total ref. (mm)", min_value=0.0, value=0.0, key=f"{key_prefix}_ref_length")
    ref_p1p2 = ref_col4.number_input("Distancia P1-P2 ref. (mm)", min_value=0.0, value=0.0, key=f"{key_prefix}_ref_p1p2")

    ref_col5, ref_col6, ref_col7, ref_col8 = st.columns(4)
    ref_p1v = ref_col5.number_input("P1-vertice ref. (mm)", min_value=0.0, value=0.0, key=f"{key_prefix}_ref_p1v")
    ref_p2v = ref_col6.number_input("P2-vertice ref. (mm)", min_value=0.0, value=0.0, key=f"{key_prefix}_ref_p2v")
    ref_r = ref_col7.number_input("R utilizado ref. (mm)", min_value=0.0, value=0.0, key=f"{key_prefix}_ref_r")
    ref_z = ref_col8.number_input("Z resultante ref. (mm)", min_value=0.0, value=0.0, key=f"{key_prefix}_ref_z")

    ref_gajo_lengths: list = []
    if fabrication_rows:
        st.caption("Longitud de eje de referencia por gajo (opcional, deja en 0 si no aplica):")
        gajo_cols = st.columns(len(fabrication_rows))
        for i, col in enumerate(gajo_cols):
            ref_gajo_lengths.append(
                col.number_input(
                    f"Gajo {i + 1} ref. (mm)", min_value=0.0, value=0.0, key=f"{key_prefix}_ref_gajo_{i}"
                )
            )

    reference = ReferenceMeasurement(
        width_mm=ref_width or None,
        height_mm=ref_height or None,
        length_mm=ref_length or None,
        p1_p2_distance_mm=ref_p1p2 or None,
        p1_to_vertex_mm=ref_p1v or None,
        p2_to_vertex_mm=ref_p2v or None,
        radius_used_mm=ref_r or None,
        z_resultant_mm=ref_z or None,
        gajo_axis_lengths_mm=[v or None for v in ref_gajo_lengths],
    )

    if has_any_reference_value(reference):
        comparison_rows = compare_overall_dimensions(overall, reference, tolerance_mm=tolerance_mm)
        comparison_rows += compare_gajo_lengths(
            [r.axis_length_mm for r in fabrication_rows], reference, tolerance_mm=tolerance_mm
        )

        st.dataframe(
            {
                "Campo": [r.label for r in comparison_rows],
                "Parametrico (mm)": [round(r.parametric_value_mm, 3) for r in comparison_rows],
                "Referencia (mm)": [round(r.reference_value_mm, 3) for r in comparison_rows],
                "Diferencia absoluta (mm)": [round(r.abs_diff_mm, 3) for r in comparison_rows],
                "Diferencia (%)": [round(r.pct_diff, 2) for r in comparison_rows],
                "Tolerancia (mm)": [r.tolerance_mm for r in comparison_rows],
                "Estado": [_status_badge(r.status) for r in comparison_rows],
            },
            use_container_width=True,
            hide_index=True,
        )

        failed_rows = [r for r in comparison_rows if r.status is ComparisonStatus.FAIL]
        if failed_rows:
            st.error(f"{len(failed_rows)} campo(s) fuera de tolerancia (±{tolerance_mm:g} mm).")
            for r in failed_rows:
                st.markdown(f"- **{r.label}**: {r.hypothesis_note}")
        else:
            st.success(
                f"Todos los campos ingresados estan dentro de tolerancia (±{tolerance_mm:g} mm) "
                "para esta referencia. Esto NO cambia el estado global del modelo — sigue "
                "PENDIENTE DE VALIDACION hasta una revision deliberada con el modelo de "
                "referencia completo."
            )
    else:
        st.caption("Ingresa al menos un valor de referencia para ver la comparacion.")


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


def render_plant3d_section(repository: ElbowRepository) -> None:
    st.header("Plant 3D")
    st.caption(
        "Proof of concept V0.3 — genera un paquete de despliegue para AutoCAD Plant 3D "
        "(CustomScript) a partir del Golden Case DN110/PN10/90°. Ninguna API real de "
        "Plant 3D se invoca desde este entorno (no esta instalado aqui). Ver "
        "docs/PLANT3D_CUSTOMSCRIPT.md y docs/PLANT3D_ENVIRONMENT.md."
    )

    st.markdown("**Estado**")
    col1, col2 = st.columns(2)
    col1.caption("CustomScript Generator")
    col1.success("READY")

    env_info = detect_plant3d_environment()
    col2.caption("Plant environment")
    if env_info.detected:
        col2.success(f"DETECTED ({env_info.source})")
    else:
        col2.warning("NOT DETECTED")

    with st.expander("Detalle de deteccion de entorno"):
        st.json(
            {
                "detected": env_info.detected,
                "source": env_info.source,
                "version": env_info.version,
                "version_documented": env_info.version_documented,
                "shared_content_path": env_info.shared_content_path,
                "custom_scripts_path": env_info.custom_scripts_path,
                "catalog_path": env_info.catalog_path,
                "specs_path": env_info.specs_path,
                "sdk_path": env_info.sdk_path,
                "platform_name": env_info.platform_name,
                "candidates_checked": env_info.candidates_checked,
            }
        )

    result = build_normalized(repository, dn_mm=110, pn_label="PN10", angle_deg=90)
    if result.status is DataAvailability.NOT_AVAILABLE:
        st.error(
            "Golden Case DN110/PN10/90° no disponible en el catalogo cargado — no se "
            "puede generar el paquete Plant 3D."
        )
        return

    params = result.elbow
    geometry_3d = build_segmented_elbow_geometry(params)
    try:
        validate_segmented_elbow_geometry(params, geometry_3d)
    except GeometryValidationError as exc:
        st.error("GEOMETRY_VALIDATION_ERROR en el Golden Case — no se genera el paquete Plant 3D.")
        for failure in exc.failures:
            st.code(f"{failure.code}: {failure.message}", language="text")
        return
    params.ports = geometry_3d.ports
    registration = register_hdpe_segmented_elbow(params, geometry_3d)

    if st.button("Generar paquete Plant 3D", key="plant3d_generate"):
        with st.spinner("Generando CustomScript y paquete de despliegue..."):
            tmp_dir = Path(tempfile.mkdtemp(prefix="piping_plant3d_"))
            pkg_dir = tmp_dir / "HDPE_SEGMENTED_ELBOW"
            package = build_deployment_package(params, geometry_3d, registration, pkg_dir)
            zip_path_str = shutil.make_archive(
                str(tmp_dir / "HDPE_SEGMENTED_ELBOW"), "zip", root_dir=tmp_dir, base_dir="HDPE_SEGMENTED_ELBOW"
            )
            script_text = (pkg_dir / "HDPE_SEGMENTED_ELBOW.py").read_text(encoding="utf-8")
        st.session_state["plant3d_zip_bytes"] = Path(zip_path_str).read_bytes()
        st.session_state["plant3d_script_text"] = script_text
        st.session_state["plant3d_warnings"] = package.warnings
        st.success(f"Paquete generado: {len(package.files)} archivos.")

    zip_bytes = st.session_state.get("plant3d_zip_bytes")
    if zip_bytes:
        for warning in st.session_state.get("plant3d_warnings", []):
            st.warning(warning)
        st.download_button(
            "Descargar paquete Plant 3D (.zip)",
            data=zip_bytes,
            file_name="HDPE_SEGMENTED_ELBOW_plant3d_package.zip",
            mime="application/zip",
            key="plant3d_download_zip",
        )
        st.markdown("**Golden Case — HDPE_SEGMENTED_ELBOW.py**")
        st.code(st.session_state.get("plant3d_script_text", ""), language="python")

    st.info(
        "Estado maximo declarado para este paquete: PLANT3D_PACKAGE_READY_FOR_VALIDATION. "
        "Nunca se declara PLANT3D_VALIDATED sin evidencia real registrada en "
        "plant3d_validation/ (ver docs/PLANT3D_MODEL_ACCEPTANCE.md)."
    )


def main() -> None:
    st.title("BESB Piping — V0.3")
    st.caption(
        "Codo HDPE segmentado PE100 (DIN 16963), con motor geometrico 3D real "
        "(gajos + planos a inglete). Independiente de AutoCAD Plant 3D."
    )

    repository = get_repository()

    tab_normalized, tab_custom, tab_engineering, tab_pumping = st.tabs(
        ["Modo A — Normalizado", "Modo B — Personalizado", "Modo C — Ingenieria", "Bombeo — Punto de Operacion"]
    )
    with tab_normalized:
        render_normalized_tab(repository)
    with tab_custom:
        render_custom_tab()
    with tab_engineering:
        st.info(
            "Modo Ingenieria: arquitectura reservada para una version futura "
            "(edicion avanzada por segmento, puertos y propiedades Plant 3D). "
            "No implementado todavia."
        )
    with tab_pumping:
        render_pump_operating_point_tab()

    render_available_libraries()
    render_plant3d_section(repository)


def pumping_main() -> None:
    st.markdown("""<style>
    .block-container {max-width:1100px; padding-top:2rem;}
    h1 {letter-spacing:-0.035em;}
    [data-testid="stMetric"] {background:#edf5fc; border:1px solid #d2e4f3; border-radius:12px; padding:14px;}
    [data-testid="stMetricValue"] {color:#125b95;}
    [data-testid="stExpander"] {border-radius:12px;}
    .stDownloadButton button {background:#125b95; color:white; border-radius:8px;}
    </style>""", unsafe_allow_html=True)
    st.title("BESB Piping")
    st.markdown("**Calculadora de bombeo**")
    render_pump_operating_point_tab()
    with st.expander("Acerca de los cálculos y sus límites"):
        st.write("Estimación de ingeniería para tramos en serie. Revisa los resultados con los datos del fabricante y los criterios de tu proyecto. Los accesorios usan coeficientes genéricos; el catálogo PEXGOL está pendiente de revisión humana.")


if __name__ == "__main__":
    pumping_main()
