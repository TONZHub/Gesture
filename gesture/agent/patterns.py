"""Correlations, surfaced sparingly.

"No judgment, but this number of dismisses correlated with your health in this
way." — the hackathon brief.

Three rules govern this module:

1. **Only when there is enough data.** Four lit days minimum. A correlation
   drawn from two points is a horoscope.
2. **Only when the effect is real.** |r| >= 0.5 or it stays quiet.
3. **Only two at a time.** The interface gets quieter as it learns you. An
   insights dashboard is the opposite of that, and is how Fabulous loses this
   exact user.

Every string in here is written to survive guard.py, which is the point: the
insight layer is where well-meaning apps start scolding, so the insight layer
is held to the same contract as everything else.
"""

from __future__ import annotations

from typing import Optional

from ..models import DayState

MIN_DAYS = 4
MIN_R = 0.5


def _pearson(xs: list[float], ys: list[float]) -> Optional[float]:
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs)
    dy = sum((y - my) ** 2 for y in ys)
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy) ** 0.5


def _paired(days: list[DayState], a, b) -> tuple[list[float], list[float]]:
    """Pairwise-complete observations for two day-level metrics."""
    xs: list[float] = []
    ys: list[float] = []
    for d in days:
        av, bv = a(d), b(d)
        if av is not None and bv is not None:
            xs.append(float(av))
            ys.append(float(bv))
    return xs, ys


# --- day-level metrics -----------------------------------------------------


def m_mood(d: DayState) -> Optional[float]:
    moods = [c.mood for c in d.checkins if c.mood is not None]
    return sum(moods) / len(moods) if moods else None


def m_sleep(d: DayState) -> Optional[float]:
    return d.sleep_hours


def m_water(d: DayState) -> Optional[float]:
    answered = [c for c in d.checkins if c.responded_at]
    return float(d.water_total) if answered else None


def m_dismiss_ratio(d: DayState) -> Optional[float]:
    answered = [c for c in d.checkins if c.responded_at]
    if not answered:
        return None
    return sum(1 for c in answered if c.dismissed) / len(answered)


def m_capacity(d: DayState) -> Optional[float]:
    return float(d.capacity) if d.began_at else None


def _confidence(r: float, n: int) -> str:
    if abs(r) >= 0.75 and n >= 6:
        return "clear"
    if abs(r) >= 0.6:
        return "likely"
    return "faint"


def surface(days: list[DayState], limit: int = 2) -> list[dict]:
    """Return at most `limit` findings, strongest first, or nothing at all."""
    found: list[dict] = []

    def consider(pid: str, a, b, positive: str, negative: str) -> None:
        xs, ys = _paired(days, a, b)
        if len(xs) < MIN_DAYS:
            return
        r = _pearson(xs, ys)
        if r is None or abs(r) < MIN_R:
            return
        found.append(
            {
                "id": pid,
                "text": (positive if r > 0 else negative).format(n=len(xs)),
                "r": round(r, 2),
                "n": len(xs),
                "confidence": _confidence(r, len(xs)),
            }
        )

    consider(
        "sleep_mood",
        m_sleep,
        m_mood,
        positive=(
            "The nights you slept longer, the next day tended to sit a little "
            "higher. That's a shape across {n} days, not a rule."
        ),
        negative=(
            "Longer nights haven't been landing as better days lately. Worth "
            "knowing, across {n} days, and worth nothing more than knowing."
        ),
    )

    consider(
        "dismiss_mood",
        m_dismiss_ratio,
        m_mood,
        positive=(
            "You waved me off more on the days that felt better. It looks "
            "like you were busy living them. {n} days."
        ),
        negative=(
            "You waved me off more on the days that already felt heavy. "
            "No judgment in that at all. It looks like your capacity telling "
            "the truth before you had words for it. {n} days."
        ),
    )

    consider(
        "water_mood",
        m_water,
        m_mood,
        positive=(
            "Water and mood have been moving together over {n} days. Could be "
            "the water, could be that better days are easier to drink on."
        ),
        negative=(
            "Water and mood have been pulling opposite ways over {n} days. "
            "Probably noise. Flagging it in case it isn't."
        ),
    )

    consider(
        "capacity_dismiss",
        m_capacity,
        m_dismiss_ratio,
        positive=(
            "On the days you set capacity high you also waved me off more. "
            "You may be calling your capacity higher than the day turns out "
            "to be. {n} days."
        ),
        negative=(
            "When you set capacity low you took the check-ins, and when you "
            "set it high you didn't need them. That's a good read on yourself. "
            "{n} days."
        ),
    )

    found.sort(key=lambda f: abs(f["r"]), reverse=True)
    return found[:limit]


def dismiss_clock(days: list[DayState]) -> Optional[dict]:
    """Time-of-day clustering of dismissals.

    Surfaces only when one three-hour band holds at least half of them, and
    frames it as territory rather than as a lapse — the intent is that a user
    learns "2pm is a wall for me", which is self-knowledge they can plan around
    and which nothing else in their life is telling them.
    """
    hours: list[int] = []
    for d in days:
        for c in d.checkins:
            if c.dismissed and c.responded_at:
                try:
                    hours.append(int(c.responded_at[11:13]))
                except (ValueError, IndexError):
                    continue
    if len(hours) < 4:
        return None

    best_start, best_count = None, 0
    for start in range(0, 22):
        count = sum(1 for h in hours if start <= h < start + 3)
        if count > best_count:
            best_start, best_count = start, count

    if best_start is None or best_count / len(hours) < 0.5:
        return None

    return {
        "id": "dismiss_clock",
        "start_hour": best_start,
        "share": round(best_count / len(hours), 2),
        "text": (
            f"Most of the times you've waved me off land between "
            f"{best_start}:00 and {best_start + 3}:00. That stretch looks like "
            f"territory rather than coincidence. It may be worth knowing about yourself."
        ),
    }
