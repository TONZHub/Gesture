"""A tiny fan-out bus for device events.

Device methods are called from sync request handlers running in FastAPI's
threadpool; the SSE endpoint consumes from the async loop. Rather than thread
an event loop reference through the device layer, each subscriber gets a plain
deque behind a lock and the SSE generator polls it. Unglamorous, but it has no
cross-thread failure modes at all, which is the correct trade for a demo that
has to work on someone else's laptop.
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Iterator

from .base import DeviceEvent

MAX_QUEUED = 64


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[deque[DeviceEvent]] = []
        self._last: DeviceEvent | None = None

    def publish(self, event: DeviceEvent) -> None:
        with self._lock:
            self._last = event
            for q in self._subscribers:
                if len(q) >= MAX_QUEUED:
                    q.popleft()  # a slow tab should never wedge the device
                q.append(event)

    def subscribe(self) -> deque[DeviceEvent]:
        q: deque[DeviceEvent] = deque()
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: deque[DeviceEvent]) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def drain(self, q: deque[DeviceEvent]) -> Iterator[DeviceEvent]:
        with self._lock:
            while q:
                yield q.popleft()

    @property
    def last(self) -> DeviceEvent | None:
        return self._last


bus = EventBus()
