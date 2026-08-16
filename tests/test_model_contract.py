"""The contract between the model, the prompt, and the guard.

The guard's job is to catch a drifting model. But a guard that also blocks warm,
on-contract output is worse than useless — the user would only ever see local
fallbacks, and the whole point of running a model would be gone.

So this file pins the *false-positive* side: a corpus of lines a well-behaved
model following Barnaby's prompt would produce, asserted to pass the guard
untouched. (The true-positive side — that banned phrasing IS caught — lives in
test_guard.py.) The corpus doubles as a written spec of what good Barnaby output
sounds like across every moment.

It cannot substitute for real Bedrock output, but it does the thing that matters
without credentials: it proves the prompt's target and the guard's net are
compatible, and it fails loudly if either drifts.
"""

from __future__ import annotations

import pytest

from gesture.agent import guard
from gesture.agent.barnaby import system_prompt
from gesture.models import Mode

# Warm, on-brand lines spanning every moment. Each must survive the guard.
GOOD_OUTPUT = [
    # overture / greeting
    "Morning. The tent is up, the ring is swept, and I saved you the good seat.",
    "There you are. Take your time — the show waits for you.",
    "You're awake. That is the first thing, and it counts.",
    # begin
    "Three in the air today. We open with the shelf; the rest are with me.",
    "Nothing goes up today, and that is a real way to spend a day. I am holding all of it.",
    "One ball today. That is the whole bill, and it is plenty.",
    # check-in
    "How's the air up there? Nothing here is a test.",
    "Noted, and not held against you. Heavy afternoons are allowed.",
    "Good to hear. Ride that one while it lasts.",
    "You drank something. Genuinely, well done.",
    # dismiss
    "Fair enough. I will come back later — you know where I am.",
    "Understood. Turning the volume right down for a while.",
    # stuck: can't start
    "The lock-up is real, and it is not a character flaw. Touch your spacebar "
    "with your thumb — that is the whole task.",
    "We are not writing the email. We are doing gesture zero-point-one: tap the "
    "icon once, and stop there.",
    # stuck: scared
    "This one has a wall in front of it. I will stand on the other side and "
    "count you in. No output required.",
    # stuck: zero capacity
    "Then the show is over for today, and that is a real ending, not an "
    "abandoned one. Close the laptop. I will still be here.",
    # stuck: brain dump
    "Go on then. All of it, any order, no punctuation required. I will read it "
    "properly before I say anything back.",
    # forgot the flow
    "You lost the thread — happens constantly, means nothing. Here is where you were.",
    # curtain call
    "You went through the hoop today. That cost you something real, so it is "
    "worth something real.",
    "You showed up. The tent is still standing. I was here, I watched it hold.",
    "You let go of the tab you keep reopening. I caught it.",
    # quiet mode, plain register
    "I am here when you are ready. Nothing is urgent yet.",
    "That sounds hard. I have written it down and I am not making it a thing.",
    "You kept the one thing going. It is still standing.",
]


@pytest.mark.parametrize("line", GOOD_OUTPUT)
def test_good_model_output_passes_the_guard(line):
    violations = guard.check(line)
    assert not violations, (
        f"guard over-blocked a warm, on-contract line "
        f"{[v.match for v in violations]}: {line!r}"
    )


@pytest.mark.parametrize("mode", [Mode.CIRCUS, Mode.QUIET])
def test_prompt_covers_every_banned_category(mode):
    """If the prompt stops telling the model about a category, a live model
    starts tripping the guard on it. Keep the guidance and the guard in step."""
    p = system_prompt(mode).lower()
    for cue in (
        "should",        # obligation
        "just",          # minimising
        "why didn't",    # interrogation
        "behind",        # shame
        "streak",        # streaks
        "optimis",       # optimisation
        "diagnos",       # clinical
        "deadline",      # pressure
    ):
        assert cue in p, f"prompt no longer warns the model about: {cue!r}"


def test_circus_prompt_describes_the_tardigrade_not_the_seal():
    """The redesign made him a water bear; the model must describe himself
    correctly if he ever refers to his own form."""
    p = system_prompt(Mode.CIRCUS).lower()
    assert "tardigrade" in p or "water bear" in p
    assert "seal" not in p
    assert "flipper" not in p


def test_prompt_asks_for_short_replies():
    for mode in (Mode.CIRCUS, Mode.QUIET):
        p = system_prompt(mode).lower()
        assert "sentence" in p  # a length ceiling is stated
