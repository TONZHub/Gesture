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

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            db_path=Path(os.getenv("GESTURE_DB", ROOT / "gesture.db")),
            use_strands=_flag("GESTURE_USE_STRANDS", True),
            aws_region=os.getenv("AWS_REGION", "us-west-2"),
            bedrock_model_id=os.getenv(
                "BEDROCK_MODEL_ID",
                "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            ),
            device=os.getenv("GESTURE_DEVICE", "simulated"),
            keepon_port=os.getenv("GESTURE_KEEPON_PORT", "/dev/ttyUSB0"),
        )


settings = Settings.load()
