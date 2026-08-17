"""Runtime configuration.

Gesture is designed to run with nothing configured. Every setting here has a
default that works offline, on a laptop, with no credentials and no hardware.
Configuration only ever *adds* capability — it is never required.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # optional
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dotenv is a convenience only
    pass

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    db_path: Path
    use_strands: bool
    aws_region: str
    bedrock_model_id: str
    device: str
    keepon_port: str
    seed_on_empty: bool
    bedrock_max_tokens: int
    bedrock_temperature: float
    demo: bool

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            db_path=Path(os.getenv("GESTURE_DB", ROOT / "gesture.db")),
            use_strands=_flag("GESTURE_USE_STRANDS", True),
            aws_region=os.getenv("AWS_REGION", "us-west-2"),
            bedrock_model_id=os.getenv(
                "BEDROCK_MODEL_ID",
                # Haiku by default — Barnaby's lines are short and warm, so the
                # cheaper, faster model is plenty, and the guard catches drift
                # from any model. Matches render.yaml and .env.example.
                "us.anthropic.claude-3-5-haiku-20241022-v1:0",
            ),
            device=os.getenv("GESTURE_DEVICE", "simulated"),
            keepon_port=os.getenv("GESTURE_KEEPON_PORT", "/dev/ttyUSB0"),
            # Off by default: nobody running this locally wants invented
            # history in their own week. The hosted demo turns it on.
            seed_on_empty=_flag("GESTURE_SEED_ON_EMPTY", False),
            # Barnaby says one to three short sentences. Capping tokens keeps
            # him from rambling and keeps latency and cost down. Temperature is
            # warm enough for personality, low enough to stay on-contract; it is
            # the main dial when tuning the prompt against the guard.
            bedrock_max_tokens=int(os.getenv("BEDROCK_MAX_TOKENS", "220")),
            bedrock_temperature=float(os.getenv("BEDROCK_TEMPERATURE", "0.7")),
            # Filming aids: a reset-and-seed and a live guard demo, plus an
            # on-screen panel to drive them. Off by default and gated on the
            # server, so the reset (which wipes data) can never fire in
            # production — even if someone finds the endpoint.
            demo=_flag("GESTURE_DEMO", False),
        )


settings = Settings.load()
