"""Numero de Reynolds y factor de friccion (Darcy-Weisbach).

PiezoCalc (referencia web) usa Swamee-Jain, una aproximacion explicita
valida solo en zona turbulenta. La planilla SMath de referencia
(Bryam Perez) resuelve Colebrook-White de forma implicita via
Newton-Raphson — mas fiel, y es lo que se porta aqui, agregando lo que
ninguna de las dos referencias marca explicitamente: la rama laminar
(Re < 2300) y una advertencia explicita en zona transicional
(2300 <= Re <= 4000), donde ninguna correlacion de friccion es
confiable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

GRAVITY_M_S2 = 9.80665


class FlowRegime(Enum):
    LAMINAR = "laminar"
    TRANSITIONAL = "transicional"
    TURBULENT = "turbulento"


@dataclass(frozen=True)
class FrictionFactorResult:
    friction_factor: float
    regime: FlowRegime
    converged: bool
    iterations: int
    note: str


def reynolds_number(velocity_m_s: float, diameter_m: float, density_kg_m3: float, viscosity_pa_s: float) -> float:
    if viscosity_pa_s <= 0:
        raise ValueError("Viscosidad debe ser > 0.")
    return (density_kg_m3 * abs(velocity_m_s) * diameter_m) / viscosity_pa_s


def classify_regime(reynolds: float) -> FlowRegime:
    if reynolds < 2300:
        return FlowRegime.LAMINAR
    if reynolds <= 4000:
        return FlowRegime.TRANSITIONAL
    return FlowRegime.TURBULENT


def colebrook_white(
    reynolds: float,
    roughness_m: float,
    diameter_m: float,
    *,
    initial_guess: float = 0.02,
    tol: float = 1e-10,
    max_iter: int = 200,
) -> FrictionFactorResult:
    """Resuelve Colebrook-White 1/sqrt(f) = -2*log10(k/(3.7D) + 2.51/(Re*sqrt(f)))
    via Newton-Raphson sobre F(f) = 1/sqrt(f) + 2*log10(...).

    Fuera de zona turbulenta (Re <= 4000) no se resuelve Colebrook-White
    (no es su rango de validez): se devuelve la solucion laminar exacta
    f = 64/Re para Re < 2300, y se marca explicitamente como
    TRANSITIONAL/no confiable para 2300 <= Re <= 4000 (Colebrook-White se
    evalua igual como mejor estimacion disponible, pero converged=True no
    implica que el regimen sea fisicamente estable).
    """
    regime = classify_regime(reynolds)
    if regime is FlowRegime.LAMINAR:
        return FrictionFactorResult(
            friction_factor=64.0 / reynolds,
            regime=regime,
            converged=True,
            iterations=0,
            note="Flujo laminar (Re < 2300): f = 64/Re, formula exacta.",
        )

    relative_roughness = roughness_m / diameter_m
    f = initial_guess
    converged = False
    iterations = 0
    for iterations in range(1, max_iter + 1):
        sqrt_f = math.sqrt(f)
        F = (1.0 / sqrt_f) + 2.0 * math.log10(relative_roughness / 3.7 + 2.51 / (reynolds * sqrt_f))
        dF = (-0.5 / (f * sqrt_f)) + 2.0 * (
            (-2.51 / (2.0 * reynolds * f * sqrt_f))
            / (math.log(10) * (relative_roughness / 3.7 + 2.51 / (reynolds * sqrt_f)))
        )
        if dF == 0:
            break
        step = F / dF
        f_new = f - step
        if f_new <= 0:
            f_new = f / 2.0
        if abs(f_new - f) < tol:
            f = f_new
            converged = True
            break
        f = f_new

    note = "Colebrook-White convergio (Newton-Raphson)."
    if regime is FlowRegime.TRANSITIONAL:
        note = (
            "Zona transicional (2300 <= Re <= 4000): Colebrook-White se evalua "
            "como mejor estimacion disponible, pero ninguna correlacion es "
            "confiable en este rango — tratar el resultado con cautela."
        )
    elif not converged:
        note = f"Colebrook-White NO convergio en {max_iter} iteraciones (tol={tol})."

    return FrictionFactorResult(
        friction_factor=f, regime=regime, converged=converged, iterations=iterations, note=note
    )


def darcy_weisbach_head_loss_m(
    velocity_m_s: float, diameter_m: float, length_m: float, friction_factor: float, g: float = GRAVITY_M_S2
) -> float:
    return friction_factor * (length_m / diameter_m) * (velocity_m_s**2) / (2.0 * g)
