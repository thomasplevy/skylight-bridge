from __future__ import annotations

import logging
import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

from .config import Settings, load_settings
from .sync import run_sync

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="Skylight Keep Sync", version="1.0.0")


def get_settings() -> Settings:
    try:
        return load_settings()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def require_auth(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")
    token = authorization.removeprefix("Bearer ").strip()
    if not secrets.compare_digest(token, settings.sync_secret):
        raise HTTPException(status_code=401, detail="unauthorized")


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/sync")
def sync(
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(require_auth)],
) -> JSONResponse:
    log.info("Sync started")
    try:
        result = run_sync(settings)
    except Exception as exc:
        log.exception("Sync failed")
        raise HTTPException(status_code=502, detail=f"sync_failed: {exc}") from exc

    payload = {
        "ok": result.ok,
        "lists": [
            {
                "key": r.key,
                "keep_title": r.keep_title,
                "added": r.added,
                "skipped": r.skipped,
                "errors": r.errors,
            }
            for r in result.lists
        ],
    }
    log.info("Sync finished ok=%s payload=%s", result.ok, payload)
    # Always 200 so cron clients using curl --fail only trip on transport/5xx.
    return JSONResponse(content=payload, status_code=200)
