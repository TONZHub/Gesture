# Architecture

## Request flow

```
browser ──REST──▶ gesture/api.py ──▶ agent/{rhythm,patterns,sky}.py ──▶ db.py
   ▲                    │
   │                    └──▶ agent/barnaby.py ──▶ Strands/Bedrock  ─┐
   │                                          └──▶ agent/voice.py  ─┤
   │                                                                ▼
   │                                                        agent/guard.py
   └────────SSE─────── devices/bus.py ◀── devices/{simulated,keepon}.py
```

## Modules

| Module | Responsibility |
|---|---|
| `models.py` | Domain vocabulary. `held` is not `skipped`; a day is `closed`, never `completed` |
| `db.py` | SQLite. One file, no migrations, no server |
| `agent/acts.py` | The five acts, their cognitive weight, capacity→balls, triage |
| `agent/guard.py` | The banned-phrase contract. Every utterance passes through it |
| `agent/voice.py` | Local voice engine. No network, always available |
| `agent/barnaby.py` | Orchestrator. Strands when available, local otherwise, guard always |
| `agent/rhythm.py` | When to check in and how much to ask for |
| `agent/patterns.py` | Correlations, gated on sample size and effect size |
| `agent/sky.py` | The week as light |
| `devices/` | `BarnabyDevice` + simulated and Keepon transports |
| `demo.py` | Deterministic week of plausible history for hosted demos and filming; never overwrites real data |

## Design invariants

These are enforced by tests, not by convention. They are the parts most likely
to be broken by a well-meaning future change.

| Invariant | Where | Why |
|---|---|---|
| Dismissals never shorten the check-in interval | `test_rhythm.py` | The moment this reverses, the app has become the thing it replaces |
| Dismissals never darken the sky | `test_sky.py` | Otherwise the picture measures compliance and users perform for it |
| Unfinished acts never darken the sky | `test_sky.py` | Same reason |
| A day with no data is unlit, not dark | `test_sky.py` | Absence and misery must not render identically |
| Every line of output survives `guard.py` | `test_guard.py` | Including the local engine, which is what the guard falls back *to* |
| The curtain call contains no denominator | `test_api.py` | "3 of 7" is a grade wearing a progress bar |
| Zero capacity schedules nothing | `test_api.py` | Booking check-ins for someone who said they have nothing left is the exact behaviour this app exists to not have |
| Quiet-mode copy carries no circus metaphor | `test_acts.py` | Quiet mode is a second front door, not a reskin |

## The rhythm calculation

```
interval = 60min × capacity × dismissals × mood × sleep     clamped to [25, 240]
```

Every factor is ≥ 1.0 in the gentler direction. `dismiss_factor` is
`min(1 + 0.45n, 2.6)` and can never return below 1.0 — asserted directly.

Weight is separate from interval:

```
streak ≥ 2                → feather   nothing is asked
streak = 1                → light     mood + water
dismiss ratio > 0.5       → light     gentle re-entry after a hard stretch
capacity < 25             → light
otherwise                 → full      mood + water + note
```

`explain()` returns the whole calculation and the UI renders it behind a
disclosure. An agent that adapts to you should be able to say why.

## The sky calculation

Per day, over whichever of mood / sleep / water exist:

```
light    = Σ(signal × weight) / Σ(weight present)      weights .65 / .25 / .10
coverage = Σ(weight present)
```

The week is the **coverage-weighted** mean of its lit days, so a day we barely
heard from doesn't get an equal vote. Bands: `< .25` 3am · `< .50` pre-dawn ·
`< .75` magic hour · else dawn.

`sky.js` paints each day as its own vertical gradient, overlapping its
neighbours, then blurs the whole thing so the week reads as one continuous
piece of weather. A bar chart would invite comparison between days, and
comparison between days is what makes every other tracker hurt to open.

## Guard mechanics

1. Mask **allowances** first — negated forms like *"not a failure"* are how the
   product states its own thesis, so they must survive.
2. Run ~20 rules across obligation, minimising, interrogation, shame,
   optimisation, streaks, clinical framing and pressure.
3. On any hit, discard the whole utterance and serve the local fallback.
4. Log it. `GET /api/voice-log` exposes every line Barnaby has said,
   **including the blocked ones** — a claim you can watch working beats one in
   a README.

The precision problem is real: `just` appears three times in Barnaby's own
canonical reply, so the rules bind it to specific constructions
(`just sit down`, `just focus`, `just do it`) rather than banning the word.

## Sound

Barnaby's bell is synthesised in Web Audio (`web/js/sound.js`) — no asset
files, so the two-command setup survives and no binary lands in the repo.
Bells are inharmonic, so the partial ratios are deliberately non-integer
(1, 1.51, 2.14, 2.87, 3.63) with higher partials decaying faster; a harmonic
series here sounds like an organ.

The rules around it matter more than the synthesis, because this app is for
people who find unexpected sound aversive — and the hardware spec marks the
tone **Optional** for that reason:

| Rule | Why |
|---|---|
| Rings on the *onset* of a jiggle, never on the state | The jiggle has no timeout; a bell that matched it would be torture. Reconnects and syncs pass `{silent: true}` |
| Circus defaults on, Quiet defaults off | Costume down means sensory down |
| `prefers-reduced-motion` defaults it off in both | No `prefers-reduced-sound` exists, but someone who asked the OS to calm down has said enough |
| An explicit toggle beats every default, permanently | Switching to Circus must never hand back a sound someone turned off |
| Muting syncs across tabs via the `storage` event | People leave this open on a second monitor; a muted window rung by a forgotten one is the exact failure to avoid |
| Rolled off above 6 kHz, peak gain ≈ 0.085 | A bright synthetic bell is the texture that makes people flinch |

Four cues: the jiggle ring, a softer descending **pet chime**, a three-note
flourish at the curtain call, and the **morning overture**. The pet chime is
the important one — it is the sound of having come back into your body, and
the only audio in the app that confirms something the user *did*.

### The overture

*Entry of the Gladiators* (Fučík, 1897, public domain) on a music box, played
when the day is begun — the tent going up. It fires on the Begin press rather
than on the greeting for two reasons: audio cannot start before a user
gesture, and that press is the actual moment the show starts, so the sound is
never a surprise.

The music-box voice is the same `_strike` idea with wider partials
(1 : 2 : 3 : 4 : 6, as a struck bar rather than a bell), a 4 ms noise tick for
the pin catching the tooth, and a few cents of per-note detune for the
hand-cranked wander. The *tinny* quality is mostly the **absence of low end** —
the bus is high-passed at 620 Hz, which sits above the fundamental of every
note in the lower half of the phrase. You hear the upper partials and your ear
reconstructs the missing fundamental, which is exactly how a small mechanical
box sounds.

The melody is plain data (`GLADIATORS` in `sound.js`), transcribed by ear as a
micro-arrangement rather than the full march: the long chromatic descent that
is the piece's signature, answered by a rising arpeggio. The descent alone is
unmistakably circus but lands somewhere melancholy, which is the wrong note to
start a morning on. Quiet mode gets `MORNING_QUIET` instead — three rising
notes, no march, the same no-metaphor promise the rest of Quiet mode makes.

Verified by offline-rendering the phrase and running an FFT over each note
window: all 14 pitches match the intended melody, peak −15.6 dBFS, no
clipping.

## Model providers

Barnaby speaks through the **Strands SDK**, through one of two model providers,
selected by `GESTURE_MODEL_PROVIDER` — and, crucially, through the **same
`guard.py`** either way. The guard is provider-agnostic on purpose: it catches
drift from Claude and from an open Llama model with the same regex, which is the
whole "personality enforced in code, not in a prompt" claim made portable.

`barnaby._build_model()` is the only place the two differ:

| `GESTURE_MODEL_PROVIDER` | Model | Notes |
|---|---|---|
| `bedrock` (default) | Claude on AWS Bedrock | `strands.models.BedrockModel`, non-streaming Converse |
| `featherless` | Open models (Llama/Qwen/Mistral/…) | `strands.models.openai.OpenAIModel` pointed at Featherless's OpenAI-compatible endpoint |

Everything downstream — the call, `_text_from_result`, the guard, the fallback,
the cooldown — is identical for both. `max_tokens` and `temperature` apply to
whichever is active.

### Going live

Barnaby needs nothing to run (local voice by default). To give him the model
voice:

**Bedrock.** Enable model access in the AWS console → Bedrock → *Model access*
for the region (`us-west-2`), grant the IAM principal `bedrock:InvokeModel` +
`bedrock:InvokeModelWithResponseStream`, and provide credentials via the standard
AWS chain. Set `GESTURE_MODEL_PROVIDER=bedrock`, `AWS_REGION`, `BEDROCK_MODEL_ID`
(the `us.` prefix is a cross-region inference profile, so the region must have the
underlying model enabled).

**Featherless.** Set `GESTURE_MODEL_PROVIDER=featherless`, `FEATHERLESS_API_KEY`,
and optionally `FEATHERLESS_MODEL` (any model on their catalogue; default is
Llama 3.1 8B Instruct). Needs the `openai` package (in `requirements.txt`).

**Verify either** with the harness — it names the active provider in its header:

```bash
GESTURE_MODEL_PROVIDER=featherless FEATHERLESS_API_KEY=... python scripts/model_check.py
```

It runs every one of Barnaby's moments through the real path and reports, per
line, whether the model spoke (`model`), whether the guard caught drift
(`guard-blocked`), or whether it fell to the local voice (`local`), plus latency.
A clean run means the model and the banned-phrase contract are in step; a high
block rate means lower the temperature or tighten the prompt. Open models tend
to drift a little more than Claude — which is exactly why the guard exists, and
why running the harness on both is a good sanity check.

**How the path degrades.** `barnaby.py` builds the agent lazily and bounds the
call with a short timeout (connect 3s, read 15s, one attempt). Any failure — no
credentials, no key, no model access, a throttle, a slow first token — is caught,
logged, and answered by the local voice, then a 60s cooldown stops it retrying a
dead provider on every tap. The user never sees an error; they just get Barnaby.

## Accessibility

This app is for people existing tools fail — so an interface a stranger can't
operate with a keyboard, or that shakes a large object in the vision of someone
with a vestibular condition, would contradict its own thesis. The pass:

- **Everything is a real control.** Every affordance is a native `<button>` or
  labelled input, keyboard-operable, with a visible `:focus-visible` ring. The
  Barnaby SVGs are decorative and `aria-hidden`; his *content* is his speech.
- **His speech is announced.** The `.say` lines are `aria-live="polite"` status
  regions, so a screen-reader user hears what Barnaby says as it changes.
- **The overlays are dialogs.** Check-in and stuck are `role="dialog"
  aria-modal`, labelled by their prompt. Opening moves focus in and traps Tab;
  closing returns focus to the trigger. Escape closes the stuck sheet and —
  deliberately — *dismisses* a check-in, because the Intentional Dismiss is
  meant to be the zero-friction way out and a keyboard escape hatch is exactly
  that. Dismissing costs nothing by design, so an accidental Escape is harmless.
- **The Window has a text alternative.** The canvas carries a label, the band
  name and line are real text, and the full per-day numbers live in a table
  underneath.
- **Reduced motion is handled, not ignored.** `prefers-reduced-motion` collapses
  every animation and transition to instant (not `animation: none`, which can
  break `animationend`), and the blink and the celebrate-hop are skipped in JS.
  The one piece of *information* carried by motion — the jiggle — is replaced by
  a steady bright halo, so the "come back to your body" cue survives without any
  movement. It never stands alone anyway: the check-in also opens a modal and
  rings the bell.
- **Contrast and targets.** All text clears WCAG AA (4.5:1) in both modes,
  including the faintest small print on the lighter surfaces; interactive
  targets are ≥44px on touch pointers.

## Responsive

Single stylesheet, no framework. The layout is fluid; phones (≤560px) get a
tightened pass where the bottom controls — the dock and the "I'm stuck" button —
share one row without colliding (the dock sheds its mini-Barnaby and shortens
"Pet Barnaby"/"Ground me" to "Pet"/"Ground"). Fixed controls honour
`env(safe-area-inset-*)` for notched phones. Verified clean at 320/360/375px.

## Device layer

Five verbs — `jiggle`, `still`, `face`, `project`, `celebrate`. The hardware
spec is ambitious (projector, 360° pan, SAM voice, screen face) but each of
those is a way of doing one of these five, and a narrow interface is what lets
the Keepon land mid-week without touching the agent layer.

Events fan out through `devices/bus.py` to the browser over SSE. The bus uses a
deque-per-subscriber behind a lock rather than an asyncio queue: device methods
are called from FastAPI's threadpool while the SSE generator runs on the loop,
and polling has no cross-thread failure modes at all. Unglamorous, correct
trade for something that has to work on a judge's laptop.

The Keepon transport degrades silently — no pyserial, no port, or a board that
stops answering mid-session all leave the on-screen Barnaby working. Hardware
failing must never take the software with it.

## What is deliberately not here

- **No accounts, no sync, no cloud storage.** Nothing about the product needs
  them, and health data plus a hackathon deadline is a bad combination.
- **No streaks, no scores, no badges.** Banned at the guard level.
- **No push notifications.** The rhythm is in-app and, eventually, in the
  object on your desk. A lock-screen badge is the failure mode being replaced.
- **No insights dashboard.** `patterns.py` returns at most two findings. The
  interface gets quieter as it learns you, and a wall of charts is the opposite
  of that.
