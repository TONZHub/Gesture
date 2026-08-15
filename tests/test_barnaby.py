"""The orchestrator: model in front, local voice behind, guard across both."""

from __future__ import annotations

import pytest

from gesture.agent.barnaby import Barnaby
from gesture.models import Mode, StateAnchor


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    from gesture import db

    db.reset(tmp_path / "b.db")
    yield
    db.reset(tmp_path / "b.db")


def test_a_drifting_model_is_caught_and_the_user_never_sees_it(monkeypatch):
    """The central architectural claim.

    If the model returns something that breaks the contract, the guard drops it
    and the local voice answers instead — so the posture survives a model that
    forgot its instructions.
    """
    b = Barnaby(Mode.CIRCUS)
    monkeypatch.setattr(
        b, "_ask_model", lambda prompt: "You really should just sit down and focus."
    )

    u = b.checkin_prompt("full", 0)

    assert u.source == "guard-fallback"
    assert "should" not in u.text.lower()

    from gesture.agent import guard

    assert guard.is_clean(u.text)


def test_a_clean_model_response_is_used_as_is(monkeypatch):
    b = Barnaby(Mode.QUIET)
    monkeypatch.setattr(b, "_ask_model", lambda prompt: "How's it going?")
    u = b.checkin_prompt("full", 0)
    assert u.text == "How's it going?"
    assert u.source == "strands"


def test_blocked_output_is_logged_for_inspection(monkeypatch):
    from gesture import db

    b = Barnaby(Mode.CIRCUS)
    monkeypatch.setattr(b, "_ask_model", lambda prompt: "Why didn't you finish this?")
    b.checkin_prompt("full", 0)

    blocked = [e for e in db.voice_log(20) if e["blocked"]]
    assert blocked
    assert "interrogation" in blocked[0]["reason"]


def test_model_failure_falls_back_silently(monkeypatch):
    def boom(prompt):
        raise RuntimeError("bedrock is having a day")

    b = Barnaby(Mode.CIRCUS)
    monkeypatch.setattr(b, "_ask_model", boom)

    with pytest.raises(RuntimeError):
        b._ask_model("x")

    # Through the real path, a dead model is invisible.
    monkeypatch.setattr(b, "_ask_model", lambda prompt: None)
    u = b.checkin_prompt("full", 0)
    assert u.source == "local"
    assert u.text


def test_failure_starts_a_cooldown_instead_of_retrying_every_call(monkeypatch):
    """A model that is down must cost one slow response, not one per
    interaction — otherwise every tap pays the timeout while a human waits."""
    b = Barnaby(Mode.CIRCUS)
    calls = {"n": 0}

    def failing_agent(prompt):
        calls["n"] += 1
        raise RuntimeError("bedrock is throttling")

    # Pretend the agent built fine, then fails when called. Goes through the
    # real _get_agent so the cooldown is actually exercised.
    b._agent = failing_agent

    for _ in range(5):
        assert b._ask_model("anything") is None

    assert calls["n"] == 1, f"retried the dead model {calls['n']} times"
    assert b._cooling_down()


def test_cooldown_expires_and_the_model_is_tried_again(monkeypatch):
    b = Barnaby(Mode.CIRCUS)
    b.RETRY_AFTER_SECONDS = 0.0
    b._failed_at = 1.0
    assert b._cooling_down() is False


def test_feather_checkins_skip_the_model_entirely(monkeypatch):
    """Nothing is being asked, and a generated sentence tends to start asking."""
    b = Barnaby(Mode.CIRCUS)
    called = {"n": 0}

    def spy(prompt):
        called["n"] += 1
        return "some model text"

    monkeypatch.setattr(b, "_ask_model", spy)
    u = b.checkin_prompt("feather", 3)
    assert called["n"] == 0
    assert u.source == "local"


def test_forgot_flow_is_answered_from_state_not_invention(monkeypatch):
    """The whole value of this one is being accurate about where they were."""
    from conftest import make_act, make_day
    from gesture.models import ActKind

    b = Barnaby(Mode.QUIET)
    monkeypatch.setattr(b, "_ask_model", lambda prompt: None)

    day = make_day(
        acts=[make_act(1, ActKind.HOOPS, "ring the surgery")],
    )
    day.intention = "get the admin done before lunch"

    u = b.stuck(StateAnchor.FORGOT_FLOW, day, None)
    assert "ring the surgery" in u.text
    assert "get the admin done before lunch" in u.text


@pytest.mark.parametrize("mode", [Mode.CIRCUS, Mode.QUIET])
def test_system_prompt_carries_the_banned_list(mode):
    from gesture.agent.barnaby import system_prompt

    p = system_prompt(mode).lower()
    assert "streak" in p
    assert "should" in p
    # Both prompts mention the circus — Quiet's does so to forbid it.
    if mode is Mode.CIRCUS:
        assert "ringmaster" in p
    else:
        assert "costume off" in p
        assert "no circus imagery" in p
