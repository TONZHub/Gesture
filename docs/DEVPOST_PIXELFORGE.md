# Gesture — Pixel Forge AI Hackathon submission

*Copy each section into the matching Devpost field. Written for a general-AI
audience: it leads with the agent and the craft, and lets who-it's-for land as
the why. Pronouns are first-person singular — adjust if you're crediting a team.*

---

## Tagline (one line)

A rhythm-based AI companion for brains that lose the day in the gap — where the
agent's personality is enforced in code, not hoped for in a prompt.

---

## Inspiration

There's a gap between *knowing* a thing needs to happen and being *able* to do
it. For an executive-dysfunctional brain that gap is a wall, and every tool
built to help with it makes the wall taller. Reminder apps just tell you that
you forgot. Habit trackers turn a hard week into a broken streak. "Focus" apps
say *just start*. AI assistants answer "I'm being bullied" with "hmm, I don't
know that one."

I built Gesture from lived experience, not a research deck. I wanted a thing
that doesn't optimise for output — it optimises for **self-knowledge**. Something
that sits *in* the gap with you instead of nagging you across it. And I wanted
to see whether a modern LLM could hold that posture reliably enough to trust it
near someone on a bad day — which turned out to be the real technical problem.

## What it does

Gesture is three calm screens and a companion named Barnaby — a jester
tardigrade (a water bear, the animal that survives the unsurvivable by curling
up, going still, and waiting out the bad conditions).

- **Begin** — once a day you set the *shape*: how much capacity you have, when
  the day runs, what's on it. Capacity maps to "balls in play"; everything you
  can't hold today, Barnaby holds for you. *Held is not dropped.*
- **Check-In** — arrives on the agent's own rhythm, never a fixed timer. Mood,
  water, an optional note, and an **Intentional Dismiss** that's always there,
  costs nothing, and is recorded as *data, not failure*.
- **The Window** — your week rendered as a sky that shifts from 3am blue-black
  to dawn gold. You feel it before you read it; the numbers are underneath.

Barnaby performs your tasks as circus acts, adopts the pose of whatever you're
working on, shakes when it's time to come back (and stills when you touch him),
and plays *Entry of the Gladiators* on a little music box when the day begins.
There's a Circus voice and a Quiet voice — same companion, costume on or off —
because for some neurodivergent users the metaphor is delight and for others
it's friction.

## The AI — and why it's built differently

The agent runs on **AWS Strands + Bedrock (Claude)**, and the interesting part
isn't that there's an LLM in it. It's *how the LLM is governed.*

**1. The personality is enforced in code, not in a prompt.** Every single line
Barnaby says — whether it came from Bedrock or from a local fallback — passes
through a deterministic banned-phrase guard before a human ever sees it: ~20
rules across obligation, minimising ("just start"), interrogation ("why didn't
you"), shame, streaks, optimisation, clinical framing, and deadline pressure. If
the model drifts into "you really should have started earlier," it's caught by
the *same regex* that would catch a careless hardcoded string, discarded whole,
and replaced by a safe line. The user never sees the slip. Prompting a model to
be kind is a wish; this makes it a property of the system — and it's tested in
both directions (banned phrasing is caught; warm on-contract output passes
untouched, so the guard never drowns the model in fallbacks).

**2. The agent's core behaviour is to back off.** Every engagement product on
earth responds to being ignored by pushing *harder*. Gesture does the opposite,
and provably: dismiss it and the next check-in comes *later* and asks for *less*
(60 → 87 → 114 → 141 minutes; full → light → feather). A test fails if anyone
ever reverses that sign.

**3. It refuses to measure compliance.** The Window's light is drawn only from
how the week *felt* — mood, sleep, water. Dismissals and unfinished tasks
**cannot** darken it. If ignoring the app made your sky go black, you'd learn to
perform for it, and the data the agent adapts on would be poisoned. Days it
barely heard from are drawn faintly, not confidently average.

**4. It degrades without dying.** No credentials, no network, no model access —
Barnaby still speaks, through a local voice engine held to the very same guard.
A presence that requires connectivity isn't a presence, and a demo that dies
because Bedrock throttled is a dead demo.

## How I built it

- **Backend:** Python 3.11, FastAPI, SQLite (one file, no server, and a user
  can delete their whole history by deleting one file). The agent layer is
  Strands + Bedrock with the local engine as a first-class fallback, both behind
  `guard.py`.
- **Frontend:** vanilla JS, **no build step** — clone it, run two commands. The
  Window is a `<canvas>`; Barnaby is inline SVG; the act poses reuse the same
  body; the live companion re-renders in place so it keeps breathing and
  blinking while it changes acts.
- **Everything is synthesised — zero binary assets.** The character, the five
  act poses, and the expressions are all SVG. The bell and the *Entry of the
  Gladiators* overture are built live in the Web Audio API (inharmonic partials
  for the bell, a high-passed music-box comb for the overture) — no image or
  audio files in the repo at all.
- **The design values are tests.** 137 of them, and the load-bearing ones assert
  the *invariants*: dismissals never shorten the interval, dismissals never
  darken the sky, the curtain call contains no "3 of 7" score, every line
  survives the guard.
- **A verify harness** (`scripts/model_check.py`) runs every one of Barnaby's
  moments through the real model path and reports, per line, model vs
  guard-blocked vs local, plus latency — the drift rate you'd tune the prompt
  against.

## Challenges I ran into

- **Making the guard strict without making it deaf.** A guard that blocks warm,
  on-brand output is worse than none — the user only ever hears fallbacks. The
  hard part was a corpus of *good* lines that must pass, so the net catches
  drift without strangling personality.
- **Reduced motion, when motion is the message.** Barnaby's shake is the whole
  intervention — but you must never shake a large object in the vision of
  someone with a vestibular condition. The fix: under `prefers-reduced-motion`
  the shake becomes a steady bright halo. Same "come back" signal, zero movement.
- **"Tinny" is subtraction.** Getting the overture to sound like a real music
  box was mostly about *removing* low end (a high-pass above the fundamentals)
  so your ear reconstructs the missing bass — which is exactly how a small
  mechanical thing sounds.
- **Verifying the model path with no keys.** I couldn't reach Bedrock during the
  build, so I made the path provably correct against the installed SDK and
  shipped the harness above, so it verifies itself the moment credentials land.

## Accomplishments I'm proud of

- A consumer LLM feature where **kindness is a tested system property**, not a
  prompt you cross your fingers over.
- A reflection screen that **can't be gamed** because it never measures
  compliance.
- A whole character, five act poses, and a full musical overture with **no asset
  files** — all synthesised.
- An accessibility pass that isn't a checkbox: keyboard-operable throughout,
  focus-managed dialogs, live-region speech, AA contrast, and the reduced-motion
  halo. For an app whose whole thesis is "the tools fail this population," an
  interface a stranger can't drive would contradict itself.

## What I learned

That the interesting frontier with LLMs in a caring product isn't capability —
it's *governance*. The model is genuinely good at warmth; the engineering is all
in guaranteeing it can't have a bad moment at the exact person who can least
afford one. Putting the guard between the model and the human, and making the
agent's adaptive behaviour bend *away* from pressure, did more for trust than any
amount of prompt-crafting.

## What's next

- **Bedrock live in the hosted demo** (the path and harness are ready; it needs
  model access + keys).
- **A physical Barnaby** — a hacked My Keepon that jiggles on your desk and
  stills when you pet it; firmware and the device abstraction are already in the
  repo.
- **Real longitudinal patterns.** The correlation engine is deliberately honest
  ("a shape, not a rule") and stays silent below four days — it's the part most
  hungry for real data over time.

## Built With

`python` · `fastapi` · `sqlite` · `aws` · `amazon-bedrock` · `strands-agents` ·
`anthropic-claude` · `web-audio-api` · `svg` · `canvas` · `javascript` · `html` ·
`css` · `arduino` (physical companion)

---

## Submission checklist (Pixel Forge)

- [ ] **Hosted/live URL** — deploy `render.yaml` (Render, free tier) and paste the link
- [ ] **Public repo** — make the repository public
- [x] **Open-source license** — MIT (`LICENSE`)
- [ ] **~3-min demo video** — shared with the Agents for Humans cut; see the shot list in `docs/HACKATHON.md`
- [ ] **Devpost form** — paste the sections above
- [ ] *(strengthens "AI is core")* Bedrock live — run `python scripts/model_check.py` for a clean report
