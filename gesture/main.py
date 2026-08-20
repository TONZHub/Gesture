"""Application entry point.

    python -m gesture            # http://127.0.0.1:8000
    uvicorn gesture.main:app --reload
"""

from __future__ import annotations

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .api import router
from .config import WEB_DIR, settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-22s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("gesture")

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.connect()
    log.info("Barnaby is awake — device=%s, db=%s", settings.device, settings.db_path)
    if not settings.use_strands:
        log.info("Strands disabled; Barnaby is on the local voice engine.")

    if settings.seed_on_empty:
        from .demo import seed_if_empty

        written = seed_if_empty()
        if written:
            log.info("Empty database — seeded %d days of demo history.", written)

    yield


app = FastAPI(
    title="Gesture",
    description="A rhythm-based agent for brains that lose the day in the gap.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.middleware("http")
async def use_browser_time_zone(request: Request, call_next):
    """Keep a hosted visitor's day and check-in window in their local time."""
    token = db.request_time_zone.set(request.headers.get("X-Gesture-Timezone"))
    try:
        return await call_next(request)
    finally:
        db.request_time_zone.reset(token)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "version": app.version}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
