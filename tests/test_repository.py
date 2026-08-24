import math

import pytest

from core.models.common import DataAvailability
from data.repository import ElbowRepository


@pytest.fixture(scope="module")
def repository() -> ElbowRepository:
    return ElbowRepository.from_excel()


def test_known_combination_matches_spec_example(repository: ElbowRepository):
    """DN315 / PN10 / 90° is the exact worked example from the project spec."""
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=90)

    assert result.status is DataAvailability.AVAILABLE
    e = result.elbow
    assert e.od_mm == 315
    assert e.thickness_mm == 18.7
    assert math.isclose(e.inside_diameter_mm, 277.6, rel_tol=1e-6)
    assert e.sdr == 17
    assert e.radius_mm == 473
    assert e.le_mm == 300
    assert e.z_mm == 773
    assert e.dn_equivalent_in == '12"'
    assert e.din16963_compliant is True


def test_unavailable_combination_is_reported_as_not_available(repository: ElbowRepository):
    """DN560 / PN20 is marked N/D in BD_PN; must never be fabricated."""
    result = repository.lookup(dn_mm=560, pn_label="PN20", angle_deg=90)

    assert result.status is DataAvailability.NOT_AVAILABLE
    assert result.elbow is None
    assert result.notes


def test_unknown_dn_is_not_available(repository: ElbowRepository):
    result = repository.lookup(dn_mm=999, pn_label="PN10", angle_deg=90)
    assert result.status is DataAvailability.NOT_AVAILABLE
    assert result.elbow is None


def test_30_degree_configuration_is_not_itemized(repository: ElbowRepository):
    """The 30° sheet only has descriptive prose; must not invent a breakdown."""
    result = repository.lookup(dn_mm=110, pn_label="PN10", angle_deg=30)

    config = result.elbow.segment_configuration
    assert config.is_itemized is False
    assert config.segment_angles_deg is None
    assert config.source_text


def test_90_degree_configuration_is_itemized_and_sums_to_total(repository: ElbowRepository):
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=90)

    config = result.elbow.segment_configuration
    assert config.is_itemized is True
    assert config.segment_angles_deg == [15.0, 30.0, 30.0, 15.0]
    assert sum(config.segment_angles_deg) == 90.0


def test_dn_above_din_scope_is_flagged_non_compliant(repository: ElbowRepository):
    """DN1400 has catalog data but is explicitly outside DIN 16963 scope."""
    result = repository.lookup(dn_mm=1400, pn_label="PN4", angle_deg=90)

    assert result.status is DataAvailability.AVAILABLE
    assert result.elbow.din16963_compliant is False
    assert any("DIN 16963" in note for note in result.elbow.notes)


def test_available_dn_pn_angle_lists_are_populated(repository: ElbowRepository):
    assert len(repository.available_dn_mm()) == 23
    assert set(repository.available_pn_labels()) == {"PN4", "PN6", "PN8", "PN10", "PN12,5", "PN16", "PN20"}
    assert repository.available_angles_deg() == [30, 45, 60, 90]
