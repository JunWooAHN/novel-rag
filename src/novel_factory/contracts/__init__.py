"""Small shared, storage-independent contracts."""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SourceSpan:
    work_id: str
    source_revision_id: int
    source_sha256: str
    segmentation_id: int
    start_cp: int
    end_cp: int
    text_sha256: str

    def __post_init__(self) -> None:
        if not self.work_id or self.source_revision_id < 1 or self.segmentation_id < 1:
            raise ValueError("source identity is required")
        if len(self.source_sha256) != 64 or len(self.text_sha256) != 64:
            raise ValueError("source and span SHA-256 are required")
        if self.start_cp < 0 or self.end_cp <= self.start_cp:
            raise ValueError("source span must be a nonempty half-open CP range")


@dataclass(frozen=True)
class SceneSpec:
    """v1 semantic contract; never a model prompt or an approved story scene by itself."""

    scene_id: str
    goal: str
    constraints: tuple[str, ...]
    provenance_kind: Literal["learning_hypothesis", "locked_writing"]
    provenance_id: str
    viewpoint_actor_id: str
    known_fact_refs: tuple[str, ...]
    prior_context_refs: tuple[str, ...]
    learning_input_span: SourceSpan | None = None
    learning_target_span: SourceSpan | None = None
    contract_version: int = 1

    def __post_init__(self) -> None:
        if (self.contract_version != 1 or not self.scene_id or not self.goal
                or not self.provenance_id or not self.viewpoint_actor_id):
            raise ValueError("SceneSpec v1 requires identity, goal, viewpoint and provenance")
        if self.provenance_kind not in ("learning_hypothesis", "locked_writing"):
            raise ValueError("learning hypothesis and locked writing are distinct")
        if self.provenance_kind == "learning_hypothesis":
            a, b = self.learning_input_span, self.learning_target_span
            if a is None or b is None:
                raise ValueError("learning hypothesis needs bounded input and separate target")
            if ((a.work_id, a.source_revision_id, a.source_sha256, a.segmentation_id) !=
                    (b.work_id, b.source_revision_id, b.source_sha256, b.segmentation_id)
                    or a.end_cp > b.start_cp):
                raise ValueError("learning input must precede target in the same source version")
        elif self.learning_input_span is not None or self.learning_target_span is not None:
            raise ValueError("locked writing cannot carry training target spans")
