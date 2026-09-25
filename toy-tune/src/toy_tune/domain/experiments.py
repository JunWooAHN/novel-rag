from dataclasses import dataclass

from toy_tune.domain.errors import ValidationError, UnsupportedError


@dataclass(frozen=True)
class ModelRef:
    repository: str
    revision: str
    format: str


@dataclass(frozen=True)
class TrainingRequest:
    model: ModelRef
    dataset_id: str
    run_id: str
    dtype: str
    max_steps: int
    seed: int


@dataclass(frozen=True)
class Capabilities:
    engine: str
    operations: frozenset[str]
    formats: frozenset[str]
    dtypes: frozenset[str]

    def require(self, operation: str, model: ModelRef, dtype: str):
        if operation not in self.operations or model.format not in self.formats or dtype not in self.dtypes:
            raise UnsupportedError("Requested operation/model format/dtype is not supported by this engine.")


TRANSITIONS = {
    "created": {"validated", "failed"},
    "validated": {"running", "failed"},
    "running": {"completed", "failed", "interrupted"},
    "interrupted": {"validated"},
    "failed": set(),
    "completed": set(),
}


def validate_transition(previous: str, following: str):
    if following not in TRANSITIONS.get(previous, set()):
        raise ValidationError("Invalid run state transition.")
