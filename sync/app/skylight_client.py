from __future__ import annotations

import logging
import time
from pathlib import Path

from pyskylight.auth import Credentials, refresh
from pyskylight.client import SkylightClient
from pyskylight.config import TokenCache
from pyskylight.constants import DEFAULT_BASE_URL
from pyskylight.errors import SkylightAuthError

from .config import Settings

log = logging.getLogger(__name__)


class SkylightBridge:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache = TokenCache(path=settings.skylight_token_path)
        self._client: SkylightClient | None = None

    def connect(self) -> None:
        self._client = SkylightClient(self._ensure_credentials())

    @property
    def client(self) -> SkylightClient:
        if self._client is None:
            raise RuntimeError("SkylightBridge.connect() was not called")
        return self._client

    def add_item(self, list_id: str, label: str) -> None:
        try:
            self.client.add_list_item(self._settings.skylight_frame_id, list_id, label)
        except SkylightAuthError:
            log.info("Skylight auth failed; refreshing token and retrying")
            self._client = SkylightClient(self._force_refresh())
            self.client.add_list_item(self._settings.skylight_frame_id, list_id, label)

    def _ensure_credentials(self) -> Credentials:
        creds = self._cache.load(DEFAULT_BASE_URL)
        now = time.time()
        if creds and not creds.is_expired(now):
            return creds
        if creds and creds.refresh_token:
            try:
                return self._refresh_and_save(creds.refresh_token)
            except Exception as exc:
                log.warning("Cached refresh failed (%s); trying seed token", exc)
        return self._force_refresh()

    def _force_refresh(self) -> Credentials:
        seed = self._settings.skylight_refresh_token
        cached = self._cache.load(DEFAULT_BASE_URL)
        token = (cached.refresh_token if cached and cached.refresh_token else seed) or seed
        return self._refresh_and_save(token)

    def _refresh_and_save(self, refresh_token: str) -> Credentials:
        fresh = refresh(refresh_token, base_url=DEFAULT_BASE_URL)
        self._cache.save(fresh, DEFAULT_BASE_URL)
        # Ensure parent exists even if TokenCache path differs in edge cases.
        Path(self._settings.data_dir).mkdir(parents=True, exist_ok=True)
        return fresh
