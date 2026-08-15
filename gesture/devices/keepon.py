"""The physical Barnaby — a hacked My Keepon.

Hardware, per the spec: My Keepon base (round, soft, dark too-big eyes,
whiskers) plus a vibration motor for the jiggle, a capacitive touch sensor so
petting him stops it, a galaxy projector for the environment shift, and a
handmade purple jester collar. Arduino in the middle, USB serial to the host.

The unit is in transit (arriving 18–21 Aug), so this class is written against
the wire protocol rather than against a device that exists yet. It degrades
without drama: if pyserial is missing, or the port is absent, or the board
stops answering mid-session, Barnaby keeps working on screen and nothing the
user is doing breaks. Hardware failing should never take the software with it.

Wire protocol (newline-delimited ASCII, 115200 baud) — mirrored in
`hardware/barnaby_firmware.ino`:

    host -> board          board -> host
    J <intensity 0-255>    PET        capacitive sensor triggered
    S                      READY      boot handshake
    F <expression>
    P <scene>
    C
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .base import BarnabyDevice, DeviceEvent
from .bus import bus

log = logging.getLogger("gesture.device.keepon")

_FACE_CODES = {
    "soft": "0",
    "worried": "1",
    "relieved": "2",
    "delighted": "3",
    "listening": "4",
}

_SCENE_CODES = {
    "off": "0",
    "dim": "1",
    "overture": "2",
    "focus": "3",
    "break": "4",
    "curtain": "5",
}


class KeeponBarnaby(BarnabyDevice):
    name = "keepon"

    def __init__(self, port: str, baud: int = 115200) -> None:
        self.port = port
        self.baud = baud
        self.jiggling = False
        self.expression = "soft"
        self.scene = "off"
        self._serial: Optional[Any] = None
        self._dead = False
        self._connect()

    def _connect(self) -> None:
        try:
            import serial  # pyserial, optional extra

            self._serial = serial.Serial(self.port, self.baud, timeout=1)
            log.info("Barnaby connected on %s", self.port)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "No physical Barnaby on %s (%s) — running on screen only",
                self.port,
                exc,
            )
            self._serial = None
            self._dead = True

    def _send(self, line: str) -> None:
        if self._serial is None or self._dead:
            return
        try:
            self._serial.write((line + "\n").encode("ascii"))
        except Exception as exc:  # noqa: BLE001
            # One failure is enough; stop poking a board that has gone away.
            log.warning("Barnaby went quiet on %s (%s)", self.port, exc)
            self._dead = True

    # ------------------------------------------------------------------
    # Every command also goes to the bus, so the on-screen Barnaby stays in
    # sync with the physical one. That is what makes the demo video work:
    # the seal on the desk and the seal on the laptop move together.
    # ------------------------------------------------------------------

    def jiggle(self, reason: str, intensity: float = 0.6) -> None:
        self.jiggling = True
        self._send(f"J {int(max(0.0, min(intensity, 1.0)) * 255)}")
        bus.publish(DeviceEvent("jiggle", {"reason": reason, "intensity": intensity}))

    def still(self) -> None:
        self.jiggling = False
        self._send("S")
        bus.publish(DeviceEvent("still", {}))

    def face(self, expression: str) -> None:
        self.expression = expression
        self._send(f"F {_FACE_CODES.get(expression, '0')}")
        bus.publish(DeviceEvent("face", {"expression": expression}))

    def project(self, scene: str) -> None:
        self.scene = scene
        self._send(f"P {_SCENE_CODES.get(scene, '0')}")
        bus.publish(DeviceEvent("project", {"scene": scene}))

    def celebrate(self) -> None:
        self._send("C")
        bus.publish(DeviceEvent("celebrate", {}))

    def poll(self) -> None:
        """Read pending board messages. `PET` means a hand landed on Barnaby.

        Called from the app's background tick — the physical touch and the
        on-screen pet button are the same event as far as everything upstream
        is concerned.
        """
        if self._serial is None or self._dead:
            return
        try:
            while self._serial.in_waiting:
                line = self._serial.readline().decode("ascii", "ignore").strip()
                if line == "PET":
                    self.pet()
        except Exception as exc:  # noqa: BLE001
            log.warning("Lost Barnaby while reading (%s)", exc)
            self._dead = True

    def pet(self) -> None:
        bus.publish(DeviceEvent("pet", {}))
        super().pet()
