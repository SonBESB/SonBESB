import pytest

from components.elbows.hdpe_segmented_elbow import build_custom
from core.library.elbow_registration import ComplianceStatus, register_hdpe_segmented_elbow
from core.library.provenance import DataProvenance, SourceType
from core.models.common import EndType
from core.serialization.json_export import elbow_to_dict
from data.repository import ElbowRepository
from data_sources.registry import REGISTERED_SOURCES, DataSourceStatus, get_data_source
from tests.golden_cases import GOLDEN_CASE_DN110_PN10_90


def test_data_provenance_model_fields():
    provenance = DataProvenance(
        document="Catalogo HDPE 2(1).pdf",
        section="6.1",
        table="6.1.1",
        standard_reference="DIN 16963 Part 1",
        source_type=SourceType.MANUFACTURER_CATALOG,
    )
    assert provenance.document == "Catalogo HDPE 2(1).pdf"
    assert provenance.document_revision is None  # optional field, not guessed


def test_normalized_elbow_carries_hdpe_catalog_provenance():
    repository = ElbowRepository.from_excel()
    result = repository.lookup(**GOLDEN_CASE_DN110_PN10_90)
    registration = register_hdpe_segmented_elbow(result.elbow, geometry=None)

    assert registration.provenance is not None
    assert registration.provenance.document == "Catalogo HDPE 2(1).pdf"
    assert registration.provenance.section == "6.1"
    assert registration.provenance.standard_reference == "DIN 16963 Part 1"
    assert registration.provenance.source_type is SourceType.MANUFACTURER_CATALOG


def test_custom_mode_has_no_norm_and_is_not_certified():
    params, issues = build_custom(
        od_mm=630.0, thickness_mm=37.4, angle_deg=73.0, radius_mm=900.0, le_mm=350.0, end_type=EndType.BUTT_FUSION,
    )
    registration = register_hdpe_segmented_elbow(params, geometry=None)

    assert registration.standard.key == "CUSTOM"
    assert registration.compliance_status is ComplianceStatus.NOT_CERTIFIED
    assert registration.provenance is None  # nothing to attribute a custom geometry to


def test_provenance_reaches_the_json_export():
    repository = ElbowRepository.from_excel()
    result = repository.lookup(**GOLDEN_CASE_DN110_PN10_90)
    registration = register_hdpe_segmented_elbow(result.elbow, geometry=None)
    payload = elbow_to_dict(result.elbow, registration=registration)

    provenance = payload["component"]["provenance"]
    assert provenance["document"] == "Catalogo HDPE 2(1).pdf"
    assert provenance["table"] == "6.1.1"


def test_reference_sources_distinguish_registration_and_partial_transcription():
    keys = {s.key for s in REGISTERED_SOURCES}
    assert keys == {"hdpe_catalog", "codelco_support_standard", "hipogeno_support_standard", "pexgol_catalog"}

    assert get_data_source("pexgol_catalog").status is DataSourceStatus.PARTIALLY_DIGITIZED
    assert get_data_source("hdpe_catalog").status is DataSourceStatus.PARTIALLY_DIGITIZED
    assert get_data_source("codelco_support_standard").status is DataSourceStatus.REGISTERED_NOT_DIGITIZED
    assert get_data_source("hipogeno_support_standard").status is DataSourceStatus.REGISTERED_NOT_DIGITIZED


def test_unknown_data_source_key_raises():
    with pytest.raises(KeyError):
        get_data_source("not_a_registered_source")
