"""Geometric sanity checks for MODE B (custom elbows).

These are basic physical/geometric plausibility checks only. They do NOT
verify DIN 16963 compliance — a custom elbow is, by definition, never
declared standard-compliant (see ElbowParameters.din16963_compliant, which
build_custom() always sets to False).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

from core.models.elbow import ElbowParameters


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    message: str
    severity: Severity = Severity.ERROR


def validate_custom_elbow(params: ElbowParameters) -> List[ValidationIssue]:
    """Runs the basic geometric checks listed in the project spec.

    Returns an empty list when the geometry is plausible. Does not raise —
    callers decide whether ERROR-severity issues block geometry/preview.
    """
    issues: List[ValidationIssue] = []

    if params.od_mm <= 0:
        issues.append(ValidationIssue("od_mm", "El diametro exterior (OD) debe ser mayor que 0."))
    if params.thickness_mm <= 0:
        issues.append(ValidationIssue("thickness_mm", "El espesor debe ser mayor que 0."))
    if params.od_mm > 0 and params.thickness_mm > 0 and params.od_mm <= 2 * params.thickness_mm:
        issues.append(
            ValidationIssue("thickness_mm", "El OD debe ser mayor que 2 x espesor (diametro interior positivo).")
        )
    if params.inside_diameter_mm <= 0:
        issues.append(ValidationIssue("inside_diameter_mm", "El diametro interior resultante debe ser mayor que 0."))
    if params.radius_mm <= 0:
        issues.append(ValidationIssue("radius_mm", "El radio debe ser mayor que 0."))
    if not (0 < params.angle_deg < 180):
        issues.append(ValidationIssue("angle_deg", "El angulo debe estar entre 0° y 180° (exclusivo)."))
    if params.le_mm <= 0:
        issues.append(ValidationIssue("le_mm", "Le debe ser una longitud positiva."))
    if params.z_mm is not None and params.z_mm <= 0:
        issues.append(ValidationIssue("z_mm", "Z debe ser una longitud positiva."))

    if params.segment_configuration and params.segment_configuration.segment_angles_deg:
        total = sum(params.segment_configuration.segment_angles_deg)
        if abs(total - params.angle_deg) > 0.5:
            issues.append(
                ValidationIssue(
                    "segment_configuration",
                    f"La suma de segmentos ({total}°) no coincide con el angulo total ({params.angle_deg}°).",
                    severity=Severity.WARNING,
                )
            )

    return issues


def has_blocking_errors(issues: List[ValidationIssue]) -> bool:
    return any(issue.severity is Severity.ERROR for issue in issues)
