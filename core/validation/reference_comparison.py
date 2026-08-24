"""Compares the parametric model's dimensions against a physical/CAD reference.

This is the V0.2.1 "validacion de ingenieria" layer: it never adjusts
the geometry to make it match a reference. It only reports absolute and
percentage differences plus a PASS/FAIL verdict per field, and — for a
FAILED field — which specific modeling hypothesis (documented in
docs/GEOMETRY_VALIDATION_REFERENCE.md) that dimension depends on, so a
mismatch points at what to re-examine rather than just "something is
off".

Reference values are optional per field: a field left blank (None) by the
user is simply skipped, never defaulted or guessed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from core.geometry.engineering_report import OverallDimensions

DEFAULT_TOLERANCE_PRESETS_MM = (1.0, 2.0, 5.0)
DEFAULT_TOLERANCE_MM = 1.0


class ComparisonStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


OVERALL_FIELD_LABELS = {
    "width_mm": "Ancho total",
    "height_mm": "Alto total",
    "length_mm": "Largo total",
    "p1_p2_distance_mm": "Distancia P1-P2",
    "p1_to_vertex_mm": "Distancia P1 - vertice teorico",
    "p2_to_vertex_mm": "Distancia P2 - vertice teorico",
    "radius_used_mm": "R utilizado",
    "z_resultant_mm": "Z resultante",
}

FIELD_HYPOTHESIS_NOTES = {
    "width_mm": (
        "Depende del envolvente 3D de la malla (OD + trayectoria del eje, que a su vez "
        "depende de la hipotesis de que las uniones de los gajos estan sobre el circulo R)."
    ),
    "height_mm": (
        "Para un codo plano debe ser exactamente igual al OD. Si difiere, el codo de "
        "referencia probablemente tiene una componente fuera de plano no soportada en V0.2.1."
    ),
    "length_mm": (
        "Misma dependencia que 'Ancho total': envolvente 3D derivada de la hipotesis de "
        "gajos inscritos en el circulo R."
    ),
    "p1_p2_distance_mm": (
        "Depende de Z (tabulado o calculado) y del angulo total realmente logrado por la "
        "suma de gajos de la Configuracion."
    ),
    "p1_to_vertex_mm": (
        "Corresponde a Z = Le + R * tan(angulo/2). Revisar si el Le o el R de referencia "
        "difieren de los valores tabulados en BD_Codos."
    ),
    "p2_to_vertex_mm": (
        "Misma formula que 'P1 - vertice teorico' (Z es simetrico en este modelo)."
    ),
    "radius_used_mm": (
        "Es el R tabulado en BD_Codos, usado tal cual (nunca recalculado). Si difiere, "
        "revisar esa fila del Excel o si el R real de fabricacion no coincide con el "
        "catalogo."
    ),
    "z_resultant_mm": (
        "Z tabulado (Modo A) o Z = Le + R*tan(angulo/2) (Modo B cuando no se ingresa Z "
        "manual). Revisar cual de los dos aplica a esta comparacion."
    ),
    "gajo_axis_length_mm": (
        "HIPOTESIS DE MODELADO CENTRAL: que cada numero de 'Configuracion' (ej. "
        "15-30-30-15) es el arco, en grados, que ese gajo ocupa sobre el circulo de "
        "radio R — no otra convencion de corte de fabrica. Una desviacion sistematica "
        "en las longitudes de gajo es la señal mas directa de que esta hipotesis "
        "necesita revisarse contra el modelo de referencia."
    ),
}


@dataclass(frozen=True)
class ComparisonRow:
    field: str
    label: str
    parametric_value_mm: float
    reference_value_mm: float
    abs_diff_mm: float
    pct_diff: float
    tolerance_mm: float
    status: ComparisonStatus
    hypothesis_note: str


@dataclass
class ReferenceMeasurement:
    """User-entered measurements from the physical/CAD reference elbow.

    Every field is optional; None means "not entered yet", not zero.
    """

    width_mm: Optional[float] = None
    height_mm: Optional[float] = None
    length_mm: Optional[float] = None
    p1_p2_distance_mm: Optional[float] = None
    p1_to_vertex_mm: Optional[float] = None
    p2_to_vertex_mm: Optional[float] = None
    radius_used_mm: Optional[float] = None
    z_resultant_mm: Optional[float] = None
    gajo_axis_lengths_mm: List[Optional[float]] = field(default_factory=list)


def _make_row(field_key: str, label: str, parametric: float, reference: float, tolerance_mm: float, note: str) -> ComparisonRow:
    abs_diff = abs(parametric - reference)
    pct_diff = (abs_diff / reference * 100) if reference else float("inf")
    status = ComparisonStatus.PASS if abs_diff <= tolerance_mm else ComparisonStatus.FAIL
    return ComparisonRow(
        field=field_key,
        label=label,
        parametric_value_mm=parametric,
        reference_value_mm=reference,
        abs_diff_mm=abs_diff,
        pct_diff=pct_diff,
        tolerance_mm=tolerance_mm,
        status=status,
        hypothesis_note=note,
    )


def compare_overall_dimensions(
    parametric: OverallDimensions,
    reference: ReferenceMeasurement,
    tolerance_mm: float = DEFAULT_TOLERANCE_MM,
) -> List[ComparisonRow]:
    rows: List[ComparisonRow] = []
    for field_key, label in OVERALL_FIELD_LABELS.items():
        reference_value = getattr(reference, field_key)
        if reference_value is None:
            continue
        parametric_value = getattr(parametric, field_key)
        rows.append(
            _make_row(
                field_key, label, parametric_value, reference_value, tolerance_mm,
                FIELD_HYPOTHESIS_NOTES[field_key],
            )
        )
    return rows


def compare_gajo_lengths(
    parametric_axis_lengths_mm: List[float],
    reference: ReferenceMeasurement,
    tolerance_mm: float = DEFAULT_TOLERANCE_MM,
) -> List[ComparisonRow]:
    rows: List[ComparisonRow] = []
    for i, parametric_value in enumerate(parametric_axis_lengths_mm):
        if i >= len(reference.gajo_axis_lengths_mm):
            break
        reference_value = reference.gajo_axis_lengths_mm[i]
        if reference_value is None:
            continue
        rows.append(
            _make_row(
                f"gajo_{i + 1}_axis_length_mm",
                f"Gajo {i + 1} — longitud de eje",
                parametric_value,
                reference_value,
                tolerance_mm,
                FIELD_HYPOTHESIS_NOTES["gajo_axis_length_mm"],
            )
        )
    return rows


def has_any_reference_value(reference: ReferenceMeasurement) -> bool:
    overall_provided = any(getattr(reference, key) is not None for key in OVERALL_FIELD_LABELS)
    gajo_provided = any(v is not None for v in reference.gajo_axis_lengths_mm)
    return overall_provided or gajo_provided


def all_rows_pass(rows: List[ComparisonRow]) -> bool:
    return len(rows) > 0 and all(r.status is ComparisonStatus.PASS for r in rows)
