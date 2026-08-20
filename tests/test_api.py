"""End to end, through the HTTP surface, with the model switched off."""

from __future__ import annotations

import os

import pytest

from gesture.agent.acts import balls_for_capacity

os.environ["GESTURE_USE_STRANDS"] = "0"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("GESTURE_DB", str(tmp_path / "t.db"))
    # Tests drive the filming aids (bring a check-in due, reset, trip the
    # guard), so demo mode is on here. Production leaves it off.
    monkeypatch.setenv("GESTURE_DEMO", "1")

    from fastapi.testclient import TestClient

    from gesture import db
    from gesture.config import Settings

    import gesture.config as cfg

    cfg.settings = Settings.load()
    monkeypatch.setattr("gesture.db.settings", cfg.settings, raising=False)
    monkeypatch.setattr("gesture.api.settings", cfg.settings, raising=False)
    db.reset(tmp_path / "t.db")

    from gesture.main import app

    with TestClient(app) as c:
        yield c


def begin(client, **kw):
    payload = {
        "mode": "circus",
        "capacity": 50,
        "window_start": "00:01",
        "window_end": "23:59",
        "sleep_hours": 7.0,
        "acts": [
            {"kind": "hoops", "title": "email the landlord"},
            {"kind": "juggling", "title": "tidy one shelf"},
        ],
    }
    payload.update(kw)
    return client.post("/api/begin", json=payload)


def test_health(client):
    assert client.get("/health").json()["ok"] is True


# --- demo / filming aids --------------------------------------------------


def test_state_reports_demo_flag(client):
    assert client.get("/api/state").json()["demo"] is True


def test_demo_reset_reseeds_and_leaves_today_unbegun(client):
    r = client.post("/api/demo/reset")
    assert r.status_code == 200
    assert r.json()["seeded_days"] >= 4
    # A clean top-of-demo: history behind, but today not begun (Begin shows).
    assert client.get("/api/state").json()["day"]["began_at"] is None
    assert client.get("/api/window").json()["sky"]["lit_days"] >= 4


def test_demo_guard_trip_catches_the_model_live(client):
    from gesture.agent import guard

    r = client.post("/api/demo/guard-trip").json()
    assert r["blocked"] is True
    assert r["rules"]
    assert r["attempted"] != r["served"]
    assert guard.is_clean(r["served"])
    # and it lands in the voice log as a blocked line, for the on-screen proof
    log = client.get("/api/voice-log").json()["entries"]
    assert any(e["blocked"] for e in log)


def test_demo_endpoints_are_404_when_disabled(tmp_path, monkeypatch):
    """In production GESTURE_DEMO is off, so the reset (which wipes data) and
    the other aids must not exist — even if someone finds the route."""
    monkeypatch.setenv("GESTURE_DB", str(tmp_path / "off.db"))
    monkeypatch.setenv("GESTURE_DEMO", "0")
    monkeypatch.setenv("GESTURE_USE_STRANDS", "0")

    from fastapi.testclient import TestClient

    from gesture import db
    from gesture.config import Settings

    import gesture.config as cfg

    cfg.settings = Settings.load()
    monkeypatch.setattr("gesture.db.settings", cfg.settings, raising=False)
    monkeypatch.setattr("gesture.api.settings", cfg.settings, raising=False)
    db.reset(tmp_path / "off.db")

    from gesture.main import app

    with TestClient(app) as c:
        assert c.get("/api/state").json()["demo"] is False
        assert c.post("/api/demo/reset").status_code == 404
        assert c.post("/api/demo/guard-trip").status_code == 404
        assert c.post("/api/demo/due-now").status_code == 404


def test_begin_shapes_the_day(client):
    r = begin(client)
    assert r.status_code == 200
    body = r.json()
    assert body["barnaby"]["text"]
    assert body["in_play"]
    assert body["rhythm"]["interval_minutes"] > 0


def test_zero_capacity_schedules_nothing(client):
    """Booking check-ins for someone who said they have nothing left is the
    exact behaviour this app exists to not have."""
    begin(client, capacity=0)
    assert client.get("/api/state").json()["next_checkin_at"] is None


def test_checkin_not_due_reports_next_scheduled_time(client):
    """The common poll state: nothing waiting, but a time to show for it."""
    begin(client)
    r = client.get("/api/checkin").json()
    assert r["due"] is False
    assert r["next_at"] is not None


def test_capacity_endpoint_updates_the_day(client):
    begin(client, capacity=50)
    r = client.post("/api/capacity/20").json()
    assert r["balls"] == balls_for_capacity(20)
    assert client.get("/api/state").json()["day"]["capacity"] == 20


def test_capacity_endpoint_rejects_out_of_range_values(client):
    begin(client, capacity=50)
    for bad in (-1, 101):
        r = client.post(f"/api/capacity/{bad}")
        assert r.status_code == 422
    # Rejected values must not have touched the stored day.
    assert client.get("/api/state").json()["day"]["capacity"] == 50


def test_full_checkin_loop_adapts(client):
    begin(client)
    intervals = []
    for _ in range(3):
        client.post("/api/demo/due-now")
        assert client.get("/api/checkin").json()["due"] is True
        r = client.post("/api/checkin", json={"dismissed": True}).json()
        intervals.append(r["rhythm"]["interval_minutes"])
    assert intervals == sorted(intervals)
    assert intervals[-1] > intervals[0]


def test_answering_resets_the_backoff(client):
    begin(client)
    for _ in range(3):
        client.post("/api/demo/due-now")
        client.get("/api/checkin")
        client.post("/api/checkin", json={"dismissed": True})

    client.post("/api/demo/due-now")
    client.get("/api/checkin")
    r = client.post(
        "/api/checkin", json={"dismissed": False, "mood": 4, "water": 1}
    ).json()
    assert r["rhythm"]["dismiss_streak"] == 0


def test_responding_without_a_pending_checkin_is_a_conflict(client):
    begin(client)
    assert client.post("/api/checkin", json={"dismissed": True}).status_code == 409


def test_stuck_returns_a_gesture_not_a_lecture(client):
    begin(client)
    r = client.post(
        "/api/stuck", json={"anchor": "cant_start", "text": "cannot open email"}
    ).json()

    from gesture.agent import guard

    assert guard.is_clean(r["text"])
    assert len(r["text"]) < 700


def test_zero_capacity_anchor_clears_the_day(client):
    begin(client, capacity=80)
    client.post("/api/stuck", json={"anchor": "zero_capacity"})
    s = client.get("/api/state").json()
    assert s["day"]["capacity"] == 0
    assert s["in_play"] == []


def test_acts_can_be_completed(client):
    begin(client)
    act_id = client.get("/api/state").json()["in_play"][0]["id"]
    r = client.patch(f"/api/acts/{act_id}", json={"done": True}).json()
    all_acts = r["in_play"] + r["held"]
    assert any(a["id"] == act_id and a["done"] for a in all_acts) or not any(
        a["id"] == act_id for a in all_acts
    )


def test_window_renders_even_on_an_empty_week(client):
    w = client.get("/api/window?days=7").json()
    assert w["sky"]["band"] in {"unlit", "three_am", "predawn", "magic_hour", "dawn"}
    assert len(w["sky"]["days"]) == 7
    assert w["patterns"] == []


def test_curtain_call_has_no_denominator(client):
    """No '3 of 7'. Anywhere. Ever."""
    import re

    begin(client)
    act_id = client.get("/api/state").json()["in_play"][0]["id"]
    client.patch(f"/api/acts/{act_id}", json={"done": True})
    r = client.post("/api/curtain").json()

    joined = " ".join(r["lines"]) + " " + r["barnaby"]["text"]
    assert not re.search(r"\d+\s*(?:/|of)\s*\d+", joined), joined

    from gesture.agent import guard

    assert guard.is_clean(joined)


def test_curtain_call_does_not_tell_the_day_twice(client):
    """The recap renders as its own list, so the spoken bow must not repeat
    it — otherwise the user reads their whole day over again."""
    begin(client)
    for act in client.get("/api/state").json()["in_play"]:
        client.patch(f"/api/acts/{act['id']}", json={"done": True})
    r = client.post("/api/curtain").json()

    assert r["lines"]
    for line in r["lines"]:
        assert line not in r["barnaby"]["text"]


def test_curtain_recap_introduces_titles_with_a_colon(client):
    """User-written titles are fragments; dropped mid-sentence they produce
    'You let go of close the tab I keep reopening.'"""
    begin(
        client,
        acts=[{"kind": "trapeze", "title": "close the tab I keep reopening"}],
    )
    act = client.get("/api/state").json()["in_play"][0]
    client.patch(f"/api/acts/{act['id']}", json={"done": True})
    line = client.post("/api/curtain").json()["lines"][0]
    assert ": close the tab I keep reopening" in line


def test_curtain_call_on_a_day_with_nothing_done(client):
    begin(client, acts=[], capacity=0)
    r = client.post("/api/curtain").json()
    assert r["zero_capacity"] is True
    assert r["barnaby"]["text"]


def test_mode_switch(client):
    assert client.post("/api/mode/quiet").json()["mode"] == "quiet"
    assert client.get("/api/state").json()["day"]["mode"] == "quiet"


def test_door_choice_survives_before_begin(client):
    """Regression: the door is answered before Begin, so on a fresh day there
    was no row to update and the answer was dropped. Quiet-mode users would
    have been handed the circus."""
    client.post("/api/mode/quiet")
    assert client.get("/api/state").json()["day"]["mode"] == "quiet"

    body = begin(client, mode="quiet").json()
    assert client.get("/api/state").json()["day"]["mode"] == "quiet"
    # And the copy that comes back carries no circus metaphor.
    assert "ball" not in body["barnaby"]["text"].lower()


def test_voice_log_records_what_barnaby_said(client):
    begin(client)
    entries = client.get("/api/voice-log").json()["entries"]
    assert entries
    assert all("text" in e and "source" in e for e in entries)


def test_device_state_syncs_late_listeners(client):
    """A tab opening just after a check-in came due must still see Barnaby
    shaking — events only reach subscribers present when they fire."""
    from gesture.devices import get_device

    d = get_device()
    d.jiggle("checkin", 0.7)
    assert d.state()["jiggling"] is True

    d.pet()
    assert d.state()["jiggling"] is False
    assert d.state()["expression"] == "relieved"


def test_pet_and_nudge(client):
    assert client.post("/api/barnaby/nudge").json()["ok"] is True
    assert client.post("/api/barnaby/pet").json()["ok"] is True


def test_demo_due_now_schedules_from_scratch_when_nothing_is_pending(client):
    """A zero-capacity day books no check-in at all -- due-now must still be
    able to conjure one for the demo, not assume a row already exists."""
    begin(client, capacity=0)
    assert client.get("/api/state").json()["next_checkin_at"] is None

    r = client.post("/api/demo/due-now")
    assert r.status_code == 200
    assert client.get("/api/checkin").json()["due"] is True
