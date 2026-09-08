"""Punto de operacion: interseccion entre curva de bomba y curva de
sistema, vía biseccion (sin depender de scipy — no es una dependencia
del proyecto).

A diferencia de asumir que siempre existe una interseccion "razonable"
y devolver el mejor numero disponible, aqui se verifica primero que
haya cambio de signo en H_bomba(Q) - H_sistema(Q) dentro del rango
buscado; si no lo hay, se devuelve un resultado con found=False y una
razon explicita en vez de un caudal inventado.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class OperatingPointResult:
    found: bool
    flow_m3_s: float | None
    head_m: float | None
    iterations: int
    reason: str


def solve_operating_point(
    pump_head_fn: Callable[[float], float],
    system_head_fn: Callable[[float], float],
    q_min: float,
    q_max: float,
    *,
    tol: float = 1e-6,
    max_iter: int = 200,
) -> OperatingPointResult:
    def diff(q: float) -> float:
        return pump_head_fn(q) - system_head_fn(q)

    f_min = diff(q_min)
    f_max = diff(q_max)

    if f_min == 0:
        return OperatingPointResult(True, q_min, pump_head_fn(q_min), 0, "Interseccion exacta en q_min.")
    if f_max == 0:
        return OperatingPointResult(True, q_max, pump_head_fn(q_max), 0, "Interseccion exacta en q_max.")

    if (f_min > 0) == (f_max > 0):
        return OperatingPointResult(
            found=False,
            flow_m3_s=None,
            head_m=None,
            iterations=0,
            reason=(
                f"No hay cambio de signo entre q_min={q_min:g} y q_max={q_max:g} "
                f"(H_bomba-H_sistema = {f_min:.4g} en q_min, {f_max:.4g} en q_max). "
                "La curva de bomba y la curva de sistema no se cruzan en el rango "
                "evaluado — revisa el rango de caudal o si la bomba es capaz de "
                "vencer la carga estatica del sistema."
            ),
        )

    lo, hi = q_min, q_max
    f_lo = f_min
    iterations = 0
    for iterations in range(1, max_iter + 1):
        mid = (lo + hi) / 2.0
        f_mid = diff(mid)
        if abs(f_mid) < tol or (hi - lo) / 2.0 < tol:
            return OperatingPointResult(True, mid, pump_head_fn(mid), iterations, "Biseccion convergio.")
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid

    mid = (lo + hi) / 2.0
    return OperatingPointResult(
        True, mid, pump_head_fn(mid), iterations, f"Biseccion alcanzo max_iter={max_iter} sin tol exacta."
    )
