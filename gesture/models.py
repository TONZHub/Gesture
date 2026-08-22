"""Domain vocabulary.

The names in this file are the product. `held` is not `skipped`. `dismissed`
is not `missed`. A day is `closed` at the curtain call, never `completed`.
If a word here starts sounding like a productivity app, it is a bug.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class Mode(str, Enum):
    """The two doors into the same house."""

    CIRCUS = "circus"
    QUIET = "quiet"


class ActKind(str, Enum):
    """Task types, named for the cognitive demand they actually make."""

    JUGGLING = "juggling"      # many small things, context-switching is the job
    HOOPS = "hoops"            # a wall in front of it; you leap, you don't carry
    BALANCING = "balancing"    # the one thing that must stay upright today
    TIGHTROPE = "tightrope"    # deep focus, one foot in front of the other
    TRAPEZE = "trapeze"        # the letting go, the transition, the release
    PLATES = "plates"          # recurring upkeep; a touch so it doesn't fall


class StateAnchor(str, Enum):
    """Where you are stuck. These look identical from outside and need
    completely different responses — which is the whole point of Gesture."""

    CANT_START = "cant_start"
    FORGOT_FLOW = "forgot_flow"
    SCARED = "scared"
    ZERO_CAPACITY = "zero_capacity"
    BRAIN_DUMP = "brain_dump"


class CheckInWeight(str, Enum):
    """How much the check-in asks for.

    The interface gets *quieter* as it learns you, never busier. Weight walks
    down when you dismiss and back up only when you engage.
    """

    FULL = "full"        # mood + water + note + a nudge toward an act
    LIGHT = "light"      # mood + water
    FEATHER = "feather"  # presence only; nothing is asked of you


# --------------------------------------------------------------------------
# Requests
# --------------------------------------------------------------------------


class ActIn(BaseModel):
    kind: ActKind
    title: str = Field(min_length=1, max_length=280)


class BeginIn(BaseModel):
    """The one time per day the user is asked to set the shape."""

    mode: Mode = Mode.CIRCUS
    capacity: int = Field(default=50, ge=0, le=100)
    window_start: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    window_end: str = Field(default="21:00", pattern=r"^\d{2}:\d{2}$")
    intention: Optional[str] = Field(default=None, max_length=1000)
    acts: list[ActIn] = Field(default_factory=list)
    sleep_hours: Optional[float] = Field(default=None, ge=0, le=24)


class CheckInIn(BaseModel):
    """A response to a check-in. Every field is optional — including all of
    them at once, which is what an Intentional Dismiss is."""

    dismissed: bool = False
    mood: Optional[int] = Field(default=None, ge=1, le=5)
    water: Optional[int] = Field(default=None, ge=0, le=20)
    note: Optional[str] = Field(default=None, max_length=2000)
    anchor: Optional[StateAnchor] = None


class StuckIn(BaseModel):
    """The 'I am stuck right now' door, available from any screen."""

    anchor: Optional[StateAnchor] = None
    text: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def has_something_to_interpret(self) -> "StuckIn":
        if self.anchor is None and not (self.text and self.text.strip()):
            raise ValueError("Choose what feels closest or tell Barnaby what is happening.")
        return self


class ActUpdateIn(BaseModel):
    done: Optional[bool] = None
    held: Optional[bool] = None


# --------------------------------------------------------------------------
# Responses
# --------------------------------------------------------------------------


class Act(BaseModel):
    id: int
    kind: ActKind
    title: str
    held: bool = False
    done: bool = False


class CheckIn(BaseModel):
    id: int
    scheduled_for: str
    responded_at: Optional[str] = None
    weight: CheckInWeight
    dismissed: bool = False
    mood: Optional[int] = None
    water: Optional[int] = None
    note: Optional[str] = None
    anchor: Optional[StateAnchor] = None


class DayState(BaseModel):
    date: str
    mode: Mode
    capacity: int
    window_start: str
    window_end: str
    intention: Optional[str] = None
    began_at: Optional[str] = None
    closed_at: Optional[str] = None
    acts: list[Act] = Field(default_factory=list)
    checkins: list[CheckIn] = Field(default_factory=list)
    water_total: int = 0
    sleep_hours: Optional[float] = None


class Utterance(BaseModel):
    """Anything Barnaby says, plus how it got said.

    `source` is surfaced in the UI on purpose: the demo should be able to show
    that the offline voice and the model voice are held to the same contract.
    """

    text: str
    source: str  # "strands" | "local" | "guard-fallback"
    face: str = "soft"  # soft | worried | relieved | delighted | listening


class StuckDecision(BaseModel):
    """A bounded interpretation of a stuck moment."""

    anchor: StateAnchor
    reflection: str = Field(min_length=1, max_length=360)
    micro_gesture: str = Field(min_length=1, max_length=240)
    follow_up_seconds: int = Field(default=60, ge=0, le=300)
    source: str  # "strands" | "local" | "guard-fallback"
    used_context: list[str] = Field(default_factory=list)
    guard: str = "passed"
