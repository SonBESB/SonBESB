import pytest

from core.geometry.engineering_report import OverallDimensions
from core.validation.reference_comparison import (
    FIELD_HYPOTHESIS_NOTES,
    OVERALL_FIELD_LABELS,
    ComparisonStatus,
    ReferenceMeasurement,
    all_rows_pass,
    compare_gajo_lengths,
    compare_overall_dimensions,
    has_any_reference_value,
)

GOLDEN_OVERALL = OverallDimensions(
    width_mm=930.5,
    height_mm=315.0,
    length_mm=930.5,
    p1_p2_distance_mm=1093.1870837144024,
    p1_to_vertex_mm=773.0,
    p2_to_vertex_mm=773.0,
    radius_used_mm=473.0,
    z_resultant_mm=773.0,
)


def test_exact_match_is_pass_with_zero_difference():
    reference = ReferenceMeasurement(z_resultant_mm=773.0, radius_used_mm=473.0)
    rows = compare_overall_dimensions(GOLDEN_OVERALL, reference, tolerance_mm=1.0)

    assert len(rows) == 2
    for row in rows:
        assert row.status is ComparisonStatus.PASS
        assert row.abs_diff_mm == 0.0
        assert row.pct_diff == 0.0


def test_deviation_within_tolerance_passes():
    reference = ReferenceMeasurement(z_resultant_mm=773.8)
    rows = compare_overall_dimensions(GOLDEN_OVERALL, reference, tolerance_mm=1.0)

    assert rows[0].status is ComparisonStatus.PASS
    assert rows[0].abs_diff_mm == pytest.approx(0.8)


def test_deviation_beyond_tolerance_fails_with_correct_diffs():
    reference = ReferenceMeasurement(z_resultant_mm=783.0)  # +10mm
    rows = compare_overall_dimensions(GOLDEN_OVERALL, reference, tolerance_mm=1.0)

    assert rows[0].status is ComparisonStatus.FAIL
    assert rows[0].abs_diff_mm == 10.0
    assert rows[0].pct_diff == (10.0 / 783.0 * 100)


def test_never_adjusts_the_parametric_value():
    """The comparison must be read-only: parametric_value_mm always equals
    the input GOLDEN_OVERALL field, regardless of the reference or result."""
    reference = ReferenceMeasurement(z_resultant_mm=900.0)
    rows = compare_overall_dimensions(GOLDEN_OVERALL, reference, tolerance_mm=1.0)
    assert rows[0].parametric_value_mm == GOLDEN_OVERALL.z_resultant_mm == 773.0


def test_unset_reference_fields_are_skipped_not_defaulted():
    reference = ReferenceMeasurement(z_resultant_mm=773.0)  # everything else None
    rows = compare_overall_dimensions(GOLDEN_OVERALL, reference, tolerance_mm=1.0)
    assert len(rows) == 1
    assert rows[0].field == "z_resultant_mm"


def test_every_overall_field_has_a_hypothesis_note():
    for field_key in OVERALL_FIELD_LABELS:
        assert field_key in FIELD_HYPOTHESIS_NOTES
        assert len(FIELD_HYPOTHESIS_NOTES[field_key]) > 10


def test_gajo_length_comparison_aligns_by_index_and_skips_none():
    parametric_lengths = [123.478, 244.843, 244.843, 123.478]
    reference = ReferenceMeasurement(gajo_axis_lengths_mm=[123.478, None, 300.0, 123.478])
    rows = compare_gajo_lengths(parametric_lengths, reference, tolerance_mm=1.0)

    assert len(rows) == 3  # index 1 (None) skipped
    labels = [r.label for r in rows]
    assert "Gajo 1" in labels[0]
    assert "Gajo 3" in labels[1]
    assert rows[1].status is ComparisonStatus.FAIL  # 244.843 vs 300.0
    assert rows[2].status is ComparisonStatus.PASS


def test_gajo_length_comparison_handles_shorter_reference_list():
    parametric_lengths = [123.478, 244.843, 244.843, 123.478]
    reference = ReferenceMeasurement(gajo_axis_lengths_mm=[123.478])
    rows = compare_gajo_lengths(parametric_lengths, reference, tolerance_mm=1.0)
    assert len(rows) == 1


def test_has_any_reference_value():
    assert has_any_reference_value(ReferenceMeasurement()) is False
    assert has_any_reference_value(ReferenceMeasurement(radius_used_mm=473.0)) is True
    assert has_any_reference_value(ReferenceMeasurement(gajo_axis_lengths_mm=[None, 100.0])) is True


def test_all_rows_pass():
    reference_pass = ReferenceMeasurement(z_resultant_mm=773.0)
    reference_fail = ReferenceMeasurement(z_resultant_mm=900.0)

    assert all_rows_pass(compare_overall_dimensions(GOLDEN_OVERALL, reference_pass, tolerance_mm=1.0)) is True
    assert all_rows_pass(compare_overall_dimensions(GOLDEN_OVERALL, reference_fail, tolerance_mm=1.0)) is False
    assert all_rows_pass([]) is False  # no comparison performed yet != validated
