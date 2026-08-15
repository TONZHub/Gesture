"""A week of plausible history, for demos and for The Window.

Two callers:

* `scripts/seed.py`, run by hand before filming or before showing anyone.
* Application startup, when `GESTURE_SEED_ON_EMPTY` is set — which is how the
  hosted demo stays worth looking at. Render's free disk is ephemeral, so every
  deploy and every spin-down wipes the database. Without this, a judge clicking
  the link lands on "Not enough sky yet" and never sees the one screen the whole
  submission is built around.

The week is deliberately un-triumphant: a hard Monday, a genuinely bad
Wednesday, one day with no data at all, and a slow lift toward the weekend. A
demo week where everything goes well is a demo of a different product.

`leave_today_empty` matters for the hosted build. Seeding today would drop the
visitor straight onto the day screen with the day already begun, and they would
never see Begin — the first of the three screens. So history fills in behind
them and today stays theirs to start.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from . import db
from .models import ActKind, CheckInWeight, Mode

# mood floor/ceiling, sleep, water, dismiss chance, acts, done ratio
SCENARIOS = [
    dict(label="heavy", mood=(1, 2), sleep=4.5, water=1, dismiss=0.75, acts=3, done=0.0),
    dict(label="flat",  mood=(2, 3), sleep=6.0, water=2, dismiss=0.5,  acts=2, done=0.5),
    dict(label="worst", mood=(1, 1), sleep=3.5, water=0, dismiss=0.9,  acts=1, done=0.0),
    dict(label="gone",  mood=None,   sleep=None, water=0, dismiss=0.0, acts=0, done=0.0),
    dict(label="lift",  mood=(3, 4), sleep=7.5, water=4, dismiss=0.25, acts=3, done=0.66),
    dict(label="good",  mood=(4, 5), sleep=8.0, water=5, dismiss=0.1,  acts=4, done=0.75),
    dict(label="steady", mood=(3, 4), sleep=7.0, water=3, dismiss=0.3, acts=3, done=0.66),
]

CAPACITIES = {
    "heavy": 20, "flat": 45, "worst": 5, "lift": 60, "good": 85, "steady": 55,
}

TITLES = [
    ("hoops", "email the landlord"),
    ("juggling", "tidy one shelf"),
    ("tightrope", "the deck for Thursday"),
    ("balancing", "eat something proper"),
    ("trapeze", "close the tab I keep reopening"),
    ("juggling", "pharmacy"),
    ("hoops", "ring the surgery"),
]


def seed(
    db_path: Optional[str] = None,
    days: int = 7,
    seed_value: int = 7,
    *,
    fresh: bool = True,
    leave_today_empty: bool = False,
) -> int:
    """Write `days` of history. Returns the number of days actually written."""
    rng = random.Random(seed_value)

    if fresh and db_path:
        Path(db_path).unlink(missing_ok=True)
        db.reset(Path(db_path))
    else:
        db.connect()

    real_now = db.now
    today = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    written = 0

    try:
        for i in range(days - 1, -1, -1):
            if leave_today_empty and i == 0:
                continue

            when = today - timedelta(days=i)
            sc = SCENARIOS[(days - 1 - i) % len(SCENARIOS)]
            date = when.date().isoformat()

            # Travel to that day so every timestamp written lands correctly.
            db.now = lambda w=when: w  # type: ignore[assignment]

            if sc["label"] == "gone":
                # A day the user never opened the app. It must render as
                # absence, not as a bad day — that distinction is the point.
                continue

            day_id = db.begin_day(
                day=date,
                mode=Mode.CIRCUS,
                capacity=CAPACITIES[str(sc["label"])],
                window_start="09:00",
                window_end="21:00",
                intention=None,
                sleep_hours=sc["sleep"],
            )

            chosen = rng.sample(TITLES, k=min(int(sc["acts"]), len(TITLES)))
            act_ids = [db.add_act(day_id, ActKind(k), t) for k, t in chosen]
            for aid in act_ids[: int(len(act_ids) * float(sc["done"]))]:
                db.update_act(aid, done=True, held=None)

            for n in range(5):
                at = when.replace(hour=10) + timedelta(minutes=90 * n)
                db.now = lambda w=at: w  # type: ignore[assignment]
                cid = db.schedule_checkin(day_id, at, CheckInWeight.FULL)
                dismissed = rng.random() < float(sc["dismiss"])
                db.respond_checkin(
                    cid,
                    dismissed=dismissed,
                    mood=(
                        None
                        if dismissed or not sc["mood"]
                        else rng.randint(*sc["mood"])  # type: ignore[misc]
                    ),
                    water=None if dismissed else (1 if rng.random() < 0.6 else None),
                    note=None,
                    anchor=None,
                )
            written += 1
    finally:
        db.now = real_now  # type: ignore[assignment]

    return written


def seed_if_empty() -> int:
    """Fill in history only when there is none. Never touches real data."""
    if db.has_any_days():
        return 0
    return seed(fresh=False, leave_today_empty=True)
