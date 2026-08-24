"""Self-check pass over a built SegmentedElbowGeometry.

Because build_segmented_elbow_geometry() consumes OD/thickness/R/Le/Z
directly, most checks here would be tautological if they simply re-read
the same numbers back — that is not the point. Each check either (a)
recomputes a quantity through an independent formula (e.g. the P1-P2
distance via the law of cosines, instead of via the same dir1/dir2*Z
construction used to place the points), or (b) verifies an invariant the
builder must uphold but could silently violate on a future edit (e.g.
every gajo joint lying exactly on the R-radius circle).

Never adjusts anything: on a mismatch beyond tolerance this raises
GeometryValidationError carrying the found vs. expected values, per the
project spec's "GEOMETRY_VALIDATION_ERROR, nunca ajustar en silencio".
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from core.geometry.segmented_elbow import SegmentedElbowGeometry
from core.models.elbow import ElbowParameters

LINEAR_TOLERANCE_MM = 1e-6
ANGULAR_TOLERANCE_DEG = 1e-6


def _dist(a, b) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


@dataclass(frozen=True)
class GeometryCheckFailure:
    code: str
    message: str
    expected: float
    found: float
    difference: float


class GeometryValidationError(Exception):
    """GEOMETRY_VALIDATION_ERROR: raised with the full list of failed checks."""

    def __init__(self, failures: List[GeometryCheckFailure]):
        self.failures = failures
        summary = "; ".join(f"{f.code}: esperado={f.expected!r} obtenido={f.found!r} diff={f.difference!r}" for f in failures)
        super().__init__(f"GEOMETRY_VALIDATION_ERROR: {summary}")


def _angle_between_deg(a, b) -> float:
    cos_angle = sum(x * y for x, y in zip(a, b)) / (
        math.sqrt(sum(c * c for c in a)) * math.sqrt(sum(c * c for c in b))
    )
    cos_angle = max(-1.0, min(1.0, cos_angle))
    return math.degrees(math.acos(cos_angle))


def validate_segmented_elbow_geometry(
    params: ElbowParameters, geometry: SegmentedElbowGeometry
) -> None:
    """Raises GeometryValidationError if any self-check fails beyond tolerance."""
    failures: List[GeometryCheckFailure] = []

    def check(code: str, message: str, expected: float, found: float, tolerance: float) -> None:
        diff = abs(expected - found)
        if diff > tolerance:
            failures.append(GeometryCheckFailure(code, message, expected, found, diff))

    # 1. Final deflection angle equals the requested angle_deg. This must be
    #    measured between the two *flow* directions (leg1_stub.direction,
    #    leg2_stub.direction — i.e. axis_start->axis_end for each stub), NOT
    #    between p1_direction/p2_direction: those are the outward,
    #    away-from-vertex port directions, and the angle between them is
    #    (180 - angle_deg), not angle_deg (they only coincide at exactly
    #    90 degrees, where sin/cos of the half-angle are equal — which is
    #    exactly the coincidence that let this check pass on the golden
    #    DN315/90 case despite comparing the wrong two vectors; the 30
    #    degree case exposed it). See docs/SEGMENTED_ELBOW_GEOMETRY.md.
    angle_between = _angle_between_deg(geometry.leg1_stub.direction, geometry.leg2_stub.direction)
    check(
        "ANGLE_MISMATCH",
        "El angulo de deflexion (flujo P1->P2) no coincide con angle_deg.",
        params.angle_deg,
        angle_between,
        ANGULAR_TOLERANCE_DEG,
    )

    # 2. Z geometrico (vertex -> face distance) coherente con Z tabulado/calculado.
    z_expected = geometry.z_mm
    for label, face in (("P1", geometry.p1_face), ("P2", geometry.p2_face)):
        check(
            f"Z_MISMATCH_{label}",
            f"La distancia vertice-{label} no coincide con Z.",
            z_expected,
            _dist(geometry.vertex, face),
            LINEAR_TOLERANCE_MM,
        )

    # 3. Independent P1-P2 distance cross-check via the law of cosines,
    #    using a formula different from the one used to place P1/P2. The
    #    triangle vertex-P1-P2 has two sides of length Z meeting at the
    #    vertex with the interior angle actually formed by the *outward*
    #    p1_direction/p2_direction vectors — which is (180 - angle_deg),
    #    not angle_deg itself (see check 1's comment) — so that is the
    #    angle the law of cosines needs here.
    vertex_interior_angle_deg = _angle_between_deg(geometry.p1_direction, geometry.p2_direction)
    expected_chord = 2 * z_expected * math.sin(math.radians(vertex_interior_angle_deg) / 2)
    check(
        "P1_P2_DISTANCE_MISMATCH",
        "La distancia P1-P2 no coincide con la prevista por ley de cosenos.",
        expected_chord,
        _dist(geometry.p1_face, geometry.p2_face),
        LINEAR_TOLERANCE_MM,
    )

    # 4. Radius used: every gajo joint point must lie on the tabulated R circle.
    if geometry.segments:
        for segment in geometry.segments:
            for point_label, point in (("start", segment.axis_start), ("end", segment.axis_end)):
                check(
                    f"RADIUS_MISMATCH_{segment.label}_{point_label}",
                    "Un punto de union del gajo no esta sobre el radio R tabulado.",
                    params.radius_mm,
                    _dist(geometry.arc_center, point),
                    LINEAR_TOLERANCE_MM,
                )

        # 5. Segment angle sum must equal the total angle — a hard invariant,
        #    stricter than the WARNING-level check in core/validation, because
        #    silently building a bend that doesn't reach the requested angle
        #    would be worse than refusing to build it.
        segment_sum = sum(s.angle_deg for s in geometry.segments)
        check(
            "SEGMENT_ANGLE_SUM_MISMATCH",
            "La suma de angulos de los gajos no coincide con angle_deg.",
            params.angle_deg,
            segment_sum,
            ANGULAR_TOLERANCE_DEG,
        )

    if failures:
        raise GeometryValidationError(failures)
