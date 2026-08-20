"""The device event bus.

Unit-level, not through the SSE endpoint: the endpoint's generator loops
forever by design (polling every 0.25s for as long as a tab is open), which
makes it a bad fit for a synchronous test run. The fan-out logic underneath
it -- publish, subscribe, drain, unsubscribe, and the slow-subscriber
overflow guard -- is what actually has behaviour worth pinning down.
"""

from __future__ import annotations

from gesture.devices.base import DeviceEvent
from gesture.devices.bus import MAX_QUEUED, EventBus


def _event(kind: str = "jiggle") -> DeviceEvent:
    return DeviceEvent(kind=kind, payload={"kind": kind})


def test_a_fresh_subscriber_gets_nothing_until_something_is_published():
    bus = EventBus()
    q = bus.subscribe()
    assert list(bus.drain(q)) == []


def test_published_events_reach_every_live_subscriber():
    bus = EventBus()
    a, b = bus.subscribe(), bus.subscribe()
    bus.publish(_event("jiggle"))

    assert [e.kind for e in bus.drain(a)] == ["jiggle"]
    assert [e.kind for e in bus.drain(b)] == ["jiggle"]


def test_drain_empties_the_queue_so_the_same_event_is_not_seen_twice():
    bus = EventBus()
    q = bus.subscribe()
    bus.publish(_event())

    assert len(list(bus.drain(q))) == 1
    assert list(bus.drain(q)) == []


def test_unsubscribe_stops_further_delivery():
    bus = EventBus()
    q = bus.subscribe()
    bus.unsubscribe(q)
    bus.publish(_event())

    assert list(bus.drain(q)) == []


def test_unsubscribing_twice_is_harmless():
    bus = EventBus()
    q = bus.subscribe()
    bus.unsubscribe(q)
    bus.unsubscribe(q)  # must not raise


def test_a_slow_subscriber_drops_its_oldest_event_instead_of_growing_forever():
    """A tab left open in the background must never wedge the device by
    backing up an unbounded queue -- it should just miss old events."""
    bus = EventBus()
    q = bus.subscribe()
    for i in range(MAX_QUEUED + 5):
        bus.publish(_event(str(i)))

    drained = list(bus.drain(q))
    assert len(drained) == MAX_QUEUED
    # The oldest events were the ones dropped; the newest survive.
    assert drained[-1].kind == str(MAX_QUEUED + 4)


def test_last_tracks_the_most_recent_event_regardless_of_subscribers():
    bus = EventBus()
    assert bus.last is None
    bus.publish(_event("still"))
    assert bus.last.kind == "still"
