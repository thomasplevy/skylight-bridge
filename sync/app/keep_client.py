from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import gkeepapi
from gkeepapi.node import List as KeepList
from gkeepapi.node import ListItem

from .config import Settings

log = logging.getLogger(__name__)


class KeepClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._keep = gkeepapi.Keep()

    def connect(self) -> None:
        state = self._load_state()
        self._keep.authenticate(
            self._settings.google_email,
            self._settings.google_master_token,
            state=state,
        )
        self._persist_state()

    def sync(self) -> None:
        self._keep.sync()
        self._persist_state()

    def find_list(self, title: str) -> KeepList | None:
        for node in self._keep.all():
            if isinstance(node, KeepList) and not node.trashed and node.title == title:
                return node
        return None

    def unchecked_items(self, keep_list: KeepList) -> list[ListItem]:
        return list(keep_list.unchecked)

    def check_item(self, item: ListItem) -> None:
        item.checked = True

    def _load_state(self) -> dict[str, Any] | None:
        path = self._settings.keep_state_path
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, ValueError):
            return None

    def _persist_state(self) -> None:
        path = self._settings.keep_state_path
        try:
            path.write_text(json.dumps(self._keep.dump()), encoding="utf-8")
            path.chmod(0o600)
        except OSError as exc:
            log.warning("Failed to persist Keep state: %s", exc)
