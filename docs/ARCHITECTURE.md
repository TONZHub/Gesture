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
