from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .config import Settings
from .keep_client import KeepClient
from .skylight_client import SkylightBridge

log = logging.getLogger(__name__)


@dataclass
class ListSyncResult:
    key: str
    keep_title: str
    added: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class SyncResult:
    lists: list[ListSyncResult]
    ok: bool


def run_sync(settings: Settings) -> SyncResult:
    keep = KeepClient(settings)
    sky = SkylightBridge(settings)

    keep.connect()
    sky.connect()

    results: list[ListSyncResult] = []

    for mapping in settings.list_mappings:
        result = ListSyncResult(key=mapping.key, keep_title=mapping.keep_title)
        keep_list = keep.find_list(mapping.keep_title)
        if keep_list is None:
            msg = f"Keep list not found: {mapping.keep_title!r}"
            log.error(msg)
            result.errors.append(msg)
            results.append(result)
            continue

        for item in keep.unchecked_items(keep_list):
            label = (item.text or "").strip()
            if not label:
                result.skipped += 1
                continue
            try:
                sky.add_item(mapping.skylight_list_id, label)
                keep.check_item(item)
                result.added += 1
                log.info("Synced %r → %s", label, mapping.key)
            except Exception as exc:
                err = f"{label!r}: {exc}"
                log.exception("Failed to sync item to %s", mapping.key)
                result.errors.append(err)

        results.append(result)

    # Push Keep check-offs (and refresh local cache).
    try:
        keep.sync()
    except Exception as exc:
        log.exception("Keep sync() after check-offs failed")
        if results:
            results[-1].errors.append(f"keep_sync: {exc}")

    ok = all(not r.errors for r in results)
    return SyncResult(lists=results, ok=ok)
