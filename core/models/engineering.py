"""Placeholder for MODE C — ENGINEERING.

Not implemented in V0.1. This module exists only so the architecture has a
clear extension point: a future EngineeringElbowParameters would let a user
edit segment-by-segment angles, per-port EndType/orientation, and Plant 3D
placement fields directly, instead of deriving them from DN/PN/angle or from
the simplified custom-mode inputs.

Intentionally no logic lives here yet.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.models.elbow import ElbowParameters


@dataclass
class EngineeringElbowParameters(ElbowParameters):
    """Reserved for future per-segment / per-port advanced editing.

    TODO (post-V0.1): add explicit per-segment angle list independent of
    SegmentConfiguration inference, per-port orientation overrides, and
    Plant 3D-specific placement/property fields once that integration
    stage begins.
    """
