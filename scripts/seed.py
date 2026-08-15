"""Seed a week of history so The Window has something to draw.

The Window is the emotional payload of the whole submission and it needs seven
days of texture to land. This writes a plausible, deliberately un-triumphant
week: a hard Monday, a genuinely bad Wednesday, one day with no data at all,
and a slow lift toward the weekend. It should read as magic hour — not as a
success story, because a demo week where everything goes well is a demo of a
different product.

    python scripts/seed.py [--db gesture.db] [--days 7]
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gesture import db  # noqa: E402
from gesture.models import ActKind, CheckInWeight, Mode  # noqa: E402

# mood floor/ceiling, sleep, water, dismiss chance, acts, done ratio
SCENARIOS = [
    dict(label="heavy", mood=(1, 2), sleep=4.5, water=1, dismiss=0.75, acts=3, done=0.0),
    dict(label="flat",  mood=(2, 3), sleep=6.0, water=2, dismiss=0.5,  acts=2, done=0.5),
    dict(label="worst", mood=(1, 1), sleep=3.5, water=0, dismiss=0.9,  acts=1, done=0.0),
    dict(label="gone",  mood=None,   sleep=None, water=0, dismiss=0.0, acts=0, done=0.0),
    dict(label="lift",  mood=(3, 4), sleep=7.5, water=4, dismiss=0.25, acts=3, done=0.66),
    dict(label="good",  mood=(4, 5), sleep=8.0, water=5, dismiss=0.1,  acts=4, done=0.75),
    dict(label="steady",mood=(3, 4), sleep=7.0, water=3, dismiss=0.3,  acts=3, done=0.66),
]

TITLES = [
    ("hoops", "email the landlord"),
    ("juggling", "tidy one shelf"),
    ("tightrope", "the deck for Thursday"),
    ("balancing", "eat something proper"),
    ("trapeze", "close the tab I keep reopening"),
    ("juggling", "pharmacy"),
    ("hoops", "ring the surgery"),
]


def seed(db_path: str, days: int, seed_value: int = 7) -> None:
    rng = random.Random(seed_value)
    Path(db_path).unlink(missing_ok=True)
    db.reset(Path(db_path))

    real_now = db.now
    today = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    for i in range(days - 1, -1, -1):
        when = today - timedelta(days=i)
        sc = SCENARIOS[(days - 1 - i) % len(SCENARIOS)]
        date = when.date().isoformat()

        # Travel to that day so every timestamp written lands correctly.
        db.now = lambda w=when: w  # type: ignore[assignment]

        if sc["label"] == "gone":
            # A day the user never opened the app. It must render as absence,
            # not as a bad day — that distinction is the point of the model.
            continue

        capacity = {
            "heavy": 20, "flat": 45, "worst": 5, "lift": 60, "good": 85, "steady": 55,
        }[sc["label"]]

        day_id = db.begin_day(
            day=date,
            mode=Mode.CIRCUS,
            capacity=capacity,
            window_start="09:00",
            window_end="21:00",
            intention=None,
            sleep_hours=sc["sleep"],
        )

        chosen = rng.sample(TITLES, k=min(sc["acts"], len(TITLES)))
        act_ids = [db.add_act(day_id, ActKind(k), t) for k, t in chosen]
        for aid in act_ids[: int(len(act_ids) * sc["done"])]:
            db.update_act(aid, done=True, held=None)

        # Check-ins across the day, roughly every 90 minutes.
        for n in range(5):
            at = when.replace(hour=10) + timedelta(minutes=90 * n)
            db.now = lambda w=at: w  # type: ignore[assignment]
            cid = db.schedule_checkin(day_id, at, CheckInWeight.FULL)
            dismissed = rng.random() < sc["dismiss"]
            db.respond_checkin(
                cid,
                dismissed=dismissed,
                mood=None if dismissed or not sc["mood"] else rng.randint(*sc["mood"]),
                water=None if dismissed else (1 if rng.random() < 0.6 else None),
                note=None,
                anchor=None,
            )

    db.now = real_now  # type: ignore[assignment]
    print(f"Seeded {days} days into {db_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="gesture.db")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    seed(args.db, args.days, args.seed)
