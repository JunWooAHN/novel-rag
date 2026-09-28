"""Small, immutable source identity for the multilingual trial."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


@dataclass(frozen=True)
class SourceUnit:
    unit_id: str
    wiki_id: str
    page_id: int
    revision_id: int
    slot: str
    language: str
    title: str
    start_byte: int
    end_byte: int
    text: str
    text_sha256: str

    def validate(self) -> None:
        if not all((self.unit_id, self.wiki_id, self.slot, self.language, self.title)):
            raise ValueError("Source identity is incomplete")
        if self.page_id <= 0 or self.revision_id <= 0 or self.start_byte < 0:
            raise ValueError("Invalid source identity or byte span")
        # Whitespace-only spans still account for full source bytes; the
        # extraction queue excludes them with an explicit result state.
        if self.end_byte <= self.start_byte or not self.text:
            raise ValueError("Empty source unit")
        if self.end_byte - self.start_byte != len(self.text.encode("utf-8")):
            raise ValueError("UTF-8 byte span length differs from source unit")
        if digest(self.text.encode("utf-8")) != self.text_sha256:
            raise ValueError("Source unit hash differs from its text")
