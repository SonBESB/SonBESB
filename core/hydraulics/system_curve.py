"""Curva de sistema (carga estatica + friccion + singulares) para tramos
en serie.

Mismo modelo que PiezoCalc (tramos en serie, bomba al inicio, dos
depositos abiertos) pero cada punto de la curva se calcula con friccion
real (Colebrook-White + viscosidad real, ver friction.py) en vez de
Swamee-Jain con agua fija, y las perdidas singulares nunca quedan en 0
por defecto ni se aplican con un factor arbitrario silencioso.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from core.hydraulics.friction import FlowRegime, colebrook_white, darcy_weisbach_head_loss_m, reynolds_number
from core.hydraulics.minor_losses import minor_loss_head_m, total_minor_loss_coefficient


@dataclass(frozen=True)
class PipeSegment:
    label: str
    length_m: float
    inside_diameter_mm: float
    roughness_mm: float
    fitting_counts: dict[str, int] = field(default_factory=dict)

    @property
    def inside_diameter_m(self) -> float:
        return self.inside_diameter_mm / 1000.0

    @property
    def roughness_m(self) -> float:
        return self.roughness_mm / 1000.0

    @property
    def area_m2(self) -> float:
        return math.pi * (self.inside_diameter_m**2) / 4.0

    @property
    def minor_loss_coefficient(self) -> float:
        return total_minor_loss_coefficient(self.fitting_counts)


@dataclass(frozen=True)
class SegmentEvaluation:
    label: str
    flow_m3_s: float
    velocity_m_s: float
    reynolds: float
    regime: FlowRegime
    friction_factor: float
    friction_converged: bool
    friction_note: str
    friction_head_loss_m: float
    minor_head_loss_m: float

    @property
    def total_head_loss_m(self) -> float:
        return self.friction_head_loss_m + self.minor_head_loss_m


def evaluate_segment(segment: PipeSegment, flow_m3_s: float, density_kg_m3: float, viscosity_pa_s: float) -> SegmentEvaluation:
    velocity = flow_m3_s / segment.area_m2
    reynolds = reynolds_number(velocity, segment.inside_diameter_m, density_kg_m3, viscosity_pa_s)
    friction = colebrook_white(reynolds, segment.roughness_m, segment.inside_diameter_m)
    hf = darcy_weisbach_head_loss_m(velocity, segment.inside_diameter_m, segment.length_m, friction.friction_factor)
    hs = minor_loss_head_m(velocity, segment.minor_loss_coefficient)
    return SegmentEvaluation(
        label=segment.label,
        flow_m3_s=flow_m3_s,
        velocity_m_s=velocity,
        reynolds=reynolds,
        regime=friction.regime,
        friction_factor=friction.friction_factor,
        friction_converged=friction.converged,
        friction_note=friction.note,
        friction_head_loss_m=hf,
        minor_head_loss_m=hs,
    )


@dataclass(frozen=True)
class SystemPoint:
    flow_m3_s: float
    static_head_m: float
    total_head_m: float
    segment_evaluations: tuple[SegmentEvaluation, ...]


def evaluate_system(
    segments: list[PipeSegment],
    flow_m3_s: float,
    static_head_m: float,
    density_kg_m3: float,
    viscosity_pa_s: float,
) -> SystemPoint:
    evaluations = tuple(evaluate_segment(seg, flow_m3_s, density_kg_m3, viscosity_pa_s) for seg in segments)
    total_head = static_head_m + sum(e.total_head_loss_m for e in evaluations)
    return SystemPoint(
        flow_m3_s=flow_m3_s, static_head_m=static_head_m, total_head_m=total_head, segment_evaluations=evaluations
    )


def build_system_curve(
    segments: list[PipeSegment],
    static_head_m: float,
    density_kg_m3: float,
    viscosity_pa_s: float,
    flow_range_m3_s: list[float],
) -> list[SystemPoint]:
    """Evalua la curva de sistema en cada Q de flow_range_m3_s.

    Q=0 se salta (velocidad indefinida en la formula de friccion) y se
    reemplaza por el punto (0, static_head_m) directamente — sin friccion
    a caudal nulo, coherente con la fisica del problema.
    """
    points: list[SystemPoint] = []
    for q in flow_range_m3_s:
        if q <= 0:
            points.append(SystemPoint(flow_m3_s=0.0, static_head_m=static_head_m, total_head_m=static_head_m, segment_evaluations=()))
            continue
        points.append(evaluate_system(segments, q, static_head_m, density_kg_m3, viscosity_pa_s))
    return points
