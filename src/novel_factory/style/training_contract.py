"""Small offline training request/result contract; no engine or SQLite dependency."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import re
from typing import Protocol

from novel_factory.style.dataset_release import canonical, sha
import json


HEX = re.compile(r"[0-9a-f]{64}\Z")


class TrainingStore(Protocol):
    def create_attempt(self, request: dict, request_sha256: str) -> dict: ...
    def import_attempt_result(self, result: dict, result_sha256: str) -> dict: ...


REQUEST_KEYS = {"schema_version", "run_id", "attempt_id", "dataset_release_id",
                "dataset_fingerprint", "packet_sha256", "prepared_dataset_id",
                "prepared_manifest_path", "prepared_manifest_sha256", "model_revision", "scope"}
RESULT_KEYS = {"schema_version", "run_id", "attempt_id", "request_sha256", "status",
               "artifact_path", "artifact_sha256", "validation_scope", "training_completed",
               "reload_verified", "token_validation", "loss_mask_validation"}


def _real_result_evidence(result: dict, request: dict, artifact: Path) -> None:
    """Bind one completed real candidate to the same attempt's saved training and reload proof."""
    if (artifact.name != "adapter.tar" or artifact.is_symlink()
            or result["validation_scope"] != "real_tokenizer_and_reload"
            or result["token_validation"] != "passed_real_tokenizer"
            or result["loss_mask_validation"] != "passed_real_tokenizer"
            or not result["training_completed"] or not result["reload_verified"]):
        raise ValueError("real result lacks verified training and reload evidence")
    folder = artifact.parent
    try:
        files = (folder / "run-request.json", folder / "train-report.json",
                 folder / "reload-report.json", folder / "result.json")
        if any(not path.is_file() or path.is_symlink() for path in files):
            raise ValueError()
        pinned, train, reload, remote_result = (json.loads(path.read_bytes()) for path in files)
        repository, revision = request["model_revision"].split("@", 1)
        request_sha = sha(canonical(request))
        losses = train["losses"]
        if (pinned != request
                or remote_result != {**result, "artifact_path": remote_result["artifact_path"]}
                or Path(remote_result["artifact_path"]).name != "adapter.tar"
                or any(row["run_id"] != request["run_id"]
                       or row["attempt_id"] != request["attempt_id"]
                       or row["request_sha256"] != request_sha for row in (train, reload))
                or train["dataset_id"] != request["prepared_dataset_id"]
                or train["model_repository"] != repository
                or train["model_revision"] != revision
                or train["selected_sample_ids"] != request["selected_sample_ids"]
                or train["token_validation"] != "passed_real_tokenizer"
                or train["loss_mask_validation"] != "passed_real_tokenizer"
                or type(train["changed_lora_elements"]) is not int
                or train["changed_lora_elements"] <= 0
                or type(train["trainable_parameters"]) is not int
                or train["trainable_parameters"] <= 0
                or type(train["max_steps"]) is not int or train["max_steps"] not in (1, 2)
                or not isinstance(losses, list) or len(losses) != train["max_steps"]
                or any(type(loss) not in (int, float) or not math.isfinite(loss) for loss in losses)
                or not isinstance(train["target_modules"], list) or not train["target_modules"]
                or any(not isinstance(name, str)
                       or not name.startswith("model.language_model.layers.")
                       or ".self_attn." not in name
                       or not name.endswith(("q_proj", "v_proj", "q_proj.linear", "v_proj.linear"))
                       for name in train["target_modules"])
                or reload["model_revision"] != revision
                or reload["reload_verified"] is not True
                or type(reload["generated_token_count"]) is not int
                or reload["generated_token_count"] <= 0
                or reload["artifact_sha256"] != result["artifact_sha256"]):
            raise ValueError()
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        raise ValueError("real result sidecars differ from the pinned attempt") from None


def validate_request(request: dict) -> str:
    expected_keys = REQUEST_KEYS | ({"selected_sample_ids"} if request.get("scope") == "real" else set())
    if (set(request) != expected_keys or request["schema_version"] != 1
            or request["scope"] not in ("demo", "real")
            or any(not isinstance(request[k], str) or not request[k]
                   for k in ("run_id", "attempt_id", "dataset_release_id", "prepared_dataset_id",
                             "prepared_manifest_path",
                             "model_revision"))
            or any(not isinstance(request[k], str) or not HEX.fullmatch(request[k])
                   for k in ("dataset_fingerprint", "packet_sha256", "prepared_manifest_sha256"))):
        raise ValueError("invalid pinned training request")
    if request["scope"] == "real":
        selected = request["selected_sample_ids"]
        if (not isinstance(selected, list) or not 1 <= len(selected) <= 4
                or any(not isinstance(item, str) or not item for item in selected)
                or len(set(selected)) != len(selected)):
            raise ValueError("real training needs distinct, explicitly selected train sample IDs")
    if request["scope"] == "demo" and not request["run_id"].startswith("demo:"):
        raise ValueError("demo run needs a demo identity")
    if request["scope"] == "real" and request["run_id"].startswith("demo:"):
        raise ValueError("real run cannot have a demo identity")
    manifest = Path(request["prepared_manifest_path"])
    if not manifest.is_file():
        raise ValueError("prepared dataset manifest is missing")
    raw = manifest.read_bytes()
    if sha(raw) != request["prepared_manifest_sha256"]:
        raise ValueError("prepared dataset manifest hash differs")
    try:
        value = json.loads(raw)
        metadata = value["metadata"]
        if (value["artifact_id"] != request["prepared_dataset_id"]
                or metadata["source_dataset_release_id"] != request["dataset_release_id"]
                or metadata["source_dataset_fingerprint"] != request["dataset_fingerprint"]
                or value["files"]["frozen-packet.json"] != request["packet_sha256"]):
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        raise ValueError("prepared dataset manifest references another release") from None
    files = value["files"]
    if not isinstance(files, dict) or not files:
        raise ValueError("prepared dataset file index is invalid")
    for name, expected in files.items():
        if (not isinstance(name, str) or name in ("", ".", "..", "manifest.json")
                or Path(name).name != name or "/" in name or "\\" in name
                or not isinstance(expected, str) or not HEX.fullmatch(expected)):
            raise ValueError("prepared dataset file index is invalid")
        path = manifest.parent / name
        if not path.is_file():
            raise ValueError("prepared dataset payload is missing")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected:
            raise ValueError("prepared dataset payload hash differs")
    if {path.name for path in manifest.parent.iterdir()} != set(files) | {manifest.name}:
        raise ValueError("prepared dataset contains unlisted payloads")
    return sha(canonical(request))


def validate_result(result: dict, request: dict) -> str:
    if (set(result) != RESULT_KEYS or result["schema_version"] != 1
            or result["run_id"] != request["run_id"]
            or result["attempt_id"] != request["attempt_id"]
            or result["request_sha256"] != validate_request(request)
            or result["status"] not in ("completed", "failed")
            or type(result["training_completed"]) is not bool
            or type(result["reload_verified"]) is not bool):
        raise ValueError("training result does not match its pinned request")
    if result["status"] == "failed":
        if (result["artifact_path"] is not None or result["artifact_sha256"] is not None
                or result["training_completed"] or result["reload_verified"]):
            raise ValueError("failed attempt cannot register an artifact")
    else:
        if (not isinstance(result["artifact_path"], str) or not result["artifact_path"]
                or not isinstance(result["artifact_sha256"], str)
                or not HEX.fullmatch(result["artifact_sha256"])):
            raise ValueError("completed attempt needs a hashed artifact")
        artifact = Path(result["artifact_path"])
        if not artifact.is_file():
            raise ValueError("training artifact is missing")
        digest = hashlib.sha256()
        with artifact.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != result["artifact_sha256"]:
            raise ValueError("training artifact hash differs")
        if request["scope"] == "real":
            _real_result_evidence(result, request, artifact)
        elif result["validation_scope"] != "synthetic_contract":
            raise ValueError("demo result needs explicit synthetic validation scope")
    return sha(canonical(result))


def request_attempt(store: TrainingStore, request: dict) -> dict:
    return store.create_attempt(request, validate_request(request))


def import_result(store: TrainingStore, result: dict, request: dict) -> dict:
    return store.import_attempt_result(result, validate_result(result, request))
