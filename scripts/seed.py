"""Seed a week of history so The Window has something to draw.

    python scripts/seed.py [--db gesture.db] [--days 7] [--leave-today-empty]

The logic lives in `gesture/demo.py` so that application startup can share it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gesture.demo import seed  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="gesture.db")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument(
        "--leave-today-empty",
        action="store_true",
        help="Fill in history but leave today unbegun, so the Begin screen "
        "is still the first thing a visitor sees.",
    )
    args = ap.parse_args()

    n = seed(
        args.db,
        args.days,
        args.seed,
        leave_today_empty=args.leave_today_empty,
    )
    print(f"Seeded {n} days into {args.db}")
