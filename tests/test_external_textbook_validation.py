"""Casos de validacion externos, tomados de fuentes academicas independientes
(no escritos por este proyecto), usados para confirmar que el motor
hidraulico reproduce resultados conocidos y no solo se auto-consistente.

Caso: Purdue University, ME 30800/30900 "Fluid Mechanics" (Prof. C. Wassgren),
ejemplo resuelto "pump_13": bombeo de agua entre dos estanques con una bomba
centrifuga, verificando el punto de operacion por interseccion de curvas.
Fuente: https://engineering.purdue.edu/~wassgren/teaching/ME30800/Examples/pump_13.pdf
        https://engineering.purdue.edu/~wassgren/teaching/ME30900/Examples/pump_13.pdf
(dos variantes del mismo problema en distintos semestres; se combinan los
datos porque coinciden en tuberia, curva de bomba y caudal de operacion).

Datos del problema (segun la fuente):
    agua: rho=1000 kg/m3, viscosidad cinematica=1.0e-6 m2/s (mu=1.0e-3 Pa.s)
    tuberia: acero comercial, 20 m de longitud total, D=0.20 m
    perdidas singulares: entrada de borde vivo K=0.5, codo K=1.5, salida K=1.0
        -> SigmaK=3.0
    desnivel entre estanques: z2-z1 = 7.00 m
    curva de la bomba ajustada: H(Q) = -32.5 Q^2 + 1.23 Q + 27.8 (Q en m3/s, H en m)
    resultado publicado: caudal de operacion Q ~ 0.284-0.285 m3/s
    (la rugosidad de "acero comercial" no se publica como numero exacto en los
    extractos disponibles; se usa el valor tabulado estandar de 0.045 mm)

No se ajusto ningun valor del motor para que esto calzara: es el mismo
solve_operating_point + evaluate_system que usa la aplicacion.
"""

from __future__ import annotations

import pytest

from core.hydraulics.minor_losses import minor_loss_head_m
from core.hydraulics.operating_point import solve_operating_point
from core.hydraulics.system_curve import PipeSegment, evaluate_system

DENSITY_KG_M3 = 1000.0
VISCOSITY_PA_S = 1.0e-3
LENGTH_M = 20.0
DIAMETER_MM = 200.0
ROUGHNESS_MM = 0.045  # acero comercial, valor tabulado estandar (no publicado exacto en la fuente)
ELEVATION_M = 7.00
SIGMA_K = 3.0  # entrada 0.5 + codo 1.5 + salida 1.0

SEGMENT = PipeSegment(label="Tramo 1", length_m=LENGTH_M, inside_diameter_mm=DIAMETER_MM, roughness_mm=ROUGHNESS_MM)


def _pump_head_m(flow_m3_s: float) -> float:
    return -32.5 * flow_m3_s**2 + 1.23 * flow_m3_s + 27.8


def _system_head_m(flow_m3_s: float) -> float:
    ev = evaluate_system([SEGMENT], flow_m3_s, ELEVATION_M, DENSITY_KG_M3, VISCOSITY_PA_S).segment_evaluations[0]
    return ELEVATION_M + ev.friction_head_loss_m + minor_loss_head_m(ev.velocity_m_s, SIGMA_K)


def test_purdue_pump13_operating_point_matches_published_flow_rate():
    op = solve_operating_point(_pump_head_m, _system_head_m, q_min=0.01, q_max=0.49)
    assert op.found
    # Publicado: Q ~ 0.284-0.285 m3/s. Tolerancia amplia (2%) porque la
    # rugosidad exacta de "acero comercial" usada por la fuente no esta
    # publicada en el extracto disponible.
    assert op.flow_m3_s == pytest.approx(0.2845, rel=0.02)
