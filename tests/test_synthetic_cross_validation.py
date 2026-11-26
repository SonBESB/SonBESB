"""10 casos sinteticos de validacion cruzada, de complejidad tipo universitaria.

IMPORTANTE — que son y que NO son estos casos: no son problemas citados de
un libro de texto ni de un examen real (eso requeriria acceso a internet a
fuentes que este entorno no puede alcanzar — ver docs/HYDRAULICS_PUMP_OPERATING_POINT.md
y la conversacion que origino este archivo). Son escenarios de ingenieria
construidos para este chequeo, cubriendo con numeros no triviales las
distintas capacidades del motor hidraulico. Lo que SI los hace una prueba
real: cada valor esperado se calcula con un "oraculo" independiente — una
reimplementacion desde cero de las mismas ecuaciones de la mecanica de
fluidos estandar (Colebrook-White, Darcy-Weisbach, NPSH via la formula de
atmosfera ISA y la ecuacion de Tetens para presion de vapor, leyes de
afinidad, combinacion de bombas en paralelo, celeridad de Joukowsky), escrita
en este archivo sin importar nada de core.hydraulics/. Si el motor de la
aplicacion tuviera un error de formula, signo o unidades, este oraculo no lo
reproduciria y el test fallaria.

Resultado de la corrida original (ver mensaje al usuario): maxima diferencia
porcentual entre el oraculo y la aplicacion en los 10 casos: 0.0016% —
atribuible a tolerancia numerica del solver (biseccion/Newton-Raphson), no a
un error de formula.

Casos cubiertos: (1) laminar, (2) turbulento liso, (3) turbulento rugoso,
(4) tramos en serie con distinto diametro, (5) perdidas singulares
dominantes, (6) punto de operacion bomba-sistema, (7) NPSH disponible con
riesgo de cavitacion, (8) leyes de afinidad, (9) dos bombas identicas en
paralelo, (10) golpe de ariete.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from core.hydraulics.affinity import PumpCurve, PumpCurvePoint, scale_by_affinity, twin_parallel
from core.hydraulics.curve_fit import fit_polynomial
from core.hydraulics.minor_losses import minor_loss_head_m
from core.hydraulics.npsh import npsh_available
from core.hydraulics.operating_point import solve_operating_point
from core.hydraulics.power import hydraulic_power_w
from core.hydraulics.surge import compute_surge
from core.hydraulics.system_curve import PipeSegment, evaluate_system

G = 9.80665
RHO_WATER, MU_WATER = 998.2, 1.002e-3


# ---------------------------------------------------------------- oraculo --
def _area(D):
    return math.pi * D**2 / 4.0


def _velocity(Q, D):
    return Q / _area(D)


def _reynolds(v, D, rho, mu):
    return rho * v * D / mu


def _colebrook_f(Re, eps, D, tol=1e-12, itmax=200):
    if Re < 2300:
        return 64.0 / Re
    f = 0.25 / (math.log10(eps / (3.7 * D) + 5.74 / Re**0.9)) ** 2
    for _ in range(itmax):
        rhs = -2.0 * math.log10(eps / (3.7 * D) + 2.51 / (Re * math.sqrt(f)))
        f_new = 1.0 / rhs**2
        if abs(f_new - f) < tol:
            return f_new
        f = f_new
    return f


def _darcy_hf(f, L, D, v):
    return f * (L / D) * (v**2) / (2 * G)


def _minor_hs(sigma_k, v):
    return sigma_k * (v**2) / (2 * G)


def _bisection(func, lo, hi, tol=1e-10, itmax=200):
    flo, fhi = func(lo), func(hi)
    assert flo * fhi < 0
    for _ in range(itmax):
        mid = 0.5 * (lo + hi)
        fm = func(mid)
        if abs(fm) < tol or (hi - lo) < 1e-12:
            return mid
        if flo * fm < 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return 0.5 * (lo + hi)


def _p_atm_pa(altitude_m):
    return 101325.0 * (1 - 0.0065 * altitude_m / 293.0) ** 5.2561


def _p_vap_pa(temp_c):
    return 610.8 * math.exp(17.27 * temp_c / (temp_c + 237.3))


def _npsh_a_oracle(altitude_m, temp_c, suction_head_m, hf_succ, hs_succ, rho):
    head_atm_vap = (_p_atm_pa(altitude_m) - _p_vap_pa(temp_c)) / (rho * G)
    return head_atm_vap - suction_head_m - hf_succ - hs_succ


def _celeridad(K, rho, D, E, e):
    return math.sqrt((K / rho) / (1 + (K * D) / (E * e)))


# ------------------------------------------------------------------ casos --
def test_case_01_laminar_oil():
    rho, mu = 900.0, 0.08
    D, L, Q = 0.05, 30.0, 0.001
    v = _velocity(Q, D)
    re_oracle = _reynolds(v, D, rho, mu)
    f_oracle = _colebrook_f(re_oracle, 0.0, D)
    hf_oracle = _darcy_hf(f_oracle, L, D, v)

    seg = PipeSegment(label="T1", length_m=L, inside_diameter_mm=D * 1000, roughness_mm=0.0)
    ev = evaluate_system([seg], Q, 0.0, rho, mu).segment_evaluations[0]

    assert ev.reynolds == pytest.approx(re_oracle, rel=1e-9)
    assert ev.friction_factor == pytest.approx(f_oracle, rel=1e-9)
    assert ev.friction_head_loss_m == pytest.approx(hf_oracle, rel=1e-9)


def test_case_02_turbulent_smooth():
    D, L, eps, Q = 0.100, 200.0, 0.0015e-3, 0.02
    v = _velocity(Q, D)
    re_oracle = _reynolds(v, D, RHO_WATER, MU_WATER)
    f_oracle = _colebrook_f(re_oracle, eps, D)
    hf_oracle = _darcy_hf(f_oracle, L, D, v)

    seg = PipeSegment(label="T1", length_m=L, inside_diameter_mm=D * 1000, roughness_mm=eps * 1000)
    ev = evaluate_system([seg], Q, 0.0, RHO_WATER, MU_WATER).segment_evaluations[0]

    assert ev.friction_factor == pytest.approx(f_oracle, rel=1e-6)
    assert ev.friction_head_loss_m == pytest.approx(hf_oracle, rel=1e-6)


def test_case_03_turbulent_rough_cast_iron():
    D, L, eps, Q = 0.150, 500.0, 0.26e-3, 0.05
    v = _velocity(Q, D)
    re_oracle = _reynolds(v, D, RHO_WATER, MU_WATER)
    f_oracle = _colebrook_f(re_oracle, eps, D)
    hf_oracle = _darcy_hf(f_oracle, L, D, v)

    seg = PipeSegment(label="T1", length_m=L, inside_diameter_mm=D * 1000, roughness_mm=eps * 1000)
    ev = evaluate_system([seg], Q, 0.0, RHO_WATER, MU_WATER).segment_evaluations[0]

    assert ev.friction_factor == pytest.approx(f_oracle, rel=1e-6)
    assert ev.friction_head_loss_m == pytest.approx(hf_oracle, rel=1e-6)


def test_case_04_series_segments_different_diameters():
    Q = 0.015
    DA, LA, epsA = 0.100, 50.0, 0.045e-3
    DB, LB, epsB = 0.075, 80.0, 0.045e-3

    vA = _velocity(Q, DA)
    fA = _colebrook_f(_reynolds(vA, DA, RHO_WATER, MU_WATER), epsA, DA)
    vB = _velocity(Q, DB)
    fB = _colebrook_f(_reynolds(vB, DB, RHO_WATER, MU_WATER), epsB, DB)
    hf_oracle = _darcy_hf(fA, LA, DA, vA) + _darcy_hf(fB, LB, DB, vB)

    segA = PipeSegment(label="A", length_m=LA, inside_diameter_mm=DA * 1000, roughness_mm=epsA * 1000)
    segB = PipeSegment(label="B", length_m=LB, inside_diameter_mm=DB * 1000, roughness_mm=epsB * 1000)
    detail = evaluate_system([segA, segB], Q, 0.0, RHO_WATER, MU_WATER)
    hf_app = sum(e.friction_head_loss_m for e in detail.segment_evaluations)

    assert hf_app == pytest.approx(hf_oracle, rel=1e-6)


def test_case_05_minor_losses_dominant():
    D, L, eps, Q = 0.080, 20.0, 0.045e-3, 0.01
    sigma_k = 10 * 0.9 + 2 * 0.2  # 10 codos 90 grados + 2 valvulas de compuerta
    v = _velocity(Q, D)
    f_oracle = _colebrook_f(_reynolds(v, D, RHO_WATER, MU_WATER), eps, D)
    hf_oracle = _darcy_hf(f_oracle, L, D, v)
    hs_oracle = _minor_hs(sigma_k, v)

    seg = PipeSegment(label="T1", length_m=L, inside_diameter_mm=D * 1000, roughness_mm=eps * 1000)
    ev = evaluate_system([seg], Q, 0.0, RHO_WATER, MU_WATER).segment_evaluations[0]
    hs_app = minor_loss_head_m(ev.velocity_m_s, sigma_k)

    assert ev.friction_head_loss_m == pytest.approx(hf_oracle, rel=1e-6)
    assert hs_app == pytest.approx(hs_oracle, rel=1e-9)


def test_case_06_pump_system_operating_point():
    D, L, eps, dz = 0.150, 300.0, 0.15e-3, 15.0
    q_pts = np.array([0.0, 0.03, 0.06])
    h_pts = np.array([40.0, 35.0, 22.0])
    coeffs = np.polyfit(q_pts, h_pts, 2)  # minimos cuadrados independiente (numpy)

    def pump_h_oracle(q):
        return np.polyval(coeffs, q)

    def sys_h_oracle(q):
        v = _velocity(q, D)
        f = _colebrook_f(_reynolds(v, D, RHO_WATER, MU_WATER), eps, D)
        return dz + _darcy_hf(f, L, D, v)

    q_op_oracle = _bisection(lambda q: pump_h_oracle(q) - sys_h_oracle(q), 0.001, 0.09)
    h_op_oracle = pump_h_oracle(q_op_oracle)

    fit = fit_polynomial(list(q_pts), list(h_pts), 2)
    seg = PipeSegment(label="T1", length_m=L, inside_diameter_mm=D * 1000, roughness_mm=eps * 1000)

    def sys_h_app(q):
        return dz + evaluate_system([seg], q, dz, RHO_WATER, MU_WATER).segment_evaluations[0].friction_head_loss_m

    op = solve_operating_point(fit.evaluate, sys_h_app, q_min=0.001, q_max=0.09)

    assert op.found
    assert op.flow_m3_s == pytest.approx(q_op_oracle, rel=1e-4)
    assert op.head_m == pytest.approx(h_op_oracle, rel=1e-4)


def test_case_07_npsh_cavitation_risk():
    altitude, temp_c, suction_head = 500.0, 25.0, 4.0
    D, L, eps, Q = 0.100, 8.0, 0.045e-3, 0.03
    sigma_k = 1.5 + 0.5  # valvula de pie + entrada

    v = _velocity(Q, D)
    f_oracle = _colebrook_f(_reynolds(v, D, RHO_WATER, MU_WATER), eps, D)
    hf_succ = _darcy_hf(f_oracle, L, D, v)
    hs_succ = _minor_hs(sigma_k, v)
    npsha_oracle = _npsh_a_oracle(altitude, temp_c, suction_head, hf_succ, hs_succ, RHO_WATER)

    seg = PipeSegment(label="Succ", length_m=L, inside_diameter_mm=D * 1000, roughness_mm=eps * 1000)
    ev = evaluate_system([seg], Q, 0.0, RHO_WATER, MU_WATER).segment_evaluations[0]
    hs_app = minor_loss_head_m(ev.velocity_m_s, sigma_k)
    result = npsh_available(altitude, temp_c, suction_head, ev.friction_head_loss_m, hs_app, RHO_WATER)

    assert result.npsh_available_m == pytest.approx(npsha_oracle, rel=1e-6)


def test_case_08_affinity_laws():
    Q0, H0, phi = 0.05, 30.0, 0.8
    q_exp, h_exp = phi * Q0, phi**2 * H0
    p0 = RHO_WATER * G * Q0 * H0
    p_exp = phi**3 * p0

    curve = PumpCurve(points=(PumpCurvePoint(flow_m3_s=Q0, head_m=H0, efficiency=0.7),), label="nominal")
    scaled = scale_by_affinity(curve, phi)
    p_app = phi**3 * hydraulic_power_w(RHO_WATER, Q0, H0)

    assert scaled.points[0].flow_m3_s == pytest.approx(q_exp, rel=1e-12)
    assert scaled.points[0].head_m == pytest.approx(h_exp, rel=1e-12)
    assert p_app == pytest.approx(p_exp, rel=1e-9)


def test_case_09_two_identical_pumps_in_parallel():
    D, L, eps, dz = 0.120, 150.0, 0.045e-3, 8.0
    q_pts = np.array([0.0, 0.02, 0.04])
    h_pts = np.array([25.0, 22.0, 15.0])
    coeffs = np.polyfit(q_pts, h_pts, 2)

    def pump_h_single_oracle(q):
        return np.polyval(coeffs, q)

    def pump_h_parallel_oracle(q):
        return pump_h_single_oracle(q / 2.0)  # 2 bombas identicas: mismo H a Q/2 cada una

    def sys_h_oracle(q):
        v = _velocity(q, D)
        f = _colebrook_f(_reynolds(v, D, RHO_WATER, MU_WATER), eps, D)
        return dz + _darcy_hf(f, L, D, v)

    q_op_oracle = _bisection(lambda q: pump_h_parallel_oracle(q) - sys_h_oracle(q), 0.001, 0.09)
    h_op_oracle = pump_h_parallel_oracle(q_op_oracle)

    curve = PumpCurve(points=tuple(PumpCurvePoint(flow_m3_s=q, head_m=h) for q, h in zip(q_pts, h_pts)), label="nominal")
    curve_parallel = twin_parallel(curve, 2)
    fit_par = fit_polynomial([p.flow_m3_s for p in curve_parallel.points], [p.head_m for p in curve_parallel.points], 2)
    seg = PipeSegment(label="T1", length_m=L, inside_diameter_mm=D * 1000, roughness_mm=eps * 1000)

    def sys_h_app(q):
        return dz + evaluate_system([seg], q, dz, RHO_WATER, MU_WATER).segment_evaluations[0].friction_head_loss_m

    op = solve_operating_point(fit_par.evaluate, sys_h_app, q_min=0.001, q_max=0.09)

    assert op.found
    assert op.flow_m3_s == pytest.approx(q_op_oracle, rel=1e-4)
    assert op.head_m == pytest.approx(h_op_oracle, rel=1e-4)


def test_case_10_water_hammer():
    D, e, E, Kf = 0.300, 0.008, 200e9, 2.15e9
    v_op, t_close, length = 2.0, 1.0, 800.0

    a_oracle = _celeridad(Kf, RHO_WATER, D, E, e)
    tc_oracle = 2 * length / a_oracle
    assert t_close < tc_oracle  # confirma regimen RAPIDO, como se diseno el caso
    dh_oracle = a_oracle * v_op / G

    result = compute_surge(
        length_m=length, delta_velocity_m_s=v_op, closure_time_s=t_close,
        fluid_bulk_modulus_pa=Kf, density_kg_m3=RHO_WATER,
        inside_diameter_m=D, wall_thickness_m=e,
        pipe_elastic_modulus_pa=E, static_head_before_m=0.0,
    )

    assert result.wave_speed_m_s == pytest.approx(a_oracle, rel=1e-9)
    assert result.critical_time_s == pytest.approx(tc_oracle, rel=1e-9)
    assert result.surge_head_m == pytest.approx(dh_oracle, rel=1e-9)
