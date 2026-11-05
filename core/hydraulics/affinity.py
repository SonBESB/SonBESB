"""Leyes de afinidad (bomba homologa) y combinacion de bombas gemelas.

PiezoCalc aplica Q ∝ N, H ∝ N² para escalar la curva de bomba entre
velocidades VDF, pero mantiene la eficiencia fija (75%) en los tres
escenarios de velocidad — la potencia electrica de cada escenario queda
sesgada porque la eficiencia real de una bomba centrifuga cae fuera del
punto de mejor eficiencia (BEP), y ese punto tambien se desplaza al
escalar.

Aqui la eficiencia se trata como lo hace la planilla SMath de
referencia: como parte de la curva. Cada punto (Q, H, eta) se escala
como Q' = Q*phi, H' = H*phi^2, y eta' = eta — el mismo valor de
eficiencia que tenia ese punto se traslada al punto escalado
correspondiente, en vez de imponer una eficiencia plana e igual para
todo el rango. Si el usuario no entrega una curva de eficiencia (solo
un escalar), se sigue permitiendo — pero la UI debe marcarlo
explicitamente como "eficiencia constante asumida", nunca presentarlo
como si fuera una curva medida.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PumpCurvePoint:
    flow_m3_s: float
    head_m: float
    efficiency: float | None = None  # 0-1, opcional


@dataclass(frozen=True)
class PumpCurve:
    points: tuple[PumpCurvePoint, ...]
    label: str


def scale_by_affinity(curve: PumpCurve, phi: float, *, label: str | None = None) -> PumpCurve:
    """phi = N2/N1 (variador de frecuencia) o D2/D1 (recorte de rodete).

    Q' = Q*phi, H' = H*phi^2 (leyes de afinidad estandar para maquinas
    centrifugas geometricamente similares). La eficiencia de cada punto
    NO se recalcula — se traslada tal cual al punto escalado, que es la
    practica de ingenieria habitual cerca del punto de diseno (valida
    para phi razonablemente cercano a 1; no se declara valida para
    recortes de rodete grandes o cambios de velocidad extremos).
    """
    scaled_points = tuple(
        PumpCurvePoint(flow_m3_s=p.flow_m3_s * phi, head_m=p.head_m * (phi**2), efficiency=p.efficiency)
        for p in curve.points
    )
    return PumpCurve(points=scaled_points, label=label or f"{curve.label} (phi={phi:.3f})")


def scale_power_by_affinity(power_w: float, phi: float) -> float:
    """P' = P*phi^3 — solo valida si la eficiencia no cambia entre el
    punto original y el escalado; si tienes P a partir de una curva de
    eficiencia real, prefiere recalcular P = rho*g*Q'*H'/eta' en vez de
    esta ley cubica (ver power.py)."""
    return power_w * (phi**3)


def twin_parallel(curve: PumpCurve, n_pumps: int, *, label: str | None = None) -> PumpCurve:
    """n bombas identicas en paralelo: mismo H, Q se suma n veces."""
    scaled = tuple(
        PumpCurvePoint(flow_m3_s=p.flow_m3_s * n_pumps, head_m=p.head_m, efficiency=p.efficiency)
        for p in curve.points
    )
    return PumpCurve(points=scaled, label=label or f"{curve.label} (x{n_pumps} paralelo)")


def twin_series(curve: PumpCurve, n_pumps: int, *, label: str | None = None) -> PumpCurve:
    """n bombas identicas en serie: mismo Q, H se suma n veces."""
    scaled = tuple(
        PumpCurvePoint(flow_m3_s=p.flow_m3_s, head_m=p.head_m * n_pumps, efficiency=p.efficiency)
        for p in curve.points
    )
    return PumpCurve(points=scaled, label=label or f"{curve.label} (x{n_pumps} serie)")
