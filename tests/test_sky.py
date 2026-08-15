"""The Window.

The load-bearing test here is `test_dismissals_never_darken_the_sky`. It is
the difference between a reflection and a participation grade, and it is the
kind of rule that quietly rots the moment someone adds "engagement" to the
light calculation six months from now.
"""

from __future__ import annotations

from conftest import make_checkin, make_day
from gesture.agent import sky


def test_a_day_with_no_signal_is_unlit_not_dark():
    """Absence and misery must not render identically."""
    assert sky.day_light(make_day(began=False)) is None

    result = sky.render([make_day(began=False)])
    assert result["band"] == "unlit"
    assert result["days"][0]["lit"] is False
    # An empty week is not a 3am week.
    assert result["band"] != "three_am"


def test_dismissals_never_darken_the_sky():
    """THE invariant.

    Adding dismissed check-ins to a day must not change its light by even a
    fraction. If dismissing made your sky darker, the picture would be
    measuring compliance, and users would learn to perform for it — which
    would poison the very data the agent adapts on.
    """
    base = make_day(sleep_hours=7.0, checkins=[make_checkin(0, mood=4, water=2)])
    before = sky.day_light(base)

    noisy = make_day(
        sleep_hours=7.0,
        checkins=[
            make_checkin(0, mood=4, water=2),
            *[make_checkin(i, dismissed=True) for i in range(1, 9)],
        ],
    )
    assert sky.day_light(noisy) == before


def test_unfinished_acts_never_darken_the_sky():
    from gesture.models import ActKind

    from conftest import make_act

    plain = make_day(sleep_hours=7.0, checkins=[make_checkin(0, mood=3)])
    with_undone = make_day(
        sleep_hours=7.0,
        checkins=[make_checkin(0, mood=3)],
        acts=[make_act(i, ActKind.HOOPS) for i in range(5)],
    )
    assert sky.day_light(with_undone) == sky.day_light(plain)


def test_light_tracks_how_the_day_felt():
    grim = make_day(sleep_hours=3.0, checkins=[make_checkin(0, mood=1)])
    good = make_day(sleep_hours=8.5, checkins=[make_checkin(0, mood=5, water=6)])
    assert sky.day_light(grim) < 0.25
    assert sky.day_light(good) > 0.75


def test_bands_span_night_to_dawn():
    assert sky._band_for(0.05).key == "three_am"
    assert sky._band_for(0.35).key == "predawn"
    assert sky._band_for(0.60).key == "magic_hour"
    assert sky._band_for(0.90).key == "dawn"


def test_coverage_marks_days_we_barely_heard_from():
    """A day where everything was dismissed leaves only sleep behind. It must
    be drawn as uncertain, not as a confident middling day."""
    thin = make_day(
        sleep_hours=4.5,
        checkins=[make_checkin(i, dismissed=True) for i in range(5)],
    )
    full = make_day(sleep_hours=4.5, checkins=[make_checkin(0, mood=2, water=3)])

    thin_light, thin_cov = sky.day_signal(thin)
    _, full_cov = sky.day_signal(full)
    assert thin_cov < full_cov
    assert thin_cov == sky.WEIGHTS["sleep"]


def test_week_average_is_weighted_by_coverage():
    """One barely-known day should not get an equal vote on the whole week."""
    known = [
        make_day(date=f"2026-08-{d}", sleep_hours=8.0,
                 checkins=[make_checkin(0, mood=5, water=5)])
        for d in range(10, 15)
    ]
    thin = make_day(
        date="2026-08-15",
        sleep_hours=0.5,
        checkins=[make_checkin(i, dismissed=True) for i in range(4)],
    )
    weighted = sky.render(known + [thin])["light"]

    naive_lights = [sky.day_light(d) for d in known + [thin]]
    naive = sum(naive_lights) / len(naive_lights)
    assert weighted > naive


def test_render_exposes_the_numbers_underneath():
    day = make_day(sleep_hours=7.0, checkins=[make_checkin(0, mood=4, water=2)])
    detail = sky.render([day])["days"][0]["detail"]
    assert detail["mood"] == 4
    assert detail["sleep_hours"] == 7.0
    assert detail["water"] == 2
    assert detail["checkins"] == 1
