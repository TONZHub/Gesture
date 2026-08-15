"""The device contract.

Five verbs. Deliberately small — the hardware spec is ambitious (projector,
360° pan, SAM voice, screen face) but every one of those is a way of doing one
of these five things, and a narrow interface is what lets the Keepon land
mid-week without touching the agent layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DeviceEvent:
    kind: str  # jiggle | still | face | project | celebrate | pet
    payload: dict[str, Any] = field(default_factory=dict)


class BarnabyDevice(ABC):
    """A physical (or simulated) Barnaby."""

    name = "device"

    #: Current state, mirrored by every implementation.
    jiggling: bool = False
    expression: str = "soft"
    scene: str = "off"

    def state(self) -> dict[str, Any]:
        """A snapshot for clients that connect after an event was published.

        Events fan out only to subscribers present at publish time, so a tab
        that opens a moment after a check-in comes due would otherwise never
        see Barnaby shake — which is the one behaviour the whole product turns
        on. New listeners are handed this and catch up immediately.
        """
        return {
            "jiggling": self.jiggling,
            "expression": self.expression,
            "scene": self.scene,
        }

    @abstractmethod
    def jiggle(self, reason: str, intensity: float = 0.6) -> None:
        """Shake until touched.

        The intervention *is* the jiggle. A phone notification is invisible to
        a dissociated or hyperfocused brain; an object moving in peripheral
        vision is not. Requiring a physical touch to stop it forces the one
        thing that breaks the loop — coming back into your body.
        """

    @abstractmethod
    def still(self) -> None:
        """Stop. Called when the user pets him, or when the moment passes."""

    @abstractmethod
    def face(self, expression: str) -> None:
        """worried | relieved | soft | delighted | listening"""

    @abstractmethod
    def project(self, scene: str) -> None:
        """overture | focus | break | curtain | dim | off

        Quiet mode users get `off`. The environment shift is a regulation tool
        for sensory-seeking brains, and an intrusion for everyone else.
        """

    @abstractmethod
    def celebrate(self) -> None:
        """The small wiggle at the curtain call."""

    def pet(self) -> None:
        """The user touched Barnaby. Default behaviour: settle."""
        self.still()
        self.face("relieved")
