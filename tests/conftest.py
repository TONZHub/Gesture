from __future__ import annotations

from datetime import datetime, timedelta

from gesture.models import Act, ActKind, CheckIn, CheckInWeight, DayState, Mode

BASE = datetime(2026, 8, 15, 9, 0, 0)


def make_checkin(
    i: int,
    *,
    dismissed: bool = False,
    mood: int | None = None,
    water: int | None = None,
    responded: bool = True,
    at: datetime | None = None,
) -> CheckIn:
    when = at or (BASE + timedelta(minutes=60 * i))
    return CheckIn(
        id=i,
        scheduled_for=when.isoformat(timespec="seconds"),
        responded_at=when.isoformat(timespec="seconds") if responded else None,
        weight=CheckInWeight.FULL,
        dismissed=dismissed,
        mood=mood,
        water=water,
    )


def make_day(
    *,
    date: str = "2026-08-15",
    capacity: int = 50,
    mode: Mode = Mode.CIRCUS,
    checkins: list[CheckIn] | None = None,
    acts: list[Act] | None = None,
    sleep_hours: float | None = None,
    began: bool = True,
    window_end: str = "21:00",
) -> DayState:
    cis = checkins or []
    return DayState(
        date=date,
        mode=mode,
        capacity=capacity,
        window_start="09:00",
        window_end=window_end,
        began_at=BASE.isoformat(timespec="seconds") if began else None,
        acts=acts or [],
        checkins=cis,
        water_total=sum(c.water or 0 for c in cis),
        sleep_hours=sleep_hours,
    )


def make_act(i: int, kind: ActKind, title: str = "a thing", **kw) -> Act:
    return Act(id=i, kind=kind, title=title, **kw)
