import json
from pathlib import Path

from toy_tune.domain.errors import ValidationError
from toy_tune.domain.samples import Sample, digest, identifier


class JsonSourceReader:
    """Explicit source bundle only; never searches sibling projects."""

    def __init__(self, path: Path):
        try:
            self.raw = path.read_bytes()
        except OSError:
            raise ValidationError("Cannot read the selected source bundle.") from None

    def snapshot(self) -> bytes:
        return self.raw

    def read(self) -> tuple[Sample, ...]:
        try:
            bundle = json.loads(self.raw)
            if (set(bundle) != {"schema_version", "sources", "samples"}
                    or type(bundle["schema_version"]) is not int or bundle["schema_version"] != 1
                    or not isinstance(bundle["sources"], list) or not isinstance(bundle["samples"], list)):
                raise ValueError()
            sources = {}
            for row in bundle["sources"]:
                if set(row) != {"source_id", "text"} or not isinstance(row["text"], str):
                    raise ValueError()
                key = identifier(row["source_id"])
                if key in sources:
                    raise ValueError()
                sources[key] = row["text"]
            samples = tuple(Sample(**row) for row in bundle["samples"])
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ValidationError("Invalid source bundle schema; prose is omitted from diagnostics.") from None
        if not samples:
            raise ValidationError("Source bundle contains no samples.")
        for sample in samples:
            text = sources.get(sample.source_id)
            if text is None or digest(text) != sample.source_sha256:
                raise ValidationError("Source SHA-256 mismatch or missing source.")
            if sample.answer_end > len(text) or text[sample.answer_start:sample.answer_end] != sample.answer:
                raise ValidationError("Answer must exactly match the source character range.")
            if sample.packet_id is not None:
                raise ValidationError("Referenced packet ingestion is not implemented; omit packet_id for this phase.")
        return samples
