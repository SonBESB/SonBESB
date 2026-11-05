"""Ajuste de curvas Q-H (bomba o sistema) por regresion, no por
interpolacion lineal a tramos.

PiezoCalc conecta sus 3 puntos de curva de bomba con rectas — cerca de
los extremos (cierre a caudal cero, caudal de fuga) eso puede desviar
la carga varios metros respecto a la curva real, que es tipicamente
concava. La planilla SMath de referencia (Bryam Perez) sí hace
regresion por minimos cuadrados (su funcion `polyfit`, grados
constante/lineal/cuadratica/cubica) — eso es lo que se porta aqui, con
numpy.polyfit y el R^2 siempre reportado (nunca se oculta que tan bien
ajusta el polinomio a los puntos ingresados).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PolynomialFit:
    degree: int
    coefficients: tuple[float, ...]  # orden numpy: mayor grado primero
    r_squared: float

    def evaluate(self, q: float) -> float:
        return float(np.polyval(self.coefficients, q))


def fit_polynomial(q_values: list[float], h_values: list[float], degree: int) -> PolynomialFit:
    """Ajusta H = f(Q) por minimos cuadrados.

    degree debe ser < len(q_values) (grados de libertad); si el usuario
    pide un grado que no se puede resolver con los puntos disponibles se
    levanta ValueError en vez de degradar el grado en silencio — la UI
    decide como pedirle al usuario mas puntos o bajar el grado.
    """
    if len(q_values) != len(h_values):
        raise ValueError("q_values y h_values deben tener el mismo largo.")
    if len(q_values) < degree + 1:
        raise ValueError(
            f"Se necesitan al menos {degree + 1} puntos para un ajuste de grado {degree} "
            f"(hay {len(q_values)})."
        )

    q = np.asarray(q_values, dtype=float)
    h = np.asarray(h_values, dtype=float)
    coeffs = np.polyfit(q, h, degree)

    predicted = np.polyval(coeffs, q)
    residual_ss = float(np.sum((h - predicted) ** 2))
    total_ss = float(np.sum((h - np.mean(h)) ** 2))
    r_squared = 1.0 if total_ss == 0 else 1.0 - residual_ss / total_ss

    return PolynomialFit(degree=degree, coefficients=tuple(coeffs.tolist()), r_squared=r_squared)
