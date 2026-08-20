# Swarm lanes — parallel coding boundaries

Multiple coders working this repo at once, in **one shared working tree**. The
only thing that keeps a parallel night from collapsing into merge conflicts is
**file-disjoint lanes**: no two coders ever edit the same file. Find your lane,
edit *only* the files it owns, and leave every other file alone.

## The two rules (every coder, no exceptions)

1. **Edit only the files in your lane's ownership list below.** If a task looks
   like it needs a file another lane owns, STOP and leave a note in your commit
   message or `docs/SWARM_LANES.md` under "Cross-lane asks" — do not reach across.
2. **Commit small, commit often**, with a `[lane-X]` prefix. Run `pytest` before
   every commit; never push a red tree. Pull before you push.

Branch: `claude/barnaby-gesture-hackathon-wefpoj`.

## Frozen — do not edit without serializing

- **`gesture/agent/guard.py`** — the banned-phrase contract. Lane A tunes prompts
  *around* it; every other lane *depends* on it. Changing it changes everyone's
  ground truth. If it genuinely must change, that's a solo edit with all other
  coders paused — coordinate it, don't slip it into a lane.
- **`gesture/main.py`, `gesture/__init__.py`, `gesture/__main__.py`** — wiring.
  Effectively untouched tonight; if one needs a line, it's a quick serialized edit.

---

## Lane A — Agent & model voice

**Owns only:**
- `gesture/agent/barnaby.py`
- `gesture/agent/voice.py`
- `gesture/config.py`
- `scripts/model_check.py`

Everything about *what Barnaby says* and *how the model is called* — the
orchestrator, the local voice engine, the provider config, the verify harness.
Do not touch `guard.py`.

**Ideas:** retry-with-backoff on transient provider errors before falling to
local; per-line latency percentiles in `model_check.py`; tighten the
`_CIRCUS`/`_QUIET` prompts against whichever guard category trips most.

---

## Lane B — Character, sound & sky visuals

**Owns only:**
- `web/js/barnaby.js`
- `web/js/sound.js`
- `web/js/sky.js`
- `web/css/gesture.css`

Everything you *see and hear* except page structure: the tardigrade SVG and act
poses, the Web Audio bell/overture, The Window canvas, the stylesheet. Never
touch `app.js` or `index.html`.

**Ideas:** tune the `GLADIATORS` overture array by ear; a new act pose;
reduced-motion visual polish; Window palette tuning.

---

## Lane C — App logic & markup

**Owns only:**
- `web/js/app.js`
- `web/index.html`

The controller and the page. You are the *only* coder allowed in `index.html`.

**Ideas:** demo-panel refinements for filming, interaction-flow polish, mobile
edge cases, focus-management hardening.

---

## Lane D — Backend, API & domain logic

**Owns only:**
- `gesture/api.py`
- `gesture/db.py`
- `gesture/demo.py`
- `gesture/models.py`
- `gesture/agent/patterns.py`
- `gesture/agent/rhythm.py`
- `gesture/agent/sky.py`
- `gesture/agent/acts.py`
- `gesture/devices/*`

The Python behaviour that isn't the model call: endpoints, storage, the
correlation engine, the adaptive rhythm, sky math, act definitions, the device
abstraction. Do not touch `config.py` (Lane A) or `guard.py` (frozen).

**Ideas:** harden `/api/demo/*`; correlation-engine edge cases; seeding
robustness; rhythm invariant coverage.

---

## Lane E — Docs, tests & deploy

**Owns only:**
- `docs/*`
- `tests/*`
- `render.yaml`
- `README.md`
- `.env.example`
- `scripts/seed.py`

Tests for whatever A–D land, plus docs and deploy. You rebase most often because
you touch tests that cover everyone's code — **pull frequently**.

**Ideas:** expand coverage for new work; Devpost/HACKATHON polish; deploy-note
accuracy; keep the test count in `DEVPOST_PIXELFORGE.md` honest.

---

## Recommended staffing

- **Pushing toward demo-ready** (live model, deploy, film): weight **A + C + E**.
- **Feature depth** (more acts, richer agent, deeper visuals): weight **A + B + D**.

## Cross-lane asks

*(Coders: if you hit something outside your lane, log it here instead of reaching
across. Whoever owns that file picks it up.)*

- ~~**Lane B → Lane D:** if a 6th act ever gets added to `ActKind`
  (`gesture/agent/acts.py`), ping Lane B — `web/js/barnaby.js`'s `ACT_ART`
  table is keyed by act kind and a matching pose can be added same-session.~~
  **Resolved:** the 6th act — `plates` (Plate spinning / "Keeping things
  going") — landed with its `ActProfile`, `ACT_ART` pose, and a triage test,
  after the swarm subsided. Both sides done together, no orphaned key.
