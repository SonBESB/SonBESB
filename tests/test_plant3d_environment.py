"""V0.3 tests for plant3d/environment/ — config loading and detection.

These tests run on this project's actual Linux sandbox, which has no
AutoCAD Plant 3D installed. They verify the detector is honest about that
(detected=False, source="NOT_DETECTED") and that a manual config-file
override is applied correctly, including the Windows-path derivation bug
fixed during V0.3 (pathlib mixing "/" into "\\"-style paths on Linux).
"""

from pathlib import Path

import pytest

from plant3d.environment.config import Plant3DConfig, load_config
from plant3d.environment.detector import (
    KNOWN_DOCUMENTED_VERSIONS,
    detect_plant3d_environment,
)


def test_load_config_returns_none_when_file_absent(tmp_path):
    assert load_config(tmp_path / "does_not_exist.yaml") is None


def test_load_config_parses_real_yaml(tmp_path):
    config_path = tmp_path / "plant3d_config.yaml"
    config_path.write_text(
        "plant3d:\n"
        "  version: \"2024\"\n"
        "  shared_content: \"C:\\\\AutoCAD Plant 3D 2024 Content\"\n",
        encoding="utf-8",
    )
    config = load_config(config_path)
    assert config == Plant3DConfig(version="2024", shared_content=r"C:\AutoCAD Plant 3D 2024 Content")


def test_detect_without_config_on_this_sandbox_is_honestly_not_detected():
    """This sandbox is Linux with no Plant 3D installed: detection must
    never claim otherwise."""
    info = detect_plant3d_environment(config_path=Path("/nonexistent/plant3d_config.yaml"))
    assert info.detected is False
    assert info.source == "NOT_DETECTED"
    assert info.shared_content_path is None
    assert len(info.candidates_checked) == 12  # 2 drive roots x 6 candidate versions


def test_detect_with_config_file_override(tmp_path):
    config_path = tmp_path / "plant3d_config.yaml"
    config_path.write_text(
        "plant3d:\n"
        "  version: \"2024\"\n"
        "  shared_content: \"C:\\\\AutoCAD Plant 3D 2024 Content\"\n",
        encoding="utf-8",
    )
    info = detect_plant3d_environment(config_path=config_path)
    assert info.detected is True
    assert info.source == "CONFIG_FILE"
    assert info.version == "2024"
    assert info.version_documented is True


def test_derived_subpaths_use_only_windows_separators(tmp_path):
    """Regression guard: _derive_subpaths must never mix '/' into these
    paths, even when this code runs on a Linux/macOS host."""
    config_path = tmp_path / "plant3d_config.yaml"
    config_path.write_text(
        "plant3d:\n"
        "  shared_content: \"C:\\\\AutoCAD Plant 3D 2024 Content\"\n",
        encoding="utf-8",
    )
    info = detect_plant3d_environment(config_path=config_path)
    for path in (info.custom_scripts_path, info.catalog_path, info.specs_path, info.sdk_path):
        assert path is not None
        assert "/" not in path
    assert info.custom_scripts_path == r"C:\AutoCAD Plant 3D 2024 Content\CPak Common\CustomScripts"
    assert info.catalog_path == r"C:\AutoCAD Plant 3D 2024 Content\Catalogs"
    assert info.specs_path == r"C:\AutoCAD Plant 3D 2024 Content\Specs"
    assert info.sdk_path == r"C:\AutoCAD Plant 3D 2024 Content\SDK"


def test_unsupported_plant_version_is_flagged_not_documented(tmp_path):
    """A version outside KNOWN_DOCUMENTED_VERSIONS must be reported as
    version_documented=False, never silently treated as supported."""
    config_path = tmp_path / "plant3d_config.yaml"
    config_path.write_text(
        "plant3d:\n"
        "  version: \"2018\"\n"
        "  shared_content: \"C:\\\\AutoCAD Plant 3D 2018 Content\"\n",
        encoding="utf-8",
    )
    info = detect_plant3d_environment(config_path=config_path)
    assert info.version == "2018"
    assert "2018" not in KNOWN_DOCUMENTED_VERSIONS
    assert info.version_documented is False


def test_explicit_subpaths_in_config_are_respected_over_derived_ones(tmp_path):
    config_path = tmp_path / "plant3d_config.yaml"
    config_path.write_text(
        "plant3d:\n"
        "  shared_content: \"C:\\\\AutoCAD Plant 3D 2024 Content\"\n"
        "  custom_scripts: \"D:\\\\Custom\\\\Scripts\"\n",
        encoding="utf-8",
    )
    info = detect_plant3d_environment(config_path=config_path)
    assert info.custom_scripts_path == r"D:\Custom\Scripts"
    # Non-overridden subpaths still get correctly derived.
    assert info.catalog_path == r"C:\AutoCAD Plant 3D 2024 Content\Catalogs"


def test_missing_plant_environment_has_no_paths_at_all():
    info = detect_plant3d_environment(config_path=Path("/nonexistent/plant3d_config.yaml"))
    assert info.custom_scripts_path is None
    assert info.catalog_path is None
    assert info.specs_path is None
    assert info.sdk_path is None
    assert info.version is None
