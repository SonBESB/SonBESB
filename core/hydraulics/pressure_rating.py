"""Presion de diseno vs clase de presion nominal (PN) de la tuberia.

PiezoCalc pide una clase PN por tramo pero su propia tabla de detalle
muestra literalmente "no evaluado" en la columna Presion — el dato se
pide y nunca se usa. Aqui se calcula la condicion de presion mas
exigente en regimen permanente (bomba a caudal cero / valvula cerrada
= "shutoff head") y se compara contra la clase PN elegida.

Por que shutoff y no el punto de operacion normal: a caudal cero no
hay perdida por friccion, asi que TODA la carga de la bomba (H a Q=0,
tomada de la curva ajustada) aparece como presion estatica en la
descarga — es la condicion de presion mas alta que ve la tuberia en
operacion normal (sin contar golpe de ariete, ver surge.py). Evaluar
solo el punto de operacion, como hace cualquier calculadora que omite
este chequeo, subestima la presion de diseno real.

Limitacion declarada: el perfil de elevacion entre tramos se reparte
de forma PROPORCIONAL a la longitud acumulada (mismo supuesto
simplificado que declara PiezoCalc en su "perfil ilustrativo — no
representa presiones reales"). Para un chequeo de clase de tuberia
real, reemplazar por las cotas de terreno relevadas en cada nodo.

Las clases PN son una referencia nominal a 20 C para agua (norma tipo
ISO 4065 / DIN 8074-8075 para HDPE); no se aplica ningun derateo por
temperatura — si el fluido/temperatura de servicio se aleja de esas
condiciones, la presion admisible real de la tuberia puede ser menor
que su PN nominal.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.hydraulics.system_curve import PipeSegment

PN_BAR_TABLE: dict[str, float] = {
    "PN6": 6.0,
    "PN10": 10.0,
    "PN16": 16.0,
    "PN20": 20.0,
    "PN25": 25.0,
    "PN32": 32.0,
}

PASCAL_PER_BAR = 100_000.0


@dataclass(frozen=True)
class SegmentPressureCheck:
    label: str
    start_length_m: float
    end_length_m: float
    max_design_pressure_bar: float
    pn_label: str
    pn_bar: float
    passed: bool
    margin_bar: float


def build_shutoff_pressure_profile(
    segments: list[PipeSegment],
    shutoff_head_m: float,
    static_head_m: float,
    density_kg_m3: float,
    pn_labels: list[str],
    g: float = 9.80665,
) -> list[SegmentPressureCheck]:
    """Presion de diseno (a Q=0) al inicio de cada tramo vs su clase PN.

    pn_labels debe tener el mismo largo que segments (un PN por tramo).
    La elevacion se reparte proporcional a la longitud acumulada de
    static_head_m (ver limitacion en el docstring del modulo).
    """
    if len(segments) != len(pn_labels):
        raise ValueError("segments y pn_labels deben tener el mismo largo.")

    total_length = sum(s.length_m for s in segments)
    if total_length <= 0:
        raise ValueError("La longitud total de los tramos debe ser > 0.")

    results = []
    cumulative = 0.0
    for segment, pn_label in zip(segments, pn_labels):
        if pn_label not in PN_BAR_TABLE:
            raise KeyError(f"Clase de presion '{pn_label}' no esta en PN_BAR_TABLE.")
        pn_bar = PN_BAR_TABLE[pn_label]

        elevation_at_start = static_head_m * (cumulative / total_length)
        pressure_head_at_start = shutoff_head_m - elevation_at_start
        pressure_bar = max(pressure_head_at_start, 0.0) * density_kg_m3 * g / PASCAL_PER_BAR

        results.append(
            SegmentPressureCheck(
                label=segment.label,
                start_length_m=cumulative,
                end_length_m=cumulative + segment.length_m,
                max_design_pressure_bar=pressure_bar,
                pn_label=pn_label,
                pn_bar=pn_bar,
                passed=pressure_bar <= pn_bar,
                margin_bar=pn_bar - pressure_bar,
            )
        )
        cumulative += segment.length_m
    return results
