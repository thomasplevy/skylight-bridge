from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ListMapping:
    key: str
    keep_title: str
    skylight_list_id: str


@dataclass(frozen=True)
class Settings:
    sync_secret: str
    google_email: str
    google_master_token: str
    skylight_refresh_token: str
    skylight_frame_id: str
    data_dir: Path
    list_mappings: tuple[ListMapping, ...]

    @property
    def skylight_token_path(self) -> Path:
        return self.data_dir / "skylight_token.json"

    @property
    def keep_state_path(self) -> Path:
        return self.data_dir / "keep_state.json"


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_settings() -> Settings:
    pairs = (
        ("groceries", "KEEP_LIST_GROCERIES", "SKYLIGHT_LIST_GROCERIES", "Groceries"),
        ("sams", "KEEP_LIST_SAMS", "SKYLIGHT_LIST_SAMS", "Sam's Club"),
        ("todo", "KEEP_LIST_TODO", "SKYLIGHT_LIST_TODO", "Todo"),
        ("home_depot", "KEEP_LIST_HOME_DEPOT", "SKYLIGHT_LIST_HOME_DEPOT", "Home Depot"),
    )
    mappings: list[ListMapping] = []
    for key, keep_env, sky_env, default_title in pairs:
        sky_id = os.environ.get(sky_env, "").strip()
        if not sky_id:
            continue
        keep_title = os.environ.get(keep_env, default_title).strip() or default_title
        mappings.append(ListMapping(key=key, keep_title=keep_title, skylight_list_id=sky_id))

    if not mappings:
        raise RuntimeError(
            "No list mappings configured. Set at least one of "
            "SKYLIGHT_LIST_GROCERIES, SKYLIGHT_LIST_SAMS, SKYLIGHT_LIST_TODO, "
            "SKYLIGHT_LIST_HOME_DEPOT"
        )

    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    data_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        sync_secret=_require("SYNC_SECRET"),
        google_email=_require("GOOGLE_EMAIL"),
        google_master_token=_require("GOOGLE_MASTER_TOKEN"),
        skylight_refresh_token=_require("SKYLIGHT_REFRESH_TOKEN"),
        skylight_frame_id=_require("SKYLIGHT_FRAME_ID"),
        data_dir=data_dir,
        list_mappings=tuple(mappings),
    )
