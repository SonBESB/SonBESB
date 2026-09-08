"""Vista Streamlit: punto de operacion de un sistema de bombeo.

Inspirada en PiezoCalc (pump.geo-alba.com) en cuanto a flujo de trabajo
(tramos en serie + accesorios + curva de bomba -> punto de equilibrio en
vivo), pero el motor de calculo es el de core/hydraulics/, portado y
corregido desde la planilla SMath de referencia (Bryam Perez):
Colebrook-White real (no Swamee-Jain con agua fija), ajuste de curva de
bomba por regresion (no interpolacion lineal de 3 puntos), eficiencia
opcionalmente como curva por punto (no un escalar fijo en todos los
escenarios VDF), y verificacion NPSH disponible vs requerido — que
PiezoCalc no tiene.

Este modulo solo conecta widgets con core/hydraulics/; no calcula nada
por si mismo.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from core.hydraulics.affinity import PumpCurve, PumpCurvePoint, scale_by_affinity, twin_parallel, twin_series
from core.hydraulics.curve_fit import fit_polynomial
from core.hydraulics.fluids import FluidProperties, TemperatureOutOfRangeError, custom_fluid, water_properties
from core.hydraulics.minor_losses import FITTING_K_DISCREPANCIES, FITTING_K_TABLE
from core.hydraulics.npsh import DEFAULT_NPSH_SAFETY_MARGIN_M, check_npsh, npsh_available
from core.hydraulics.operating_point import solve_operating_point
from core.hydraulics.power import compute_power
from core.hydraulics.system_curve import PipeSegment, build_system_curve, evaluate_system

_DEGREE_LABELS = {"Constante (grado 0)": 0, "Lineal (grado 1)": 1, "Cuadratica (grado 2)": 2, "Cubica (grado 3)": 3}


def render_pump_operating_point_tab() -> None:
    st.markdown(
        "Calcula el punto de operacion (interseccion curva de bomba / curva de sistema) "
        "de una linea de impulsion con hasta dos tramos en serie. Motor de calculo propio "
        "(`core/hydraulics/`) — metodologia y fuentes citadas en "
        "`docs/HYDRAULICS_PUMP_OPERATING_POINT.md`. Todo se recalcula en vivo al cambiar "
        "un input."
    )
    st.warning(
        "MODELO DE INGENIERIA — no reemplaza el calculo/seleccion de bomba de un "
        "proveedor ni la norma de diseno del proyecto. Los coeficientes K de accesorios "
        "son de tabla generica (ver aviso en la seccion de piezas especiales), no de "
        "catalogo especifico al diametro."
    )

    fluid = _render_fluid_section("pump")
    segments = _render_segments_section("pump")
    static_head_m = st.number_input(
        "Altura estatica del sistema (delta de cota, deposito destino - origen) [m]",
        value=18.5, step=0.1, key="pump_static_head",
    )

    q_points, h_points, eta_points, degree = _render_pump_curve_section("pump")
    if len(q_points) < degree + 1:
        st.error(f"Se necesitan al menos {degree + 1} puntos para un ajuste de grado {degree}.")
        return

    motor_efficiency_pct = st.number_input("Eficiencia motor (%)", min_value=1.0, max_value=100.0, value=92.0, key="pump_eta_motor")
    scenarios = _render_scenarios_section("pump")

    base_curve = PumpCurve(
        points=tuple(
            PumpCurvePoint(flow_m3_s=q / 1000.0, head_m=h, efficiency=(e / 100.0 if e is not None else None))
            for q, h, e in zip(q_points, h_points, eta_points)
        ),
        label="Bomba nominal",
    )
    flat_efficiency_pct = None
    if any(e is None for e in eta_points):
        if any(e is not None for e in eta_points):
            st.error(
                "Curva de eficiencia incompleta: o se define eta para TODOS los puntos de la "
                "curva de bomba, o para NINGUNO (en ese caso se usa un valor constante abajo). "
                "No se interpola un valor faltante."
            )
            return
        flat_efficiency_pct = st.number_input(
            "Eficiencia de bomba constante (%) — asumida, no medida por punto",
            min_value=1.0, max_value=100.0, value=75.0, key="pump_eta_flat",
        )

    q_max_curve = max(q_points) / 1000.0
    flow_range = np.linspace(0.0, q_max_curve * 1.05, 60).tolist()
    system_points = build_system_curve(
        segments, static_head_m, fluid.density_kg_m3, fluid.viscosity_pa_s, flow_range
    )
    system_q = [p.flow_m3_s for p in system_points]
    system_h = [p.total_head_m for p in system_points]

    def system_head_fn(q: float) -> float:
        return float(np.interp(q, system_q, system_h))

    results = []
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[q * 1000 for q in system_q], y=system_h, name="Sistema", line=dict(color="orange", width=3)))

    for scenario in scenarios:
        curve = _apply_scenario(base_curve, scenario)
        curve_q = [p.flow_m3_s for p in curve.points]
        curve_h = [p.head_m for p in curve.points]
        try:
            fit = fit_polynomial(curve_q, curve_h, degree)
        except ValueError as exc:
            st.error(f"{scenario['label']}: {exc}")
            continue

        def pump_head_fn(q: float, _fit=fit) -> float:
            return _fit.evaluate(q)

        q_bound = max(curve_q) * 1.2
        op = solve_operating_point(pump_head_fn, system_head_fn, q_min=0.0, q_max=q_bound)

        q_plot = np.linspace(0, q_bound, 60)
        fig.add_trace(
            go.Scatter(x=q_plot * 1000, y=[pump_head_fn(q) for q in q_plot], name=scenario["label"], line=dict(dash="dot" if scenario["label"] != "Nominal" else "solid"))
        )

        if op.found:
            if flat_efficiency_pct is not None:
                eta = flat_efficiency_pct / 100.0
            else:
                pt_q = [p.flow_m3_s for p in curve.points]
                pt_eta = [p.efficiency for p in curve.points]
                eta = float(np.interp(op.flow_m3_s, pt_q, pt_eta))
            power = compute_power(fluid.density_kg_m3, op.flow_m3_s, op.head_m, eta, motor_efficiency_pct / 100.0)
            fig.add_trace(go.Scatter(x=[op.flow_m3_s * 1000], y=[op.head_m], mode="markers", marker=dict(size=10), name=f"{scenario['label']} (operacion)", showlegend=False))
            results.append(
                {
                    "Escenario": scenario["label"],
                    "Q (L/s)": round(op.flow_m3_s * 1000, 2),
                    "H (m)": round(op.head_m, 2),
                    "eta bomba (%)": round(eta * 100, 1),
                    "P hidraulica (kW)": round(power.hydraulic_power_w / 1000, 2),
                    "P electrica (kW)": round(power.electrical_power_w / 1000, 2),
                    "Estado": "equilibrio",
                }
            )
        else:
            results.append(
                {
                    "Escenario": scenario["label"], "Q (L/s)": None, "H (m)": None, "eta bomba (%)": None,
                    "P hidraulica (kW)": None, "P electrica (kW)": None, "Estado": f"SIN INTERSECCION: {op.reason}",
                }
            )

    fig.update_layout(
        title="Punto de operacion — curva de bomba vs curva de sistema",
        xaxis_title="Caudal Q (L/s)", yaxis_title="Carga H (m)", height=480,
    )
    st.plotly_chart(fig, use_container_width=True, key="pump_operating_chart")

    st.subheader("Resultados por escenario")
    st.dataframe(results, use_container_width=True, hide_index=True)

    nominal = next((r for r in results if r["Escenario"] == "Nominal" and r["Q (L/s)"] is not None), None)

    st.subheader("Detalle por tramo (en el punto de operacion nominal)")
    if nominal:
        q_op = nominal["Q (L/s)"] / 1000.0
        detail = evaluate_system(segments, q_op, static_head_m, fluid.density_kg_m3, fluid.viscosity_pa_s)
        rows = []
        for seg, ev in zip(segments, detail.segment_evaluations):
            rows.append(
                {
                    "Tramo": ev.label, "L (m)": seg.length_m, "DI (mm)": seg.inside_diameter_mm,
                    "v (m/s)": round(ev.velocity_m_s, 3), "Re": f"{ev.reynolds:.3e}",
                    "Regimen": ev.regime.value, "f": round(ev.friction_factor, 4),
                    "hf (m)": round(ev.friction_head_loss_m, 3), "hs (m)": round(ev.minor_head_loss_m, 3),
                    "Convergio": ev.friction_converged,
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)
        for ev in detail.segment_evaluations:
            if not ev.friction_converged or ev.regime.value == "transicional":
                st.warning(f"{ev.label}: {ev.friction_note}")
    else:
        st.info("Sin punto de operacion nominal (ver estado en la tabla de resultados) — no se muestra detalle por tramo.")

    npsh_result = _render_npsh_section("pump", fluid, nominal)

    st.subheader("Resumen ejecutivo")
    st.markdown(_build_executive_summary(nominal, results, npsh_result, segments))


def _render_fluid_section(key_prefix: str) -> FluidProperties:
    st.markdown("**Fluido**")
    col1, col2, col3 = st.columns(3)
    custom = col1.checkbox("Fluido personalizado (no agua)", key=f"{key_prefix}_fluid_custom")
    if custom:
        density = col2.number_input("Densidad (kg/m3)", min_value=1.0, value=1000.0, key=f"{key_prefix}_fluid_density")
        viscosity = col3.number_input("Viscosidad dinamica (Pa.s)", min_value=1e-6, value=1.0e-3, format="%.6f", key=f"{key_prefix}_fluid_visc")
        temperature = col1.number_input("Temperatura (C)", value=20.0, key=f"{key_prefix}_fluid_temp_custom")
        fluid = custom_fluid("Personalizado", density, viscosity, temperature)
        st.warning(f"{fluid.source}")
    else:
        temperature = col2.number_input("Temperatura (C)", min_value=0.0, max_value=100.0, value=20.0, key=f"{key_prefix}_fluid_temp")
        try:
            fluid = water_properties(temperature)
        except TemperatureOutOfRangeError as exc:
            st.error(str(exc))
            st.stop()
        col3.caption(f"rho={fluid.density_kg_m3:.1f} kg/m3 · mu={fluid.viscosity_pa_s * 1000:.4f} mPa.s")
        st.caption(f"Fuente: {fluid.source}")
    return fluid


def _render_segments_section(key_prefix: str) -> list[PipeSegment]:
    st.markdown("**Linea de impulsion — tramos en serie**")
    n_segments = st.radio("Numero de tramos", [1, 2], horizontal=True, key=f"{key_prefix}_n_segments")
    segments = []
    cols = st.columns(n_segments)
    for i in range(n_segments):
        with cols[i]:
            st.markdown(f"*Tramo {i + 1}*")
            length = st.number_input("Longitud (m)", min_value=0.1, value=1250.0 if i == 0 else 100.0, key=f"{key_prefix}_len_{i}")
            di = st.number_input("Diametro interior (mm)", min_value=1.0, value=250.0, key=f"{key_prefix}_di_{i}")
            roughness = st.number_input("Rugosidad absoluta (mm)", min_value=0.0, value=0.007, format="%.4f", key=f"{key_prefix}_rough_{i}")
            fitting_names = st.multiselect("Accesorios en este tramo", list(FITTING_K_TABLE.keys()), key=f"{key_prefix}_fit_names_{i}")
            fitting_counts = {}
            for name in fitting_names:
                fitting_counts[name] = st.number_input(f"{name} (K={FITTING_K_TABLE[name]:g})", min_value=0, value=1, step=1, key=f"{key_prefix}_fit_{i}_{name}")
                if name in FITTING_K_DISCREPANCIES:
                    st.caption(f"⚠ {FITTING_K_DISCREPANCIES[name]}")
            segments.append(PipeSegment(label=f"Tramo {i + 1}", length_m=length, inside_diameter_mm=di, roughness_mm=roughness, fitting_counts=fitting_counts))
    return segments


def _render_pump_curve_section(key_prefix: str):
    st.markdown("**Curva de la bomba**")
    st.caption(
        "Ajuste por regresion de minimos cuadrados (no interpolacion lineal entre puntos). "
        "La columna eta (%) es opcional: si se completa para TODOS los puntos, la eficiencia "
        "se trata como curva (no como valor constante) en cada escenario."
    )
    default_rows = [
        {"Q (L/s)": 0.0, "H (m)": 38.0, "eta (%)": 0.0},
        {"Q (L/s)": 100.0, "H (m)": 34.0, "eta (%)": 0.0},
        {"Q (L/s)": 220.0, "H (m)": 24.0, "eta (%)": 0.0},
    ]
    edited = st.data_editor(default_rows, num_rows="dynamic", key=f"{key_prefix}_curve_editor", use_container_width=True)
    q_points = [float(r["Q (L/s)"]) for r in edited if r.get("Q (L/s)") is not None]
    h_points = [float(r["H (m)"]) for r in edited if r.get("H (m)") is not None]
    eta_raw = [r.get("eta (%)") for r in edited if r.get("Q (L/s)") is not None]
    eta_points = [(float(e) if e else None) for e in eta_raw]

    degree_label = st.selectbox("Modelo de ajuste", list(_DEGREE_LABELS.keys()), index=2, key=f"{key_prefix}_degree")
    degree = _DEGREE_LABELS[degree_label]
    return q_points, h_points, eta_points, degree


def _render_scenarios_section(key_prefix: str) -> list[dict]:
    st.markdown("**Escenarios (VDF / bombas gemelas)**")
    st.caption(
        "Leyes de afinidad: Q proporcional a phi, H proporcional a phi^2. La eficiencia de "
        "cada punto se traslada al punto escalado (no se fuerza un valor plano)."
    )
    scenarios = [{"label": "Nominal", "phi": 1.0, "parallel_n": 1, "series_n": 1}]
    n_extra = st.number_input("Escenarios VDF adicionales", min_value=0, max_value=5, value=0, key=f"{key_prefix}_n_scenarios")
    nominal_rpm = st.number_input("Velocidad nominal (rpm)", min_value=1.0, value=2900.0, key=f"{key_prefix}_rpm_nominal") if n_extra else None
    for i in range(int(n_extra)):
        rpm = st.number_input(f"Velocidad escenario {i + 1} (rpm)", min_value=1.0, value=2900.0 - (i + 1) * 300, key=f"{key_prefix}_rpm_{i}")
        scenarios.append({"label": f"{rpm:g} rpm", "phi": rpm / nominal_rpm, "parallel_n": 1, "series_n": 1})

    col1, col2 = st.columns(2)
    n_parallel = col1.number_input("N bombas identicas en paralelo (aplica a todos los escenarios)", min_value=1, value=1, key=f"{key_prefix}_n_parallel")
    n_series = col2.number_input("N bombas identicas en serie (aplica a todos los escenarios)", min_value=1, value=1, key=f"{key_prefix}_n_series")
    if n_parallel > 1 or n_series > 1:
        for s in scenarios:
            s["parallel_n"] = int(n_parallel)
            s["series_n"] = int(n_series)
    return scenarios


def _apply_scenario(base_curve: PumpCurve, scenario: dict) -> PumpCurve:
    curve = base_curve
    if scenario["phi"] != 1.0:
        curve = scale_by_affinity(curve, scenario["phi"], label=scenario["label"])
    if scenario["parallel_n"] > 1:
        curve = twin_parallel(curve, scenario["parallel_n"], label=scenario["label"])
    if scenario["series_n"] > 1:
        curve = twin_series(curve, scenario["series_n"], label=scenario["label"])
    return PumpCurve(points=curve.points, label=scenario["label"])


def _render_npsh_section(key_prefix: str, fluid: FluidProperties, nominal: dict | None):
    with st.expander("Verificacion NPSH (succion) — opcional"):
        st.caption(
            "Ausente por completo en PiezoCalc. NPSHa = (Patm - Pvap)/(rho*g) - h_succion - "
            "h_friccion_succion - h_singulares_succion. Formulas y margen de seguridad "
            "documentados en docs/HYDRAULICS_PUMP_OPERATING_POINT.md."
        )
        enabled = st.checkbox("Calcular NPSH disponible", key=f"{key_prefix}_npsh_enabled")
        if not enabled:
            return None

        col1, col2 = st.columns(2)
        altitude = col1.number_input("Altitud de la bomba (m s.n.m.)", value=0.0, key=f"{key_prefix}_npsh_alt")
        suction_head = col2.number_input(
            "Altura de succion (m) — positivo = succion en elevacion, negativo = succion inundada",
            value=3.0, key=f"{key_prefix}_npsh_suction_head",
        )
        suction_segment = _render_segments_section(f"{key_prefix}_npsh_suction")[0] if st.checkbox(
            "Definir tramo de succion (para friccion)", key=f"{key_prefix}_npsh_suction_seg_toggle"
        ) else None

        npsh_required = st.number_input("NPSH requerido por el fabricante en el punto de operacion (m)", min_value=0.0, value=3.0, key=f"{key_prefix}_npsh_req")
        margin = st.number_input("Margen de seguridad (m)", min_value=0.0, value=DEFAULT_NPSH_SAFETY_MARGIN_M, key=f"{key_prefix}_npsh_margin")

        friction_head = 0.0
        minor_head = 0.0
        if suction_segment and nominal:
            q_op = nominal["Q (L/s)"] / 1000.0
            ev = evaluate_system([suction_segment], q_op, 0.0, fluid.density_kg_m3, fluid.viscosity_pa_s).segment_evaluations[0]
            friction_head = ev.friction_head_loss_m
            minor_head = ev.minor_head_loss_m
        elif not suction_segment:
            st.info("Sin tramo de succion definido: NPSHa se calcula sin perdidas de friccion en la succion (hf=hs=0).")

        result = npsh_available(altitude, fluid.temperature_c, suction_head, friction_head, minor_head, fluid.density_kg_m3)
        check = check_npsh(result.npsh_available_m, npsh_required, margin)

        st.metric("NPSH disponible (NPSHa)", f"{result.npsh_available_m:.2f} m")
        if check.passed:
            st.success(f"PASS — NPSHa supera NPSHr + margen por {check.margin_actual_m - margin:.2f} m adicionales.")
        else:
            st.error(f"FAIL — falta {margin - check.margin_actual_m:.2f} m de margen. Riesgo de cavitacion.")
        return check


def _build_executive_summary(nominal, results, npsh_result, segments) -> str:
    if not nominal:
        return (
            "No se encontro un punto de operacion en equilibrio para el escenario nominal — "
            "revisa si la curva de bomba y la curva de sistema se cruzan en el rango de "
            "caudal evaluado."
        )
    lines = [
        f"- Punto de operacion nominal: **Q = {nominal['Q (L/s)']} L/s**, "
        f"**H = {nominal['H (m)']} m**, eficiencia de bomba usada {nominal['eta bomba (%)']}%.",
        f"- Potencia hidraulica {nominal['P hidraulica (kW)']} kW; potencia electrica estimada "
        f"**{nominal['P electrica (kW)']} kW** ({nominal['P electrica (kW)'] * 1.34102:.1f} HP).",
    ]
    other = [r for r in results if r["Escenario"] != "Nominal"]
    if other:
        lines.append(f"- {len(other)} escenario(s) adicional(es) evaluados — ver tabla de resultados.")
    failed = [r for r in results if "SIN INTERSECCION" in str(r["Estado"])]
    if failed:
        lines.append(
            f"- **{len(failed)} escenario(s) sin interseccion** entre curva de bomba y curva "
            "de sistema — la bomba no es capaz de vencer la carga estatica/friccional en "
            "esas condiciones."
        )
    if npsh_result is not None:
        estado = "PASS" if npsh_result.passed else "FAIL — riesgo de cavitacion"
        lines.append(
            f"- NPSH: disponible {npsh_result.npsh_available_m:.2f} m vs requerido "
            f"{npsh_result.npsh_required_m:.2f} m + margen {npsh_result.safety_margin_m:.2f} m "
            f"-> **{estado}**."
        )
    else:
        lines.append("- NPSH no evaluado en esta corrida (seccion opcional sin activar).")
    return "\n".join(lines)
