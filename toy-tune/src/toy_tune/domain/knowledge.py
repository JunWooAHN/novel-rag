from dataclasses import dataclass

from toy_tune.domain.errors import ValidationError
from toy_tune.domain.samples import identifier


def nonempty(values):
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValidationError("Knowledge fields must be nonempty strings.")


@dataclass(frozen=True)
class KnowledgeQuery:
    work_id: str
    canon_revision: str
    original_release: str
    story_time: str
    pov_character_id: str

    def __post_init__(self):
        nonempty((self.work_id, self.canon_revision, self.original_release,
                  self.story_time, self.pov_character_id))


@dataclass(frozen=True)
class Evidence:
    fact_id: str
    text: str
    status: str
    source_id: str

    def __post_init__(self):
        nonempty((self.fact_id, self.text, self.source_id))
        if self.status not in {"active", "contested", "overridden"}:
            raise ValidationError("Unknown evidence status.")


@dataclass(frozen=True)
class RetrievalPacket:
    packet_id: str
    query: KnowledgeQuery
    facts: tuple[Evidence, ...]
    schema_version: int = 1

    def __post_init__(self):
        identifier(self.packet_id)
        if (type(self.schema_version) is not int or self.schema_version != 1
                or not isinstance(self.query, KnowledgeQuery)
                or not isinstance(self.facts, tuple)
                or any(not isinstance(fact, Evidence) for fact in self.facts)):
            raise ValidationError("Invalid retrieval packet.")
