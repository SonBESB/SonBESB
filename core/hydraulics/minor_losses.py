"""Coeficientes K de perdidas singulares (accesorios) y su perdida de carga.

FUENTE: planilla SMath "Bombas.sm" (autor: Bryam Perez), funcion `ks(m)`.
Se deja constancia explicita de una discrepancia real encontrada al
comparar contra PiezoCalc (pump.geo-alba.com): esa app web lista
"Valvula de compuerta" con K=0.2, mientras que esta fuente usa K=2 — un
factor 10x de diferencia. Ninguna de las dos referencias cita de donde
sale su tabla (ambas son valores de manual sin norma citada, ej. Crane
TP-410), asi que se usa la tabla SMath por ser la mas completa
(19 tipos vs 12) y porque su autor documento tambien Colebrook-White y
NPSH correctamente, pero se advierte en la UI que ningun K de esta
tabla debe tomarse como definitivo sin contrastarlo contra el catalogo
real del fabricante del accesorio.

Limitacion conocida (heredada de ambas referencias, no resuelta aqui):
K se trata como constante por tipo de accesorio, sin dependencia del
diametro. En la practica (metodo Crane, K = f_T * L/D) K si varia con
el diametro nominal — para accesorios criticos de una linea real, un K
de catalogo especifico al diametro es mas confiable que esta tabla
generica.
"""

from __future__ import annotations

from core.hydraulics.friction import GRAVITY_M_S2

FITTING_K_TABLE: dict[str, float] = {
    "Ampliacion gradual": 0.3,
    "Reduccion gradual": 0.15,
    "Curva 180": 2.0,
    "Curva 90": 0.9,
    "Curva 45": 0.4,
    "Curva 22.5": 0.1,
    "Tee lateral": 1.5,
    "Tee recto": 0.35,
    "Valvula compuerta": 0.2,
    "Valvula retencion clapeta": 2.0,
    "Valvula retencion bola": 1.2,
    "Valvula globo angulo": 5.0,
    "Valvula globo": 10.0,
    "Yee 45 recto": 0.35,
    "Yee 45 lateral": 0.8,
    "Entrada tope": 0.5,
    "Entrada acampanada": 0.1,
    "Entrada reentrante": 0.9,
    "Salida": 1.0,
}

FITTING_K_DISCREPANCIES: dict[str, str] = {
    "Valvula compuerta": (
        "PiezoCalc (pump.geo-alba.com) usa K=0.2 para valvula de compuerta; "
        "esta tabla tambien usa K=0.2 tras corregir una transcripcion previa "
        "de la planilla SMath (que traia K=2, un factor 10x). Verificar "
        "contra el fabricante del accesorio real antes de usar en diseno."
    ),
}


def total_minor_loss_coefficient(fitting_counts: dict[str, int]) -> float:
    """Suma K*cantidad. Levanta KeyError si el tipo de accesorio no existe
    en la tabla — nunca asume K=0 en silencio para un accesorio desconocido."""
    total = 0.0
    for name, count in fitting_counts.items():
        if count == 0:
            continue
        if name not in FITTING_K_TABLE:
            raise KeyError(f"Accesorio '{name}' no esta en FITTING_K_TABLE.")
        total += FITTING_K_TABLE[name] * count
    return total


def minor_loss_head_m(velocity_m_s: float, k_total: float, g: float = GRAVITY_M_S2) -> float:
    return k_total * (velocity_m_s**2) / (2.0 * g)
