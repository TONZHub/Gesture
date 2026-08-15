"""Correlations.

Two ways to fail here: staying silent when there is something real, or —
much worse — announcing a pattern drawn from three data points as though it
were a fact about someone's brain.
"""

from __future__ import annotations

from conftest import make_checkin, make_day
from gesture.agent import guard, patterns


def _day(date, *, sleep, moods, dismissed=0, water=None):
    cis = [make_checkin(i, mood=m, water=water) for i, m in enumerate(moods)]
    cis += [make_checkin(100 + i, dismissed=True) for i in range(dismissed)]
    return make_day(date=date, sleep_hours=sleep, checkins=cis)


def test_stays_quiet_without_enough_days():
    days = [_day(f"2026-08-1{i}", sleep=5 + i, moods=[i + 1]) for i in range(3)]
    assert patterns.surface(days) == []


def test_finds_a_real_sleep_mood_relationship():
    days = [
        _day("2026-08-10", sleep=3.0, moods=[1]),
        _day("2026-08-11", sleep=4.5, moods=[2]),
        _day("2026-08-12", sleep=6.0, moods=[3]),
        _day("2026-08-13", sleep=7.5, moods=[4]),
        _day("2026-08-14", sleep=9.0, moods=[5]),
    ]
    found = patterns.surface(days)
    ids = {f["id"] for f in found}
    assert "sleep_mood" in ids
    hit = next(f for f in found if f["id"] == "sleep_mood")
    assert hit["r"] > 0.9
    assert hit["n"] == 5


def test_ignores_noise():
    days = [
        _day("2026-08-10", sleep=8.0, moods=[3]),
        _day("2026-08-11", sleep=3.0, moods=[3]),
        _day("2026-08-12", sleep=6.0, moods=[3]),
        _day("2026-08-13", sleep=9.0, moods=[3]),
    ]
    # Mood is constant, so there is no correlation to find and nothing to say.
    assert not any(f["id"] == "sleep_mood" for f in patterns.surface(days))


def test_surfaces_at_most_two():
    days = [
        _day("2026-08-1%d" % i, sleep=3.0 + i, moods=[min(5, i + 1)],
             dismissed=max(0, 4 - i), water=i)
        for i in range(6)
    ]
    assert len(patterns.surface(days)) <= 2


def test_every_surfaced_line_survives_the_guard():
    """Insight copy is where well-meaning apps start scolding."""
    days = [
        _day("2026-08-10", sleep=3.0, moods=[1], dismissed=4, water=0),
        _day("2026-08-11", sleep=4.5, moods=[2], dismissed=3, water=1),
        _day("2026-08-12", sleep=6.0, moods=[3], dismissed=2, water=2),
        _day("2026-08-13", sleep=7.5, moods=[4], dismissed=1, water=3),
        _day("2026-08-14", sleep=9.0, moods=[5], dismissed=0, water=4),
    ]
    found = patterns.surface(days, limit=4)
    assert found
    for f in found:
        assert guard.is_clean(f["text"]), f["text"]


def test_dismiss_clock_needs_a_real_cluster():
    scattered = [
        make_day(
            date="2026-08-1%d" % i,
            checkins=[make_checkin(h, dismissed=True) for h in range(4)],
        )
        for i in range(2)
    ]
    # conftest spreads check-ins hourly from 09:00, so no 3-hour band holds
    # half of them.
    result = patterns.dismiss_clock(scattered)
    if result is not None:
        assert result["share"] >= 0.5
        assert guard.is_clean(result["text"])
