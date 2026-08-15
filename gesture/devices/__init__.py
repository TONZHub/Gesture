"""Barnaby's body.

The physical Barnaby (a hacked My Keepon with a vibration motor, a touch
sensor and a projector) ships mid-hackathon. The software cannot wait for a
parcel, and the demo must not depend on one, so everything talks to
`BarnabyDevice` and the transport is a config flag.

    GESTURE_DEVICE=simulated   on-screen Barnaby (default, always works)
    GESTURE_DEVICE=keepon      the real unit over serial

Both emit the same events, so the browser Barnaby jiggles whether or not
there is a seal on the desk.
"""

from __future__ import annotations

from ..config import settings
from .base import BarnabyDevice, DeviceEvent
from .bus import bus
from .simulated import SimulatedBarnaby

_device: BarnabyDevice | None = None


def get_device() -> BarnabyDevice:
    global _device
    if _device is None:
        if settings.device == "keepon":
            from .keepon import KeeponBarnaby

            _device = KeeponBarnaby(settings.keepon_port)
        else:
            _device = SimulatedBarnaby()
    return _device


__all__ = ["BarnabyDevice", "DeviceEvent", "bus", "get_device", "SimulatedBarnaby"]
