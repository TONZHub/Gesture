"""Act triage — how much Barnaby hands over, and what he keeps hold of."""

from __future__ import annotations

import pytest

from conftest import make_act
from gesture.agent import acts
from gesture.models import ActKind, Mode


@pytest.mark.parametrize(
    "capacity,expected",
    [(0, 0), (10, 1), (15, 1), (30, 2), (50, 3), (70, 4), (90, 5), (100, 5)],
)
def test_capacity_maps_to_balls(capacity, expected):
    assert acts.balls_for_capacity(capacity) == expected


def test_zero_capacity_puts_nothing_in_play():
    items = [make_act(i, ActKind.JUGGLING) for i in range(4)]
    in_play, held = acts.triage(items, 0)
    assert in_play == []
    assert len(held) == 4


def test_held_items_are_held_not_lost():
    items = [make_act(i, ActKind.HOOPS) for i in range(5)]
    in_play, held = acts.triage(items, 50)
    assert len(in_play) + len(held) == 5


def test_cheapest_first_so_a_low_day_is_not_handed_the_heaviest_thing():
    items = [
        make_act(1, ActKind.TIGHTROPE, "deep focus thing"),
        make_act(2, ActKind.JUGGLING, "small thing"),
    ]
    in_play, _ = acts.triage(items, 20)  # one ball's worth of budget
    assert [a.title for a in in_play] == ["small thing"]


def test_done_and_already_held_items_are_not_re_offered():
    items = [
        make_act(1, ActKind.JUGGLING, "done one", done=True),
        make_act(2, ActKind.JUGGLING, "held one", held=True),
        make_act(3, ActKind.JUGGLING, "live one"),
    ]
    in_play, held = acts.triage(items, 90)
    titles = [a.title for a in in_play]
    assert titles == ["live one"]
    assert "done one" not in [a.title for a in held]


def test_both_modes_name_every_act():
    for mode in (Mode.CIRCUS, Mode.QUIET):
        entries = acts.catalogue(mode)
        assert len(entries) == len(ActKind)
        assert all(e["name"] and e["blurb"] for e in entries)


def test_quiet_names_carry_no_circus_metaphor():
    circus_words = {"juggl", "hoop", "tightrope", "trapeze", "balanc", "ring"}
    for e in acts.catalogue(Mode.QUIET):
        text = (e["name"] + " " + e["blurb"]).lower()
        assert not any(w in text for w in circus_words), e
