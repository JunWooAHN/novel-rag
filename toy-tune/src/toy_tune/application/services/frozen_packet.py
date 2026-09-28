"""CPU preparation of one DB-derived, explicitly split style packet."""
import hashlib
import json

from toy_tune.application.services.dataset_builder import json_bytes
from toy_tune.domain.errors import ValidationError
from toy_tune.domain.samples import Sample


SPLITS = ("train", "development_validation", "development_holdout")


def validate_supervised_labels(input_ids: list[int], labels: list[int], prompt_length: int) -> None:
    """A tokenizer-independent contract check; real Gemma tokenization remains pending."""
    if (not input_ids or len(input_ids) != len(labels) or not 0 < prompt_length < len(input_ids)
            or any(type(x) is not int for x in input_ids + labels)
            or any(x != -100 for x in labels[:prompt_length])
            or labels[prompt_length:] != input_ids[prompt_length:]):
        raise ValidationError("Prompt labels must be masked and target labels must match input IDs.")


def build_frozen_packet(raw: bytes):
    try:
        packet = json.loads(raw)
        required = {"schema_version", "packet_kind", "dataset_release_id", "dataset_fingerprint",
                    "parent_import_id", "role", "split_semantics", "counts", "hypothesis_status",
                    "token_validation", "loss_mask_validation", "samples"}
        if (set(packet) != required or packet["schema_version"] != 1
                or packet["packet_kind"] != "novel_factory_style_dataset"
                or packet["role"] != "gemma_style"
                or packet["split_semantics"] != "development_holdout_is_not_unseen_final_test"
                or packet["hypothesis_status"] != "reviewed_learning_input_not_author_intent_or_story_canon"
                or packet["token_validation"] != "pending_real_tokenizer"
                or packet["loss_mask_validation"] != "pending_real_tokenizer"
                or not isinstance(packet["samples"], list) or not packet["samples"]
                or set(packet["counts"]) != set(SPLITS)):
            raise ValueError()
        groups = {split: [] for split in SPLITS}
        seen = set()
        for order, row in enumerate(packet["samples"]):
            if set(row) != {"sample_id", "work_id", "split", "prompt", "answer", "source_pin",
                            "review_sha256", "learning_hypothesis_sha256", "line_sha256"}:
                raise ValueError()
            split, pin = row["split"], row["source_pin"]
            if (split not in groups or row["sample_id"] in seen
                    or set(pin) != {"source_revision_id", "source_sha256", "segmentation_id",
                                    "answer_start_cp", "answer_end_cp", "answer_sha256"}
                    or pin["answer_start_cp"] < 0 or pin["answer_end_cp"] <= pin["answer_start_cp"]
                    or hashlib.sha256(row["answer"].encode("utf-8")).hexdigest() != pin["answer_sha256"]
                    or any(len(row[k]) != 64 for k in ("review_sha256", "learning_hypothesis_sha256", "line_sha256"))):
                raise ValueError()
            seen.add(row["sample_id"])
            answer = row["answer"]
            sample = Sample(sample_id=row["sample_id"], work_id=row["work_id"],
                            scene_id=row["sample_id"], order=order, prompt=row["prompt"],
                            answer=answer, source_id=row["sample_id"],
                            source_sha256=pin["answer_sha256"], answer_start=0,
                            answer_end=len(answer), question_method="reviewed-learning-hypothesis-v1",
                            packet_id=packet["dataset_release_id"])
            if " ".join(answer.split()) in " ".join(sample.prompt.split()):
                raise ValueError()
            groups[split].append(sample)
        if any(packet["counts"][split] != len(groups[split]) or not groups[split] for split in SPLITS):
            raise ValueError()
        targets = {split: [" ".join(s.answer.split()) for s in group]
                   for split, group in groups.items()}
        target_splits = {}
        for split, answers in targets.items():
            for answer in answers:
                if answer in target_splits and target_splits[answer] != split:
                    raise ValueError()
                target_splits[answer] = split
        for split, group in groups.items():
            for sample in group:
                prompt = " ".join(sample.prompt.split())
                if any(target in prompt for other, answers in targets.items()
                       if other != split for target in answers):
                    raise ValueError()
        files = {"frozen-packet.json": raw}
        for split, group in groups.items():
            files[split + ".jsonl"] = ("\n".join(json.dumps(s.to_dict(), ensure_ascii=False,
                sort_keys=True) for s in group) + "\n").encode("utf-8")
        files["statistics.json"] = json_bytes({split: {"samples": len(group)}
                                                 for split, group in groups.items()})
        fingerprints = {name: hashlib.sha256(value).hexdigest() for name, value in sorted(files.items())}
        identity = {"schema_version": 1, "builder_version": 2, "files": fingerprints,
                    "source_dataset_release_id": packet["dataset_release_id"]}
        dataset_id = "ds-" + hashlib.sha256(json_bytes(identity)).hexdigest()[:24]
        metadata = {**identity, "counts": {split: len(groups[split]) for split in SPLITS},
                    "role": "gemma_style", "source_parent_import_id": packet["parent_import_id"],
                    "source_dataset_fingerprint": packet["dataset_fingerprint"],
                    "split_policy": "frozen_reviewed_assignment_no_repartition",
                    "token_validation": "pending_real_tokenizer",
                    "loss_mask_validation": "pending_real_tokenizer",
                    "leakage_check": "exact normalized targets; human review remains required"}
        return dataset_id, files, metadata
    except (ValueError, TypeError, KeyError, AttributeError):
        raise ValidationError("Invalid reviewed style packet; prose is omitted from diagnostics.") from None


def verify_frozen_derivation(raw: bytes, manifest: dict) -> None:
    """Check every prepared payload is exactly derived from this reviewed packet."""
    artifact_id, files, metadata = build_frozen_packet(raw)
    expected = {name: hashlib.sha256(value).hexdigest() for name, value in files.items()}
    if (manifest.get("artifact_id") != artifact_id or manifest.get("files") != expected
            or manifest.get("metadata") != metadata):
        raise ValidationError("Prepared dataset is not derived from the pinned reviewed packet.")
