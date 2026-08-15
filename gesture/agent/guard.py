"""The banned-phrase contract.

The seed doc lists phrases Barnaby must never say. Prompting a model not to say
them is a wish. This module makes it a property of the system: every line of
Barnaby's output — from the local voice engine, from Bedrock, from anywhere —
passes through `enforce()` before a human sees it. A model that drifts gets
caught by the same net as a typo in a hardcoded string.

This matters more than it looks. The user this is built for has spent their
whole life being talked to in exactly these registers by people who meant
well. One "you really should have started earlier" undoes a week of trust.
So it is not a style preference. It is a safety property, and it is tested.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ..models import Mode


@dataclass(frozen=True)
class Violation:
    rule: str
    match: str
    reason: str


# Phrases that are safe *because they are being negated or refused*. Barnaby is
# allowed to say "dismissing is not failure" — that is the product's thesis.
# These spans are masked out before the ban rules run.
ALLOWANCES: tuple[str, ...] = (
    r"\bnot (?:a )?failure\b",
    r"\bisn'?t (?:a )?failure\b",
    r"\bnever (?:a )?failure\b",
    r"\bnot failing\b",
    r"\bno streaks?\b",
    r"\bnot behind\b",
    r"\bnever behind\b",
    r"\bnot lazy\b",
    r"\bisn'?t lazy\b",
    r"\bno guilt\b",
    r"\bwithout (?:the )?guilt\b",
    r"\bnot an idiot\b",
)


# (rule, pattern, why it is banned)
RULES: tuple[tuple[str, str, str], ...] = (
    (
        "obligation",
        r"\byou (?:really )?(?:should|need to|ought to|have got to|gotta)\b",
        "Prescribes. Turns Barnaby into one more voice assigning homework.",
    ),
    (
        "obligation",
        r"\byou'?d better\b",
        "Implied threat wrapped in advice.",
    ),
    (
        "minimising",
        r"\bit'?s (?:so |super |really |very )?easy\b",
        "If it were easy it would already be done. Says the wall is imaginary.",
    ),
    (
        "minimising",
        r"\bjust (?:sit down|focus|do it\b|start\b|try harder|push through|get started)",
        "'Just' is the word that has failed this user their entire life.",
    ),
    (
        "minimising",
        r"\ball you (?:have to|need to) do is\b",
        "Collapses the actual difficulty into a rhetorical shrug.",
    ),
    (
        "minimising",
        r"\bsimply\b",
        "Same shrug, longer word.",
    ),
    (
        "interrogation",
        r"\bwhy (?:didn'?t|haven'?t|did'?nt|don'?t) you\b",
        "Demands a justification for being stuck. Fires rejection sensitivity.",
    ),
    (
        "interrogation",
        r"\bhow come you (?:didn'?t|haven'?t)\b",
        "Interrogation with a friendlier accent.",
    ),
    (
        "shame",
        r"\byou (?:failed|are failing|'?re failing)\b",
        "Names the person as the failure rather than the day as hard.",
    ),
    (
        "shame",
        r"\b(?:was|is|were|are|that'?s) (?:a |an )?failure\b|\byour failure\b",
        "A verdict. The negated form ('not a failure') is allowed; this is not.",
    ),
    (
        "shame",
        r"\byou'?re (?:behind|falling behind|so behind)\b",
        "Behind implies a race the user never entered.",
    ),
    (
        "shame",
        r"\b(?:lazy|slacking|no excuses?|stop making excuses)\b",
        "Moral framing of a neurological state.",
    ),
    (
        "shame",
        r"\byou only (?:did|managed|got)\b",
        "'Only' is a grade. Barnaby does not grade.",
    ),
    (
        "optimisation",
        r"\b(?:optimi[sz]e|throughput|productivity|efficiency|cadence|kpis?|"
        r"maximi[sz]e your|leverage your|workflow)\b",
        "Optimisation theatre. Gesture optimises for self-knowledge, not output.",
    ),
    (
        "streaks",
        r"\b(?:streaks?|don'?t break the chain|keep the chain|days in a row)\b",
        "Streaks convert inconsistency into debt. Banned by design.",
    ),
    (
        "clinical",
        r"\blet'?s analy[sz]e why your\b",
        "Turns a hard afternoon into a case study.",
    ),
    (
        "clinical",
        r"\byour (?:executive dysfunction|adhd|autism|disorder|symptoms?|condition) "
        r"(?:is|are|was|were) (?:triggered|acting up|flaring)\b",
        "Pathologises. The brain is not the problem to be fixed.",
    ),
    (
        "clinical",
        r"\b(?:treatment plan|diagnos(?:e|is|ing)|what'?s wrong with you|fix you)\b",
        "Clinical liability and, worse, clinical tone.",
    ),
    (
        "pressure",
        r"\b(?:before the deadline|running out of time|time is running out|"
        r"you'?re late|hurry up|tick tock)\b",
        "Deadline pressure is the thing that built the wall in the first place.",
    ),
    (
        "pressure",
        r"\b(?:power through|rise and grind|crush it|beast mode|no pain no gain)\b",
        "Hustle register. Exhausting to a brain already running at a deficit.",
    ),
)

_COMPILED = tuple((r, re.compile(p, re.IGNORECASE), why) for r, p, why in RULES)
_ALLOW = tuple(re.compile(p, re.IGNORECASE) for p in ALLOWANCES)


def _mask_allowances(text: str) -> str:
    """Blank out negated/refused phrasings, preserving length so that any
    reported match offsets still line up with the original string."""
    masked = text
    for pat in _ALLOW:
        masked = pat.sub(lambda m: " " * len(m.group(0)), masked)
    return masked


def check(text: str) -> list[Violation]:
    """Return every contract violation in `text`. Empty list means clean."""
    masked = _mask_allowances(text)
    found: list[Violation] = []
    for rule, pattern, why in _COMPILED:
        for m in pattern.finditer(masked):
            found.append(Violation(rule=rule, match=m.group(0).strip(), reason=why))
    return found


def is_clean(text: str) -> bool:
    return not check(text)


# What Barnaby says instead, when something he was about to say got caught.
# These are deliberately plain — a fallback should never try to be clever.
_FALLBACK: dict[Mode, str] = {
    Mode.CIRCUS: "Let me try that again. The tent is still up, and so are you.",
    Mode.QUIET: "Let me put that a different way. I'm still here.",
}


def enforce(
    text: str,
    mode: Mode = Mode.CIRCUS,
    fallback: Optional[str] = None,
) -> tuple[str, list[Violation]]:
    """Gate a candidate utterance.

    Returns `(safe_text, violations)`. When violations exist the original text
    is discarded entirely rather than patched — a sentence built on the wrong
    posture cannot be repaired by deleting one word from it.
    """
    violations = check(text)
    if not violations:
        return text, []
    return (fallback or _FALLBACK[mode]), violations
