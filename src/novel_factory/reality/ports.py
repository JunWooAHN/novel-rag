"""Only the seams exercised by this trial; adapters remain replaceable."""

from __future__ import annotations

from typing import Protocol

from .domain import SourceUnit


class UnitReader(Protocol):
    def pending_units(self, limit: int) -> list[SourceUnit]: ...


class CandidateExtractor(Protocol):
    def extract(self, prompt: str) -> str: ...


class TextEmbedder(Protocol):
    model: str
    revision: str
    dimension: int

    def passage(self, text: str) -> list[float]: ...

    def query(self, text: str) -> list[float]: ...
