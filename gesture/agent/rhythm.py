"""When to check in, and how much to ask for.

This is the agent's only real decision, and the whole philosophy lives in its
sign. Every engagement product on earth responds to being ignored by pushing
harder — more notifications, more urgency, a red badge. Gesture responds by
backing off, and by asking for less when it does come back.

    Dismiss is not failure. Dismiss is data.

The consequence, spelled out: a user who dismisses four times in a row has
told Barnaby something true about today, and the correct response to being
told the truth is not to ask again more loudly.

Everything here is deterministic and inspectable — `explain()` returns the
exact factors behind the next interval, which is also what the demo shows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Optional

from ..models import CheckInWeight, DayState

BASE_INTERVAL_MIN = 60
MIN_INTERVAL_MIN = 25
MAX_INTERVAL_MIN = 240


@dataclass
class Rhythm:
    interval_minutes: int
    weight: CheckInWeight
    next_at: Optional[datetime]
    factors: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _parse_hm(value: str) -> time:
    hh, mm = value.split(":")
    return time(int(hh), int(mm))


def dismiss_streak(day: DayState) -> int:
    """Consecutive dismissals at the tail of the day.

    Sorted by (responded_at, id): timestamps are second-granular, so several
    responses inside one second would otherwise sort arbitrarily and a streak
    could survive the answer that ought to have broken it. `id` is monotonic
    and is the real tiebreaker.
    """
    streak = 0
    for c in sorted(
        (c for c in day.checkins if c.responded_at),
        key=lambda c: (c.responded_at or "", c.id),
        reverse=True,
    ):
        if c.dismissed:
            streak += 1
        else:
            break
    return streak


def dismiss_ratio(day: DayState) -> float:
    answered = [c for c in day.checkins if c.responded_at]
    if not answered:
        return 0.0
    return sum(1 for c in answered if c.dismissed) / len(answered)


def recent_mood(day: DayState) -> Optional[float]:
    moods = [c.mood for c in day.checkins if c.mood is not None]
    if not moods:
        return None
    return sum(moods[-3:]) / len(moods[-3:])


# --------------------------------------------------------------------------
# Factors. Each returns a multiplier on the base interval. Above 1.0 means
# "come back later" — which is always the gentler direction.
# --------------------------------------------------------------------------


def capacity_factor(capacity: int) -> float:
    """Low capacity earns more room, not more supervision."""
    if capacity <= 0:
        return 2.5
    if capacity < 25:
        return 1.6
    if capacity < 40:
        return 1.3
    if capacity < 65:
        return 1.0
    if capacity < 85:
        return 0.9
    return 0.85


def dismiss_factor(streak: int) -> float:
    """The core move: back off geometrically as dismissals accumulate."""
    return min(1.0 + 0.45 * streak, 2.6)


def mood_factor(mood: Optional[float]) -> float:
    """A low mood lowers demand. It never raises frequency — a bad afternoon
    is not an alert condition, and treating it as one is how apps become one
    more thing to manage."""
    if mood is None:
        return 1.0
    if mood <= 2.0:
        return 1.2
    if mood >= 4.0:
        return 0.95
    return 1.0


def sleep_factor(sleep_hours: Optional[float]) -> float:
    if sleep_hours is None:
        return 1.0
    return 1.15 if sleep_hours < 6 else 1.0


# --------------------------------------------------------------------------


def next_weight(day: DayState) -> CheckInWeight:
    """How much the next check-in is allowed to ask for.

    Weight walks *down* fast and *up* slowly. Coming back from a hard stretch
    should not be greeted by the full questionnaire.
    """
    streak = dismiss_streak(day)
    if streak >= 2:
        return CheckInWeight.FEATHER
    if streak == 1:
        return CheckInWeight.LIGHT
    if dismiss_ratio(day) > 0.5:
        return CheckInWeight.LIGHT
    if day.capacity and day.capacity < 25:
        return CheckInWeight.LIGHT
    return CheckInWeight.FULL


def compute(day: DayState, now: datetime) -> Rhythm:
    """Decide the next check-in. Returns `next_at=None` when the day's window
    has closed — at which point the curtain call is what happens instead."""
    streak = dismiss_streak(day)
    mood = recent_mood(day)

    factors = {
        "capacity": capacity_factor(day.capacity),
        "dismissals": dismiss_factor(streak),
        "mood": mood_factor(mood),
        "sleep": sleep_factor(day.sleep_hours),
    }

    minutes = BASE_INTERVAL_MIN
    for f in factors.values():
        minutes *= f
    minutes = int(max(MIN_INTERVAL_MIN, min(MAX_INTERVAL_MIN, round(minutes))))

    notes: list[str] = []
    if streak:
        notes.append(
            f"{streak} dismissal{'s' if streak != 1 else ''} in a row — "
            f"giving you a wider berth."
        )
    if day.capacity < 25:
        notes.append("Low capacity today — fewer interruptions.")
    if mood is not None and mood <= 2.0:
        notes.append("Mood is low — asking for less, not more.")
    if day.sleep_hours is not None and day.sleep_hours < 6:
        notes.append("Short night — stretching the gaps out.")
    if not notes:
        notes.append("Steady day. Holding the default rhythm.")

    candidate = now + timedelta(minutes=minutes)
    end = datetime.combine(now.date(), _parse_hm(day.window_end))
    next_at: Optional[datetime] = candidate if candidate <= end else None

    return Rhythm(
        interval_minutes=minutes,
        weight=next_weight(day),
        next_at=next_at,
        factors=factors,
        notes=notes,
    )


def explain(day: DayState, now: datetime) -> dict:
    """Inspectable reasoning. Rendered in the UI behind a disclosure, because
    an agent that adapts to you should be able to say why."""
    r = compute(day, now)
    return {
        "interval_minutes": r.interval_minutes,
        "weight": r.weight.value,
        "next_at": r.next_at.isoformat(timespec="seconds") if r.next_at else None,
        "base_minutes": BASE_INTERVAL_MIN,
        "factors": {k: round(v, 3) for k, v in r.factors.items()},
        "notes": r.notes,
        "dismiss_streak": dismiss_streak(day),
        "dismiss_ratio": round(dismiss_ratio(day), 3),
    }
