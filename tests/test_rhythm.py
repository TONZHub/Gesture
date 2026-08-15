"""The rhythm engine.

The central assertion of this file is a one-way property: **nothing a user
does can make Barnaby come back sooner as a consequence of disengaging.**
Every engagement product gets this backwards, so it is pinned down here.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from conftest import BASE, make_checkin, make_day
from gesture.agent import rhythm
from gesture.models import CheckInWeight

NOW = BASE + timedelta(hours=2)


def test_default_day_holds_the_base_rhythm():
    r = rhythm.compute(make_day(), NOW)
    assert r.interval_minutes == rhythm.BASE_INTERVAL_MIN
    assert r.weight is CheckInWeight.FULL


def test_dismissals_lengthen_the_interval_monotonically():
    intervals = []
    for n in range(5):
        day = make_day(
            checkins=[make_checkin(i, dismissed=True) for i in range(n)]
        )
        intervals.append(rhythm.compute(day, NOW).interval_minutes)
    assert intervals == sorted(intervals), intervals
    assert intervals[-1] > intervals[0]


def test_dismissals_never_shorten_the_interval():
    """The invariant. If this ever fails, the product has become the thing it
    was built to replace."""
    baseline = rhythm.compute(make_day(), NOW).interval_minutes
    for n in range(1, 8):
        day = make_day(checkins=[make_checkin(i, dismissed=True) for i in range(n)])
        assert rhythm.compute(day, NOW).interval_minutes >= baseline


def test_weight_walks_down_with_dismissals():
    def weight(n):
        return rhythm.next_weight(
            make_day(checkins=[make_checkin(i, dismissed=True) for i in range(n)])
        )

    assert weight(0) is CheckInWeight.FULL
    assert weight(1) is CheckInWeight.LIGHT
    assert weight(2) is CheckInWeight.FEATHER
    assert weight(5) is CheckInWeight.FEATHER


def test_weight_returns_gently_not_all_at_once():
    """After a run of dismissals, answering once must not snap straight back
    to the full questionnaire."""
    day = make_day(
        checkins=[
            make_checkin(0, dismissed=True),
            make_checkin(1, dismissed=True),
            make_checkin(2, dismissed=True),
            make_checkin(3, dismissed=False, mood=3),
        ]
    )
    assert rhythm.dismiss_streak(day) == 0
    assert rhythm.next_weight(day) is CheckInWeight.LIGHT


def test_streak_breaks_on_the_answer_even_within_one_second():
    """Second-granular timestamps must not let a streak survive an answer."""
    same = BASE
    day = make_day(
        checkins=[
            make_checkin(0, dismissed=True, at=same),
            make_checkin(1, dismissed=True, at=same),
            make_checkin(2, dismissed=False, mood=4, at=same),
        ]
    )
    assert rhythm.dismiss_streak(day) == 0


def test_low_capacity_widens_the_gap():
    low = rhythm.compute(make_day(capacity=10), NOW).interval_minutes
    mid = rhythm.compute(make_day(capacity=50), NOW).interval_minutes
    high = rhythm.compute(make_day(capacity=95), NOW).interval_minutes
    assert low > mid > high


def test_low_mood_lowers_demand_rather_than_raising_frequency():
    sad = make_day(checkins=[make_checkin(0, mood=1), make_checkin(1, mood=2)])
    ok = make_day(checkins=[make_checkin(0, mood=4), make_checkin(1, mood=4)])
    assert (
        rhythm.compute(sad, NOW).interval_minutes
        > rhythm.compute(ok, NOW).interval_minutes
    )


def test_short_sleep_widens_the_gap():
    tired = rhythm.compute(make_day(sleep_hours=4.0), NOW).interval_minutes
    rested = rhythm.compute(make_day(sleep_hours=8.0), NOW).interval_minutes
    assert tired > rested


def test_interval_is_clamped():
    day = make_day(
        capacity=0,
        sleep_hours=2.0,
        checkins=[make_checkin(i, dismissed=True) for i in range(20)],
    )
    r = rhythm.compute(day, NOW)
    assert rhythm.MIN_INTERVAL_MIN <= r.interval_minutes <= rhythm.MAX_INTERVAL_MIN


def test_no_checkin_scheduled_past_the_days_window():
    day = make_day(window_end="17:00")
    late = datetime(2026, 8, 15, 16, 55)
    assert rhythm.compute(day, late).next_at is None


def test_explain_exposes_its_reasoning():
    day = make_day(checkins=[make_checkin(0, dismissed=True)])
    e = rhythm.explain(day, NOW)
    assert set(e["factors"]) == {"capacity", "dismissals", "mood", "sleep"}
    assert e["dismiss_streak"] == 1
    assert e["notes"]


@pytest.mark.parametrize("n", range(6))
def test_dismiss_factor_never_drops_below_one(n):
    assert rhythm.dismiss_factor(n) >= 1.0
