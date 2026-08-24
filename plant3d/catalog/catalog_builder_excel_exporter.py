"""Excel exporter for Plant 3D's Catalog Builder — REFERENCE_TEMPLATE_REQUIRED.

Per the V0.3 spec: do not guess Autodesk's exact Excel format. Catalog
Builder's "Export to Excel" output (Catalog Builder -> Create Catalog
Template -> Elbow -> Custom Parametric Shape -> HDPE_SEGMENTED_ELBOW ->
Export to Excel) has never been obtained from a real installation in
this project. Until that real file is added under
plant3d/templates/reference/ and inspected, this exporter refuses to
produce anything claiming to be importable — it only ever raises
ReferenceTemplateRequiredError.

What IS safe to produce today is the plain intermediate dataset (see
catalog_builder_payload.py) — our own already-validated numbers, with no
Autodesk-specific formatting decisions baked in.
"""

from __future__ import annotations

from pathlib import Path

from core.geometry.segmented_elbow import SegmentedElbowGeometry
from core.models.elbow import ElbowParameters

REFERENCE_TEMPLATE_REQUIRED = "REFERENCE_TEMPLATE_REQUIRED"
REFERENCE_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "reference"


class ReferenceTemplateRequiredError(Exception):
    """Raised whenever Excel export is attempted without a real reference
    template obtained from Catalog Builder's own "Export to Excel"."""

    def __init__(self, message: str | None = None):
        super().__init__(
            message
            or (
                f"{REFERENCE_TEMPLATE_REQUIRED}: no se ha incorporado un Excel real exportado por "
                "Catalog Builder (Catalog Builder -> Create Catalog Template -> Elbow -> Custom "
                "Parametric Shape -> HDPE_SEGMENTED_ELBOW -> Export to Excel) bajo "
                "plant3d/templates/reference/. Ver docs/PLANT3D_CATALOG_WORKFLOW.md."
            )
        )


class CatalogBuilderExcelExporter:
    """Will eventually map our dataset onto a real Catalog Builder Excel
    template. Until plant3d/templates/reference/ contains a real exported
    file, export_to_excel() always raises ReferenceTemplateRequiredError —
    never a guessed format."""

    def __init__(self, reference_template_dir: Path = REFERENCE_TEMPLATE_DIR):
        self._reference_template_dir = reference_template_dir

    def has_reference_template(self) -> bool:
        if not self._reference_template_dir.is_dir():
            return False
        return any(self._reference_template_dir.glob("*.xls*"))

    def export_to_excel(self, params: ElbowParameters, geometry: SegmentedElbowGeometry, output_path: Path) -> Path:
        if not self.has_reference_template():
            raise ReferenceTemplateRequiredError()
        # Intentionally unreachable until a real template is inspected —
        # the actual column mapping will be written against that file,
        # not guessed here.
        raise NotImplementedError(
            "Reference template present but mapping not yet implemented — "
            "see docs/PLANT3D_CATALOG_WORKFLOW.md."
        )
