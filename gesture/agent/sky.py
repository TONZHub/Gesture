"""The Window — a week rendered as light.

Your week as a sky that shifts from night to day. Hard weeks are 3am
blue-black. Good weeks are dawn threshold light. In-between weeks are magic
hour, where you genuinely cannot tell dusk from dawn. You feel it before you
read it.

One design rule governs this whole file, and it is the rule that separates
Gesture from every habit tracker ever shipped:

    **Dismissals never darken the sky.**

The sky is built from how the week *felt* — mood, sleep, water — and never
from how compliant the user was with the app. If ignoring Barnaby made your
sky go black, then the picture would be a participation grade with better art
direction, and the user would learn to perform for it. Dismissals are real
data and they belong in the rhythm and in patterns.py. They do not belong in
the image the user has to look at.

The second rule: a day with no data is *unlit*, not dark. Absence renders as
haze. There is a difference between a hard day and a day you didn't log, and
collapsing them would be a lie told in gradient.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..models import DayState

# signal -> weight, renormalised over whichever signals a day actually has
WEIGHTS = {"mood": 0.65, "sleep": 0.25, "water": 0.10}


@dataclass(frozen=True)
class Band:
    key: str
    name: str
    line: str
    colors: tuple[str, str, str]  # top, middle, horizon


BANDS: tuple[Band, ...] = (
    Band(
        key="three_am",
        name="3am",
        line="This was a 3am week. You were in it the whole time.",
        colors=("#05070f", "#0b1020", "#161d33"),
    ),
    Band(
        key="predawn",
        name="Pre-dawn",
        line="A dark stretch. It did move, though. Slowly, but it moved.",
        colors=("#0a1024", "#1b2447", "#3a3f63"),
    ),
    Band(
        key="magic_hour",
        name="Magic hour",
        line="Dusk or dawn? It's impossible to tell from inside. Both look like this.",
        colors=("#233056", "#6b5a76", "#c99a72"),
    ),
    Band(
        key="dawn",
        name="Dawn threshold",
        line="Threshold light. Something in this week opened up.",
        colors=("#3b4a7a", "#a886a0", "#f0c48a"),
    ),
)


def _band_for(light: float) -> Band:
    if light < 0.25:
        return BANDS[0]
    if light < 0.50:
        return BANDS[1]
    if light < 0.75:
        return BANDS[2]
    return BANDS[3]


def _mood_light(day: DayState) -> Optional[float]:
    moods = [c.mood for c in day.checkins if c.mood is not None]
    if not moods:
        return None
    return (sum(moods) / len(moods) - 1) / 4  # 1..5 -> 0..1


def _sleep_light(day: DayState) -> Optional[float]:
    if day.sleep_hours is None:
        return None
    return max(0.0, min(day.sleep_hours / 9.0, 1.0))


def _water_light(day: DayState) -> Optional[float]:
    if not day.water_total:
        return None
    return min(day.water_total / 6.0, 1.0)


def day_signal(day: DayState) -> Optional[tuple[float, float]]:
    """Return `(light, coverage)`, or None when the day holds no signal at all.

    `coverage` is the share of the weighting a day actually has evidence for.
    It exists because of a failure mode worth naming: on a genuinely awful day
    the user dismisses every check-in, so mood and water are never recorded and
    the only surviving signal is last night's sleep. Averaged naively, the
    hardest day of the week renders as a perfectly pleasant mid-sky.

    So a thin day is drawn *dimly* rather than confidently, and it counts
    proportionally less toward the week. Being unsure is rendered as being
    unsure. Guessing brightly at a day someone could not speak during is the
    exact failure this app exists to avoid.

    Note what is absent from this calculation: dismissals, acts completed, and
    whether Begin was pressed. None of those describe how a day felt.
    """
    signals = {
        "mood": _mood_light(day),
        "sleep": _sleep_light(day),
        "water": _water_light(day),
    }
    present = {k: v for k, v in signals.items() if v is not None}
    if not present:
        return None
    coverage = sum(WEIGHTS[k] for k in present)
    light = sum(v * WEIGHTS[k] for k, v in present.items()) / coverage
    return light, coverage


def day_light(day: DayState) -> Optional[float]:
    sig = day_signal(day)
    return None if sig is None else sig[0]


def render(days: list[DayState]) -> dict:
    """Everything The Window needs: the week's band, and each day's own light."""
    per_day = []
    for d in days:
        sig = day_signal(d)
        light = None if sig is None else sig[0]
        coverage = 0.0 if sig is None else sig[1]
        per_day.append(
            {
                "date": d.date,
                "light": None if light is None else round(light, 3),
                "coverage": round(coverage, 3),
                "band": None if light is None else _band_for(light).key,
                "lit": light is not None,
                # Detail available underneath — the image lands first, but the
                # numbers are never hidden from someone who wants them.
                "detail": {
                    "mood": _avg([c.mood for c in d.checkins if c.mood is not None]),
                    "sleep_hours": d.sleep_hours,
                    "water": d.water_total,
                    "checkins": len([c for c in d.checkins if c.responded_at]),
                    "dismissed": len([c for c in d.checkins if c.dismissed]),
                    "acts_done": len([a for a in d.acts if a.done]),
                    "acts_held": len([a for a in d.acts if a.held]),
                    "began": bool(d.began_at),
                },
            }
        )

    lit = [p for p in per_day if p["light"] is not None]
    if not lit:
        return {
            "band": "unlit",
            "name": "Not enough sky yet",
            "line": "Not enough of the week here to draw it. That's alright. "
            "it fills in as you go.",
            "colors": ["#0a0d18", "#141a2c", "#232a44"],
            "light": None,
            "days": per_day,
            "lit_days": 0,
        }

    # Weighted by coverage, so a day we barely heard from does not get an
    # equal vote on what the whole week looked like.
    total_w = sum(p["coverage"] for p in lit)
    week_light = sum(p["light"] * p["coverage"] for p in lit) / total_w
    band = _band_for(week_light)
    return {
        "band": band.key,
        "name": band.name,
        "line": band.line,
        "colors": list(band.colors),
        "light": round(week_light, 3),
        "days": per_day,
        "lit_days": len(lit),
    }


def _avg(xs: list) -> Optional[float]:
    return round(sum(xs) / len(xs), 2) if xs else None
