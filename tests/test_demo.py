"""The demo seeder.

This runs on startup in the hosted build, so the important tests are the ones
about restraint: it must never overwrite real data, never double-seed on a
restart, and never take today away from the visitor.
"""

from __future__ import annotations

import pytest

from gesture import db, demo
from gesture.agent import sky


@pytest.fixture()
def fresh(tmp_path):
    db.reset(tmp_path / "seed.db")
    yield
    db.reset(tmp_path / "seed.db")


def test_seeds_a_week_of_history(fresh):
    written = demo.seed(fresh=False)
    assert written >= 5
    assert db.has_any_days()

    week = sky.render(db.recent_days(7))
    assert week["lit_days"] >= 4
    assert week["band"] != "unlit"


def test_seed_if_empty_is_a_no_op_when_data_exists(fresh):
    demo.seed(fresh=False)
    before = len(db.recent_days(7))
    lit_before = sky.render(db.recent_days(7))["lit_days"]

    assert demo.seed_if_empty() == 0

    assert len(db.recent_days(7)) == before
    assert sky.render(db.recent_days(7))["lit_days"] == lit_before


def test_seed_if_empty_never_overwrites_a_real_day(fresh):
    """A user's own first day must survive a restart with seeding enabled."""
    from gesture.models import Mode

    db.begin_day(
        mode=Mode.QUIET,
        capacity=35,
        window_start="08:00",
        window_end="18:00",
        intention="mine, not invented",
        sleep_hours=6.5,
    )

    assert demo.seed_if_empty() == 0

    today = db.day_state()
    assert today.intention == "mine, not invented"
    assert today.capacity == 35
    assert today.mode is Mode.QUIET


def test_leave_today_empty_keeps_the_begin_screen(fresh):
    """The hosted demo fills in history *behind* the visitor. If today were
    seeded they would land mid-day and never see Begin, the first of the three
    screens the submission is about."""
    demo.seed(fresh=False, leave_today_empty=True)

    assert db.day_state().began_at is None
    assert sky.render(db.recent_days(7))["lit_days"] >= 4


def test_the_seeded_week_is_not_a_success_story(fresh):
    """A demo week where everything goes well is a demo of a different
    product. There must be a genuinely dark day and a day with no data."""
    demo.seed(fresh=False)
    days = sky.render(db.recent_days(7))["days"]

    assert any(d["band"] == "three_am" for d in days), "no hard day in the week"
    assert any(not d["lit"] for d in days), "no missing day in the week"


def test_seeding_is_deterministic(fresh, tmp_path):
    demo.seed(fresh=False, seed_value=7)
    first = [d["light"] for d in sky.render(db.recent_days(7))["days"]]

    db.reset(tmp_path / "seed2.db")
    demo.seed(fresh=False, seed_value=7)
    second = [d["light"] for d in sky.render(db.recent_days(7))["days"]]

    assert first == second
