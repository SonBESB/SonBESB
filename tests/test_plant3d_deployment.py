"""V0.3 tests for plant3d/deployment/ (manifest + package builder) and
plant3d/catalog/ (Catalog Builder Excel exporter), using
GOLDEN_CASE_DN110_PN10_90.

Central rule under test: a validation stage may only advance when a real,
non-empty evidence file exists on disk — never by assumption, and never
past MODEL_VALIDATED's evidence without every earlier stage's evidence
also present.
"""

import ast
import json

import pytest

from core.geometry.segmented_elbow import build_segmented_elbow_geometry
from core.library.elbow_registration import register_hdpe_segmented_elbow
from data.repository import ElbowRepository
from plant3d.catalog.catalog_builder_excel_exporter import (
    REFERENCE_TEMPLATE_REQUIRED,
    CatalogBuilderExcelExporter,
    ReferenceTemplateRequiredError,
)
from plant3d.catalog.catalog_builder_payload import build_catalog_builder_payload
from plant3d.deployment.manifest import (
    PACKAGE_STATUS_READY_FOR_VALIDATION,
    PACKAGE_STATUS_VALIDATED,
    ValidationStage,
    build_initial_manifest,
    update_manifest_with_evidence,
    write_manifest,
)
from plant3d.deployment.package_builder import build_deployment_package
from tests.golden_cases import GOLDEN_CASE_DN110_PN10_90


@pytest.fixture(scope="module")
def repository() -> ElbowRepository:
    return ElbowRepository.from_excel()


@pytest.fixture(scope="module")
def golden(repository):
    result = repository.lookup(**GOLDEN_CASE_DN110_PN10_90)
    params = result.elbow
    geometry = build_segmented_elbow_geometry(params)
    params.ports = geometry.ports
    registration = register_hdpe_segmented_elbow(params, geometry)
    return params, geometry, registration


# --- manifest -----------------------------------------------------------


def test_initial_manifest_is_generated_never_more():
    manifest = build_initial_manifest(component_family="HDPE_SEGMENTED_ELBOW", golden_case_label="DN110 PN10 90")
    assert manifest.current_stage is ValidationStage.GENERATED
    assert manifest.package_status == PACKAGE_STATUS_READY_FOR_VALIDATION


def test_manifest_stays_generated_with_no_evidence_files(tmp_path):
    manifest = build_initial_manifest(component_family="HDPE_SEGMENTED_ELBOW", golden_case_label="DN110 PN10 90")
    updated = update_manifest_with_evidence(manifest, tmp_path)
    assert updated.current_stage is ValidationStage.GENERATED
    assert updated.package_status == PACKAGE_STATUS_READY_FOR_VALIDATION


def test_manifest_stays_generated_with_empty_evidence_files(tmp_path):
    """A 0-byte evidence file (like the ones shipped in plant3d_validation/)
    must never count as real evidence."""
    (tmp_path / "registration_result.txt").write_text("", encoding="utf-8")
    manifest = build_initial_manifest(component_family="HDPE_SEGMENTED_ELBOW", golden_case_label="DN110 PN10 90")
    updated = update_manifest_with_evidence(manifest, tmp_path)
    assert updated.current_stage is ValidationStage.GENERATED


def test_manifest_advances_one_stage_with_one_real_evidence_file(tmp_path):
    (tmp_path / "registration_result.txt").write_text("PLANTREGISTERCUSTOMSCRIPTS: OK\n", encoding="utf-8")
    manifest = build_initial_manifest(component_family="HDPE_SEGMENTED_ELBOW", golden_case_label="DN110 PN10 90")
    updated = update_manifest_with_evidence(manifest, tmp_path)
    assert updated.current_stage is ValidationStage.REGISTERED
    assert updated.package_status == PACKAGE_STATUS_READY_FOR_VALIDATION  # not VALIDATED yet


def test_manifest_stops_at_first_missing_stage_even_if_a_later_one_exists(tmp_path):
    (tmp_path / "registration_result.txt").write_text("OK\n", encoding="utf-8")
    # catalog_result.md intentionally missing
    (tmp_path / "spec_result.md").write_text("OK\n", encoding="utf-8")
    manifest = build_initial_manifest(component_family="HDPE_SEGMENTED_ELBOW", golden_case_label="DN110 PN10 90")
    updated = update_manifest_with_evidence(manifest, tmp_path)
    assert updated.current_stage is ValidationStage.REGISTERED


def test_manifest_reaches_validated_only_with_all_four_evidence_files(tmp_path):
    for name in ("registration_result.txt", "catalog_result.md", "spec_result.md", "model_result.md"):
        (tmp_path / name).write_text("OK\n", encoding="utf-8")
    manifest = build_initial_manifest(component_family="HDPE_SEGMENTED_ELBOW", golden_case_label="DN110 PN10 90")
    updated = update_manifest_with_evidence(manifest, tmp_path)
    assert updated.current_stage is ValidationStage.MODEL_VALIDATED
    assert updated.package_status == PACKAGE_STATUS_VALIDATED


def test_write_manifest_produces_valid_json(tmp_path):
    manifest = build_initial_manifest(component_family="HDPE_SEGMENTED_ELBOW", golden_case_label="DN110 PN10 90")
    path = write_manifest(manifest, tmp_path / "validation_manifest.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["current_stage"] == "GENERATED"
    assert payload["package_status"] == PACKAGE_STATUS_READY_FOR_VALIDATION


# --- shipped evidence placeholders (repo-state guard) --------------------


def test_shipped_plant3d_validation_evidence_files_not_yet_reached_are_empty():
    """Guards against accidentally committing fake evidence: stages not
    yet reached by a real manual test ship as literal 0-byte
    placeholders. registration_result.txt is excluded here — as of
    V0.3.1 it holds real evidence from an actual Plant 3D 2025 test (see
    test below)."""
    from pathlib import Path

    evidence_dir = Path(__file__).resolve().parent.parent / "plant3d_validation"
    for name in ("catalog_result.md", "spec_result.md", "model_result.md"):
        path = evidence_dir / name
        assert path.is_file(), f"missing placeholder: {path}"
        assert path.stat().st_size == 0, f"{path} must ship empty (0 bytes), found real content"


def test_shipped_registration_result_holds_real_v031_evidence():
    """registration_result.txt was filled with real evidence from an
    actual AutoCAD Plant 3D 2025 test (V0.3.1): registration/compile
    passed, but TESTACPSCRIPT returned NIL due to an entry-point name
    mismatch. Guards against this real evidence being silently reverted
    to an empty placeholder or overwritten with different claims."""
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "plant3d_validation" / "registration_result.txt"
    assert path.is_file()
    content = path.read_text(encoding="utf-8")
    assert content.strip() != ""
    assert "REGISTER" in content and "PASS" in content
    assert "TESTACPSCRIPT" in content and "NIL" in content
    assert "ENTRY_POINT_MATCH" in content and "FAIL" in content
    assert "PLANT3D_VALIDATED" not in content.replace("NO PLANT3D_VALIDATED", "")


# --- package builder ------------------------------------------------------


def test_deployment_package_produces_expected_files(golden, tmp_path):
    params, geometry, registration = golden
    package = build_deployment_package(params, geometry, registration, tmp_path / "HDPE_SEGMENTED_ELBOW")

    names = {f.name for f in package.files}
    assert "HDPE_SEGMENTED_ELBOW.py" in names
    assert "golden_case.json" in names
    assert "validation_manifest.json" in names
    assert "README_PLANT3D.md" in names
    for f in package.files:
        assert f.is_file()
        assert f.stat().st_size > 0


def test_deployment_package_script_is_valid_python(golden, tmp_path):
    params, geometry, registration = golden
    package = build_deployment_package(params, geometry, registration, tmp_path / "HDPE_SEGMENTED_ELBOW")
    script_path = next(f for f in package.files if f.name == "HDPE_SEGMENTED_ELBOW.py")
    ast.parse(script_path.read_text(encoding="utf-8"))


def test_deployment_package_golden_case_json_matches_published_values(golden, tmp_path):
    params, geometry, registration = golden
    package = build_deployment_package(params, geometry, registration, tmp_path / "HDPE_SEGMENTED_ELBOW")
    golden_case_path = next(f for f in package.files if f.name == "golden_case.json")
    payload = json.loads(golden_case_path.read_text(encoding="utf-8"))
    component = payload["component"]
    assert component["dn_mm"] == 110
    assert component["radius_mm"] == 165
    assert component["z_mm"] == 315


def test_deployment_package_manifest_starts_at_generated(golden, tmp_path):
    params, geometry, registration = golden
    package = build_deployment_package(params, geometry, registration, tmp_path / "HDPE_SEGMENTED_ELBOW")
    manifest_path = next(f for f in package.files if f.name == "validation_manifest.json")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["current_stage"] == "GENERATED"
    assert payload["package_status"] == PACKAGE_STATUS_READY_FOR_VALIDATION


def test_deployment_package_never_writes_proprietary_plant_files(golden, tmp_path):
    params, geometry, registration = golden
    package = build_deployment_package(params, geometry, registration, tmp_path / "HDPE_SEGMENTED_ELBOW")
    for f in package.files:
        assert f.suffix.lower() not in (".pcat", ".pspx", ".pspc")


def test_deployment_package_is_deterministic_across_two_output_dirs(golden, tmp_path):
    params, geometry, registration = golden
    package_a = build_deployment_package(params, geometry, registration, tmp_path / "a" / "HDPE_SEGMENTED_ELBOW")
    package_b = build_deployment_package(params, geometry, registration, tmp_path / "b" / "HDPE_SEGMENTED_ELBOW")
    script_a = next(f for f in package_a.files if f.name == "HDPE_SEGMENTED_ELBOW.py").read_text(encoding="utf-8")
    script_b = next(f for f in package_b.files if f.name == "HDPE_SEGMENTED_ELBOW.py").read_text(encoding="utf-8")
    assert script_a == script_b


# --- catalog builder excel exporter ---------------------------------------


def test_catalog_builder_payload_matches_golden_case(golden):
    params, geometry, _registration = golden
    payload = build_catalog_builder_payload(params, geometry)
    assert payload["status"] == REFERENCE_TEMPLATE_REQUIRED
    assert payload["dn_mm"] == 110
    assert payload["radius_mm"] == 165
    assert payload["z_mm"] == 315


def test_excel_exporter_has_no_reference_template_by_default(tmp_path):
    exporter = CatalogBuilderExcelExporter(reference_template_dir=tmp_path)
    assert exporter.has_reference_template() is False


def test_excel_exporter_raises_without_reference_template(golden, tmp_path):
    params, geometry, _registration = golden
    exporter = CatalogBuilderExcelExporter(reference_template_dir=tmp_path)
    with pytest.raises(ReferenceTemplateRequiredError):
        exporter.export_to_excel(params, geometry, tmp_path / "out.xlsx")


def test_excel_exporter_detects_a_real_template_once_present(tmp_path):
    (tmp_path / "catalog_builder_export.xlsx").write_bytes(b"placeholder")
    exporter = CatalogBuilderExcelExporter(reference_template_dir=tmp_path)
    assert exporter.has_reference_template() is True


def test_repo_ships_no_real_catalog_builder_template_yet():
    """Guards the REFERENCE_TEMPLATE_REQUIRED gate: nobody has added a
    real Catalog Builder export to the repo, so the exporter must still
    refuse to run against the actual shipped templates/reference/."""
    exporter = CatalogBuilderExcelExporter()
    assert exporter.has_reference_template() is False
