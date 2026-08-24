"""Loads plant3d_config.yaml — the manual-override path for Plant 3D
environment settings.

Never required: detect_plant3d_environment() falls back to filesystem
probing when no config file exists. This exists purely so a user on a
real Plant 3D machine can point the tooling at their actual install
without editing source code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

DEFAULT_CONFIG_FILENAME = "plant3d_config.yaml"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / DEFAULT_CONFIG_FILENAME


@dataclass(frozen=True)
class Plant3DConfig:
    version: Optional[str] = None
    shared_content: Optional[str] = None
    custom_scripts: Optional[str] = None
    catalogs: Optional[str] = None
    specs: Optional[str] = None
    sdk: Optional[str] = None


def load_config(config_path: Optional[Path] = None) -> Optional[Plant3DConfig]:
    """Returns None (not an error) when no config file is present."""
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.is_file():
        return None

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    section = raw.get("plant3d", {}) or {}
    return Plant3DConfig(
        version=str(section["version"]) if section.get("version") is not None else None,
        shared_content=section.get("shared_content"),
        custom_scripts=section.get("custom_scripts"),
        catalogs=section.get("catalogs"),
        specs=section.get("specs"),
        sdk=section.get("sdk"),
    )
