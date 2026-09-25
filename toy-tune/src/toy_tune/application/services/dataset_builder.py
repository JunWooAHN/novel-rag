import hashlib
import json

from toy_tune.domain.errors import ValidationError
from toy_tune.domain.samples import Sample


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def build_dataset(samples: tuple[Sample, ...], counts: tuple[int, int, int], allow_context_overlap: bool,
                  source_snapshot: bytes):
    if len(counts) != 3 or any(type(c) is not int or c <= 0 for c in counts) or sum(counts) != len(samples):
        raise ValidationError("Positive train/validation/test counts must exactly cover all samples.")
    if len({s.work_id for s in samples}) != 1:
        raise ValidationError("The initial chronological builder accepts one work per dataset.")
    ordered = sorted(samples, key=lambda s: s.order)
    if len({s.sample_id for s in samples}) != len(samples) or len({s.order for s in samples}) != len(samples):
        raise ValidationError("Duplicate sample ID or chronological order.")
    a, b, _ = counts
    splits = dict(zip(("train", "validation", "test"), (ordered[:a], ordered[a:a+b], ordered[a+b:])))
    seen_scenes, seen_answers = {}, {}
    warnings = []
    for name, group in splits.items():
        for s in group:
            scene_key = (s.work_id, s.scene_id)
            answer_key = " ".join(s.answer.split())
            if scene_key in seen_scenes and seen_scenes[scene_key] != name:
                raise ValidationError("A scene appears in multiple splits.")
            if answer_key in seen_answers and seen_answers[answer_key] != name:
                raise ValidationError("An identical normalized answer appears in multiple splits.")
            seen_scenes[scene_key], seen_answers[answer_key] = name, name
            if answer_key in " ".join(s.prompt.split()):
                raise ValidationError("A prompt contains its complete normalized target.")
            for other_name, other_group in splits.items():
                if other_name != name and any(
                    " ".join(other.answer.split()) in " ".join(s.prompt.split()) for other in other_group
                ):
                    if not allow_context_overlap:
                        raise ValidationError("A prompt contains a target from another split; review boundary context.")
                    warnings.append({"code": "cross_split_context", "sample_id": s.sample_id})
    files = {"source-bundle.json": source_snapshot}
    for name, group in splits.items():
        rows = [json.dumps(s.to_dict(), ensure_ascii=False, sort_keys=True) for s in group]
        files[name + ".jsonl"] = ("\n".join(rows) + "\n").encode()
    statistics = {
        name: {"samples": len(group), "answer_characters": sum(len(s.answer) for s in group)}
        for name, group in splits.items()
    }
    files["statistics.json"] = json_bytes(statistics)
    fingerprints = {
        name: hashlib.sha256(value).hexdigest() for name, value in sorted(files.items())
    }
    identity = {"schema_version": 1, "builder_version": 1, "files": fingerprints,
                "allow_context_overlap": allow_context_overlap}
    dataset_id = "ds-" + hashlib.sha256(json_bytes(identity)).hexdigest()[:24]
    metadata = {**identity, "counts": dict(zip(splits, counts)), "warnings": warnings,
                "token_validation": "pending", "loss_mask_validation": "pending",
                "leakage_check": "exact normalized matches only; human review required"}
    return dataset_id, files, metadata
