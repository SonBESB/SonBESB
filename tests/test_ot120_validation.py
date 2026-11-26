"""Caso de validacion OT-120, verificado de forma independiente en MATLAB
por el usuario (estanque atmosferico en el origen, 1,5 bar objetivo en el
destino, HDPE PE100 DI 96,8 mm, 120 m, Q=82 L/min).

Esto no es un chequeo puntual: es un test de regresion permanente. Si algun
cambio futuro al motor hidraulico (friccion, perdidas singulares, balance de
presion de borde) deja de reproducir estos numeros, este test debe fallar.

Valores de referencia (calculo independiente del usuario, no ajustados aqui
para que coincidan):
    friccion            ~ 0.05805 m
    accesorios (10% hf) ~ 0.00580 m
    altura base (sin ablandador ni otras perdidas) ~ 27.887 m.c.a.
"""

from __future__ import annotations

import pytest

from core.hydraulics.system_curve import PipeSegment, evaluate_system, pressure_boundary_head_m


DENSITY_KG_M3 = 998.2
VISCOSITY_PA_S = 1.002e-3
DESNIVEL_GEOMETRICO_M = 12.5
PRESION_DISPONIBLE_BAR = 0.0  # estanque atmosferico: no hay presion de red en el origen
PRESION_REQUERIDA_BAR = 1.5
CAUDAL_DISENO_L_S = 82 / 60

SEGMENT = PipeSegment(
    label="Tramo 1", length_m=120.0, inside_diameter_mm=96.8, roughness_mm=0.0015, minor_loss_fraction=0.10,
)


def _ot120_static_head_m() -> float:
    return DESNIVEL_GEOMETRICO_M + pressure_boundary_head_m(PRESION_DISPONIBLE_BAR, PRESION_REQUERIDA_BAR, DENSITY_KG_M3)


def test_ot120_static_head_matches_independent_calc():
    # 12.5 (desnivel) + 15.32 (carga equivalente de 1.5 bar, estanque de origen abierto) ~ 27.82 m
    assert _ot120_static_head_m() == pytest.approx(27.823, abs=5e-3)


def test_ot120_friction_and_minor_losses_match_independent_calc():
    detail = evaluate_system([SEGMENT], CAUDAL_DISENO_L_S / 1000, _ot120_static_head_m(), DENSITY_KG_M3, VISCOSITY_PA_S)
    ev = detail.segment_evaluations[0]
    assert ev.friction_head_loss_m == pytest.approx(0.05805, abs=2e-5)
    assert ev.minor_head_loss_m == pytest.approx(0.00580, abs=2e-5)


def test_ot120_base_head_without_installed_equipment_matches_independent_calc():
    # "Altura base sin ablandador ni otras perdidas" del caso de validacion.
    detail = evaluate_system([SEGMENT], CAUDAL_DISENO_L_S / 1000, _ot120_static_head_m(), DENSITY_KG_M3, VISCOSITY_PA_S)
    assert detail.total_head_m == pytest.approx(27.887, abs=2e-3)


def test_ot120_base_head_plus_4m_constant_equipment_loss_matches_independent_calc():
    # "Altura con 4 m.c.a. adicionales supuestos" (ablandador 2 m + otras perdidas 2 m,
    # ambas constantes a 82 L/min). La app todavia no modela equipos instalados con su
    # propia curva -- esto documenta la hipotesis manual mientras tanto.
    detail = evaluate_system([SEGMENT], CAUDAL_DISENO_L_S / 1000, _ot120_static_head_m(), DENSITY_KG_M3, VISCOSITY_PA_S)
    constant_equipment_loss_m = 2.0 + 2.0
    assert detail.total_head_m + constant_equipment_loss_m == pytest.approx(31.887, abs=2e-3)
