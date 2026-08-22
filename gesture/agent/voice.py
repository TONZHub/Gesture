"""The local voice engine.

Barnaby's words, generated on the machine, with no network call and no
credentials. This exists for three reasons:

1. Demo safety. A hackathon demo that dies because Bedrock rate-limited is a
   hackathon demo that dies.
2. Latency. The morning overture should not wait on a cold model.
3. Dignity. If someone is at 3am zero-capacity and the wifi is out, Barnaby
   still answers. A presence that requires connectivity is not a presence.

When Strands is available it writes better sentences than these. It does not
write *differently posed* ones — both paths answer to guard.py.
"""

from __future__ import annotations

import random
from typing import Optional, Sequence

from ..models import Act, DayState, Mode, StateAnchor, Utterance
from .acts import profile


class Voice:
    def __init__(self, mode: Mode = Mode.CIRCUS, rng: Optional[random.Random] = None):
        self.mode = mode
        self.rng = rng or random.Random()

    @property
    def circus(self) -> bool:
        return self.mode is Mode.CIRCUS

    def _pick(self, circus: Sequence[str], quiet: Sequence[str]) -> str:
        return self.rng.choice(list(circus if self.circus else quiet))

    # ------------------------------------------------------------------
    # The overture — first contact of the day
    # ------------------------------------------------------------------

    def overture(self) -> Utterance:
        return Utterance(
            text=self._pick(
                circus=[
                    "The lights are coming up. Take your time. The show waits for you.",
                    "Morning. The tent is up, the ring is swept, and I saved you the good seat.",
                    "There you are. I've been out here warming up the band.",
                ],
                quiet=[
                    "Morning. I'm here when you're ready.",
                    "Good morning. Nothing is urgent yet.",
                    "You're awake. That's the first thing.",
                ],
            ),
            source="local",
            face="delighted",
        )

    def welcome(self) -> Utterance:
        return Utterance(
            text=self._pick(
                circus=[
                    "Welcome. I'm Barnaby. I'm not here to judge you, track you, or "
                    "hand you a ten-step schedule. I'm here to sit in the gap with you.",
                ],
                quiet=[
                    "I'm Barnaby. I won't track you or grade you. "
                    "I'm here to help you keep hold of the day.",
                ],
            ),
            source="local",
            face="soft",
        )

    # ------------------------------------------------------------------
    # Begin
    # ------------------------------------------------------------------

    def begin_ack(
        self, in_play: list[Act], held: list[Act], capacity: int
    ) -> Utterance:
        if capacity <= 0 or not in_play:
            return Utterance(
                text=self._pick(
                    circus=[
                        "Nothing goes in the air today. I'll hold all of it. "
                        "I'll be right here. Intermissions are part of the show.",
                    ],
                    quiet=[
                        "Nothing is in play today. I'm holding all of it. "
                        "Resting is a real way to spend a day.",
                    ],
                ),
                source="local",
                face="soft",
            )

        first = in_play[0]
        p = profile(first.kind)
        n = len(in_play)
        held_note = ""
        if held:
            k = len(held)
            noun = "one" if k == 1 else f"{k}"
            verb = "is" if k == 1 else "are"
            held_note = self._pick(
                circus=[
                    f" The other {noun} {verb} with me. Not going anywhere.",
                    f" I've got the other {noun} behind my back. {'It' if k == 1 else 'They'} can wait.",
                ],
                quiet=[
                    f" The other {noun} {verb} set aside. {'It' if k == 1 else 'They'}'ll keep.",
                    f" I'm holding the other {noun} for later.",
                ],
            )

        opener = self._pick(
            circus=[
                f"Alright. {n} in the air today.",
                f"{n} up today. That's the whole bill.",
            ],
            quiet=[
                f"{n} thing{'s' if n != 1 else ''} today.",
                f"{n} on the list today.",
            ],
        )
        pointer = self._pick(
            circus=[f" We open with {p.circus_name.lower()}: {first.title}."],
            quiet=[f" Start with: {first.title}."],
        )
        return Utterance(
            text=opener + pointer + held_note, source="local", face="delighted"
        )

    # ------------------------------------------------------------------
    # Check-in
    # ------------------------------------------------------------------

    def checkin_prompt(self, weight: str, dismiss_streak: int) -> Utterance:
        if weight == "feather":
            return Utterance(
                text=self._pick(
                    circus=[
                        "No questions. Just waving from the ring.",
                        "Not asking for anything. Only saying hello.",
                    ],
                    quiet=[
                        "No questions. Just checking you're alright.",
                        "Nothing needed. Only saying hello.",
                    ],
                ),
                source="local",
                face="soft",
            )
        if weight == "light":
            return Utterance(
                text=self._pick(
                    circus=[
                        "Quick one: how's the air up there?",
                        "Small check. Where are you at?",
                    ],
                    quiet=["How are you doing?", "Quick check: how are you?"],
                ),
                source="local",
                face="listening",
            )
        return Utterance(
            text=self._pick(
                circus=[
                    "How's the show going? Nothing here is a test.",
                    "Checking in. Answer what you feel like answering.",
                ],
                quiet=[
                    "Checking in. Answer whatever you want to.",
                    "How's it going? Any of these are optional.",
                ],
            ),
            source="local",
            face="listening",
        )

    def dismiss_ack(self, dismiss_streak: int) -> Utterance:
        """Dismissing must feel *good*, or the data it produces is worthless.

        If dismissing carries a sting the user starts performing engagement,
        and then the correlations underneath are measuring compliance instead
        of capacity. So Barnaby gets quieter and means it.
        """
        if dismiss_streak >= 3:
            return Utterance(
                text=self._pick(
                    circus=[
                        "Got it. I'll stop tapping the glass for a while. "
                        "you know where I am.",
                        "Understood. Turning the volume right down.",
                    ],
                    quiet=[
                        "Okay. I'll leave you be for a while.",
                        "Understood. I'll come back much later.",
                    ],
                ),
                source="local",
                face="soft",
            )
        return Utterance(
            text=self._pick(
                circus=["Fair enough. Carry on.", "No problem. Back to it."],
                quiet=["Okay.", "No problem.", "That's fine."],
            ),
            source="local",
            face="soft",
        )

    def checkin_ack(self, mood: Optional[int], water: Optional[int]) -> Utterance:
        if mood is not None and mood <= 2:
            base = self._pick(
                circus=[
                    "That's a heavy one. Noted, and not held against you.",
                    "Rough patch. I've written it down and I'm not making it a thing.",
                ],
                quiet=[
                    "That sounds hard. Noted.",
                    "Okay. That's a difficult one. I've got it.",
                ],
            )
            face = "worried"
        elif mood is not None and mood >= 4:
            base = self._pick(
                circus=["Good to hear. Ride that one.", "Nice. I'll take it."],
                quiet=["Good. Glad to hear it.", "That's good."],
            )
            face = "delighted"
        else:
            base = self._pick(
                circus=["Noted.", "Got it, thank you."],
                quiet=["Noted.", "Thanks."],
            )
            face = "relieved"

        if water:
            base += self._pick(
                circus=[" And you drank something. Genuinely, well done."],
                quiet=[" And you had water. Good."],
            )
        return Utterance(text=base, source="local", face=face)

    # ------------------------------------------------------------------
    # The five stuck-states
    # ------------------------------------------------------------------

    MICRO_GESTURES: tuple[str, ...] = (
        "Touch your spacebar with your thumb. That's the whole task.",
        "Tap the icon once. Don't open anything after it.",
        "Put one hand flat on the desk and leave it there.",
        "Open the blank window and look at the white.",
        "Type one character. It's allowed to be the wrong one.",
        "Read the first line out loud. Stop at the end of it.",
    )

    def stuck(self, anchor: StateAnchor, text: Optional[str] = None) -> Utterance:
        gesture = self.rng.choice(self.MICRO_GESTURES)

        if anchor is StateAnchor.CANT_START:
            body = self._pick(
                circus=[
                    "The lock-up is real, and it isn't a character flaw. Your brain "
                    "is treating this like a saber-toothed tiger. So we're not doing "
                    f"the thing. We're doing gesture 0.1: {gesture} "
                    "Want me to sit with you for sixty seconds after?",
                ],
                quiet=[
                    "This is a real thing happening in your body, not a failure of "
                    f"willpower. We're not doing the task. Only this: {gesture} "
                    "I can sit with you for sixty seconds afterwards.",
                ],
            )
            return Utterance(text=body, source="local", face="soft")

        if anchor is StateAnchor.SCARED:
            body = self._pick(
                circus=[
                    "Okay. This one has a wall in front of it. We don't climb it "
                    "today. I'll stand on the other side and count you in. "
                    "Sixty seconds, no output required. Ready when you are.",
                ],
                quiet=[
                    "This one is frightening, which is information, not weakness. "
                    "Nothing has to be produced. I'll stay with you for sixty "
                    "seconds while you sit near it.",
                ],
            )
            return Utterance(text=body, source="local", face="worried")

        if anchor is StateAnchor.ZERO_CAPACITY:
            body = self._pick(
                circus=[
                    "Then the show is over for today and that's a real ending, not "
                    "an abandoned one. I'm putting everything on the shelf. Close "
                    "the laptop. Drink some water. I'll still be here.",
                ],
                quiet=[
                    "Then we stop. Everything goes on the shelf, and it stays there "
                    "without penalty. Close the laptop. Have some water. "
                    "I'll be here later.",
                ],
            )
            return Utterance(text=body, source="local", face="soft")

        if anchor is StateAnchor.FORGOT_FLOW:
            body = self._pick(
                circus=[
                    "Lost the thread. It happens constantly and means nothing. "
                    "Here's where you were.",
                ],
                quiet=["You lost track. Here's where you were."],
            )
            return Utterance(text=body, source="local", face="listening")

        # BRAIN_DUMP — the miko principle: receive before responding.
        body = self._pick(
            circus=[
                "Go on then. All of it, in any order, no punctuation required. "
                "I'm not going to tidy it while you talk.",
            ],
            quiet=[
                "Tell me all of it. Any order. I'll read it properly before I say "
                "anything back.",
            ],
        )
        return Utterance(text=body, source="local", face="listening")

    # ------------------------------------------------------------------
    # The curtain call
    # ------------------------------------------------------------------

    def curtain_call(self, day: DayState, lines: list[str]) -> Utterance:
        """The closing words only.

        The act-by-act recap is rendered as its own list by the caller, so this
        must not repeat it — otherwise the user reads the same day twice.
        """
        if not lines:
            return Utterance(
                text=self._pick(
                    circus=[
                        "You showed up. The tent is still standing. That counts, and "
                        "I'm not saying it to be nice. I was here and watched it hold.",
                    ],
                    quiet=[
                        "You showed up today. That counts. "
                        "Nothing else was required of you.",
                    ],
                ),
                source="local",
                face="soft",
            )
        return Utterance(
            text=self._pick(
                circus=[
                    "I was here for all of it. That's your star. It cost you "
                    "something real, so it's worth something real.",
                    "That was the show. I watched every bit of it, and it counted.",
                ],
                quiet=[
                    "I was here for it. That was a real day's worth.",
                    "That was today. It counted, and I saw it.",
                ],
            ),
            source="local",
            face="delighted",
        )
