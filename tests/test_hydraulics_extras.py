"""Tests de las 4 mejoras agregadas tras el analisis inicial:
presion vs PN, velocidad min/max, golpe de ariete."""

from __future__ import annotations

import pytest

from core.hydraulics.pressure_rating import build_shutoff_pressure_profile
from core.hydraulics.surge import compute_surge, critical_time_s, wave_speed_m_s
from core.hydraulics.system_curve import PipeSegment
from core.hydraulics.velocity_check import check_velocity


def test_shutoff_pressure_profile_matches_hand_calc_flat_line():
    # Linea horizontal (static_head=0): presion de diseno = shutoff head
    # en toda la linea, sin caida por elevacion.
    segments = [PipeSegment(label="Tramo 1", length_m=1000, inside_diameter_mm=250, roughness_mm=0.007)]
    checks = build_shutoff_pressure_profile(
        segments, shutoff_head_m=40.0, static_head_m=0.0, density_kg_m3=1000.0, pn_labels=["PN10"]
    )
    expected_bar = 40.0 * 1000.0 * 9.80665 / 1e5
    assert checks[0].max_design_pressure_bar == pytest.approx(expected_bar)
    assert checks[0].passed  # ~3.9 bar < PN10


def test_shutoff_pressure_profile_fails_when_exceeding_pn():
    segments = [PipeSegment(label="Tramo 1", length_m=100, inside_diameter_mm=100, roughness_mm=0.01)]
    checks = build_shutoff_pressure_profile(
        segments, shutoff_head_m=200.0, static_head_m=0.0, density_kg_m3=1000.0, pn_labels=["PN6"]
    )
    assert not checks[0].passed
    assert checks[0].margin_bar < 0


def test_shutoff_pressure_profile_decreases_with_elevation_gain():
    # Dos tramos iguales, static_head=20m repartido proporcional a longitud
    # -> el segundo tramo (mas alto) debe ver menos presion que el primero.
    segments = [
        PipeSegment(label="Tramo 1", length_m=500, inside_diameter_mm=200, roughness_mm=0.007),
        PipeSegment(label="Tramo 2", length_m=500, inside_diameter_mm=200, roughness_mm=0.007),
    ]
    checks = build_shutoff_pressure_profile(
        segments, shutoff_head_m=50.0, static_head_m=20.0, density_kg_m3=1000.0, pn_labels=["PN16", "PN16"]
    )
    assert checks[1].max_design_pressure_bar < checks[0].max_design_pressure_bar


def test_shutoff_pressure_profile_rejects_unknown_pn():
    segments = [PipeSegment(label="Tramo 1", length_m=100, inside_diameter_mm=100, roughness_mm=0.01)]
    with pytest.raises(KeyError):
        build_shutoff_pressure_profile(segments, 40.0, 0.0, 1000.0, pn_labels=["PN999"])


def test_velocity_check_flags_low_and_high():
    assert check_velocity("T1", 0.3).status == "BAJA"
    assert check_velocity("T1", 2.0).status == "OK"
    assert check_velocity("T1", 5.0).status == "ALTA"


def test_wave_speed_water_in_steel_pipe_is_near_1000_to_1400_m_s():
    # Orden de magnitud tipico de manual para acero: ~1200-1400 m/s
    a = wave_speed_m_s(
        fluid_bulk_modulus_pa=2.15e9, density_kg_m3=1000.0, inside_diameter_m=0.25,
        wall_thickness_m=0.008, pipe_elastic_modulus_pa=200e9,
    )
    assert 900 < a < 1450


def test_wave_speed_water_in_hdpe_is_much_lower_than_steel():
    a_hdpe = wave_speed_m_s(2.15e9, 1000.0, 0.25, 0.0148, 0.9e9)
    a_steel = wave_speed_m_s(2.15e9, 1000.0, 0.25, 0.008, 200e9)
    assert a_hdpe < a_steel  # HDPE es mucho mas elastico -> onda mas lenta


def test_critical_time_matches_definition():
    assert critical_time_s(length_m=1000, wave_speed_m_s_=1000) == pytest.approx(2.0)


def test_compute_surge_rapid_vs_slow_closure_continuous_at_boundary():
    common = dict(
        length_m=500, delta_velocity_m_s=2.0, fluid_bulk_modulus_pa=2.15e9, density_kg_m3=1000.0,
        inside_diameter_m=0.25, wall_thickness_m=0.0148, pipe_elastic_modulus_pa=0.9e9, static_head_before_m=30.0,
    )
    a = wave_speed_m_s(2.15e9, 1000.0, 0.25, 0.0148, 0.9e9)
    t_c = critical_time_s(500, a)

    fast = compute_surge(closure_time_s=t_c * 0.5, **common)
    boundary = compute_surge(closure_time_s=t_c, **common)
    slow = compute_surge(closure_time_s=t_c * 3, **common)

    assert fast.closure_regime == "RAPIDO"
    assert slow.closure_regime == "LENTO"
    assert boundary.surge_head_m == pytest.approx(fast.surge_head_m, rel=1e-6)
    assert slow.surge_head_m < fast.surge_head_m  # cierre mas lento atenua la sobrepresion


def test_compute_surge_peak_pressure_includes_static_head():
    a = wave_speed_m_s(2.15e9, 1000.0, 0.25, 0.0148, 0.9e9)
    t_c = critical_time_s(500, a)
    result = compute_surge(
        length_m=500, delta_velocity_m_s=2.0, closure_time_s=t_c * 0.5,
        fluid_bulk_modulus_pa=2.15e9, density_kg_m3=1000.0, inside_diameter_m=0.25,
        wall_thickness_m=0.0148, pipe_elastic_modulus_pa=0.9e9, static_head_before_m=30.0,
    )
    assert result.peak_pressure_head_m == pytest.approx(30.0 + result.surge_head_m)
