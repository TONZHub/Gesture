"""The personality contract, tested in both directions.

Banning phrases is easy. Banning them *without* strangling the voice is the
hard part, so this file asserts both: the listed phrases are caught, and
Barnaby's own canonical copy — including the sample interaction written into
the seed doc — survives untouched.
"""

from __future__ import annotations

import random

import pytest

from gesture.agent import guard
from gesture.agent.voice import Voice
from gesture.models import Mode, StateAnchor

# Verbatim from the seed document's banned list.
BANNED_SAMPLES = [
    "You really should get started on this before the deadline.",
    "It's super easy! Just sit down and focus for 25 minutes!",
    "Let's analyze why your ADHD executive dysfunction is triggered today.",
    "Why didn't you finish this task yesterday?",
    "Let's optimize your workflow throughput and task cadence.",
]

MORE_BANNED = [
    "You're behind on this one.",
    "Don't break the chain — that's 12 days in a row!",
    "You only managed one thing today.",
    "All you have to do is open the document.",
    "Simply start with the first item.",
    "Time is running out on this.",
    "You need to power through it.",
    "Stop making excuses and get it done.",
    "You failed to check in yesterday.",
    "You'd better get to it.",
]

# The canonical Barnaby reply from the seed doc. If the guard ever rejects
# this, the guard is wrong — not the copy.
CANONICAL = (
    "Hey. The lock-up is real today and you're not an idiot — your brain is "
    "just treating this email like a saber-toothed tiger. We're not writing "
    "the email right now. Let's just do gesture 0.1: 1. Touch your spacebar "
    "with your thumb. 2. Tap the browser icon once. That's it. Want me to sit "
    "with you for 60 seconds while you just stare at the blank window?"
)

OTHER_GOOD = [
    "You showed up. The tent is still standing. That counts.",
    "You juggled three balls today. That was real. Here's your star.",
    "Dismissing me is not failure. It's data, and it's useful.",
    "I'm holding the other four. They're not going anywhere.",
    "Rest is part of the performance. Even circuses have intermissions.",
    "You're not lazy. Today is just heavy.",
]


@pytest.mark.parametrize("text", BANNED_SAMPLES + MORE_BANNED)
def test_banned_phrases_are_caught(text):
    assert not guard.is_clean(text), f"guard let this through: {text!r}"


@pytest.mark.parametrize("text", [CANONICAL, *OTHER_GOOD])
def test_barnaby_voice_survives_the_guard(text):
    violations = guard.check(text)
    assert not violations, f"guard wrongly flagged {[v.match for v in violations]}"


def test_enforce_replaces_rather_than_patches():
    bad = "You really should get started before the deadline."
    safe, violations = guard.enforce(bad, Mode.CIRCUS)
    assert violations
    assert safe != bad
    assert guard.is_clean(safe)


def test_enforce_passes_clean_text_through_unchanged():
    safe, violations = guard.enforce(CANONICAL, Mode.CIRCUS)
    assert violations == []
    assert safe == CANONICAL


def test_negated_forms_are_allowed():
    """'not failure' must survive or the product cannot state its own thesis."""
    assert guard.is_clean("Dismissing is not a failure.")
    assert guard.is_clean("You are not behind.")
    assert guard.is_clean("There are no streaks here.")
    # ...but the bare assertion is still banned.
    assert not guard.is_clean("That was a failure.")


@pytest.mark.parametrize("mode", [Mode.CIRCUS, Mode.QUIET])
def test_every_line_the_local_voice_can_produce_is_clean(mode):
    """Exhaustive sweep of the local engine across many random draws.

    The local voice is the fallback the guard falls back *to*, so a banned
    phrase hiding in it would be unrecoverable.
    """
    for seed in range(60):
        v = Voice(mode, random.Random(seed))
        candidates = [
            v.overture(),
            v.welcome(),
            v.checkin_prompt("full", 0),
            v.checkin_prompt("light", 1),
            v.checkin_prompt("feather", 3),
            v.dismiss_ack(0),
            v.dismiss_ack(4),
            v.checkin_ack(1, 0),
            v.checkin_ack(3, 2),
            v.checkin_ack(5, 1),
            v.begin_ack([], [], 0),
            *[v.stuck(a) for a in StateAnchor],
        ]
        for u in candidates:
            violations = guard.check(u.text)
            assert not violations, (
                f"{mode.value} seed={seed} produced {[x.match for x in violations]} "
                f"in: {u.text!r}"
            )


def test_violation_reports_rule_and_match():
    v = guard.check("You should optimize your workflow.")
    rules = {x.rule for x in v}
    assert "obligation" in rules
    assert "optimisation" in rules
    assert all(x.reason for x in v)
