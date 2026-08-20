"""The six acts.

A to-do list sorts tasks by when they are due. Gesture sorts them by what they
cost you to do, because for an executive-dysfunctional brain those are wildly
different numbers. "Reply to Dad" and "Reply to landlord" are the same size on
a calendar and nowhere near the same size in a body.

Each act has a Circus name and a Quiet name. Same taxonomy, two vocabularies —
the Quiet names carry no metaphor to translate through.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import ActKind, Mode


@dataclass(frozen=True)
class ActProfile:
    kind: ActKind
    circus_name: str
    quiet_name: str
    circus_blurb: str
    quiet_blurb: str
    emoji: str
    #: Roughly how much executive load one act of this kind takes, used to
    #: decide how many acts fit inside today's capacity.
    weight: float

    def name(self, mode: Mode) -> str:
        return self.circus_name if mode is Mode.CIRCUS else self.quiet_name

    def blurb(self, mode: Mode) -> str:
        return self.circus_blurb if mode is Mode.CIRCUS else self.quiet_blurb


PROFILES: dict[ActKind, ActProfile] = {
    ActKind.JUGGLING: ActProfile(
        kind=ActKind.JUGGLING,
        circus_name="Juggling",
        quiet_name="Several small things",
        circus_blurb="Lots of balls, all moving. Barnaby hands you one at a time.",
        quiet_blurb="Several small things that need doing. One at a time.",
        emoji="🤹",
        weight=1.0,
    ),
    ActKind.HOOPS: ActProfile(
        kind=ActKind.HOOPS,
        circus_name="Hoops",
        quiet_name="The hard one",
        circus_blurb="The one with a wall in front of it. You don't carry it — you leap.",
        quiet_blurb="The one you have been avoiding. It is allowed to be hard.",
        emoji="🔵",
        weight=2.0,
    ),
    ActKind.BALANCING: ActProfile(
        kind=ActKind.BALANCING,
        circus_name="Balancing",
        quiet_name="The one that matters",
        circus_blurb="The one thing that just has to stay upright today.",
        quiet_blurb="The single thing that needs to stay standing. Not finished. Standing.",
        emoji="⚖️",
        weight=1.0,
    ),
    ActKind.TIGHTROPE: ActProfile(
        kind=ActKind.TIGHTROPE,
        circus_name="Tightrope",
        quiet_name="Deep focus",
        circus_blurb="One foot in front of the other. Don't look down.",
        quiet_blurb="The thing that needs uninterrupted attention.",
        emoji="🎪",
        weight=2.0,
    ),
    ActKind.TRAPEZE: ActProfile(
        kind=ActKind.TRAPEZE,
        circus_name="Trapeze",
        quiet_name="Letting go",
        circus_blurb="The thing you release before you can catch the next one.",
        quiet_blurb="Something to finish with, or put down, before moving on.",
        emoji="🎭",
        weight=1.5,
    ),
    ActKind.PLATES: ActProfile(
        kind=ActKind.PLATES,
        circus_name="Plate spinning",
        quiet_name="Keeping things going",
        circus_blurb="The ones that never finish — they just wobble if you don't"
        " tap them. You don't carry a plate; you touch it and move on.",
        quiet_blurb="Ongoing things that need a small touch now and then, not"
        " finishing. Just enough that they don't fall over.",
        emoji="🍽️",
        # The lightest thing on the list on purpose: on a bad day, keeping one
        # plate from crashing is a real, whole act — so it's handed over first.
        weight=0.5,
    ),
}


def profile(kind: ActKind) -> ActProfile:
    return PROFILES[kind]


def catalogue(mode: Mode) -> list[dict]:
    """Everything the Begin screen needs to render the act picker."""
    return [
        {
            "kind": p.kind.value,
            "name": p.name(mode),
            "blurb": p.blurb(mode),
            "emoji": p.emoji,
        }
        for p in PROFILES.values()
    ]


# --------------------------------------------------------------------------
# Capacity → how many balls are in play
# --------------------------------------------------------------------------


def balls_for_capacity(capacity: int) -> int:
    """How many acts Barnaby hands over, given today's capacity.

    From the seed doc: 15% survival is one, maybe two. 50% steady is three or
    four. 90% is five or more. Zero capacity means Barnaby holds all of them
    and sits with you instead.
    """
    if capacity <= 0:
        return 0
    if capacity < 25:
        return 1
    if capacity < 40:
        return 2
    if capacity < 65:
        return 3
    if capacity < 85:
        return 4
    return 5


def triage(acts: list, capacity: int) -> tuple[list, list]:
    """Split acts into (in play, held by Barnaby).

    Held is not dropped, and it is not deferred-with-a-penalty. Barnaby is
    literally holding them. They are waiting. That distinction is the entire
    difference between a loss model and a rest model, and it is why this
    function never reorders by deadline.
    """
    limit = balls_for_capacity(capacity)
    live = [a for a in acts if not a.done and not a.held]

    # Cheapest-first, so a low-capacity day is not immediately handed the
    # heaviest thing on the list.
    live.sort(key=lambda a: PROFILES[a.kind].weight)

    in_play: list = []
    budget = float(limit)
    for act in live:
        cost = PROFILES[act.kind].weight
        if limit and (budget - cost) >= 0:
            in_play.append(act)
            budget -= cost
    held = [a for a in live if a not in in_play]
    return in_play, held
