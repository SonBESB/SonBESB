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

import json
from dataclasses import asdict
from core.hydraulics.pipe_catalog import CLASSES, load_pexgol_catalog, catalog_provenance, allowed_pressure_bar

from core.hydraulics.affinity import PumpCurve, PumpCurvePoint, scale_by_affinity, twin_parallel, twin_series
from core.hydraulics.curve_fit import fit_polynomial
from core.hydraulics.fluids import FluidProperties, TemperatureOutOfRangeError, custom_fluid, water_properties
from core.hydraulics.minor_losses import FITTING_K_DISCREPANCIES, FITTING_K_TABLE
from core.hydraulics.npsh import DEFAULT_NPSH_SAFETY_MARGIN_M, check_npsh, npsh_available
from core.hydraulics.operating_point import solve_operating_point
from core.hydraulics.power import compute_power
from core.hydraulics.pressure_rating import PN_BAR_TABLE, build_shutoff_pressure_profile
from core.hydraulics.surge import PIPE_ELASTIC_MODULUS_PA, WATER_BULK_MODULUS_PA, compute_surge
from core.hydraulics.system_curve import PipeSegment, build_system_curve, evaluate_system
from core.hydraulics.velocity_check import DEFAULT_MAX_VELOCITY_M_S, DEFAULT_MIN_VELOCITY_M_S, check_velocity

_DEGREE_LABELS = {"Constante (grado 0)": 0, "Lineal (grado 1)": 1, "Cuadratica (grado 2)": 2, "Cubica (grado 3)": 3}


def render_pump_operating_point_tab() -> None:
    st.info("Empieza aquí: recorre los pasos 1 a 3 de arriba hacia abajo. Los valores cargados son un EJEMPLO; reemplázalos por los de tu instalación. Al llegar al paso 4 verás el resultado calculado.")
    st.markdown("**Necesitarás:** desnivel, longitud y diámetro interior de la tubería, y al menos tres puntos de la curva de tu bomba para el ajuste cuadrático inicial.")
    with st.container(border=True):
        st.subheader("1 · ¿Qué líquido vas a bombear y hasta qué altura?")
        st.write("Para agua, basta con indicar su temperatura. El desnivel es la cota del destino menos la cota del origen.")
        fluid = _render_fluid_section("pump")
        static_head_m = st.number_input(
            "Desnivel entre destino y origen (m)",
            value=18.5, step=0.1, key="pump_static_head",
            help="Ejemplo: origen a 100 m y destino a 118,5 m → 18,5 m. No es la longitud de tubería. Si el destino está más abajo, usa un valor negativo.",
        )

        st.caption("Ejemplo: origen 100 m → destino 118,5 m → desnivel +18,5 m.")
    with st.container(border=True):
        st.subheader("2 · ¿Cómo es tu tubería?")
        st.write("Comienza con un tramo. Ingresa la longitud real del recorrido y el diámetro INTERIOR, o elige una referencia PEXGOL para cargar sus dimensiones.")
        segments, pn_labels, catalog_rows = _render_segments_section("pump", fluid=fluid)
    with st.container(border=True):
        st.subheader("3 · Ingresa los datos de tu bomba")
        st.write("Busca la curva Q–H del fabricante. Haz doble clic en las celdas para reemplazar el ejemplo: Q es caudal en L/s y H es altura en metros. Si no tienes esa curva, solo puedes explorar el ejemplo; no seleccionar tu bomba real.")
        q_points, h_points, eta_points, degree = _render_pump_curve_section("pump")
        if len(q_points) < degree + 1:
            st.error(f"Se necesitan al menos {degree + 1} puntos para un ajuste de grado {degree}.")
            return

        motor_efficiency_pct = st.number_input("Eficiencia motor (%)", min_value=1.0, max_value=100.0, value=92.0, key="pump_eta_motor")
        with st.expander("Comparar velocidades y bombas en serie / paralelo"):
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

    nominal_shutoff_head_m = None
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

        if scenario["label"] == "Nominal":
            nominal_shutoff_head_m = fit.evaluate(0.0)
            if min(curve_q) > 0:
                st.caption(
                    f"⚠ La curva de bomba no incluye Q=0: el shutoff head usado para el "
                    f"chequeo de presion ({nominal_shutoff_head_m:.2f} m) es una EXTRAPOLACION "
                    "del ajuste, no un dato medido."
                )

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

    nominal = next((r for r in results if r["Escenario"] == "Nominal" and r["Q (L/s)"] is not None), None)
    with st.container(border=True):
        st.subheader("4 · Revisa el resultado de los datos ingresados")
        if nominal:
            flow, head, power = st.columns(3)
            flow.metric("Caudal", f"{nominal['Q (L/s)']:.2f} L/s")
            head.metric("Altura", f"{nominal['H (m)']:.2f} m")
            power.metric("Potencia eléctrica", f"{nominal['P electrica (kW)']:.2f} kW")
        else:
            st.info("No hay un punto de equilibrio. Revisa la curva y el desnivel de tu sistema.")
        fig.update_layout(
            xaxis_title="Caudal (L/s)", yaxis_title="Altura (m)", height=390,
            margin=dict(l=10, r=10, t=25, b=10),
            legend=dict(orientation="h", y=-0.2), template="plotly_white",
            font=dict(family="sans-serif", size=14),
        )
        st.plotly_chart(fig, use_container_width=True, key="pump_operating_chart")
        st.caption("El cruce de las curvas indica el caudal y la altura de funcionamiento.")
        with st.expander("Comparación de escenarios"):
            st.dataframe(results, use_container_width=True, hide_index=True)
        if any(catalog_rows):
            st.caption("PEXGOL · Catálogo preliminar pendiente de revisión humana.")

    _render_formula_guide(fluid, segments, nominal, q_points, h_points, degree)
    st.subheader("5 · Verificaciones y descarga")
    st.caption("Después de revisar el caudal, comprueba presión, velocidad y, si tienes los datos, succión y cierre de válvulas.")
    with st.expander("Velocidad y pérdidas por tramo"):
        st.subheader("Detalle por tramo (en el punto de operacion nominal)")
        col_vmin, col_vmax = st.columns(2)
        v_min = col_vmin.number_input("Velocidad minima recomendada (m/s) — guia, no norma", min_value=0.0, value=DEFAULT_MIN_VELOCITY_M_S, key="pump_vmin")
        v_max = col_vmax.number_input("Velocidad maxima recomendada (m/s) — guia, no norma", min_value=0.1, value=DEFAULT_MAX_VELOCITY_M_S, key="pump_vmax")

        velocity_checks = []
        if nominal:
            q_op = nominal["Q (L/s)"] / 1000.0
            detail = evaluate_system(segments, q_op, static_head_m, fluid.density_kg_m3, fluid.viscosity_pa_s)
            rows = []
            for seg, ev in zip(segments, detail.segment_evaluations):
                vcheck = check_velocity(ev.label, ev.velocity_m_s, v_min, v_max)
                velocity_checks.append(vcheck)
                rows.append(
                    {
                        "Tramo": ev.label, "L (m)": seg.length_m, "DI (mm)": seg.inside_diameter_mm,
                        "v (m/s)": round(ev.velocity_m_s, 3), "v OK?": vcheck.status, "Re": f"{ev.reynolds:.3e}",
                        "Regimen": ev.regime.value, "f": round(ev.friction_factor, 4),
                        "hf (m)": round(ev.friction_head_loss_m, 3), "hs (m)": round(ev.minor_head_loss_m, 3),
                        "Convergio": ev.friction_converged,
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)
            for ev in detail.segment_evaluations:
                if not ev.friction_converged or ev.regime.value == "transicional":
                    st.warning(f"{ev.label}: {ev.friction_note}")
            for vcheck in velocity_checks:
                if vcheck.status == "BAJA":
                    st.warning(f"{vcheck.label}: v={vcheck.velocity_m_s:.3f} m/s por debajo de {vcheck.min_velocity_m_s:g} m/s — riesgo de sedimentacion/deposito.")
                elif vcheck.status == "ALTA":
                    st.warning(f"{vcheck.label}: v={vcheck.velocity_m_s:.3f} m/s por encima de {vcheck.max_velocity_m_s:g} m/s — riesgo de erosion/golpe de ariete mas severo.")
        else:
            st.info("Sin punto de operacion nominal (ver estado en la tabla de resultados) — no se muestra detalle por tramo.")

    with st.expander("Presión admisible de las tuberías"):
        pressure_checks = _render_pressure_rating_section("pump", segments, pn_labels, nominal_shutoff_head_m, fluid, static_head_m, catalog_rows)
    npsh_result = _render_npsh_section("pump", fluid, nominal)
    surge_result = _render_surge_section("pump", segments, fluid, nominal, catalog_rows)

    st.subheader("Resumen de tu sistema")
    if any(catalog_rows):
        st.warning("Caso PRELIMINAR: contiene datos PEXGOL DRAFT_UNVERIFIED.")
    st.markdown(_build_executive_summary(nominal, results, npsh_result, segments, velocity_checks, pressure_checks, surge_result))

    _render_export_section("pump", fluid, segments, pn_labels, static_head_m, q_points, h_points, eta_points, degree, results, nominal, npsh_result, pressure_checks, surge_result, catalog_rows)


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


def _render_segments_section(key_prefix: str, show_pressure_class: bool = True, fluid=None):
    st.markdown("**Tuberías de impulsión**")
    st.caption("Añade un tramo cuando cambie el diámetro o el material de la línea. Modelo de tramos en serie, sin ramificaciones.")
    n_segments = st.number_input("Numero de tramos", min_value=1, max_value=12, value=1, step=1, key=f"{key_prefix}_n_segments")
    segments = []
    pn_labels = []
    catalog_rows = []
    total_length = 0.0
    for i in range(int(n_segments)):
        with st.expander(f"Tramo {i + 1}", expanded=(i == 0)):
            source = st.selectbox("Origen de dimensiones", ["Manual", "PEXGOL 2023 (borrador)"], key=f"{key_prefix}_source_{i}")
            row = None
            length = st.number_input("Longitud (m)", min_value=0.1, value=1250.0 if i == 0 else 100.0, key=f"{key_prefix}_len_{i}")
            if source != "Manual":
                catalog = load_pexgol_catalog()
                cls = st.selectbox("Clase PEXGOL", CLASSES, index=2, key=f"{key_prefix}_pex_class_{i}")
                options = [r for r in catalog["rows"] if r["pressure_class"] == cls]
                selected = st.selectbox("Referencia / diametro exterior", range(len(options)),
                    format_func=lambda j: f"DE {options[j]['outside_diameter_mm']:g} mm | {options[j]['catalog_code']}",
                    key=f"{key_prefix}_pex_ref_{i}_{cls}")
                row = dict(options[selected])
                row["provenance"] = asdict(catalog_provenance(row["page"]))
                row["source_sha256"] = catalog["sha256"]
                st.caption("Catálogo preliminar · datos pendientes de revisión humana.")
                st.write(f"DI publicado: {row['inside_diameter_mm']:g} mm · Espesor: {row['wall_thickness_mm']:g} mm · SDR {row['sdr']:g} · Pagina {row['page']}")
                for issue in row["issues"]:
                    st.warning(issue)
                if row['availability'] != 'standard':
                    st.caption("Disponibilidad: " + ("bajo pedido especial" if row['availability'] == 'special_order' else "cantidad minima requerida"))
                di = row["inside_diameter_mm"]
                roughness = st.number_input("Rugosidad PEXGOL (mm)", min_value=0.0, value=0.0007, format="%.5f", key=f"{key_prefix}_pex_rough_{i}")
                st.caption("Pagina 23: 0,0005–0,0007 mm. Se propone el extremo superior; editable segun servicio.")
                row['roughness_used_mm'] = roughness
                row['roughness_source'] = 'p. 23; extremo superior propuesto o valor editado por usuario'
                row['allowable_pressure_bar'] = None
                if fluid is not None and fluid.name == 'Agua':
                    try:
                        pressure, ref_temp = allowed_pressure_bar(cls, fluid.temperature_c)
                        row.update(allowable_pressure_bar=pressure, design_temperature_c=fluid.temperature_c, table_temperature_c=ref_temp, pressure_source='Tabla 9.1, p. 9, agua, C=1.25')
                        st.caption(f"Presion admisible preliminar: {pressure:g} bar a temperatura tabulada {ref_temp} C (escalon superior, sin interpolar).")
                    except ValueError as exc:
                        st.warning(str(exc))
                elif fluid is not None:
                    st.warning("Tabla 9.1 solo para agua. Presion admisible no evaluada para fluido personalizado.")
                pn_label = f"PEXGOL Clase {cls}"
            else:
                col2, col3 = st.columns(2)
                di = col2.number_input("Diametro interior (mm)", min_value=1.0, value=250.0, key=f"{key_prefix}_di_{i}", help="Usa el diámetro libre por donde circula el agua. No ingreses el diámetro exterior ni el DN sin comprobar su equivalencia.")
                roughness = col3.number_input("Rugosidad absoluta (mm)", min_value=0.0, value=0.007, format="%.4f", key=f"{key_prefix}_rough_{i}", help="Irregularidad de la pared interior en mm. El 0,007 inicial es un supuesto del ejemplo; sustituye según material, fabricante y estado de servicio.")
                pn_label = st.selectbox("Clase de presion (PN) — referencia a 20 C, sin derateo", list(PN_BAR_TABLE), index=1, key=f"{key_prefix}_pn_{i}") if show_pressure_class else None
            if show_pressure_class:
                pn_labels.append(pn_label)
            catalog_rows.append(row)
            fitting_names = st.multiselect("Accesorios en este tramo", list(FITTING_K_TABLE.keys()), key=f"{key_prefix}_fit_names_{i}", help="Selecciona codos, válvulas y otras piezas; después indica cuántas hay de cada una. Vacío significa que no se incluyen pérdidas por accesorios.")
            fitting_counts = {}
            for name in fitting_names:
                fitting_counts[name] = st.number_input(f"{name} (K={FITTING_K_TABLE[name]:g})", min_value=0, value=1, step=1, key=f"{key_prefix}_fit_{i}_{name}")
                if name in FITTING_K_DISCREPANCIES:
                    st.caption(f"⚠ {FITTING_K_DISCREPANCIES[name]}")
            segments.append(PipeSegment(label=f"Tramo {i + 1}", length_m=length, inside_diameter_mm=di, roughness_mm=roughness, fitting_counts=fitting_counts))
            total_length += length
    if n_segments > 1:
        st.caption(f"Longitud total: {total_length:.2f} m")
    return segments, pn_labels, catalog_rows


def _render_pump_curve_section(key_prefix: str):
    st.markdown("**Curva de la bomba**")
    st.caption(
        "Si la curva viene en m³/h, divide el caudal por 3,6 para obtener L/s. "
        "Ajuste por regresion de minimos cuadrados (no interpolacion lineal entre puntos). "
        "La columna eta (%) es opcional: si se completa para TODOS los puntos, la eficiencia "
        "se trata como curva (no como valor constante) en cada escenario."
    )
    default_rows = [
        {"Q (L/s)": 0.0, "H (m)": 38.0, "eta (%)": 0.0},
        {"Q (L/s)": 100.0, "H (m)": 34.0, "eta (%)": 0.0},
        {"Q (L/s)": 220.0, "H (m)": 24.0, "eta (%)": 0.0},
    ]
    st.caption("Eficiencia eta (%): deja toda la columna en 0 o vacía si no tienes una curva de eficiencia; se pedirá una eficiencia constante asumida abajo.")
    edited = st.data_editor(default_rows, num_rows="dynamic", key=f"{key_prefix}_curve_editor", use_container_width=True)
    valid_rows = []
    for r in edited:
        if r.get("Q (L/s)") is None and r.get("H (m)") is None:
            continue
        if r.get("Q (L/s)") is None or r.get("H (m)") is None:
            st.error("Completa caudal Q y altura H en cada fila de la curva, o elimina la fila incompleta.")
            st.stop()
        q, h = float(r["Q (L/s)"]), float(r["H (m)"])
        e = r.get("eta (%)")
        if not np.isfinite(q) or not np.isfinite(h) or q < 0 or h < 0:
            st.error("Q y H deben ser números finitos mayores o iguales a cero.")
            st.stop()
        if e is not None and (not np.isfinite(float(e)) or not 0 <= float(e) <= 100):
            st.error("La eficiencia debe estar entre 0 y 100 %.")
            st.stop()
        valid_rows.append(r)
    q_points = [float(r["Q (L/s)"]) for r in valid_rows]
    h_points = [float(r["H (m)"]) for r in valid_rows]
    eta_points = [float(r["eta (%)"]) if r.get("eta (%)") else None for r in valid_rows]
    if not q_points or max(q_points) <= 0 or len(set(q_points)) != len(q_points):
        st.error("Ingresa caudales distintos, con al menos uno mayor que cero.")
        st.stop()

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
            "Comprueba si la succión tiene margen suficiente para evitar cavitación. NPSHa = (Patm - Pvap)/(rho*g) - h_succion - "
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
        suction_segment = _render_segments_section(f"{key_prefix}_npsh_suction", show_pressure_class=False, fluid=fluid)[0][0] if st.checkbox(
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


def _render_pressure_rating_section(key_prefix, segments, pn_labels, shutoff_head_m, fluid, static_head_m, catalog_rows=None):
    st.subheader("Presion de diseno vs clase PN (condicion de caudal cero / shutoff)")
    st.caption(
        "A caudal "
        "cero no hay perdida por friccion: toda la carga de la bomba en Q=0 aparece como "
        "presion estatica en la descarga — es la condicion mas exigente en regimen "
        "permanente (sin contar golpe de ariete, ver seccion aparte). Perfil de elevacion "
        "repartido proporcional a la longitud — ver limitacion en "
        "docs/HYDRAULICS_PUMP_OPERATING_POINT.md."
    )
    if shutoff_head_m is None or not pn_labels:
        st.info("Sin punto de operacion nominal o sin clases PN definidas — no se evalua.")
        return None

    catalog_rows = catalog_rows or [None] * len(segments)
    limits = [r['allowable_pressure_bar'] if r else PN_BAR_TABLE[pn] for r, pn in zip(catalog_rows, pn_labels)]
    if any(p is None for p in limits):
        st.warning("Presion no evaluada: hay un tramo PEXGOL fuera del alcance de la tabla de agua/temperatura.")
        return None
    if any(catalog_rows):
        st.warning("Comparacion PRELIMINAR con catalogo sin verificar. PASS no significa aprobacion para diseno.")
    checks = build_shutoff_pressure_profile(segments, shutoff_head_m, static_head_m, fluid.density_kg_m3, pn_labels, allowable_pressures_bar=limits)
    st.dataframe(
        [
            {
                "Tramo": c.label, "Desde (m)": round(c.start_length_m, 1), "Hasta (m)": round(c.end_length_m, 1),
                "Presion de diseno (bar)": round(c.max_design_pressure_bar, 2), "Clase": c.pn_label,
                "Admisible (bar)": c.pn_bar, "Margen (bar)": round(c.margin_bar, 2), "Estado": "PASS" if c.passed else "FAIL",
            }
            for c in checks
        ],
        use_container_width=True, hide_index=True,
    )
    failed = [c for c in checks if not c.passed]
    if failed:
        st.error(f"{len(failed)} tramo(s) con presion de diseno por ENCIMA de su clase PN.")
    else:
        st.success("Todos los tramos dentro de su clase PN en la condicion de shutoff.")
    return checks


def _render_surge_section(key_prefix, segments, fluid, nominal, catalog_rows=None):
    with st.expander("Golpe de ariete (transiente) — opcional"):
        st.caption(
            "Estima la sobrepresión al cerrar una válvula. Modelo simplificado "
            "(Joukowsky + aproximacion de cierre lento, celeridad de tuberia de pared "
            "delgada) — no reemplaza un analisis transiente completo. Formulas y "
            "limitaciones en docs/HYDRAULICS_PUMP_OPERATING_POINT.md."
        )
        enabled = st.checkbox("Calcular sobrepresion por cierre de valvula", key=f"{key_prefix}_surge_enabled")
        if not enabled:
            return None
        if not nominal:
            st.info("Sin punto de operacion nominal — no se puede estimar la velocidad a cortar.")
            return None

        segment_labels = [s.label for s in segments]
        idx = st.selectbox("Tramo a analizar (tipicamente el mas cercano a la valvula/bomba)", range(len(segments)), format_func=lambda i: segment_labels[i], key=f"{key_prefix}_surge_segment")
        segment = segments[idx]

        col1, col2, col3 = st.columns(3)
        row = catalog_rows[idx] if catalog_rows else None
        if row:
            material = "PEXGOL"
            wall_thickness_mm = row['wall_thickness_mm']
            col2.metric("Espesor catalogo (mm)", f"{wall_thickness_mm:g}")
            elastic_mpa = col1.number_input("Modulo E corto plazo (MPa) — ingresado por usuario", min_value=0.1, value=465.0, key=f"{key_prefix}_surge_pex_E_{idx}")
            st.caption("465 MPa es el ejemplo PEXGOL enterrado a 20 C (p. 46); no es una tabla universal. Ajustar E para temperatura y condiciones reales.")
            if not st.checkbox("Usar este E como supuesto para la estimacion preliminar", key=f"{key_prefix}_surge_pex_E_use_{idx}"):
                return None
            elastic_pa = elastic_mpa * 1e6
            row['surge_elastic_modulus_pa'] = elastic_pa
            row['surge_elastic_modulus_source'] = 'Supuesto del usuario; referencia ejemplo p. 46, 465 MPa a 20 C'
        else:
            material = col1.selectbox("Material de la tuberia", list(PIPE_ELASTIC_MODULUS_PA.keys()), key=f"{key_prefix}_surge_material")
            wall_thickness_mm = col2.number_input("Espesor de pared (mm)", min_value=0.1, value=14.8, key=f"{key_prefix}_surge_wall")
            elastic_pa = PIPE_ELASTIC_MODULUS_PA[material]
        closure_time_s = col3.number_input("Tiempo de cierre de la valvula (s)", min_value=0.01, value=2.0, key=f"{key_prefix}_surge_closure")

        q_op = nominal["Q (L/s)"] / 1000.0
        ev = evaluate_system([segment], q_op, 0.0, fluid.density_kg_m3, fluid.viscosity_pa_s).segment_evaluations[0]
        v_operating = ev.velocity_m_s

        result = compute_surge(
            length_m=segment.length_m, delta_velocity_m_s=v_operating, closure_time_s=closure_time_s,
            fluid_bulk_modulus_pa=WATER_BULK_MODULUS_PA, density_kg_m3=fluid.density_kg_m3,
            inside_diameter_m=segment.inside_diameter_m, wall_thickness_m=wall_thickness_mm / 1000.0,
            pipe_elastic_modulus_pa=elastic_pa, static_head_before_m=nominal["H (m)"],
        )
        if material != "HDPE" or fluid.name != "Agua":
            st.caption(
                f"⚠ Modulo de compresibilidad del fluido usado: agua ({WATER_BULK_MODULUS_PA:.2e} Pa). "
                "Si el fluido real no es agua, este valor no aplica."
            )

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Celeridad de onda", f"{result.wave_speed_m_s:.0f} m/s")
        col_b.metric("Tiempo critico (2L/a)", f"{result.critical_time_s:.2f} s")
        col_c.metric("Regimen de cierre", result.closure_regime)
        st.metric("Sobrepresion (golpe de ariete)", f"{result.surge_head_m:.2f} m")
        st.metric("Presion pico estimada (estatica + golpe)", f"{result.peak_pressure_head_m:.2f} m")
        st.warning(
            "Este valor debe sumarse (no reemplazar) al chequeo de presion vs PN de la "
            "seccion anterior para ese tramo — un cierre rapido puede llevar la presion "
            "pico muy por encima de la condicion de shutoff en regimen permanente."
        )
        return result


def _render_export_section(key_prefix, fluid, segments, pn_labels, static_head_m, q_points, h_points, eta_points, degree, results, nominal, npsh_result, pressure_checks, surge_result, catalog_rows=None):
    st.subheader("Guarda tu caso")
    case = {
        "fluido": {
            "nombre": fluid.name, "densidad_kg_m3": fluid.density_kg_m3, "viscosidad_pa_s": fluid.viscosity_pa_s,
            "temperatura_c": fluid.temperature_c, "fuente": fluid.source,
        },
        "tramos": [
            {
                "label": s.label, "longitud_m": s.length_m, "diametro_interior_mm": s.inside_diameter_mm,
                "rugosidad_mm": s.roughness_mm, "accesorios": s.fitting_counts,
                "clase_pn": pn_labels[i] if i < len(pn_labels) else None,
                "catalogo": catalog_rows[i] if catalog_rows else None,
            }
            for i, s in enumerate(segments)
        ],
        "altura_estatica_m": static_head_m,
        "curva_bomba": {"grado_ajuste": degree, "puntos": [{"Q_L_s": q, "H_m": h, "eta_pct": e} for q, h, e in zip(q_points, h_points, eta_points)]},
        "resultados_por_escenario": results,
        "npsh": None if npsh_result is None else {
            "npsh_disponible_m": npsh_result.npsh_available_m, "npsh_requerido_m": npsh_result.npsh_required_m,
            "margen_seguridad_m": npsh_result.safety_margin_m, "passed": npsh_result.passed,
        },
        "presion_vs_pn": None if pressure_checks is None else [
            {"tramo": c.label, "presion_diseno_bar": c.max_design_pressure_bar, "clase_pn": c.pn_label, "pn_bar": c.pn_bar, "passed": c.passed}
            for c in pressure_checks
        ],
        "golpe_de_ariete": None if surge_result is None else {
            "celeridad_m_s": surge_result.wave_speed_m_s, "tiempo_critico_s": surge_result.critical_time_s,
            "regimen": surge_result.closure_regime, "sobrepresion_m": surge_result.surge_head_m,
            "presion_pico_m": surge_result.peak_pressure_head_m,
        },
        "_aviso": "MODELO DE INGENIERIA generado por BESB Piping (core/hydraulics/) — no reemplaza calculo de proveedor ni norma de diseno del proyecto.",
    }
    st.download_button(
        "Descargar caso (JSON)", data=json.dumps(case, indent=2, ensure_ascii=False),
        file_name="punto_operacion_bombeo.json", mime="application/json", key=f"{key_prefix}_export",
    )


def _build_executive_summary(nominal, results, npsh_result, segments, velocity_checks=None, pressure_checks=None, surge_result=None) -> str:
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

    if velocity_checks:
        bad = [v for v in velocity_checks if v.status != "OK"]
        if bad:
            lines.append(
                f"- **{len(bad)} tramo(s) fuera del rango de velocidad recomendado** "
                f"({velocity_checks[0].min_velocity_m_s:g}-{velocity_checks[0].max_velocity_m_s:g} m/s, guia no norma): "
                + ", ".join(f"{v.label} ({v.status}, {v.velocity_m_s:.2f} m/s)" for v in bad) + "."
            )
        else:
            lines.append("- Velocidad dentro del rango recomendado en todos los tramos.")

    if pressure_checks:
        failed_pn = [c for c in pressure_checks if not c.passed]
        if failed_pn:
            lines.append(
                f"- **{len(failed_pn)} tramo(s) superan su clase PN en condicion de shutoff** "
                "(caudal cero): " + ", ".join(f"{c.label} ({c.max_design_pressure_bar:.1f} bar > {c.pn_label})" for c in failed_pn) + "."
            )
        else:
            lines.append("- Presion de diseno (shutoff) dentro de la clase PN en todos los tramos.")

    if surge_result is not None:
        lines.append(
            f"- Golpe de ariete ({surge_result.closure_regime.lower()}): sobrepresion "
            f"{surge_result.surge_head_m:.2f} m, presion pico estimada "
            f"**{surge_result.peak_pressure_head_m:.2f} m** — sumar contra la clase PN, no "
            "esta incluida en el chequeo de shutoff de arriba."
        )
    return "\n".join(lines)


def _render_formula_guide(fluid, segments, nominal, q_points, h_points, degree):
    with st.expander("Ver fórmulas utilizadas y cómo se aplican a este caso", expanded=False):
        st.write("El cálculo busca el caudal al que la altura entregada por la bomba iguala la altura requerida por tu sistema. Las ecuaciones usan unidades SI; los campos en L/s y mm se convierten antes de calcular.")
        st.latex(r"Q_{\mathrm{m^3/s}}=Q_{\mathrm{L/s}}/1000,\quad D_{\mathrm m}=D_{\mathrm{mm}}/1000,\quad g=9.80665\;\mathrm{m/s^2}")
        st.markdown("**A. Velocidad y pérdidas en cada tramo**")
        st.latex(r"A=\frac{\pi D^2}{4},\quad v=\frac{Q}{A},\quad Re=\frac{\rho vD}{\mu}")
        st.latex(r"h_f=f\frac{L}{D}\frac{v^2}{2g},\qquad h_s=\left(\sum_j n_jK_j\right)\frac{v^2}{2g}")
        st.write("A: área interior (m²); v: velocidad (m/s); Re: Reynolds (sin unidad); ρ: densidad (kg/m³); μ: viscosidad dinámica (Pa·s). L es la longitud (m), f el factor de Darcy y K el coeficiente de cada accesorio repetido n veces. hf y hs se expresan en metros de columna de fluido.")
        st.latex(r"f=64/Re\quad(Re<2300)")
        st.latex(r"\frac{1}{\sqrt f}=-2\log_{10}\left(\frac{\varepsilon}{3.7D}+\frac{2.51}{Re\sqrt f}\right)")
        st.caption("Colebrook–White se resuelve iterativamente; ε es rugosidad en metros. Entre Re=2300 y 4000 se usa como estimación con aviso de régimen transicional. En Q=0, las pérdidas son cero.")
        st.markdown("**B. Curvas del sistema y de la bomba**")
        st.latex(r"H_{\mathrm{sistema}}(Q)=\Delta z+\sum_i(h_{f,i}+h_{s,i}),\qquad H_{\mathrm{bomba}}(Q)=\sum_{k=0}^{d}a_kQ^k")
        st.latex(r"H_{\mathrm{bomba}}(Q_*)=H_{\mathrm{sistema}}(Q_*)")
        st.write("Δz es el desnivel destino menos origen (m). La curva de bomba se ajusta por mínimos cuadrados al grado elegido; el cruce se busca por bisección. En esta versión, la curva del sistema se interpola entre 60 puntos y fuera de su rango conserva el extremo: revisa el rango de la curva antes de interpretar escenarios alejados del nominal.")
        fit = fit_polynomial([q / 1000 for q in q_points], h_points, degree)
        terms = [f"({c:.6g})Q^{{{degree-i}}}" for i, c in enumerate(fit.coefficients)]
        st.latex(r"H_{\mathrm{bomba,nominal}}(Q)=" + "+".join(terms))
        st.caption(f"Ajuste de la curva ingresada, antes de combinar bombas: Q en m³/s, H en m. R² = {fit.r_squared:.5f}.")
        st.markdown("**C. Potencia**")
        st.latex(r"P_h=\rho gQH,\quad P_{\mathrm{eje}}=P_h/\eta_b,\quad P_e=P_h/(\eta_b\eta_m)")
        st.write("Potencias en W (divide por 1000 para kW). ηb y ηm son eficiencias de bomba y motor como fracción: 75 % = 0,75. La eficiencia de bomba se interpola si ingresaste todos sus puntos; si no, se usa el valor constante asumido.")
        if nominal:
            q = nominal['Q (L/s)'] / 1000
            detail = evaluate_system(segments, q, 0.0, fluid.density_kg_m3, fluid.viscosity_pa_s)
            st.markdown("**Con tus datos actuales — por tramo**")
            st.dataframe([{'Tramo': seg.label, 'L (m)': seg.length_m, 'D (m)': seg.inside_diameter_m,
                'v (m/s)': ev.velocity_m_s, 'Re': ev.reynolds, 'f': ev.friction_factor,
                'hf (m)': ev.friction_head_loss_m, 'hs (m)': ev.minor_head_loss_m}
                for seg, ev in zip(segments, detail.segment_evaluations)], hide_index=True, use_container_width=True)
            st.caption(f"Caudal nominal mostrado: {nominal['Q (L/s)']:.2f} L/s. ρ = {fluid.density_kg_m3:.2f} kg/m³; μ = {fluid.viscosity_pa_s:.6g} Pa·s. Esta tabla usa el caudal mostrado redondeado.")
        st.markdown("**D. Comprobaciones opcionales**")
        st.latex(r"p_i=\frac{\rho g\max(H_b(0)-z_i,0)}{10^5}\;[\mathrm{bar}],\quad p_i\le p_{\mathrm{admisible},i}")
        st.caption("Presión a caudal cero: zi se reparte por longitud acumulada al inicio de cada tramo; no es un perfil topográfico real. PN manual se refiere a 20 °C. PEXGOL usa tabla 9.1 para agua y el escalón de temperatura superior, sin extrapolar.")
        st.latex(r"NPSH_a=\frac{p_{atm}-p_v}{\rho g}-h_{succion}-h_{f,suc}-h_{s,suc}\ge NPSH_r+M")
        st.latex(r"p_{atm}=101325\left(\frac{293-0.0065z}{293}\right)^{5.2561},\quad p_v=610.8\exp\left(\frac{17.27T}{T+237.3}\right)")
        st.caption("Presiones en Pa; z: altitud (m); T: temperatura (°C); altura de succión positiva si la bomba está sobre el líquido. NPSHr proviene del fabricante y M es el margen en m. La expresión de vapor es para agua; no valida otros líquidos.")
        st.latex(r"a=\sqrt{\frac{K_f/\rho}{1+K_fD/(Ee)}},\quad t_c=2L/a,\quad \Delta H=\begin{cases}a\Delta v/g&t\le t_c\\2L\Delta v/(gt)&t>t_c\end{cases}")
        st.caption("Golpe de ariete simplificado: a (m/s), Kf módulo volumétrico del fluido (Pa), E módulo elástico de tubería (Pa), e espesor (m), t tiempo de cierre (s). Se usa restricción 1 y Kf de agua = 2,15×10⁹ Pa. La altura pico mostrada es H nominal + ΔH; no es una simulación transitoria de toda la red.")
        st.latex(r"\phi=N/N_0,\quad Q'=\phi Q,\quad H'=\phi^2H,\quad P'=\phi^3P")
        st.caption("Afinidad para cambio de velocidad N. Bombas idénticas: en paralelo se suman caudales a igual H; en serie se suman alturas a igual Q. La eficiencia de cada punto se traslada con la curva; una eficiencia constante sigue siendo un supuesto.")
