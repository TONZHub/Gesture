"""Exercise every one of Barnaby's moments through the real model path.

This is the drop-keys-and-verify tool. Run it with no AWS credentials and it
proves the pipeline end to end on the local voice engine (every line comes back
"local"). Run it with Bedrock reachable and it becomes a real report: which
lines the model actually spoke, which passed the banned-phrase guard, which
*drifted* and were caught, and how long each call took.

    # local engine only (no creds needed)
    GESTURE_USE_STRANDS=0 python scripts/model_check.py

    # against Bedrock (needs credentials + model access in the region)
    GESTURE_USE_STRANDS=1 AWS_REGION=us-west-2 \
      BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
      python scripts/model_check.py

The number that matters is the guard-block rate: if the model drifts often, the
prompt needs work (or the temperature is too high). If it is zero and every line
is "strands", the model and the contract are in step.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gesture import db  # noqa: E402
from gesture.agent import guard  # noqa: E402
from gesture.agent.acts import triage  # noqa: E402
from gesture.agent.barnaby import Barnaby  # noqa: E402
from gesture.config import settings  # noqa: E402
from gesture.models import ActKind, Mode, StateAnchor  # noqa: E402

RESET = "\033[0m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"


def _c(text: str, color: str) -> str:
    return f"{color}{text}{RESET}" if sys.stdout.isatty() else text


def _percentile(values: list[int], pct: float) -> int:
    """Nearest-rank percentile. No numpy dependency for a handful of samples."""
    if not values:
        return 0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round(pct / 100 * (len(ordered) - 1))))
    return ordered[idx]


def _sample_day(day_path: Path) -> None:
    db.reset(day_path)
    day_id = db.begin_day(
        mode=Mode.CIRCUS,
        capacity=55,
        window_start="09:00",
        window_end="23:59",
        intention="get the admin done before it eats the week",
        sleep_hours=6.5,
    )
    db.add_act(day_id, ActKind.HOOPS, "email the landlord")
    db.add_act(day_id, ActKind.JUGGLING, "tidy one shelf")
    db.add_act(day_id, ActKind.TIGHTROPE, "the deck for Thursday")


def _moments(b: Barnaby):
    """Every place Barnaby speaks, as (label, callable) pairs."""
    day = db.day_state()
    in_play, held = triage(day.acts, day.capacity)

    yield "welcome", lambda: b.welcome()
    yield "overture", lambda: b.overture(day)
    yield "begin", lambda: b.begin_ack(in_play, held, day.capacity)
    yield "begin (zero capacity)", lambda: b.begin_ack([], day.acts, 0)
    yield "check-in (full)", lambda: b.checkin_prompt("full", 0)
    yield "check-in (light)", lambda: b.checkin_prompt("light", 1)
    yield "dismiss ack", lambda: b.dismiss_ack(1)
    yield "dismiss ack (streak)", lambda: b.dismiss_ack(3)
    yield "check-in ack (low mood)", lambda: b.checkin_ack(2, 1)
    yield "check-in ack (good)", lambda: b.checkin_ack(4, 2)
    for anchor in StateAnchor:
        yield f"stuck: {anchor.value}", (lambda a=anchor: b.stuck(a, day, None))
    yield "curtain call", lambda: b.curtain_call(day)


def run(day_path: Path) -> int:
    _sample_day(day_path)

    provider = settings.model_provider
    if provider == "featherless":
        where = f"featherless · model={settings.featherless_model}"
        if not settings.featherless_api_key:
            where += " · NO KEY"
    else:
        where = f"bedrock · model={settings.bedrock_model_id} · region={settings.aws_region}"

    print()
    print(_c("Barnaby model check", "\033[1m"))
    print(
        f"{DIM}strands={'on' if settings.use_strands else 'off'} · {where} · "
        f"temp={settings.bedrock_temperature} · "
        f"max_tokens={settings.bedrock_max_tokens}{RESET}"
    )
    print()

    counts = {"strands": 0, "guard-fallback": 0, "local": 0}
    latencies: dict[str, list[int]] = {}
    total = 0

    for mode in (Mode.CIRCUS, Mode.QUIET):
        print(_c(f"── {mode.value} " + "─" * 46, "\033[1m"))
        b = Barnaby(mode)
        for label, call in _moments(b):
            t0 = time.monotonic()
            u = call()
            ms = int((time.monotonic() - t0) * 1000)
            total += 1
            counts[u.source] = counts.get(u.source, 0) + 1
            latencies.setdefault(u.source, []).append(ms)

            tag = {
                "strands": _c("model ", GREEN),
                "guard-fallback": _c("BLOCKED", RED),
                "local": _c("local ", DIM),
            }.get(u.source, u.source)

            clean = guard.is_clean(u.text)
            if not clean:
                counts["dirty"] = counts.get("dirty", 0) + 1
            flag = "" if clean else _c("  ⚠ OUTPUT NOT CLEAN", RED)
            text = u.text.replace("\n", " ")
            if len(text) > 88:
                text = text[:85] + "…"
            print(f"  {tag} {ms:>5}ms  {DIM}{label:<24}{RESET} {text}{flag}")
        print()

    # Any raw model output the guard stopped is logged with blocked=1.
    blocked = [e for e in db.voice_log(200) if e["blocked"]]

    print(_c("── summary " + "─" * 44, "\033[1m"))
    print(f"  moments run       {total}")
    print(f"  {_c('model',GREEN)}             {counts.get('strands', 0)}")
    print(f"  {_c('guard-blocked',RED)}     {counts.get('guard-fallback', 0)}"
          f"   (model drift the guard caught)")
    print(f"  {_c('local',DIM)}             {counts.get('local', 0)}"
          f"   (model not called or unavailable)")

    print()
    print(_c("── latency (ms) " + "─" * 39, "\033[1m"))
    for source in ("strands", "local", "guard-fallback"):
        values = latencies.get(source)
        if not values:
            continue
        p50, p90, p99 = (_percentile(values, p) for p in (50, 90, 99))
        label = {"strands": "model", "local": "local", "guard-fallback": "blocked"}[source]
        print(
            f"  {label:<8} n={len(values):<3} "
            f"p50={p50:<6} p90={p90:<6} p99={p99:<6} max={max(values)}"
        )

    if not settings.use_strands:
        print()
        print(f"  {YELLOW}Strands is off — this run only proves the local "
              f"pipeline.{RESET}")
        print(f"  {DIM}Set GESTURE_USE_STRANDS=1 with AWS credentials for a real "
              f"model report.{RESET}")
    elif counts.get("strands", 0) == 0:
        print()
        print(f"  {YELLOW}The model was never reached — every line fell to the "
              f"local voice.{RESET}")
        print(f"  {DIM}Check AWS credentials, region, and Bedrock model access. "
              f"The app still works;{RESET}")
        print(f"  {DIM}this is exactly the graceful-degradation path.{RESET}")
    elif blocked:
        print()
        print(f"  {YELLOW}The guard caught {len(blocked)} drifting line(s):{RESET}")
        for e in blocked[:8]:
            print(f"    {DIM}[{e['source']}] {e['reason']}{RESET}")
            print(f"      {e['text'][:100]}")
        print(f"  {DIM}If this rate is high, tune the prompt or lower "
              f"BEDROCK_TEMPERATURE.{RESET}")
    else:
        print()
        print(f"  {GREEN}Clean run — the model and the contract are in step.{RESET}")

    print()
    # Every emitted line is guard-clean by construction; a dirty one would be a
    # real bug in the exit path, so surface it as a non-zero exit.
    return 0 if counts.get("dirty", 0) == 0 else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None, help="scratch db path (temp by default)")
    args = ap.parse_args()

    if args.db:
        run(Path(args.db))
    else:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            run(Path(d) / "model_check.db")
