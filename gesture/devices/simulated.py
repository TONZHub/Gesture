"""The on-screen Barnaby.

Every event published here is streamed to the browser over SSE, where the SVG
Barnaby shakes, changes face, and lights the room. This is the default device
and it is a real one — plenty of users will never buy hardware, and the
grounding effect of "something is moving and I have to touch it to stop it"
survives being on a screen, if not as well.
"""

from __future__ import annotations

import logging

from .base import BarnabyDevice, DeviceEvent
from .bus import bus

log = logging.getLogger("gesture.device.simulated")


class SimulatedBarnaby(BarnabyDevice):
    name = "simulated"

    def __init__(self) -> None:
        self.jiggling = False
        self.expression = "soft"
        self.scene = "off"

    def jiggle(self, reason: str, intensity: float = 0.6) -> None:
        self.jiggling = True
        bus.publish(
            DeviceEvent(
                "jiggle", {"reason": reason, "intensity": round(intensity, 2)}
            )
        )
        log.debug("jiggle (%s)", reason)

    def still(self) -> None:
        self.jiggling = False
        bus.publish(DeviceEvent("still", {}))

    def face(self, expression: str) -> None:
        self.expression = expression
        bus.publish(DeviceEvent("face", {"expression": expression}))

    def project(self, scene: str) -> None:
        self.scene = scene
        bus.publish(DeviceEvent("project", {"scene": scene}))

    def celebrate(self) -> None:
        bus.publish(DeviceEvent("celebrate", {}))

    def pet(self) -> None:
        bus.publish(DeviceEvent("pet", {}))
        super().pet()
