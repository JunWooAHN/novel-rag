"""Mechanical, source-identity-aware counts for the fixed old/new 100-unit runs."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3


RUNS = {"old_A": "fixed100-A-20260928", "old_B2": "fixed100-B2-20260928",
        "yago_A": "fixed100-YAGO-A-20260928", "yago_B2": "fixed100-YAGO-B2-20260928"}
SELECTION_SHA = "45f58bccc92f7b0455bd3c7902da200c24b579d3b706a495721132eeb9b856f0"


def analyze(path: Path, run_id: str, selected: dict[str, dict], prompts: dict | None) -> dict:
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError(f"SQLite quick_check failed: {path}")
        rows = db.execute("SELECT * FROM results WHERE run_id=? ORDER BY rank", (run_id,)).fetchall()
        run = db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
    if len(rows) != 100 or run is None or run["selection_sha256"] != SELECTION_SHA:
        raise ValueError(f"Incomplete or wrong selection: {run_id}")
    status = Counter()
    candidate_status = Counter()
    layers = Counter()
    errors = Counter()
    finish = Counter()
    empty_candidates = raw_count = 0
    output_tokens = 0
    queue_seconds = []
    end_to_end_seconds = []

    def percentile(values: list[float], percent: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        pos = (len(ordered) - 1) * percent / 100
        low = int(pos)
        high = min(low + 1, len(ordered) - 1)
        return round(ordered[low] + (ordered[high] - ordered[low]) * (pos - low), 3)

    for rank, row in enumerate(rows, 1):
        unit_id = row["unit_id"]
        if (unit_id not in selected or row["rank"] != rank
                or row["target"] != selected[unit_id]["target"]
                or row["source_sha256"] != selected[unit_id]["unit_sha256"]):
            raise ValueError(f"Fixed source differs: {run_id}/{rank}")
        if prompts and row["prompt_sha256"] != prompts[unit_id]["prompt_sha256"]:
            raise ValueError(f"YAGO prompt differs: {run_id}/{rank}")
        if row["response_bytes"] is not None:
            raw_count += 1
            raw = row["response_bytes"]
            if len(raw) != row["response_bytes_size"] or hashlib.sha256(raw).hexdigest() != row["response_sha256"]:
                raise ValueError(f"Raw response hash differs: {run_id}/{rank}")
            try:
                finish[str(json.loads(raw)["choices"][0].get("finish_reason"))] += 1
            except (ValueError, KeyError, IndexError, TypeError):
                finish["unknown"] += 1
        status[row["status"]] += 1
        output_tokens += row["output_tokens"] or 0
        if row["queue_wait_seconds"] is not None:
            queue_seconds.append(row["queue_wait_seconds"])
        if row["end_to_end_seconds"] is not None:
            end_to_end_seconds.append(row["end_to_end_seconds"])
        if row["error_type"]:
            errors[row["error_type"]] += 1
        if row["validation_json"]:
            candidates = json.loads(row["validation_json"])["candidates"]
            empty_candidates += not candidates
            for candidate in candidates:
                candidate_status[candidate["status"]] += 1
                layers[candidate["payload"]["layer"]] += 1
    return {"run_id": run_id, "row_count": len(rows), "raw_response_count": raw_count,
            "status_counts": dict(status), "candidate_count": sum(candidate_status.values()),
            "candidate_status_counts": dict(candidate_status), "layer_counts": dict(layers),
            "validated_zero_candidate_units": empty_candidates, "error_type_counts": dict(errors),
            "finish_reason_counts": dict(finish), "output_tokens_sum": output_tokens,
            "queue_wait_seconds_p50_p95": [percentile(queue_seconds, 50), percentile(queue_seconds, 95)],
            "end_to_end_seconds_p50_p95": [percentile(end_to_end_seconds, 50), percentile(end_to_end_seconds, 95)]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-sqlite", type=Path, required=True)
    parser.add_argument("--new-sqlite", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--phase", choices=["A", "final"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if hashlib.sha256(args.selection.read_bytes()).hexdigest() != SELECTION_SHA:
        raise ValueError("Fixed selection differs")
    selected = {row["unit_id"]: row for row in json.loads(args.selection.read_text())["units"]}
    preflight = json.loads(args.preflight.read_text())
    prompts = {row["unit_id"]: row for row in preflight["units"]}
    arms = ["old_A", "old_B2", "yago_A"] if args.phase == "A" else list(RUNS)
    result = {"schema": "yago-benchmark-mechanical-v1", "phase": args.phase,
              "selection_sha256": SELECTION_SHA, "runs": {}}
    for arm in arms:
        path = args.old_sqlite if arm.startswith("old_") else args.new_sqlite
        result["runs"][arm] = analyze(path, RUNS[arm], selected,
                                      prompts if arm.startswith("yago_") else None)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({arm: result["runs"][arm]["status_counts"] for arm in arms}))


if __name__ == "__main__":
    main()
