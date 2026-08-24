from core.models.common import ComponentMode, EndType
from core.models.elbow import ElbowParameters
from core.validation.elbow_validation import has_blocking_errors, validate_custom_elbow


def _base_params(**overrides) -> ElbowParameters:
    defaults = dict(
        mode=ComponentMode.CUSTOM,
        od_mm=630.0,
        thickness_mm=37.4,
        angle_deg=73.0,
        radius_mm=900.0,
        le_mm=350.0,
        z_mm=None,
        end_type=EndType.BUTT_FUSION,
        din16963_compliant=False,
    )
    defaults.update(overrides)
    return ElbowParameters(**defaults)


def test_valid_custom_elbow_has_no_errors():
    params = _base_params()
    assert validate_custom_elbow(params) == []


def test_negative_od_is_rejected():
    issues = validate_custom_elbow(_base_params(od_mm=-1.0))
    assert any(i.field == "od_mm" for i in issues)
    assert has_blocking_errors(issues)


def test_thickness_too_large_for_od_is_rejected():
    issues = validate_custom_elbow(_base_params(od_mm=50.0, thickness_mm=30.0))
    assert any(i.field == "thickness_mm" for i in issues)


def test_angle_out_of_range_is_rejected():
    issues = validate_custom_elbow(_base_params(angle_deg=180.0))
    assert any(i.field == "angle_deg" for i in issues)

    issues = validate_custom_elbow(_base_params(angle_deg=0.0))
    assert any(i.field == "angle_deg" for i in issues)


def test_non_positive_radius_and_le_are_rejected():
    issues = validate_custom_elbow(_base_params(radius_mm=0.0, le_mm=-5.0))
    fields = {i.field for i in issues}
    assert "radius_mm" in fields
    assert "le_mm" in fields
