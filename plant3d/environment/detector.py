"""Detects (or accepts manual configuration of) a local AutoCAD Plant 3D
installation.

Nothing here assumes Plant 3D is present. On any platform other than
Windows — which includes every environment this project has been
developed in so far, see docs/PLANT3D_ENVIRONMENT.md — detection always
reports `detected=False`, honestly, rather than guessing.

No single hardcoded path is trusted. `C:\\AutoCAD Plant 3D 2026 Content`
is only ever one candidate among several generated from a version range,
exactly as instructed (see docs/PLANT3D_ENVIRONMENT.md for the full
candidate-generation rule and its sources).
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from plant3d.environment.config import Plant3DConfig, load_config

# Versions for which an official PLANTREGISTERCUSTOMSCRIPTS help page was
# found during V0.3's source investigation (see docs/PLANT3D_ENVIRONMENT.md
# for the search results this list is drawn from). Not exhaustive — Plant
# 3D versions outside this list are not necessarily unsupported, just
# unconfirmed by a source this project actually checked.
KNOWN_DOCUMENTED_VERSIONS = ["2019", "2022", "2023", "2024", "2025"]

# Candidate content-folder name pattern cited by Autodesk's own
# documentation (folder literally named "CPak Common\CustomScripts" under
# a per-version "Content" directory). Only used to generate *candidates*
# to probe for existence — never assumed present.
_CANDIDATE_VERSIONS = ["2022", "2023", "2024", "2025", "2026", "2027"]
_CANDIDATE_DRIVE_ROOTS = [r"C:\\", r"D:\\"]


@dataclass(frozen=True)
class PlantEnvironmentInfo:
    detected: bool
    source: str  # "CONFIG_FILE" | "AUTO_DETECTED_CANDIDATE" | "NOT_DETECTED"
    version: Optional[str] = None
    version_documented: Optional[bool] = None
    shared_content_path: Optional[str] = None
    custom_scripts_path: Optional[str] = None
    catalog_path: Optional[str] = None
    specs_path: Optional[str] = None
    sdk_path: Optional[str] = None
    platform_name: str = platform.system()
    candidates_checked: List[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.candidates_checked is None:
            object.__setattr__(self, "candidates_checked", [])


def _candidate_shared_content_paths() -> List[str]:
    candidates = []
    for root in _CANDIDATE_DRIVE_ROOTS:
        for version in _CANDIDATE_VERSIONS:
            candidates.append(f"{root}AutoCAD Plant 3D {version} Content")
    return candidates


def _derive_subpaths(shared_content_path: str) -> dict:
    # Plain string joins on purpose: these are always Windows paths
    # (Plant 3D is Windows-only) regardless of the host OS this code
    # runs on, so pathlib.Path would mix in POSIX "/" separators when
    # developed/tested on Linux/macOS, as it did before this fix.
    base = shared_content_path.rstrip("\\/")
    return {
        "custom_scripts_path": f"{base}\\CPak Common\\CustomScripts",
        "catalog_path": f"{base}\\Catalogs",
        "specs_path": f"{base}\\Specs",
        "sdk_path": f"{base}\\SDK",
    }


def detect_plant3d_environment(config_path: Optional[Path] = None) -> PlantEnvironmentInfo:
    """Resolves Plant 3D environment info, config file first, then a
    best-effort filesystem probe. Never raises when nothing is found —
    that is itself a valid, expected result on non-Windows machines."""
    config: Optional[Plant3DConfig] = load_config(config_path)

    if config is not None and config.shared_content:
        derived = _derive_subpaths(config.shared_content)
        return PlantEnvironmentInfo(
            detected=True,
            source="CONFIG_FILE",
            version=config.version,
            version_documented=(config.version in KNOWN_DOCUMENTED_VERSIONS) if config.version else None,
            shared_content_path=config.shared_content,
            custom_scripts_path=config.custom_scripts or derived["custom_scripts_path"],
            catalog_path=config.catalogs or derived["catalog_path"],
            specs_path=config.specs or derived["specs_path"],
            sdk_path=config.sdk or derived["sdk_path"],
        )

    candidates = _candidate_shared_content_paths()
    if platform.system() == "Windows":
        for candidate in candidates:
            if Path(candidate).is_dir():
                derived = _derive_subpaths(candidate)
                version = candidate.split(" ")[-2] if " " in candidate else None
                return PlantEnvironmentInfo(
                    detected=True,
                    source="AUTO_DETECTED_CANDIDATE",
                    version=version,
                    version_documented=(version in KNOWN_DOCUMENTED_VERSIONS) if version else None,
                    shared_content_path=candidate,
                    candidates_checked=candidates,
                    **derived,
                )

    # Not Windows, or no candidate directory exists: honestly not detected.
    return PlantEnvironmentInfo(detected=False, source="NOT_DETECTED", candidates_checked=candidates)
