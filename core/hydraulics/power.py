"""Potencia hidraulica, al eje y electrica — siempre con densidad real.

La planilla SMath de referencia calcula `potencia(Q, H, eta)` con un
coeficiente fijo de 1000 kgf/m3 (agua) en vez de recibir la densidad
como parametro — un bug real: si se reusa esa funcion con un fluido de
otra densidad, el resultado queda mal sin ningun aviso. PiezoCalc si
usa la densidad ingresada por el usuario (P_elec = rho*g*Q*H /
(eta_bomba*eta_motor)), que es la formula correcta — es la que se
implementa aqui, exigiendo rho como argumento explicito siempre.
"""

from __future__ import annotations

from dataclasses import dataclass

GRAVITY_M_S2 = 9.80665


@dataclass(frozen=True)
class PowerResult:
    hydraulic_power_w: float
    shaft_power_w: float
    electrical_power_w: float


def hydraulic_power_w(density_kg_m3: float, flow_m3_s: float, head_m: float, g: float = GRAVITY_M_S2) -> float:
    return density_kg_m3 * g * flow_m3_s * head_m


def compute_power(
    density_kg_m3: float,
    flow_m3_s: float,
    head_m: float,
    pump_efficiency: float,
    motor_efficiency: float,
    g: float = GRAVITY_M_S2,
) -> PowerResult:
    if not (0 < pump_efficiency <= 1):
        raise ValueError(f"Eficiencia de bomba fuera de rango (0,1]: {pump_efficiency}")
    if not (0 < motor_efficiency <= 1):
        raise ValueError(f"Eficiencia de motor fuera de rango (0,1]: {motor_efficiency}")

    p_hydraulic = hydraulic_power_w(density_kg_m3, flow_m3_s, head_m, g)
    p_shaft = p_hydraulic / pump_efficiency
    p_electrical = p_shaft / motor_efficiency
    return PowerResult(hydraulic_power_w=p_hydraulic, shaft_power_w=p_shaft, electrical_power_w=p_electrical)
