"""NPSH disponible vs requerido — ausente por completo en PiezoCalc.

Formulas:

- Presion atmosferica vs altitud: formula barometrica de la Atmosfera
  Estandar Internacional (ISA), la misma que usa la planilla SMath de
  referencia (Bryam Perez): Patm(h) = Patm0 * ((293 - 0.0065*h)/293)^5.2561,
  con Patm0 = 101325 Pa al nivel del mar.
- Presion de vapor del agua vs temperatura: aproximacion de Tetens
  (1930), formula meteorologica estandar (no la version especifica de
  la planilla SMath, cuyo factor de escala interno no se pudo verificar
  con las unidades del archivo original).
- NPSH disponible (NPSHa): NPSHa = (Patm - Pvap)/(rho*g) - h_succion -
  h_friccion - h_singulares, donde h_succion es POSITIVO para succion
  en elevacion (la bomba debe levantar el fluido, resta) y NEGATIVO
  para succion inundada (nivel de fluido sobre el eje de la bomba,
  suma). Misma convencion que la ecuacion principal de la planilla SMath.
- Margen de seguridad por defecto: 1 m sobre el NPSH requerido del
  fabricante, igual que `NPSH.re = NPSH.r + 1m` en la referencia — un
  valor de practica de ingenieria comun (Hydraulic Institute sugiere
  margenes similares), no una norma citada especificamente por ninguna
  de las dos fuentes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

STANDARD_ATMOSPHERIC_PRESSURE_PA = 101325.0
DEFAULT_NPSH_SAFETY_MARGIN_M = 1.0


def atmospheric_head_m(altitude_m: float, density_kg_m3: float, g: float = 9.80665) -> float:
    """Presion atmosferica (ISA) expresada como columna de fluido en metros."""
    ratio = (293.0 - 0.0065 * altitude_m) / 293.0
    if ratio <= 0:
        raise ValueError(f"Altitud {altitude_m} m fuera del rango valido de la formula ISA.")
    pressure_pa = STANDARD_ATMOSPHERIC_PRESSURE_PA * (ratio**5.2561)
    return pressure_pa / (density_kg_m3 * g)


def vapor_pressure_head_m(temperature_c: float, density_kg_m3: float, g: float = 9.80665) -> float:
    """Presion de vapor del agua (Tetens, 1930) como columna de fluido en metros.

    Valida como aproximacion de ingenieria para agua entre 0 y 100 C.
    Para otro fluido, este valor debe ingresarse manualmente — no se
    extrapola la formula de Tetens a fluidos distintos del agua.
    """
    saturation_pressure_kpa = 0.6108 * math.exp((17.27 * temperature_c) / (temperature_c + 237.3))
    return (saturation_pressure_kpa * 1000.0) / (density_kg_m3 * g)


@dataclass(frozen=True)
class NpshAvailableResult:
    npsh_available_m: float
    atmospheric_head_m: float
    vapor_pressure_head_m: float
    static_suction_head_m: float
    friction_head_m: float
    minor_losses_head_m: float


def npsh_available(
    altitude_m: float,
    temperature_c: float,
    static_suction_head_m: float,
    friction_head_m: float,
    minor_losses_head_m: float,
    density_kg_m3: float,
    g: float = 9.80665,
) -> NpshAvailableResult:
    patm = atmospheric_head_m(altitude_m, density_kg_m3, g)
    pvap = vapor_pressure_head_m(temperature_c, density_kg_m3, g)
    npsha = patm - pvap - static_suction_head_m - friction_head_m - minor_losses_head_m
    return NpshAvailableResult(
        npsh_available_m=npsha,
        atmospheric_head_m=patm,
        vapor_pressure_head_m=pvap,
        static_suction_head_m=static_suction_head_m,
        friction_head_m=friction_head_m,
        minor_losses_head_m=minor_losses_head_m,
    )


@dataclass(frozen=True)
class NpshCheckResult:
    passed: bool
    npsh_available_m: float
    npsh_required_m: float
    safety_margin_m: float
    margin_actual_m: float


def check_npsh(
    npsh_available_m: float, npsh_required_m: float, safety_margin_m: float = DEFAULT_NPSH_SAFETY_MARGIN_M
) -> NpshCheckResult:
    margin_actual = npsh_available_m - npsh_required_m
    return NpshCheckResult(
        passed=margin_actual >= safety_margin_m,
        npsh_available_m=npsh_available_m,
        npsh_required_m=npsh_required_m,
        safety_margin_m=safety_margin_m,
        margin_actual_m=margin_actual,
    )
