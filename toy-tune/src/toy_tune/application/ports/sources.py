from typing import Protocol

from toy_tune.domain.samples import Sample


class SourceReader(Protocol):
    def read(self) -> tuple[Sample, ...]: ...
    def snapshot(self) -> bytes: ...
