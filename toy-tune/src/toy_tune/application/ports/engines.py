from typing import Protocol

from toy_tune.domain.experiments import Capabilities, ModelRef, TrainingRequest


class TrainingEngine(Protocol):
    def capabilities(self) -> Capabilities: ...
    def train(self, request: TrainingRequest) -> str:
        """Return a completed checkpoint/artifact reference."""
        ...


class GenerationEngine(Protocol):
    def capabilities(self) -> Capabilities: ...
    def generate(self, model: ModelRef, prompts: tuple[str, ...], seed: int) -> tuple[str, ...]: ...


class EnvironmentInspector(Protocol):
    def inspect(self, probe_gpu: bool) -> dict: ...
