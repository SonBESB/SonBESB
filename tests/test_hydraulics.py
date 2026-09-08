"""Tests del modulo core/hydraulics/ — punto de operacion de bombeo.

Verifica contra valores de referencia conocidos (no contra la
implementacion misma): Colebrook-White contra un caso de manual, R^2 de
un ajuste exacto, biseccion contra una interseccion analitica, leyes de
afinidad contra sus formulas, y los limites del chequeo NPSH.
"""

from __future__ import annotations

import math

import pytest

from core.hydraulics.affinity import PumpCurve, PumpCurvePoint, scale_by_affinity, scale_power_by_affinity, twin_parallel, twin_series
from core.hydraulics.curve_fit import fit_polynomial
from core.hydraulics.fluids import TemperatureOutOfRangeError, custom_fluid, water_properties
from core.hydraulics.friction import FlowRegime, colebrook_white, reynolds_number
from core.hydraulics.minor_losses import minor_loss_head_m, total_minor_loss_coefficient
from core.hydraulics.npsh import atmospheric_head_m, check_npsh, npsh_available, vapor_pressure_head_m
from core.hydraulics.operating_point import solve_operating_point
from core.hydraulics.power import compute_power
from core.hydraulics.system_curve import PipeSegment, build_system_curve, evaluate_system


def test_water_properties_matches_known_table_point():
    water = water_properties(20.0)
    assert water.density_kg_m3 == pytest.approx(998.2)
    assert water.viscosity_pa_s == pytest.approx(1.002e-3)


def test_water_properties_out_of_range_raises():
    with pytest.raises(TemperatureOutOfRangeError):
        water_properties(150.0)


def test_custom_fluid_is_flagged_as_unverified():
    fluid = custom_fluid("Salmuera", density_kg_m3=1200, viscosity_pa_s=1.5e-3, temperature_c=25)
    assert "no verificado" in fluid.source


def test_reynolds_number_basic():
    # v=2 m/s, D=0.25 m, agua 20C
    water = water_properties(20.0)
    re = reynolds_number(2.0, 0.25, water.density_kg_m3, water.viscosity_pa_s)
    assert re == pytest.approx(497500, rel=1e-2)


def test_colebrook_white_matches_swamee_jain_cross_check():
    # Re=1e5, rugosidad relativa k/D=0.001: cruzado contra Swamee-Jain
    # (aproximacion explicita independiente de Colebrook-White), que da
    # f=0.02234 para este caso — ambas formulas deben coincidir dentro
    # de su margen de aproximacion mutua (~1%).
    result = colebrook_white(reynolds=1e5, roughness_m=0.001 * 0.1, diameter_m=0.1)
    assert result.regime is FlowRegime.TURBULENT
    assert result.converged
    assert result.friction_factor == pytest.approx(0.02234, rel=0.02)


def test_colebrook_white_laminar_uses_exact_formula():
    result = colebrook_white(reynolds=1000, roughness_m=0.0001, diameter_m=0.1)
    assert result.regime is FlowRegime.LAMINAR
    assert result.friction_factor == pytest.approx(64.0 / 1000.0)


def test_colebrook_white_transitional_is_flagged():
    result = colebrook_white(reynolds=3000, roughness_m=0.0001, diameter_m=0.1)
    assert result.regime is FlowRegime.TRANSITIONAL
    assert "transicional" in result.note.lower()


def test_minor_loss_coefficient_sums_and_rejects_unknown_fitting():
    total = total_minor_loss_coefficient({"Curva 90": 2, "Valvula compuerta": 1})
    assert total == pytest.approx(0.9 * 2 + 0.2)
    with pytest.raises(KeyError):
        total_minor_loss_coefficient({"Accesorio inventado": 1})


def test_minor_loss_head():
    h = minor_loss_head_m(velocity_m_s=2.0, k_total=1.0)
    assert h == pytest.approx((2.0**2) / (2 * 9.80665))


def test_fit_polynomial_perfect_quadratic():
    # H = 40 - 0.002*Q^2 (puntos exactos -> R^2 = 1)
    q = [0, 50, 100]
    h = [40 - 0.002 * qi**2 for qi in q]
    fit = fit_polynomial(q, h, degree=2)
    assert fit.r_squared == pytest.approx(1.0, abs=1e-9)
    assert fit.evaluate(75) == pytest.approx(40 - 0.002 * 75**2, rel=1e-6)


def test_fit_polynomial_rejects_insufficient_points():
    with pytest.raises(ValueError):
        fit_polynomial([0, 1], [0, 1], degree=3)


def test_solve_operating_point_intersects_known_lines():
    # H_bomba(Q) = 40 - 0.1*Q ; H_sistema(Q) = 10 + 0.05*Q -> Q=200, H=20
    pump = lambda q: 40 - 0.1 * q
    system = lambda q: 10 + 0.05 * q
    result = solve_operating_point(pump, system, q_min=0, q_max=400)
    assert result.found
    assert result.flow_m3_s == pytest.approx(200, rel=1e-3)
    assert result.head_m == pytest.approx(20, rel=1e-3)


def test_solve_operating_point_reports_no_intersection():
    pump = lambda q: 5.0  # bomba plana muy baja
    system = lambda q: 20 + 0.01 * q  # sistema siempre mas exigente
    result = solve_operating_point(pump, system, q_min=0, q_max=100)
    assert not result.found
    assert "no hay cambio de signo" in result.reason.lower()


def test_affinity_scales_flow_squared_head_and_keeps_efficiency_per_point():
    curve = PumpCurve(points=(PumpCurvePoint(flow_m3_s=0.1, head_m=40, efficiency=0.7),), label="bomba")
    scaled = scale_by_affinity(curve, phi=0.9)
    p = scaled.points[0]
    assert p.flow_m3_s == pytest.approx(0.09)
    assert p.head_m == pytest.approx(40 * 0.81)
    assert p.efficiency == 0.7  # se traslada, no se recalcula


def test_affinity_power_scales_cubically():
    assert scale_power_by_affinity(1000.0, 0.5) == pytest.approx(125.0)


def test_twin_parallel_sums_flow_same_head():
    curve = PumpCurve(points=(PumpCurvePoint(flow_m3_s=0.1, head_m=40),), label="bomba")
    twins = twin_parallel(curve, 2)
    assert twins.points[0].flow_m3_s == pytest.approx(0.2)
    assert twins.points[0].head_m == pytest.approx(40)


def test_twin_series_sums_head_same_flow():
    curve = PumpCurve(points=(PumpCurvePoint(flow_m3_s=0.1, head_m=40),), label="bomba")
    twins = twin_series(curve, 2)
    assert twins.points[0].flow_m3_s == pytest.approx(0.1)
    assert twins.points[0].head_m == pytest.approx(80)


def test_atmospheric_head_at_sea_level_is_about_10_33_m():
    head = atmospheric_head_m(0.0, density_kg_m3=1000.0)
    assert head == pytest.approx(10.33, abs=0.02)


def test_vapor_pressure_head_increases_with_temperature():
    low = vapor_pressure_head_m(10.0, density_kg_m3=1000.0)
    high = vapor_pressure_head_m(40.0, density_kg_m3=1000.0)
    assert high > low


def test_check_npsh_pass_and_fail():
    passing = check_npsh(npsh_available_m=10.0, npsh_required_m=5.0, safety_margin_m=1.0)
    assert passing.passed
    failing = check_npsh(npsh_available_m=5.0, npsh_required_m=5.0, safety_margin_m=1.0)
    assert not failing.passed


def test_npsh_available_end_to_end_matches_manual_terms():
    result = npsh_available(
        altitude_m=0.0,
        temperature_c=20.0,
        static_suction_head_m=3.0,
        friction_head_m=1.0,
        minor_losses_head_m=0.5,
        density_kg_m3=1000.0,
    )
    expected = result.atmospheric_head_m - result.vapor_pressure_head_m - 3.0 - 1.0 - 0.5
    assert result.npsh_available_m == pytest.approx(expected)


def test_compute_power_rejects_invalid_efficiency():
    with pytest.raises(ValueError):
        compute_power(1000.0, 0.1, 30.0, pump_efficiency=1.5, motor_efficiency=0.9)


def test_compute_power_matches_hand_calculation():
    result = compute_power(998.0, flow_m3_s=0.1035, head_m=33.71, pump_efficiency=0.75, motor_efficiency=0.92)
    p_hyd = 998.0 * 9.80665 * 0.1035 * 33.71
    assert result.hydraulic_power_w == pytest.approx(p_hyd)
    assert result.electrical_power_w == pytest.approx(p_hyd / (0.75 * 0.92))


def test_evaluate_system_single_segment_matches_darcy_weisbach_order_of_magnitude():
    segment = PipeSegment(label="Tramo 1", length_m=1250, inside_diameter_mm=250, roughness_mm=0.007, fitting_counts={})
    point = evaluate_system(
        [segment], flow_m3_s=0.1035, static_head_m=18.5, density_kg_m3=998.0, viscosity_pa_s=1.002e-3
    )
    assert point.segment_evaluations[0].velocity_m_s == pytest.approx(0.1035 / (math.pi * 0.25**2 / 4), rel=1e-6)
    assert point.total_head_m > 18.5  # friccion siempre suma sobre la carga estatica


def test_build_system_curve_zero_flow_returns_static_head_only():
    segment = PipeSegment(label="Tramo 1", length_m=100, inside_diameter_mm=100, roughness_mm=0.01, fitting_counts={})
    curve = build_system_curve([segment], static_head_m=10.0, density_kg_m3=998.0, viscosity_pa_s=1.002e-3, flow_range_m3_s=[0.0])
    assert curve[0].total_head_m == pytest.approx(10.0)
