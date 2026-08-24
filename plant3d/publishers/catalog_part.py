"""Future publisher for catalog parts (fittings, valves) — placeholder.

Planned pipeline (not implemented):

    ComponentRegistration + geometry -> CatalogPartPublisher.publish()
        -> Plant 3D CustomScript -> PLANTREGISTERCUSTOMSCRIPTS
        -> Catalog -> Spec -> AutoCAD Plant 3D
"""

from __future__ import annotations

from typing import Any, Optional

from plant3d.publishers.base import ComponentPublisher, PublishResult, not_implemented_result


class CatalogPartPublisher(ComponentPublisher):
    def publish(self, registration: Any, geometry: Optional[Any] = None) -> PublishResult:
        return not_implemented_result("catalog part")
