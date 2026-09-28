"""Validate a product-pinned, offline training attempt before invoking the HF adapter."""
import hashlib
import json
import re

from toy_tune.domain.errors import ValidationError
from toy_tune.domain.experiments import ModelRef, TrainingRequest


KEYS = {"schema_version", "run_id", "attempt_id", "dataset_release_id", "dataset_fingerprint",
        "packet_sha256", "prepared_dataset_id", "prepared_manifest_path",
        "prepared_manifest_sha256", "model_revision", "scope", "selected_sample_ids"}
MODEL = re.compile(r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([0-9a-f]{40})\Z")


def canonical(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def validate_offline_attempt(raw: bytes, manifest_raw: bytes, manifest: dict,
                             dataset_id: str, max_steps: int,
                             allowed_model_revision: str,
                             selected_sample_ids: list[str]) -> tuple[TrainingRequest, dict, str]:
    try:
        data = json.loads(raw)
        match = MODEL.fullmatch(data["model_revision"])
        if (set(data) != KEYS or data["schema_version"] != 1 or data["scope"] != "real"
                or data["prepared_dataset_id"] != dataset_id or match is None
                or data["selected_sample_ids"] != selected_sample_ids
                or not isinstance(selected_sample_ids, list)
                or not 1 <= len(selected_sample_ids) <= 4
                or any(not isinstance(item, str) or not item for item in selected_sample_ids)
                or len(set(selected_sample_ids)) != len(selected_sample_ids)
                or data["model_revision"] != allowed_model_revision
                or not isinstance(data["run_id"], str) or not data["run_id"]
                or not isinstance(data["attempt_id"], str) or not data["attempt_id"]
                or manifest["artifact_id"] != dataset_id
                or manifest["metadata"]["source_dataset_release_id"] != data["dataset_release_id"]
                or manifest["metadata"]["source_dataset_fingerprint"] != data["dataset_fingerprint"]
                or manifest["metadata"]["role"] != "gemma_style"
                or manifest["metadata"]["token_validation"] != "pending_real_tokenizer"
                or manifest["files"]["frozen-packet.json"] != data["packet_sha256"]
                or hashlib.sha256(manifest_raw).hexdigest()
                   != data["prepared_manifest_sha256"]):
            raise ValueError()
    except (ValueError, TypeError, KeyError):
        raise ValidationError("Offline run does not match its pinned reviewed style dataset.") from None
    request = TrainingRequest(model=ModelRef(repository=match.group(1),
                                             revision=match.group(2), format="hf"),
                              dataset_id=dataset_id, run_id=data["run_id"],
                              dtype="bfloat16", max_steps=max_steps, seed=17)
    return request, data, hashlib.sha256(canonical(data)).hexdigest()
