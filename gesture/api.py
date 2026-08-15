"""HTTP surface.

Deliberately small. Three screens, five verbs, one stream.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from . import db
from .agent import patterns, rhythm, sky
from .agent.acts import balls_for_capacity, catalogue, triage
from .agent.barnaby import Barnaby
from .devices import bus, get_device
from .models import ActUpdateIn, BeginIn, CheckInIn, DayState, Mode, StuckIn

router = APIRouter(prefix="/api")

# One Barnaby per mode, kept alive so the Strands agent is built once.
_barnabys: dict[Mode, Barnaby] = {}

# Which check-in we have already made Barnaby jiggle for, so that polling the
# state endpoint does not set him off every two seconds.
_jiggled_for: set[int] = set()


def barnaby_for(mode: Mode) -> Barnaby:
    if mode not in _barnabys:
        _barnabys[mode] = Barnaby(mode)
    return _barnabys[mode]


def _day_id(day: Optional[str] = None) -> int:
    return int(db.ensure_day(day)["id"])


def _schedule_next(day: DayState, now: datetime) -> Optional[int]:
    """Book the next check-in, unless the day's window has closed."""
    r = rhythm.compute(day, now)
    if r.next_at is None:
        return None
    return db.schedule_checkin(_day_id(day.date), r.next_at, r.weight)


# --------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------


@router.get("/state")
def get_state() -> dict:
    day = db.day_state()
    now = db.now()
    in_play, held = triage(day.acts, day.capacity)

    pending = db.pending_checkin(_day_id())
    due = pending is not None

    if due and pending["id"] not in _jiggled_for:
        # A check-in has come due. This is the moment the hardware exists for.
        _jiggled_for.add(int(pending["id"]))
        device = get_device()
        device.face("worried")
        device.jiggle("checkin", intensity=0.5 if day.capacity < 40 else 0.7)

    next_row = db.next_scheduled(_day_id())

    return {
        "day": json.loads(day.model_dump_json()),
        "in_play": [json.loads(a.model_dump_json()) for a in in_play],
        "held": [json.loads(a.model_dump_json()) for a in held],
        "balls": balls_for_capacity(day.capacity),
        "acts_catalogue": catalogue(day.mode),
        "checkin_due": due,
        "pending_checkin_id": int(pending["id"]) if pending else None,
        "pending_weight": pending["weight"] if pending else None,
        "next_checkin_at": next_row["scheduled_for"] if next_row else None,
        "rhythm": rhythm.explain(day, now),
        "device": get_device().name,
        "curtain_ready": _curtain_ready(day, now),
    }


def _curtain_ready(day: DayState, now: datetime) -> bool:
    if day.closed_at:
        return False
    if not day.began_at:
        return False
    hh, mm = day.window_end.split(":")
    return now >= now.replace(
        hour=int(hh), minute=int(mm), second=0, microsecond=0
    )


@router.get("/greeting")
def greeting() -> dict:
    day = db.day_state()
    b = barnaby_for(day.mode)
    u = b.welcome() if not day.began_at else b.overture(day)
    return json.loads(u.model_dump_json())


# --------------------------------------------------------------------------
# Begin
# --------------------------------------------------------------------------


@router.post("/begin")
def begin(payload: BeginIn) -> dict:
    day_id = db.begin_day(
        mode=payload.mode,
        capacity=payload.capacity,
        window_start=payload.window_start,
        window_end=payload.window_end,
        intention=payload.intention,
        sleep_hours=payload.sleep_hours,
    )
    for act in payload.acts:
        db.add_act(day_id, act.kind, act.title)

    day = db.day_state()
    now = db.now()
    in_play, held = triage(day.acts, day.capacity)

    # Capacity zero means Barnaby holds everything, including the schedule.
    # Booking check-ins for someone who told you they have nothing left is
    # exactly the kind of thing this app exists to not do.
    if payload.capacity > 0:
        _schedule_next(day, now)

    device = get_device()
    device.face("delighted")
    device.project("overture" if day.mode is Mode.CIRCUS else "dim")

    u = barnaby_for(day.mode).begin_ack(in_play, held, day.capacity)
    return {
        "barnaby": json.loads(u.model_dump_json()),
        "in_play": [json.loads(a.model_dump_json()) for a in in_play],
        "held": [json.loads(a.model_dump_json()) for a in held],
        "rhythm": rhythm.explain(day, now),
    }


# --------------------------------------------------------------------------
# Check-in
# --------------------------------------------------------------------------


@router.get("/checkin")
def get_checkin() -> dict:
    day = db.day_state()
    pending = db.pending_checkin(_day_id())
    if pending is None:
        nxt = db.next_scheduled(_day_id())
        return {
            "due": False,
            "next_at": nxt["scheduled_for"] if nxt else None,
        }
    weight = pending["weight"]
    streak = rhythm.dismiss_streak(day)
    u = barnaby_for(day.mode).checkin_prompt(weight, streak)
    return {
        "due": True,
        "id": int(pending["id"]),
        "weight": weight,
        "barnaby": json.loads(u.model_dump_json()),
        "dismiss_streak": streak,
    }


@router.post("/checkin")
def respond_checkin(payload: CheckInIn) -> dict:
    day_id = _day_id()
    pending = db.pending_checkin(day_id)
    if pending is None:
        raise HTTPException(status_code=409, detail="No check-in is waiting.")

    db.respond_checkin(
        int(pending["id"]),
        dismissed=payload.dismissed,
        mood=payload.mood,
        water=payload.water,
        note=payload.note,
        anchor=payload.anchor,
    )

    day = db.day_state()
    now = db.now()
    b = barnaby_for(day.mode)
    device = get_device()
    device.still()

    if payload.dismissed:
        streak = rhythm.dismiss_streak(day)
        u = b.dismiss_ack(streak)
        device.face("soft")
    else:
        u = b.checkin_ack(payload.mood, payload.water)
        device.face(u.face)

    _schedule_next(day, now)
    day = db.day_state()

    return {
        "barnaby": json.loads(u.model_dump_json()),
        "rhythm": rhythm.explain(day, now),
        "next_checkin_at": (
            db.next_scheduled(day_id)["scheduled_for"]
            if db.next_scheduled(day_id)
            else None
        ),
    }


# --------------------------------------------------------------------------
# Stuck — reachable from any screen, always
# --------------------------------------------------------------------------


@router.post("/stuck")
def stuck(payload: StuckIn) -> dict:
    day = db.day_state()
    b = barnaby_for(day.mode)
    u = b.stuck(payload.anchor, day, payload.text)

    device = get_device()
    device.face("listening")
    if payload.anchor.value == "zero_capacity":
        # Drop capacity to nothing and stop asking anything of them today.
        db.set_capacity(0)
        device.project("dim")
    return json.loads(u.model_dump_json())


# --------------------------------------------------------------------------
# Acts
# --------------------------------------------------------------------------


@router.patch("/acts/{act_id}")
def update_act(act_id: int, payload: ActUpdateIn) -> dict:
    db.update_act(act_id, done=payload.done, held=payload.held)
    day = db.day_state()
    in_play, held = triage(day.acts, day.capacity)
    if payload.done:
        get_device().celebrate()
    return {
        "in_play": [json.loads(a.model_dump_json()) for a in in_play],
        "held": [json.loads(a.model_dump_json()) for a in held],
    }


@router.post("/capacity/{value}")
def set_capacity(value: int) -> dict:
    if not 0 <= value <= 100:
        raise HTTPException(status_code=422, detail="Capacity is 0-100.")
    db.set_capacity(value)
    day = db.day_state()
    in_play, held = triage(day.acts, day.capacity)
    return {
        "balls": balls_for_capacity(value),
        "in_play": [json.loads(a.model_dump_json()) for a in in_play],
        "held": [json.loads(a.model_dump_json()) for a in held],
        "rhythm": rhythm.explain(day, db.now()),
    }


@router.post("/mode/{mode}")
def set_mode(mode: Mode) -> dict:
    db.set_mode(mode)
    get_device().project("overture" if mode is Mode.CIRCUS else "dim")
    return {"mode": mode.value}


# --------------------------------------------------------------------------
# The Window
# --------------------------------------------------------------------------


@router.get("/window")
def window(days: int = 7) -> dict:
    days = max(1, min(days, 30))
    history = db.recent_days(days)
    found = patterns.surface(history)
    clock = patterns.dismiss_clock(history)
    if clock:
        found.append(clock)
    return {"sky": sky.render(history), "patterns": found}


# --------------------------------------------------------------------------
# The curtain call
# --------------------------------------------------------------------------


@router.post("/curtain")
def curtain() -> dict:
    day = db.day_state()
    b = barnaby_for(day.mode)
    u = b.curtain_call(day)
    lines = b.curtain_lines(day)
    db.close_day()

    device = get_device()
    device.project("curtain")
    device.celebrate()
    device.face("delighted")

    return {
        "barnaby": json.loads(u.model_dump_json()),
        "lines": lines,
        "zero_capacity": not lines,
    }


# --------------------------------------------------------------------------
# The device
# --------------------------------------------------------------------------


@router.post("/barnaby/pet")
def pet() -> dict:
    get_device().pet()
    return {"ok": True}


@router.post("/barnaby/nudge")
def nudge() -> dict:
    """Emergency grounding, triggered by the user.

    Someone who knows they have dissociated can reach for this. It is the one
    place in the app where Barnaby is loud on purpose.
    """
    d = get_device()
    d.face("worried")
    d.jiggle("grounding", intensity=0.85)
    return {"ok": True}


@router.get("/events")
async def events() -> StreamingResponse:
    q = bus.subscribe()

    async def stream():
        try:
            # Catch the new listener up before streaming anything else: if a
            # check-in came due a moment ago, this tab still needs to see
            # Barnaby shaking.
            yield f"event: sync\ndata: {json.dumps(get_device().state())}\n\n"
            while True:
                for ev in list(bus.drain(q)):
                    yield f"event: {ev.kind}\ndata: {json.dumps(ev.payload)}\n\n"
                await asyncio.sleep(0.25)
        finally:
            bus.unsubscribe(q)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/voice-log")
def voice_log(limit: int = 40) -> dict:
    """Every line Barnaby has said, including the ones the guard stopped.

    Exposed on purpose. "The personality is enforced in code" is a claim, and
    a claim you can watch working is worth more than one in a README.
    """
    return {"entries": db.voice_log(limit)}


# --------------------------------------------------------------------------
# Demo helpers
# --------------------------------------------------------------------------


@router.post("/demo/due-now")
def demo_due_now() -> dict:
    """Pull the next scheduled check-in forward to right now.

    An adaptive hourly rhythm is impossible to show in a three-minute demo
    video without this.
    """
    day_id = _day_id()
    nxt = db.next_scheduled(day_id)
    if nxt is None:
        day = db.day_state()
        r = rhythm.compute(day, db.now())
        cid = db.schedule_checkin(day_id, db.now(), r.weight)
    else:
        cid = int(nxt["id"])
        with db.tx() as conn:
            conn.execute(
                "UPDATE checkins SET scheduled_for = ? WHERE id = ?",
                (db.now().isoformat(timespec="seconds"), cid),
            )
    _jiggled_for.discard(cid)
    return {"ok": True, "checkin_id": cid}
