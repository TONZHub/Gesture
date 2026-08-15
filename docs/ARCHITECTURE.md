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
