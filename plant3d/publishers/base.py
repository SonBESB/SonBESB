"""Abstract publisher contracts for the future Plant 3D integration stage.

Nothing here talks to AutoCAD Plant 3D. There is no Autodesk API import,
no invented decorator or class from the Plant 3D SDK, and no .pcat/.pspx/
.pspc file writer. Every concrete publish() call returns
PLANT3D_BACKEND_NOT_IMPLEMENTED until that stage actually begins and gets
built against real Plant 3D documentation/behavior — see
docs/PLANT3D_PUBLISHING_ARCHITECTURE.md.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class PublishResultStatus(str, Enum):
    NOT_IMPLEMENTED = "PLANT3D_BACKEND_NOT_IMPLEMENTED"


@dataclass(frozen=True)
class PublishResult:
    status: PublishResultStatus
    message: str


def not_implemented_result(component_kind: str) -> PublishResult:
    return PublishResult(
        status=PublishResultStatus.NOT_IMPLEMENTED,
        message=(
            f"Publicacion a AutoCAD Plant 3D para '{component_kind}' no esta implementada "
            "todavia (etapa V0.3+). Ningun archivo de Plant 3D fue generado ni modificado."
        ),
    )


class ComponentPublisher(ABC):
    """Base contract every concrete Plant 3D publisher will implement."""

    @abstractmethod
    def publish(self, *args: Any, **kwargs: Any) -> PublishResult:
        ...
