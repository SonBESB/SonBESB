"""Chequeo de velocidad recomendada por tramo.

Ausente (como PASS/FAIL) tanto en PiezoCalc como en la planilla SMath
de referencia — ambas muestran la velocidad calculada pero ninguna la
compara contra un rango. El rango 0.6-3.0 m/s es una GUIA de practica
de ingenieria comun para agua en lineas de impulsion (evita
sedimentacion por abajo, erosion/golpe de ariete excesivo por arriba),
no una norma especifica citada — se deja como valor por defecto
editable, nunca como limite duro.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_MIN_VELOCITY_M_S = 0.6
DEFAULT_MAX_VELOCITY_M_S = 3.0


@dataclass(frozen=True)
class VelocityCheckResult:
    label: str
    velocity_m_s: float
    min_velocity_m_s: float
    max_velocity_m_s: float
    status: str  # "OK" | "BAJA" | "ALTA"


def check_velocity(
    label: str,
    velocity_m_s: float,
    min_velocity_m_s: float = DEFAULT_MIN_VELOCITY_M_S,
    max_velocity_m_s: float = DEFAULT_MAX_VELOCITY_M_S,
) -> VelocityCheckResult:
    if velocity_m_s < min_velocity_m_s:
        status = "BAJA"
    elif velocity_m_s > max_velocity_m_s:
        status = "ALTA"
    else:
        status = "OK"
    return VelocityCheckResult(
        label=label, velocity_m_s=velocity_m_s, min_velocity_m_s=min_velocity_m_s,
        max_velocity_m_s=max_velocity_m_s, status=status,
    )
