"""Application rules independent of SQLite and model SDKs."""
from dataclasses import dataclass
import hashlib
import json
from typing import Literal, Protocol

from novel_factory.contracts import SourceSpan


WorkflowKind = Literal["chapter_analysis", "reverse_window", "reverse_section"]


@dataclass(frozen=True)
class Selection:
    work_id: str
    source_revision_id: int
    source_sha256: str
    segmentation_id: int
    kind: Literal["chapter", "window"]
    number_or_id: int | str
    workflow_kind: WorkflowKind

    def __post_init__(self) -> None:
        if self.kind == "chapter" and (not isinstance(self.number_or_id, int) or self.number_or_id < 1):
            raise ValueError("chapter needs a confirmed official number")
        if self.kind == "window" and (not isinstance(self.number_or_id, str) or not self.number_or_id):
            raise ValueError("window needs an approved selection ID")
        if self.workflow_kind == "chapter_analysis" and self.kind != "chapter":
            raise ValueError("chapter analysis requires a confirmed chapter")
        if self.workflow_kind != "chapter_analysis" and self.kind != "window":
            raise ValueError("reverse analysis requires an approved window")


@dataclass(frozen=True)
class PreparedInput:
    task_id: str
    workflow_kind: WorkflowKind
    selection_kind: str
    selection_id: str
    role: str
    split: str
    span: SourceSpan
    body: str


class AnalysisStore(Protocol):
    def prepare(self, selection: Selection) -> PreparedInput: ...
    def submit(self, task_id: str, submission_id: str, actor: str, payload: str, sha256: str) -> dict: ...
    def review(self, task_id: str, submission_id: str, review_id: str, reviewer: str,
               decision: str, reason: str, submission_sha256: str,
               previous_review_sha256: str | None) -> dict: ...
    def resume(self, task_id: str | None = None) -> list[dict]: ...
    def get_input(self, task_id: str) -> PreparedInput: ...
    def get_submission(self, task_id: str, submission_id: str) -> dict: ...


def check_submission_transition(latest_review_decision: str | None,
                                has_unreviewed_submission: bool) -> None:
    """A task cannot advance past an unreviewed or accepted submission."""
    if has_unreviewed_submission:
        raise ValueError("latest submission is unreviewed")
    if latest_review_decision == "accepted":
        raise ValueError("accepted analysis is immutable until an explicit review correction using its current SHA")


def check_review_transition(submitter: str, reviewer: str, actual_submission_sha: str,
                            requested_submission_sha: str, expected_previous_sha: str | None,
                            provided_previous_sha: str | None) -> None:
    if submitter == reviewer:
        raise ValueError("submitter cannot independently review their result")
    if actual_submission_sha != requested_submission_sha:
        raise ValueError("submission SHA differs from reviewed bytes")
    if provided_previous_sha != expected_previous_sha:
        raise ValueError("review correction requires current review SHA")


def payload_sha256(payload: str) -> str:
    # Submitted bytes are the reviewed object; never silently reserialize them.
    json.loads(payload)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AnalysisWorkflow:
    def __init__(self, store: AnalysisStore):
        self.store = store

    def prepare_analysis_input(self, selection: Selection) -> PreparedInput:
        return self.store.prepare(selection)

    def submit_result(self, task_id: str, submission_id: str, actor: str, payload: str) -> dict:
        if not task_id or not submission_id or not actor:
            raise ValueError("task, submission and actor are required")
        if not isinstance(json.loads(payload), dict):
            raise ValueError("analysis result must be a JSON object")
        return self.store.submit(task_id, submission_id, actor, payload, payload_sha256(payload))

    def review_result(self, task_id: str, submission_id: str, review_id: str, reviewer: str,
                      decision: str, reason: str, submission_sha256: str,
                      previous_review_sha256: str | None = None) -> dict:
        if decision not in ("accepted", "rejected", "hold"):
            raise ValueError("review decision must be accepted, rejected or hold")
        if not task_id or not submission_id or not review_id or not reviewer or not reason.strip():
            raise ValueError("review identity and reason are required")
        if len(submission_sha256) != 64:
            raise ValueError("exact submission SHA-256 is required")
        return self.store.review(task_id, submission_id, review_id, reviewer,
                                 decision, reason, submission_sha256, previous_review_sha256)

    def resume(self, task_id: str | None = None) -> list[dict]:
        return self.store.resume(task_id)

    def get_submission(self, task_id: str, submission_id: str) -> dict:
        return self.store.get_submission(task_id, submission_id)
