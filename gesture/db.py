"""SQLite storage.

One file, no migrations, no server. A hackathon judge should be able to clone
this and run it without provisioning anything, and a neurodivergent user
should be able to delete one file and have their data actually be gone.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional

from .config import settings
from .models import (
    Act,
    ActKind,
    CheckIn,
    CheckInWeight,
    DayState,
    Mode,
    StateAnchor,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS days (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    date          TEXT NOT NULL UNIQUE,
    mode          TEXT NOT NULL DEFAULT 'circus',
    capacity      INTEGER NOT NULL DEFAULT 50,
    window_start  TEXT NOT NULL DEFAULT '09:00',
    window_end    TEXT NOT NULL DEFAULT '21:00',
    intention     TEXT,
    sleep_hours   REAL,
    began_at      TEXT,
    closed_at     TEXT
);

CREATE TABLE IF NOT EXISTS acts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    day_id      INTEGER NOT NULL REFERENCES days(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,
    title       TEXT NOT NULL,
    held        INTEGER NOT NULL DEFAULT 0,
    done_at     TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checkins (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    day_id         INTEGER NOT NULL REFERENCES days(id) ON DELETE CASCADE,
    scheduled_for  TEXT NOT NULL,
    responded_at   TEXT,
    weight         TEXT NOT NULL DEFAULT 'full',
    dismissed      INTEGER NOT NULL DEFAULT 0,
    mood           INTEGER,
    water          INTEGER,
    note           TEXT,
    anchor         TEXT
);

CREATE TABLE IF NOT EXISTS voice_log (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT NOT NULL,
    source   TEXT NOT NULL,
    text     TEXT NOT NULL,
    blocked  INTEGER NOT NULL DEFAULT 0,
    reason   TEXT
);

CREATE INDEX IF NOT EXISTS idx_acts_day ON acts(day_id);
CREATE INDEX IF NOT EXISTS idx_checkins_day ON checkins(day_id);
"""


def now() -> datetime:
    """Single source of 'now' so tests and the seeder can travel in time."""
    return datetime.now()


def today() -> str:
    return now().date().isoformat()


_conn: Optional[sqlite3.Connection] = None


def connect(path: Optional[Path] = None) -> sqlite3.Connection:
    global _conn
    if _conn is None:
        target = Path(path or settings.db_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(target), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA foreign_keys = ON")
        _conn.executescript(SCHEMA)
        _conn.commit()
    return _conn


def reset(path: Optional[Path] = None) -> sqlite3.Connection:
    """Drop the cached connection. Used by tests and by `seed.py`."""
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
    return connect(path)


@contextmanager
def tx() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# --------------------------------------------------------------------------
# Days
# --------------------------------------------------------------------------


def get_day_row(day: Optional[str] = None) -> Optional[sqlite3.Row]:
    conn = connect()
    row = conn.execute(
        "SELECT * FROM days WHERE date = ?", (day or today(),)
    ).fetchone()
    return row


def begin_day(
    *,
    day: Optional[str] = None,
    mode: Mode,
    capacity: int,
    window_start: str,
    window_end: str,
    intention: Optional[str],
    sleep_hours: Optional[float],
) -> int:
    """Set the shape of the day. Idempotent — beginning twice re-shapes rather
    than erroring, because being asked 'are you sure' is friction."""
    d = day or today()
    with tx() as conn:
        conn.execute(
            """
            INSERT INTO days (date, mode, capacity, window_start, window_end,
                              intention, sleep_hours, began_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                mode=excluded.mode,
                capacity=excluded.capacity,
                window_start=excluded.window_start,
                window_end=excluded.window_end,
                intention=excluded.intention,
                sleep_hours=COALESCE(excluded.sleep_hours, days.sleep_hours),
                began_at=COALESCE(days.began_at, excluded.began_at)
            """,
            (
                d,
                mode.value,
                capacity,
                window_start,
                window_end,
                intention,
                sleep_hours,
                now().isoformat(timespec="seconds"),
            ),
        )
    row = get_day_row(d)
    assert row is not None
    return int(row["id"])


def ensure_day(day: Optional[str] = None) -> sqlite3.Row:
    """Return today's row, creating an unbegun default if the user has not
    pressed Begin yet. A user who opens the app at 3am without beginning still
    gets to be met."""
    d = day or today()
    row = get_day_row(d)
    if row is None:
        with tx() as conn:
            conn.execute("INSERT INTO days (date) VALUES (?)", (d,))
        row = get_day_row(d)
    assert row is not None
    return row


def set_capacity(capacity: int, day: Optional[str] = None) -> None:
    ensure_day(day)
    with tx() as conn:
        conn.execute(
            "UPDATE days SET capacity = ? WHERE date = ?", (capacity, day or today())
        )


def set_mode(mode: Mode, day: Optional[str] = None) -> None:
    # ensure_day first: the door ("how do you like to be talked to?") is
    # answered *before* Begin, so on a fresh day there is no row to update yet
    # and the choice would be silently dropped.
    ensure_day(day)
    with tx() as conn:
        conn.execute(
            "UPDATE days SET mode = ? WHERE date = ?", (mode.value, day or today())
        )


def close_day(day: Optional[str] = None) -> None:
    """The curtain call. Not 'complete' — closed."""
    with tx() as conn:
        conn.execute(
            "UPDATE days SET closed_at = ? WHERE date = ?",
            (now().isoformat(timespec="seconds"), day or today()),
        )


def record_sleep(hours: float, day: Optional[str] = None) -> None:
    with tx() as conn:
        conn.execute(
            "UPDATE days SET sleep_hours = ? WHERE date = ?", (hours, day or today())
        )


# --------------------------------------------------------------------------
# Acts
# --------------------------------------------------------------------------


def add_act(day_id: int, kind: ActKind, title: str) -> int:
    with tx() as conn:
        cur = conn.execute(
            "INSERT INTO acts (day_id, kind, title, created_at) VALUES (?, ?, ?, ?)",
            (day_id, kind.value, title, now().isoformat(timespec="seconds")),
        )
    return int(cur.lastrowid)


def update_act(act_id: int, *, done: Optional[bool], held: Optional[bool]) -> None:
    with tx() as conn:
        if done is not None:
            conn.execute(
                "UPDATE acts SET done_at = ? WHERE id = ?",
                (now().isoformat(timespec="seconds") if done else None, act_id),
            )
        if held is not None:
            conn.execute(
                "UPDATE acts SET held = ? WHERE id = ?", (1 if held else 0, act_id)
            )


def acts_for(day_id: int) -> list[Act]:
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM acts WHERE day_id = ? ORDER BY id", (day_id,)
    ).fetchall()
    return [
        Act(
            id=r["id"],
            kind=ActKind(r["kind"]),
            title=r["title"],
            held=bool(r["held"]),
            done=r["done_at"] is not None,
        )
        for r in rows
    ]


# --------------------------------------------------------------------------
# Check-ins
# --------------------------------------------------------------------------


def schedule_checkin(
    day_id: int, scheduled_for: datetime, weight: CheckInWeight
) -> int:
    with tx() as conn:
        cur = conn.execute(
            "INSERT INTO checkins (day_id, scheduled_for, weight) VALUES (?, ?, ?)",
            (day_id, scheduled_for.isoformat(timespec="seconds"), weight.value),
        )
    return int(cur.lastrowid)


def pending_checkin(day_id: int) -> Optional[sqlite3.Row]:
    """The oldest scheduled-but-unanswered check-in whose time has arrived."""
    conn = connect()
    return conn.execute(
        """
        SELECT * FROM checkins
        WHERE day_id = ? AND responded_at IS NULL AND scheduled_for <= ?
        ORDER BY scheduled_for LIMIT 1
        """,
        (day_id, now().isoformat(timespec="seconds")),
    ).fetchone()


def next_scheduled(day_id: int) -> Optional[sqlite3.Row]:
    conn = connect()
    return conn.execute(
        """
        SELECT * FROM checkins
        WHERE day_id = ? AND responded_at IS NULL
        ORDER BY scheduled_for LIMIT 1
        """,
        (day_id,),
    ).fetchone()


def respond_checkin(
    checkin_id: int,
    *,
    dismissed: bool,
    mood: Optional[int],
    water: Optional[int],
    note: Optional[str],
    anchor: Optional[StateAnchor],
) -> None:
    with tx() as conn:
        conn.execute(
            """
            UPDATE checkins
            SET responded_at = ?, dismissed = ?, mood = ?, water = ?,
                note = ?, anchor = ?
            WHERE id = ?
            """,
            (
                now().isoformat(timespec="seconds"),
                1 if dismissed else 0,
                mood,
                water,
                note,
                anchor.value if anchor else None,
                checkin_id,
            ),
        )


def checkins_for(day_id: int) -> list[CheckIn]:
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM checkins WHERE day_id = ? ORDER BY scheduled_for, id",
        (day_id,),
    ).fetchall()
    return [_checkin(r) for r in rows]


def _checkin(r: sqlite3.Row) -> CheckIn:
    return CheckIn(
        id=r["id"],
        scheduled_for=r["scheduled_for"],
        responded_at=r["responded_at"],
        weight=CheckInWeight(r["weight"]),
        dismissed=bool(r["dismissed"]),
        mood=r["mood"],
        water=r["water"],
        note=r["note"],
        anchor=StateAnchor(r["anchor"]) if r["anchor"] else None,
    )


def answered_checkins(day_id: int) -> list[CheckIn]:
    return [c for c in checkins_for(day_id) if c.responded_at]


# --------------------------------------------------------------------------
# Assembled state
# --------------------------------------------------------------------------


def day_state(day: Optional[str] = None) -> DayState:
    row = ensure_day(day)
    checkins = checkins_for(int(row["id"]))
    return DayState(
        date=row["date"],
        mode=Mode(row["mode"]),
        capacity=int(row["capacity"]),
        window_start=row["window_start"],
        window_end=row["window_end"],
        intention=row["intention"],
        began_at=row["began_at"],
        closed_at=row["closed_at"],
        acts=acts_for(int(row["id"])),
        checkins=checkins,
        water_total=sum(c.water or 0 for c in checkins),
        sleep_hours=row["sleep_hours"],
    )


def has_any_days() -> bool:
    """Whether this database holds any history at all. Used to decide if the
    demo seed should run, so that it can never overwrite real data."""
    conn = connect()
    return conn.execute("SELECT 1 FROM days LIMIT 1").fetchone() is not None


def recent_days(n: int = 7, end: Optional[str] = None) -> list[DayState]:
    """The last `n` calendar days ending at `end`, including days that never
    happened. A week with holes in it is still a week, and The Window must be
    able to render the holes."""
    end_date = date.fromisoformat(end) if end else now().date()
    out: list[DayState] = []
    for i in range(n - 1, -1, -1):
        d = (end_date - timedelta(days=i)).isoformat()
        row = get_day_row(d)
        if row is None:
            out.append(
                DayState(
                    date=d,
                    mode=Mode.CIRCUS,
                    capacity=0,
                    window_start="09:00",
                    window_end="21:00",
                )
            )
        else:
            out.append(day_state(d))
    return out


# --------------------------------------------------------------------------
# Voice log — every line Barnaby says, including the ones the guard stopped
# --------------------------------------------------------------------------


def log_voice(source: str, text: str, blocked: bool, reason: Optional[str]) -> None:
    with tx() as conn:
        conn.execute(
            "INSERT INTO voice_log (ts, source, text, blocked, reason) VALUES (?,?,?,?,?)",
            (
                now().isoformat(timespec="seconds"),
                source,
                text,
                1 if blocked else 0,
                reason,
            ),
        )


def voice_log(limit: int = 50) -> list[dict]:
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM voice_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]
