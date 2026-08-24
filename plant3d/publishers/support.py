"""Future publisher for pipe supports — placeholder.

Planned pipeline (not implemented):

    SupportFamilyDefinition -> SupportPublisher.publish()
        -> Plant 3D Support Catalog -> PipeSupportsSpec -> AutoCAD Plant 3D
"""

from __future__ import annotations

from typing import Any

from plant3d.publishers.base import ComponentPublisher, PublishResult, not_implemented_result


class SupportPublisher(ComponentPublisher):
    def publish(self, support_definition: Any) -> PublishResult:
        return not_implemented_result("support")
