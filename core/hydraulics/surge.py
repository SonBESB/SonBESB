"""Golpe de ariete (transiente) — ausente en PiezoCalc y en la planilla
SMath de referencia; es el pendiente mas serio de ambas: un diseno que
pasa el chequeo de presion en regimen permanente (ver pressure_rating.py)
puede superar la clase PN de la tuberia varias veces durante un cierre
de valvula o una parada de bomba.

Modelo implementado (deliberadamente simplificado, declarado como tal):

- Celeridad de onda (formula de Korteweg, tuberia de pared delgada):
    a = sqrt( (K/rho) / (1 + (K*D)/(E*e)*c1) )
  K = modulo de compresibilidad del fluido, E = modulo elastico de la
  tuberia, D = diametro interior, e = espesor de pared, c1 = 1.0 por
  defecto (supuesto de tuberia libre de moverse axialmente; para
  tuberia anclada en ambos extremos el valor correcto es 1-nu^2, con
  nu el modulo de Poisson del material — no se calcula aqui, se deja
  como coeficiente editable).
- Tiempo critico t_c = 2L/a (tiempo de ida y vuelta de la onda).
- Cierre RAPIDO (t_cierre <= t_c): formula de Joukowsky completa,
  dH = a*dV/g.
- Cierre LENTO (t_cierre > t_c): aproximacion lineal estandar,
  dH = 2*L*dV / (g*t_cierre) — continua con Joukowsky en t_cierre=t_c,
  pero es una aproximacion de primer orden, no un metodo de las
  caracteristicas. Para un diseno definitivo (seleccion de valvula de
  alivio, tanque de compensacion, tiempo de cierre de valvula) se
  requiere un analisis transiente completo, no este chequeo.

Modulos elasticos de tuberia: valores tipicos de manual (no de
catalogo especifico del fabricante) — reemplazar por el dato real del
catalogo del proveedor cuando este disponible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

WATER_BULK_MODULUS_PA = 2.15e9  # agua a ~20 C, valor tipico de manual

PIPE_ELASTIC_MODULUS_PA: dict[str, float] = {
    "HDPE": 0.9e9,
    "PVC": 3.0e9,
    "Acero": 200e9,
    "Hierro fundido": 100e9,
}


def wave_speed_m_s(
    fluid_bulk_modulus_pa: float,
    density_kg_m3: float,
    inside_diameter_m: float,
    wall_thickness_m: float,
    pipe_elastic_modulus_pa: float,
    restraint_coefficient: float = 1.0,
) -> float:
    if wall_thickness_m <= 0:
        raise ValueError("El espesor de pared debe ser > 0 para calcular celeridad de onda.")
    denom = 1.0 + (fluid_bulk_modulus_pa * inside_diameter_m) / (pipe_elastic_modulus_pa * wall_thickness_m) * restraint_coefficient
    return math.sqrt((fluid_bulk_modulus_pa / density_kg_m3) / denom)


def critical_time_s(length_m: float, wave_speed_m_s_: float) -> float:
    return 2.0 * length_m / wave_speed_m_s_


@dataclass(frozen=True)
class SurgeResult:
    wave_speed_m_s: float
    critical_time_s: float
    closure_time_s: float
    closure_regime: str  # "RAPIDO" | "LENTO"
    surge_head_m: float
    peak_pressure_head_m: float  # cabeza estatica previa + surge


def compute_surge(
    length_m: float,
    delta_velocity_m_s: float,
    closure_time_s: float,
    fluid_bulk_modulus_pa: float,
    density_kg_m3: float,
    inside_diameter_m: float,
    wall_thickness_m: float,
    pipe_elastic_modulus_pa: float,
    static_head_before_m: float,
    g: float = 9.80665,
    restraint_coefficient: float = 1.0,
) -> SurgeResult:
    a = wave_speed_m_s(fluid_bulk_modulus_pa, density_kg_m3, inside_diameter_m, wall_thickness_m, pipe_elastic_modulus_pa, restraint_coefficient)
    t_c = critical_time_s(length_m, a)

    if closure_time_s <= t_c:
        regime = "RAPIDO"
        surge_head = a * delta_velocity_m_s / g
    else:
        regime = "LENTO"
        surge_head = 2.0 * length_m * delta_velocity_m_s / (g * closure_time_s)

    return SurgeResult(
        wave_speed_m_s=a,
        critical_time_s=t_c,
        closure_time_s=closure_time_s,
        closure_regime=regime,
        surge_head_m=surge_head,
        peak_pressure_head_m=static_head_before_m + surge_head,
    )
