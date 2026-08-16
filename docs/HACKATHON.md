# Agents for Humans — submission

**Track:** Good Neighbor Agents — serves a population (neurodivergent users,
people with dementia, executive dysfunction) that existing tech consistently
fails.

*Everyday Agents was the alternate. Good Neighbor is the stronger fit: the
pitch is a population, not one person's schedule, and "the tools built for this
group are built on neurotypical assumptions" is the whole argument.*

**Prize pool:** $40,000 · $5,000 track gold.

---

## Status

| | Item | State |
|---|---|---|
| ✅ | Decide on track | Good Neighbor Agents |
| ✅ | Strands Agents SDK setup | `agent/barnaby.py`, degrades to local voice |
| ✅ | Begin screen | Capacity → balls, act picker, both modes |
| ✅ | Check-in logic + dismiss tracking | Adaptive interval **and** adaptive weight |
| ✅ | Health input correlation engine | `agent/patterns.py`, gated on n ≥ 4 and \|r\| ≥ 0.5 |
| ✅ | The Window visual design | Canvas sky, coverage-weighted, night→dawn |
| ✅ | README + architecture diagram | `README.md`, `docs/ARCHITECTURE.md` |
| ⬜ | Demo video | Script below |
| ⬜ | builder.aws.com post | Bonus points |
| ⬜ | Physical Barnaby | Keepon arrives 18–21 Aug |

Beyond the original checklist: Circus/Quiet dual modes, the five stuck-states,
the curtain call, the code-enforced personality contract, the device
abstraction, and 92 tests.

---

## Also entered: Pixel Forge AI Hackathon

Gesture is submitted to a second event — Pixel Forge's AI Hackathon (apps/web
where AI is core), Aug 15–22, 2026 — as the *same* project. (Pixel Forge also
runs a separate Game Jam; that one is a different project entirely, *Embellished*,
not this.)

One build, two framings. Agents for Humans is pitched as a **Good Neighbor** for
a population tech fails. Pixel Forge is a general AI event, so it leads with the
**craft and the agent**: the personality enforced in code (`guard.py`), the
adaptive back-off, the tardigrade/Window/audio, and the test suite — the same
work, aimed at "novel, well-built, AI-at-the-core" rather than at a track.

Compliance checklist (Pixel Forge):

| Requirement | State |
|---|---|
| AI as a core part of the experience | ✅ Strands/Bedrock agent + enforced-in-code personality |
| Created during the event (Aug 15–22; brainstorm-ahead allowed) | ✅ Entire git history is within the window; the Aug 13 seed doc is the permitted prior planning |
| Open-source license in the repo | ✅ MIT (`LICENSE`) |
| Public repository | ⬜ Owner action — make the repo public (or mirror it) |
| Hosted / live URL | ⬜ Deploy the Render blueprint (`render.yaml`) |
| ~3-min demo video + Devpost entry | ⬜ Shared with the Agents for Humans video |

Because Pixel Forge weights "AI as core," running Bedrock live (not just the
local fallback) matters more here — which moves the day-3 model work up in
priority. The exact judging rubric wasn't reachable to confirm; paste it in if
you have it and the framing can be tuned further.

---

## One week

The Notion brief assumed a six-week window; this is a seven-day run. What is
already built is the whole software product — the remaining days are hardware,
film, and polish.

| Day | Work |
|---|---|
| **1** ✅ | Core, agent layer, three screens, guard, tests |
| **1.5** ✅ | *Ahead of plan:* jester hat, bell + Gladiators overture, tardigrade redesign, act header art + live poses, Render deploy blueprint |
| **2** ✅ | Accessibility pass (keyboard, focus management, live regions, reduced-motion, contrast AA) + responsive down to phone width. Still to do by ear: tune the `GLADIATORS` array if the transcription is off |
| **3** | Bedrock live. Compare model output against the local engine and tune the system prompt until the guard stops firing. Deploy is already blueprinted — just needs AWS keys in the dashboard |
| **4–5** | Keepon arrives. Motor + touch sensor + serial handshake, then the projector. Firmware is already written and the wire protocol is already implemented — this is assembly, not design |
| **6** | Film. Real week of data, not seeded, if there is time |
| **7** | Cut the video, write the builder.aws.com post, submit with a day in hand |

**Hardware is explicitly cuttable.** If the Keepon slips past the 21st or the
motor fights back, the simulated device carries the whole demo and the video
loses one shot. Nothing on the critical path waits on a parcel.

---

## Demo video

Three minutes. The brief says: *show the screens, then say nothing and let them
feel it.* Hold to that.

1. **The problem, 20s.** 2:15pm. An email that needs writing. Forty-five
   minutes of not opening the tab. Not laziness — a lock.
2. **Begin, 25s.** Capacity to 20%. Four things on the list; Barnaby hands
   over one and holds the rest. *"The other three are with me. Not going
   anywhere."*
3. **Dismiss, 40s.** A check-in arrives — Barnaby jiggles. Tap **Not now**.
   Again. Again. Open the rhythm panel: 60 → 87 → 114 minutes, full → light →
   feather. Say the line: *every other app pushes harder here.*
4. **Stuck, 30s.** Tap **I can't start**. Barnaby takes the email off the table
   and offers a five-second gesture. This is the emotional centre — hold on it.
5. **The Window, 35s.** The week as sky. The 3am Tuesday. The unlit Wednesday
   that is haze, not black. Then say nothing.
6. **The guard, 20s.** `/api/voice-log` with a blocked line visible.
   *The personality is enforced in code, not asked for in a prompt.*
7. **Curtain call, 20s.** The bow. The star. No denominator.

If the hardware works, open on the tardigrade on the desk shaking, and a hand
reaching out to still it. That shot is the whole thesis in two seconds and it
needs no voiceover.

**Filming aids:** `POST /api/demo/due-now` pulls the next check-in forward —
an adaptive hourly rhythm is otherwise impossible to show in three minutes.
`python scripts/seed.py` produces a deliberately un-triumphant week (a bad
Wednesday, a missing day), because a demo week where everything goes well is a
demo of a different product.

---

## What to say to judges

**The claim:** most agents optimise for engagement. This one is built so that
the correct response to being ignored is to become quieter — and that is
enforced by a test that fails if anyone reverses it.

**The three defensible pieces of engineering**

1. **The personality is a system property.** Every line — Bedrock or
   hardcoded — passes `guard.py`. A drifting model gets caught by the same
   regex as a careless string, and the user sees the local fallback instead.
   Tested in both directions: the banned list fails, Barnaby's canonical copy
   passes.
2. **The sky refuses to measure compliance.** Dismissals and unfinished tasks
   cannot darken The Window. Days we barely heard from are drawn faintly and
   count less, so the worst day of a week doesn't render as pleasantly average
   just because the user was too flat to answer.
3. **Graceful degradation is the architecture.** No credentials, no network, no
   hardware — it still runs, and still sounds like Barnaby.

**If asked what is weakest:** the correlation engine is Pearson on ≥ 4 days.
It is honest about that (`"a shape, not a rule"`) and it stays silent below the
threshold, but it is the part most in need of real longitudinal data. The
gating is deliberate — a horoscope drawn from three points would do more damage
here than saying nothing.

---

## Competitive notes

- **Finch** — gamified self-care, reward without execution support. *Absorbed
  community ideas without credit. Do not pitch wide.*
- **Fabulous** — behavioural science, Duke origin, intention–action gap. Best
  current approximation; still too noisy.
- **Ash** — AI therapist framing. Warm, carries clinical liability. Gesture
  explicitly refuses the clinical register (`guard.py`, rule `clinical`).
- **Tolan** — personality-forward. Cited by Muneeba as *creating fatigue rather
  than relief* for some autistic users. Quiet mode is the direct answer.
- **Tiimo** — visual scheduling for ADHD. Good at time, not at being with you.

Strategic note from the seed doc, still standing: **do not pitch wide, do not
post publicly before submission.** Proof of concept first, with your name in
the bones of it.
