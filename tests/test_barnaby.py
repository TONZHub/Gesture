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


def test_stuck_interpretation_is_structured_and_grounded(monkeypatch):
    from conftest import make_act, make_day
    from gesture.models import ActKind

    b = Barnaby(Mode.QUIET)
    day = make_day(acts=[make_act(1, ActKind.HOOPS, "reply to my manager")])
    monkeypatch.setattr(
        b,
        "_ask_model",
        lambda prompt: (
            '{"anchor":"scared","reflection":"The reply feels risky.",'
            '"micro_gesture":"Open the draft and rest one hand on the keyboard.",'
            '"follow_up_seconds":60}'
        ),
    )

    decision = b.interpret_stuck(None, day, "I am scared I will say it wrong")

    assert decision.anchor is StateAnchor.SCARED
    assert decision.source == "strands"
    assert "Open the draft" in decision.micro_gesture
    assert "your words" in decision.used_context
    assert "unfinished acts" in decision.used_context


def test_unsafe_stuck_interpretation_uses_guard_fallback(monkeypatch):
    from conftest import make_day

    b = Barnaby(Mode.QUIET)
    monkeypatch.setattr(
        b,
        "_ask_model",
        lambda prompt: (
            '{"anchor":"cant_start","reflection":"You are being lazy.",'
            '"micro_gesture":"Just do it.","follow_up_seconds":60}'
        ),
    )

    decision = b.interpret_stuck(None, make_day(), "I cannot open the file")

    assert decision.source == "guard-fallback"
    assert "lazy" not in decision.reflection.lower()


def test_explicit_stuck_state_outranks_model_classification(monkeypatch):
    from conftest import make_day

    b = Barnaby(Mode.QUIET)
    monkeypatch.setattr(
        b,
        "_ask_model",
        lambda prompt: (
            '{"anchor":"cant_start","reflection":"This feels risky.",'
            '"micro_gesture":"Put both feet on the floor.","follow_up_seconds":60}'
        ),
    )

    decision = b.interpret_stuck(StateAnchor.SCARED, make_day(), "I feel afraid")

    assert decision.anchor is StateAnchor.SCARED


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


# --- model providers (Bedrock / Featherless), both behind the guard ---------


def _reload_barnaby_settings(monkeypatch, **env):
    """Reload settings with env overrides and point the barnaby module at them."""
    import gesture.agent.barnaby as bmod
    from gesture.config import Settings

    for k, v in env.items():
        monkeypatch.setenv(k, v)
    s = Settings.load()
    monkeypatch.setattr(bmod, "settings", s)
    return s


def test_build_model_selects_bedrock_by_default(monkeypatch):
    _reload_barnaby_settings(monkeypatch, GESTURE_MODEL_PROVIDER="bedrock")
    assert type(Barnaby._build_model()).__name__ == "BedrockModel"


def test_build_model_selects_featherless_when_configured(monkeypatch):
    _reload_barnaby_settings(
        monkeypatch,
        GESTURE_MODEL_PROVIDER="featherless",
        FEATHERLESS_API_KEY="fk_test_key",
    )
    model = Barnaby._build_model()
    assert type(model).__name__ == "OpenAIModel"
    # carries the configured open model (an OpenAI-compatible Strands provider
    # pointed at Featherless — the base_url lives on the client, the model id
    # here proves the Featherless config was used, not Bedrock)
    assert model.config.get("model_id") == "meta-llama/Meta-Llama-3.1-8B-Instruct"


def test_featherless_without_a_key_degrades_to_local(monkeypatch):
    """A missing Featherless key must not crash — same graceful path as a
    missing Bedrock credential."""
    _reload_barnaby_settings(
        monkeypatch,
        GESTURE_MODEL_PROVIDER="featherless",
        FEATHERLESS_API_KEY="",
        GESTURE_USE_STRANDS="1",
    )
    b = Barnaby(Mode.CIRCUS)
    assert b._get_agent() is None  # raised internally, swallowed
    u = b.checkin_prompt("full", 0)
    assert u.source == "local"


def test_the_guard_wraps_whichever_provider_speaks(monkeypatch):
    """The guard is provider-agnostic: a drift line from a Featherless-backed
    Barnaby is caught exactly like a Bedrock one."""
    _reload_barnaby_settings(
        monkeypatch,
        GESTURE_MODEL_PROVIDER="featherless",
        FEATHERLESS_API_KEY="fk_test_key",
    )
    b = Barnaby(Mode.CIRCUS)
    monkeypatch.setattr(b, "_ask_model", lambda p: "You should just push through it.")
    u = b.checkin_prompt("full", 0)
    assert u.source == "guard-fallback"

    from gesture.agent import guard

    assert guard.is_clean(u.text)
