"""Small, storage-independent contract for a frozen legacy reverse release."""
from __future__ import annotations

from typing import Protocol


class LegacyReleaseReader(Protocol):
    def load_accepted_release(self, import_id: str) -> dict: ...
    def load_status(self, import_id: str, work_id: str | None,
                    selection_id: str | None) -> list[dict]: ...


def accepted_release(reader: LegacyReleaseReader, import_id: str) -> dict:
    """Only a committed, pinned release is visible to viewer and export."""
    if not import_id:
        raise ValueError("a fixed legacy import ID is required")
    release = reader.load_accepted_release(import_id)
    if release["release_id"] != import_id or len(release["rows"]) != release["accepted_count"]:
        raise ValueError("legacy release count or identity differs")
    return release


def legacy_status(reader: LegacyReleaseReader, import_id: str,
                  work_id: str | None = None,
                  selection_id: str | None = None) -> list[dict]:
    """The reviewed historical workflow state remains separate from new tasks."""
    if not import_id:
        raise ValueError("a fixed legacy import ID is required")
    return reader.load_status(import_id, work_id, selection_id)
