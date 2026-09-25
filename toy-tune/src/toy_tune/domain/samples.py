from dataclasses import asdict, dataclass
import hashlib
import re

from toy_tune.domain.errors import ValidationError


def identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}", value):
        raise ValidationError("Invalid identifier; use 1–96 ASCII letters, digits, dots, dashes or underscores.")
    return value


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Sample:
    sample_id: str
    work_id: str
    scene_id: str
    order: int
    prompt: str
    answer: str
    source_id: str
    source_sha256: str
    answer_start: int
    answer_end: int
    question_method: str
    packet_id: str | None = None

    def __post_init__(self):
        for value in (self.sample_id, self.work_id, self.scene_id, self.source_id):
            identifier(value)
        if self.packet_id is not None:
            identifier(self.packet_id)
        if type(self.order) is not int or self.order < 0:
            raise ValidationError("Sample order must be a nonnegative integer.")
        for value in (self.prompt, self.answer, self.question_method):
            if not isinstance(value, str) or not value.strip():
                raise ValidationError("Prompt, answer and question method must be nonempty strings.")
        if not isinstance(self.source_sha256, str) or not re.fullmatch("[0-9a-f]{64}", self.source_sha256):
            raise ValidationError("Invalid source SHA-256.")
        if (type(self.answer_start) is not int or type(self.answer_end) is not int
                or self.answer_start < 0 or self.answer_end <= self.answer_start):
            raise ValidationError("Invalid answer character range.")

    def to_dict(self) -> dict:
        return asdict(self)
