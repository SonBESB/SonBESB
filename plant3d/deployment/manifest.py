"""Tracks how far a component has actually gotten through the real Plant
3D validation pipeline — never further than there is evidence for.

This codebase, running with no Plant 3D installation available, can only
ever produce the GENERATED stage on its own. Every later stage
(REGISTERED, CATALOG_AVAILABLE, SPEC_AVAILABLE, MODEL_VALIDATED) requires
a human to actually run the manual steps in docs/PLANT3D_REGISTRATION_TEST.md
etc. on a real machine and record evidence in plant3d_validation/ — see
update_manifest_with_evidence() below, which is the only way this
manifest's stage ever advances past GENERATED.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

PACKAGE_STATUS_READY_FOR_VALIDATION = "PLANT3D_PACKAGE_READY_FOR_VALIDATION"
PACKAGE_STATUS_VALIDATED = "PLANT3D_VALIDATED"


class ValidationStage(str, Enum):
    GENERATED = "GENERATED"
    REGISTERED = "REGISTERED"
    CATALOG_AVAILABLE = "CATALOG_AVAILABLE"
    SPEC_AVAILABLE = "SPEC_AVAILABLE"
    MODEL_VALIDATED = "MODEL_VALIDATED"


STAGE_ORDER: List[ValidationStage] = [
    ValidationStage.GENERATED,
    ValidationStage.REGISTERED,
    ValidationStage.CATALOG_AVAILABLE,
    ValidationStage.SPEC_AVAILABLE,
    ValidationStage.MODEL_VALIDATED,
]

# Where a human records evidence for each stage after GENERATED — see
# plant3d_validation/README.md.
STAGE_EVIDENCE_FILES: Dict[ValidationStage, Optional[str]] = {
    ValidationStage.GENERATED: None,  # evidence is the generated package itself
    ValidationStage.REGISTERED: "plant3d_validation/registration_result.txt",
    ValidationStage.CATALOG_AVAILABLE: "plant3d_validation/catalog_result.md",
    ValidationStage.SPEC_AVAILABLE: "plant3d_validation/spec_result.md",
    ValidationStage.MODEL_VALIDATED: "plant3d_validation/model_result.md",
}


@dataclass(frozen=True)
class ValidationManifest:
    component_family: str
    golden_case_label: str
    current_stage: ValidationStage
    package_status: str
    evidence_files: Dict[str, Optional[str]]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_family": self.component_family,
            "golden_case_label": self.golden_case_label,
            "current_stage": self.current_stage.value,
            "package_status": self.package_status,
            "evidence_files": self.evidence_files,
            "notes": self.notes,
        }


def build_initial_manifest(component_family: str, golden_case_label: str) -> ValidationManifest:
    """The only manifest this codebase can honestly produce on its own:
    GENERATED, package ready for a human to take to a real Plant 3D
    machine. Never MODEL_VALIDATED — that requires real evidence."""
    return ValidationManifest(
        component_family=component_family,
        golden_case_label=golden_case_label,
        current_stage=ValidationStage.GENERATED,
        package_status=PACKAGE_STATUS_READY_FOR_VALIDATION,
        evidence_files={stage.value: path for stage, path in STAGE_EVIDENCE_FILES.items()},
        notes=[
            "Generado sin una instalacion de Plant 3D disponible (ver docs/PLANT3D_ENVIRONMENT.md).",
            "current_stage solo avanza cuando existe evidencia real registrada en plant3d_validation/.",
        ],
    )


def update_manifest_with_evidence(manifest: ValidationManifest, evidence_dir: Path) -> ValidationManifest:
    """Advances current_stage strictly by checking which evidence files
    actually exist and are non-empty — never by assumption."""
    reached = ValidationStage.GENERATED
    notes = list(manifest.notes)
    for stage in STAGE_ORDER[1:]:
        evidence_path = STAGE_EVIDENCE_FILES[stage]
        full_path = evidence_dir / Path(evidence_path).name if evidence_path else None
        if full_path and full_path.is_file() and full_path.stat().st_size > 0:
            reached = stage
        else:
            break

    package_status = PACKAGE_STATUS_VALIDATED if reached is ValidationStage.MODEL_VALIDATED else PACKAGE_STATUS_READY_FOR_VALIDATION
    return ValidationManifest(
        component_family=manifest.component_family,
        golden_case_label=manifest.golden_case_label,
        current_stage=reached,
        package_status=package_status,
        evidence_files=manifest.evidence_files,
        notes=notes,
    )


def write_manifest(manifest: ValidationManifest, path: Path) -> Path:
    path.write_text(json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return path
