"""Future publisher for equipment (pumps, tanks, etc.) — placeholder.

No equipment family is modeled anywhere in this project yet (see
core/library/component_family.py's GENERIC_EQUIPMENT entry). This exists
only to complete the publisher contract shape ahead of that work.
"""

from __future__ import annotations

from typing import Any

from plant3d.publishers.base import ComponentPublisher, PublishResult, not_implemented_result


class EquipmentPublisher(ComponentPublisher):
    def publish(self, equipment_definition: Any) -> PublishResult:
        return not_implemented_result("equipment")
