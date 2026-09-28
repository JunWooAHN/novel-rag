"""Freeze reviewed reverse samples without changing their role or split."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from typing import Protocol


SPLITS = ("train", "development_validation", "development_holdout")
ROLES = ("gemma_style", "sota_planning")


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class DatasetReleaseStore(Protocol):
    def read_reviewed_parent(self, import_id: str) -> dict: ...
    def publish_dataset(self, release: dict) -> dict: ...
    def read_dataset(self, release_id: str) -> dict: ...


def _item(row: dict, role: str) -> dict:
    record = row["record"]
    metadata = record["metadata"]
    if metadata["role"] != role or metadata["split"] not in SPLITS:
        raise ValueError("reviewed role or split differs")
    messages = record["messages"]
    if len(messages) != 2 or [m["role"] for m in messages] != ["user", "assistant"]:
        raise ValueError("reviewed sample needs one user input and assistant target")
    prompt, target = (m["content"] for m in messages)
    if not prompt.strip() or not target.strip() or not row["source_answer"]:
        raise ValueError("reviewed sample has empty input, target or source evidence")
    if (metadata["source_sha256"] != row["source_sha256"]
            or metadata["segmentation_id"] != row["segmentation_id"]
            or metadata["answer_start_cp"] != row["answer_start_cp"]
            or metadata["answer_end_cp"] != row["answer_end_cp"]
            or sha(row["source_answer"].encode("utf-8")) != metadata["answer_sha256"]):
        raise ValueError("reviewed source pin or answer hash differs")
    if role == "gemma_style" and (target != row["source_answer"]
                                  or metadata["target_basis"] != "observed_exact_source_slice"):
        raise ValueError("style target is not the exact reviewed source slice")
    if role == "sota_planning" and metadata["target_basis"] != "reviewed_reconstruction_not_author_intent":
        raise ValueError("planning target was promoted to author intent")
    if " ".join(target.split()) in " ".join(prompt.split()):
        raise ValueError("complete target appears in the input")
    candidate = row["candidate"]
    hypothesis = candidate["writer_input" if role == "gemma_style" else "planner_input"]
    if not isinstance(hypothesis, dict) or not hypothesis:
        raise ValueError("reviewed learning input hypothesis is missing")
    if (record["sample_id"] != row["candidate_id"]
            or sha(row["raw_line"].encode("utf-8")) != row["line_sha256"]):
        raise ValueError("candidate identity or reviewed JSONL hash differs")
    return {
        "candidate_id": row["candidate_id"], "selection_id": row["selection_id"],
        "work_id": metadata["work_id"], "role": role, "split": metadata["split"],
        "source_revision_id": row["source_revision_id"],
        "source_sha256": row["source_sha256"], "segmentation_id": row["segmentation_id"],
        "answer_start_cp": row["answer_start_cp"], "answer_end_cp": row["answer_end_cp"],
        "answer_sha256": metadata["answer_sha256"],
        "prompt_sha256": sha(prompt.encode("utf-8")), "target_sha256": sha(target.encode("utf-8")),
        "review_sha256": row["review_sha256"], "learning_hypothesis_sha256": sha(canonical(hypothesis)),
        "line_sha256": row["line_sha256"],
    }


def release_dataset(store: DatasetReleaseStore, import_id: str, role: str) -> dict:
    if role not in ROLES or not import_id:
        raise ValueError("fixed parent import and supported role are required")
    parent = store.read_reviewed_parent(import_id)
    if parent["import_id"] != import_id:
        raise ValueError("parent import identity differs")
    items = [_item(row, role) for row in parent["rows"] if row["record"]["metadata"]["role"] == role]
    if not items or len({x["candidate_id"] for x in items}) != len(items):
        raise ValueError("reviewed dataset is empty or has duplicate candidates")
    counts = Counter(x["split"] for x in items)
    if any(counts[s] == 0 for s in SPLITS):
        raise ValueError("all frozen development splits need reviewed samples")
    # The initial and full source selections interleave in source time. Preserve their reviewed
    # split assignment; never repartition by sorting the combined set.
    items.sort(key=lambda x: (SPLITS.index(x["split"]), x["work_id"], x["answer_start_cp"], x["candidate_id"]))
    identity = {"contract_version": 1, "parent_import_id": import_id,
                "parent_fingerprint": parent["fingerprint"], "role": role,
                "purpose": "style_training_candidate" if role == "gemma_style" else "planning_research_only",
                "split_semantics": "development_holdout_is_not_unseen_final_test",
                "items": items}
    fingerprint = sha(canonical(identity))
    release = {**identity, "release_id": "ds-" + role.replace("_", "-") + "-" + fingerprint[:24],
               "fingerprint": fingerprint, "counts": {s: counts[s] for s in SPLITS}}
    return store.publish_dataset(release)


def frozen_style_packet(store: DatasetReleaseStore, release_id: str) -> dict:
    """Materialize only one reviewed style release for offline preparation."""
    release = store.read_dataset(release_id)
    if release["role"] != "gemma_style" or release["purpose"] != "style_training_candidate":
        raise ValueError("planning research cannot be sent to style fine-tuning")
    parent = store.read_reviewed_parent(release["parent_import_id"])
    if parent["fingerprint"] != release["parent_fingerprint"]:
        raise ValueError("dataset parent changed")
    by_id = {row["candidate_id"]: row for row in parent["rows"]
             if row["record"]["metadata"]["role"] == "gemma_style"}
    samples = []
    for item in release["items"]:
        row = by_id.pop(item["candidate_id"], None)
        if row is None:
            raise ValueError("frozen dataset item is absent from parent")
        calculated = _item(row, "gemma_style")
        if any(calculated[k] != item[k] for k in calculated):
            raise ValueError("frozen dataset item differs from reviewed parent")
        user, assistant = row["record"]["messages"]
        samples.append({
            "sample_id": item["candidate_id"], "work_id": item["work_id"],
            "split": item["split"], "prompt": user["content"], "answer": assistant["content"],
            "source_pin": {k: item[k] for k in ("source_revision_id", "source_sha256",
                "segmentation_id", "answer_start_cp", "answer_end_cp", "answer_sha256")},
            "review_sha256": item["review_sha256"],
            "learning_hypothesis_sha256": item["learning_hypothesis_sha256"],
            "line_sha256": item["line_sha256"],
        })
    if by_id or len(samples) != sum(release["counts"].values()):
        raise ValueError("frozen dataset misses reviewed samples")
    return {"schema_version": 1, "packet_kind": "novel_factory_style_dataset",
            "dataset_release_id": release_id, "dataset_fingerprint": release["fingerprint"],
            "parent_import_id": release["parent_import_id"], "role": "gemma_style",
            "split_semantics": release["split_semantics"], "counts": release["counts"],
            "hypothesis_status": "reviewed_learning_input_not_author_intent_or_story_canon",
            "token_validation": "pending_real_tokenizer", "loss_mask_validation": "pending_real_tokenizer",
            "samples": samples}
