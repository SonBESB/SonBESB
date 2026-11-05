"""Propiedades de fluido (densidad, viscosidad) para calculo hidraulico.

PiezoCalc (referencia web) solo pide densidad y asume implicitamente la
viscosidad del agua a temperatura fija — el Reynolds y por tanto el
factor de friccion quedan mal para cualquier otro fluido u otra
temperatura sin que la interfaz lo advierta. Aqui la viscosidad es
siempre un dato explicito: se toma de la tabla de agua saturada (fuente
citada) interpolando por temperatura, o el usuario la ingresa a mano
para un fluido distinto — nunca se asume en silencio.
"""

from __future__ import annotations

from dataclasses import dataclass

# Agua saturada a 1 atm. Cengel & Cimbala, "Fluid Mechanics: Fundamentals
# and Applications" (tabla de propiedades del agua saturada, apendice A-1).
# Valores estandar de manual, no medidos por este proyecto.
_WATER_TEMPERATURE_C: list[float] = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
_WATER_DENSITY_KG_M3: list[float] = [999.8, 999.7, 998.2, 995.7, 992.2, 988.1, 983.3, 977.8, 971.8, 965.3, 958.4]
_WATER_VISCOSITY_PA_S: list[float] = [
    1.787e-3, 1.307e-3, 1.002e-3, 0.7975e-3, 0.6529e-3,
    0.5468e-3, 0.4665e-3, 0.4042e-3, 0.3547e-3, 0.3147e-3, 0.2818e-3,
]
_WATER_SOURCE = "Cengel & Cimbala, Fluid Mechanics — tabla de agua saturada (interpolada)"


@dataclass(frozen=True)
class FluidProperties:
    name: str
    density_kg_m3: float
    viscosity_pa_s: float
    temperature_c: float
    source: str

    @property
    def kinematic_viscosity_m2_s(self) -> float:
        return self.viscosity_pa_s / self.density_kg_m3


class TemperatureOutOfRangeError(ValueError):
    """La temperatura pedida cae fuera de la tabla de agua (0-100 C)."""


def water_properties(temperature_c: float) -> FluidProperties:
    """Densidad y viscosidad del agua por interpolacion lineal de tabla.

    Nunca extrapola: fuera de [0, 100] C levanta TemperatureOutOfRangeError
    en vez de devolver un valor inventado.
    """
    if temperature_c < _WATER_TEMPERATURE_C[0] or temperature_c > _WATER_TEMPERATURE_C[-1]:
        raise TemperatureOutOfRangeError(
            f"{temperature_c} C esta fuera de la tabla de agua saturada "
            f"({_WATER_TEMPERATURE_C[0]}-{_WATER_TEMPERATURE_C[-1]} C). "
            "Ingresa densidad y viscosidad manualmente para esta condicion."
        )
    density = _interp(temperature_c, _WATER_TEMPERATURE_C, _WATER_DENSITY_KG_M3)
    viscosity = _interp(temperature_c, _WATER_TEMPERATURE_C, _WATER_VISCOSITY_PA_S)
    return FluidProperties(
        name="Agua",
        density_kg_m3=density,
        viscosity_pa_s=viscosity,
        temperature_c=temperature_c,
        source=_WATER_SOURCE,
    )


def custom_fluid(name: str, density_kg_m3: float, viscosity_pa_s: float, temperature_c: float) -> FluidProperties:
    """Fluido personalizado — valores ingresados por el usuario.

    El llamador (UI) es responsable de marcar visualmente que esta
    propiedad NO viene de una tabla verificada.
    """
    return FluidProperties(
        name=name,
        density_kg_m3=density_kg_m3,
        viscosity_pa_s=viscosity_pa_s,
        temperature_c=temperature_c,
        source="FLUIDO_PERSONALIZADO — valor ingresado por el usuario, no verificado contra tabla",
    )


def _interp(x: float, xs: list[float], ys: list[float]) -> float:
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + t * (ys[i + 1] - ys[i])
    raise TemperatureOutOfRangeError(f"{x} fuera de rango de tabla")
