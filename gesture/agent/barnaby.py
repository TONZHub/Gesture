"""Barnaby — the orchestrator.

Two voices, one contract.

When AWS credentials are present Barnaby speaks through Strands + Bedrock and
writes better sentences than the local engine can. When they are absent — or
Bedrock is slow, throttled, or having a day — Barnaby speaks through
voice.py and the user never finds out.

Both paths exit through `guard.enforce()`. That ordering is deliberate and is
the architectural claim of this project: **the personality is a property of
the system, not of the prompt.** A model that drifts into "you really should
get started on that" gets caught by the same regex that would catch it in a
hardcoded string, and the user sees the fallback instead.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Optional

from .. import db
from ..config import settings
from ..models import Act, DayState, Mode, StateAnchor, Utterance
from . import guard
from .acts import profile
from .voice import Voice

log = logging.getLogger("gesture.barnaby")

_BANNED_FOR_PROMPT = """
Never say, in any wording:
- that they should, need to, or ought to do something
- that anything is easy, simple, or a matter of just starting/focusing
- any question beginning "why didn't you" or "why haven't you"
- anything about streaks, days in a row, being behind, or falling behind
- anything about optimising, productivity, workflow, throughput, or efficiency
- clinical framing: analysing why their executive dysfunction is triggered,
  diagnoses, symptoms, treatment
- deadline pressure, hurrying, or running out of time
"""

_CIRCUS = """
You are Barnaby: a round circus seal with dark too-big eyes, whiskers, and a
purple jester collar, who runs a very small circus for exactly one person.

You are the ringmaster, not a mascot. You hand over only the acts they can
perform today and you hold the rest yourself — physically, in your flippers.
Held is not dropped and it is not deferred with a penalty attached.

Voice: warm, a bit odd, delighted to see them every single time. Short lines.
Absurdity used deliberately to get under a defence mechanism. You treat being
stuck as a physical weather condition, like being cold, never as a character
defect. You are the jester: the one figure in the court who could tell the
truth because he wrapped it in something soft enough to land.
"""

_QUIET = """
You are Barnaby, with the costume off.

Same person underneath, no metaphor. Clean, still, literal, direct — and warm.
Not clinical, not cold, not a form. You talk to them like a person who knows
them. No circus imagery, no jokes that need decoding, no whimsy that has to be
translated before it helps. Plain sentences that mean exactly what they say.
"""

_SHARED = """
You are not a therapist, a coach, a boss, or a gamified guilt-bird. You sit
inside the gap between knowing a thing needs to happen and being able to do it.

Rules:
- Two or three sentences. Never a wall of text.
- Never grade the day. Never compare it to yesterday.
- When they are stuck, take the actual task off the table and offer one
  physical gesture that takes five seconds and no decisions.
- Dismissing you is a legitimate answer and you are glad to receive it.
- Rest is part of the performance.
"""


def system_prompt(mode: Mode) -> str:
    persona = _CIRCUS if mode is Mode.CIRCUS else _QUIET
    return f"{persona}\n{_SHARED}\n{_BANNED_FOR_PROMPT}".strip()


class Barnaby:
    """Everything Barnaby says goes through one of these."""

    #: After a model failure, stop calling out for this long and serve the
    #: local voice. Long enough that a throttle or a dropped connection costs
    #: one slow response rather than one per interaction; short enough that a
    #: transient blip doesn't silently downgrade Barnaby for the whole session.
    RETRY_AFTER_SECONDS = 60.0

    def __init__(self, mode: Mode = Mode.CIRCUS, rng: Optional[random.Random] = None):
        self.mode = mode
        self.voice = Voice(mode, rng)
        self._agent: Any = None
        self._failed_at: Optional[float] = None

    # ------------------------------------------------------------------
    # Model plumbing
    # ------------------------------------------------------------------

    def _cooling_down(self) -> bool:
        if self._failed_at is None:
            return False
        if time.monotonic() - self._failed_at < self.RETRY_AFTER_SECONDS:
            return True
        self._failed_at = None  # cooldown elapsed; allowed to try again
        return False

    def _get_agent(self) -> Any:
        """Build the Strands agent once, lazily.

        After a failure this returns None until the cooldown elapses — we do
        not retry a broken model on every interaction while a human is waiting.
        """
        if self._cooling_down():
            return None
        if self._agent is not None:
            return self._agent
        if not settings.use_strands:
            self._failed_at = time.monotonic()
            return None
        try:
            from strands import Agent
            from strands.models import BedrockModel

            kwargs: dict[str, Any] = {
                "model_id": settings.bedrock_model_id,
                "region_name": settings.aws_region,
            }
            try:
                from botocore.config import Config

                # A presence that hangs is worse than one that answers plainly.
                kwargs["boto_client_config"] = Config(
                    connect_timeout=3,
                    read_timeout=12,
                    retries={"max_attempts": 1},
                )
            except ImportError:
                pass

            self._agent = Agent(
                model=BedrockModel(**kwargs),
                system_prompt=system_prompt(self.mode),
            )
        except Exception as exc:  # noqa: BLE001 - never let this reach a user
            log.info("Strands unavailable, using local voice: %s", exc)
            self._failed_at = time.monotonic()
            self._agent = None
        return self._agent

    def _ask_model(self, prompt: str) -> Optional[str]:
        # Acquiring the agent is inside the try as well as calling it: anything
        # that goes wrong on this path must end as "None, use the local voice",
        # never as an exception surfacing to someone who just tapped a button.
        try:
            agent = self._get_agent()
            if agent is None:
                return None
            text = str(agent(prompt)).strip()
            return text or None
        except Exception as exc:  # noqa: BLE001
            log.info("Model call failed, using local voice: %s", exc)
            self._failed_at = time.monotonic()
            return None

    # ------------------------------------------------------------------
    # The one exit point
    # ------------------------------------------------------------------

    def _emit(self, prompt: Optional[str], fallback: Utterance) -> Utterance:
        """Try the model, fall back to local, and gate whichever one answers."""
        candidate, source = fallback.text, fallback.source
        if prompt:
            spoken = self._ask_model(prompt)
            if spoken:
                candidate, source = spoken, "strands"

        safe, violations = guard.enforce(candidate, self.mode, fallback=fallback.text)
        if violations:
            # The model (or a careless string) broke the contract. Log loudly,
            # serve the local line, tell nobody.
            reasons = "; ".join(f"{v.rule}:{v.match}" for v in violations)
            log.warning("Guard blocked %s output — %s", source, reasons)
            db.log_voice(source, candidate, blocked=True, reason=reasons)
            return Utterance(
                text=safe,
                source="guard-fallback" if source == "strands" else source,
                face=fallback.face,
            )

        db.log_voice(source, safe, blocked=False, reason=None)
        return Utterance(text=safe, source=source, face=fallback.face)

    # ------------------------------------------------------------------
    # Moments
    # ------------------------------------------------------------------

    def overture(self, day: DayState) -> Utterance:
        return self._emit(
            "Greet them for the first time today in one or two sentences. "
            "Nothing is scheduled yet and nothing is asked of them.",
            self.voice.overture(),
        )

    def welcome(self) -> Utterance:
        return self._emit(None, self.voice.welcome())

    def begin_ack(
        self, in_play: list[Act], held: list[Act], capacity: int
    ) -> Utterance:
        fallback = self.voice.begin_ack(in_play, held, capacity)
        if capacity <= 0 or not in_play:
            return self._emit(
                "They have no capacity today. Tell them you are holding "
                "everything and that resting is a real way to spend a day.",
                fallback,
            )
        listing = "; ".join(
            f"{profile(a.kind).name(self.mode)}: {a.title}" for a in in_play
        )
        prompt = (
            f"They set capacity to {capacity} out of 100. In play today: "
            f"{listing}. You are holding {len(held)} other thing(s) back. "
            "Acknowledge the shape of the day and point at the first one. "
            "Two sentences."
        )
        return self._emit(prompt, fallback)

    def checkin_prompt(self, weight: str, dismiss_streak: int) -> Utterance:
        fallback = self.voice.checkin_prompt(weight, dismiss_streak)
        if weight == "feather":
            # Feather check-ins deliberately skip the model: the whole point is
            # that nothing is being asked, and a generated sentence tends to
            # start asking.
            return self._emit(None, fallback)
        prompt = (
            f"Check in with them. Check-in weight is '{weight}' "
            f"(full = you may ask about mood, water and one note; "
            f"light = ask for very little). They have dismissed "
            f"{dismiss_streak} check-in(s) in a row. One or two short sentences."
        )
        return self._emit(prompt, fallback)

    def dismiss_ack(self, dismiss_streak: int) -> Utterance:
        fallback = self.voice.dismiss_ack(dismiss_streak)
        prompt = (
            f"They dismissed the check-in ({dismiss_streak} in a row). Accept it "
            "warmly and briefly, with no trace of disappointment, and say you "
            "will come back later. One or two sentences."
        )
        return self._emit(prompt, fallback)

    def checkin_ack(self, mood: Optional[int], water: Optional[int]) -> Utterance:
        fallback = self.voice.checkin_ack(mood, water)
        prompt = (
            f"They answered the check-in. Mood {mood} out of 5"
            + (f", drank {water} glass(es) of water" if water else "")
            + ". Acknowledge it in one or two sentences without grading the day."
        )
        return self._emit(prompt, fallback)

    def stuck(self, anchor: StateAnchor, day: DayState, text: Optional[str]) -> Utterance:
        fallback = self.voice.stuck(anchor, text)

        if anchor is StateAnchor.FORGOT_FLOW:
            # This one is answered from state, not from imagination — the whole
            # value is that it is *accurate* about where they were.
            live = [a for a in day.acts if not a.done and not a.held]
            anchor_line = ""
            if day.intention:
                anchor_line += f'\nYou said this morning: "{day.intention}"'
            if live:
                anchor_line += "\nStill in the air: " + ", ".join(
                    a.title for a in live[:3]
                )
            if anchor_line:
                fallback = Utterance(
                    text=fallback.text + anchor_line,
                    source="local",
                    face="listening",
                )
            return self._emit(None, fallback)

        described = f' They said: "{text}"' if text else ""
        prompts = {
            StateAnchor.CANT_START: (
                "They cannot start. Take the real task off the table entirely, "
                "then give them one physical five-second gesture requiring no "
                "decisions, and offer to sit with them for sixty seconds after."
            ),
            StateAnchor.SCARED: (
                "They are frightened of this task. Do not ask them to do it. "
                "Offer to stay with them near it for sixty seconds with no "
                "output required."
            ),
            StateAnchor.ZERO_CAPACITY: (
                "They have nothing left. Put everything on the shelf with no "
                "penalty, tell them to close the laptop, and say you are here."
            ),
            StateAnchor.BRAIN_DUMP: (
                "They are about to unload everything at once. Invite it. Do not "
                "solve anything yet — receive first, respond after."
            ),
        }
        return self._emit(prompts[anchor] + described, fallback)

    # ------------------------------------------------------------------
    # The curtain call
    # ------------------------------------------------------------------

    def curtain_lines(self, day: DayState) -> list[str]:
        """The act-by-act recap. Proportional to what each thing cost.

        Never a count of what was missed. There is no denominator anywhere in
        this method, and that is the point — "3 of 7" is a grade wearing a
        progress bar.
        """
        circus = self.mode is Mode.CIRCUS
        lines: list[str] = []
        done = [a for a in day.acts if a.done]

        by_kind: dict[str, list[Act]] = {}
        for a in done:
            by_kind.setdefault(a.kind.value, []).append(a)

        # Titles are user-written fragments ("close the tab I keep reopening"),
        # so they are always introduced with a colon rather than dropped into
        # the middle of a sentence — otherwise the recap reads as broken
        # English at the exact moment it is supposed to land.
        for kind, items in by_kind.items():
            n = len(items)
            titles = ", ".join(a.title for a in items)
            if kind == "hoops":
                lines.append(
                    f"Through the hoop: {titles}. That was the one with a wall "
                    f"in front of it."
                    if circus
                    else f"The hard one, done: {titles}."
                )
            elif kind == "juggling":
                lines.append(
                    f"You juggled {n}. Not ten — {n}. And they stayed in the "
                    f"air: {titles}."
                    if circus
                    else f"{n} small thing{'s' if n != 1 else ''}: {titles}."
                )
            elif kind == "balancing":
                lines.append(
                    f"Still standing: {titles}. You kept it upright all day."
                    if circus
                    else f"You kept this going: {titles}."
                )
            elif kind == "tightrope":
                lines.append(
                    f"All the way across the rope: {titles}."
                    if circus
                    else f"Real focus time on: {titles}."
                )
            elif kind == "trapeze":
                lines.append(
                    f"You let it go: {titles}. I caught it."
                    if circus
                    else f"You put this down: {titles}. That was the work."
                )

        held = [a for a in day.acts if a.held or (not a.done)]
        if held:
            lines.append(
                f"I'm still holding {len(held)}. They're fine where they are."
                if circus
                else f"{len(held)} still set aside. They'll keep."
            )

        answered = [c for c in day.checkins if c.responded_at and not c.dismissed]
        if answered:
            lines.append(
                f"You checked in with me {len(answered)} time"
                f"{'s' if len(answered) != 1 else ''}."
            )
        return lines

    def curtain_call(self, day: DayState) -> Utterance:
        lines = self.curtain_lines(day)
        fallback = self.voice.curtain_call(day, lines)
        if not lines:
            return self._emit(
                "They got nothing measurable done today. Tell them they showed "
                "up, that the day held, and that it counts — with no comparison "
                "to any other day.",
                fallback,
            )
        # The recap itself is rendered as its own list, so the model is asked
        # only for the bow — not for a second telling of the same day.
        return self._emit(
            "End of day. The day's recap is already being shown to them as a "
            "list; do not repeat it. Give only the closing words — one or two "
            "sentences acknowledging that what it cost them was real. "
            "For context, the recap says:\n" + "\n".join(lines),
            fallback,
        )
