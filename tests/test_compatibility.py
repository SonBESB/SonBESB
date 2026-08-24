from core.compatibility.engine import CompatibilityStatus, check_compatibility


def test_hdpe_elbow_din16963_pe100_is_supported():
    result = check_compatibility("HDPE_SEGMENTED_ELBOW", "DIN_16963_1", "PE100")
    assert result.status is CompatibilityStatus.SUPPORTED
    assert result.engineering_invalid is False


def test_hdpe_elbow_asme_b16_9_is_not_available_but_not_engineering_invalid():
    """NOT_AVAILABLE_IN_LIBRARY must never be conflated with an
    engineering-invalid combination — it only means this codebase has no
    data/geometry loaded for it yet."""
    result = check_compatibility("HDPE_SEGMENTED_ELBOW", "ASME_B16_9", "PE100")
    assert result.status is CompatibilityStatus.NOT_AVAILABLE_IN_LIBRARY
    assert result.engineering_invalid is False
    assert "no significa" in result.message.lower() or "not" in result.message.lower()


def test_unregistered_family_key_is_unknown_not_unsupported():
    result = check_compatibility("SOMETHING_NOT_REGISTERED", "DIN_16963_1", "PE100")
    assert result.status is CompatibilityStatus.UNKNOWN_KEY


def test_unregistered_standard_key_is_unknown():
    result = check_compatibility("HDPE_SEGMENTED_ELBOW", "NOT_A_STANDARD", "PE100")
    assert result.status is CompatibilityStatus.UNKNOWN_KEY


def test_unregistered_material_key_is_unknown():
    result = check_compatibility("HDPE_SEGMENTED_ELBOW", "DIN_16963_1", "NOT_A_MATERIAL")
    assert result.status is CompatibilityStatus.UNKNOWN_KEY


def test_hdpe_elbow_din16963_pe80_is_not_available():
    """PE80 is a registered material, but only PE100 has an actually
    supported/tested combination — registration alone does not imply
    support."""
    result = check_compatibility("HDPE_SEGMENTED_ELBOW", "DIN_16963_1", "PE80")
    assert result.status is CompatibilityStatus.NOT_AVAILABLE_IN_LIBRARY
