"""Bounded DB-based input, submission, independent review, and resume CLI."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import sys

from novel_factory.composition import (
    analysis_workflow, import_training_result, prepare_style_packet, publish_dataset_release,
    read_accepted_release, read_dataset_release, read_legacy_status, read_training_run,
    request_training_attempt,
)
from novel_factory.style.dataset_release import canonical, sha
from novel_factory.style.legacy_import import import_legacy_release, IMPORT_ID
from novel_factory.style.sqlite_store import SQLiteAnalysisStore
from novel_factory.style.workflow import Selection


def _prepared(value, include_body: bool = True) -> dict:
    result = {"task_id": value.task_id, "workflow_kind": value.workflow_kind,
              "selection_kind": value.selection_kind, "selection_id": value.selection_id,
              "role": value.role, "split": value.split, "source_span": asdict(value.span)}
    if include_body:
        result["body"] = value.body
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/analysis/novel-corpus.sqlite3"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="install analysis tables in an existing corpus DB (use a backup copy first)")
    w = sub.add_parser("register-window", help="register an explicitly approved bounded selection")
    for flag, typ in (("window-id", str), ("work", str), ("source-revision", int),
                      ("source-sha", str), ("segmentation", int), ("start-cp", int),
                      ("end-cp", int), ("text-sha", str), ("role", str), ("split", str),
                      ("workflow-kind", str), ("approval-ref", str), ("approved-by", str)):
        w.add_argument("--" + flag, type=typ, required=True)
    p = sub.add_parser("prepare", help="return exactly one pinned, bounded input body")
    for flag, typ in (("work", str), ("source-revision", int), ("source-sha", str),
                      ("segmentation", int)):
        p.add_argument("--" + flag, type=typ, required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--chapter", type=int)
    group.add_argument("--window-id")
    p.add_argument("--workflow-kind", choices=("chapter_analysis", "reverse_window", "reverse_section"))
    pw = sub.add_parser("prepare-window", help="prepare one already registered window by ID")
    pw.add_argument("window_id")
    vi = sub.add_parser("view-input", help="show only a previously prepared task's bounded DB input")
    vi.add_argument("task_id")
    ex = sub.add_parser("export-input", help="write only one task's bounded input to a file")
    ex.add_argument("task_id")
    ex.add_argument("output", type=Path)
    s = sub.add_parser("submit")
    s.add_argument("task_id")
    s.add_argument("submission_id")
    s.add_argument("actor")
    s.add_argument("input", type=Path, help="UTF-8 JSON result, not source text")
    vr = sub.add_parser("view-result", help="read exact stored submission and current review from DB")
    vr.add_argument("task_id")
    vr.add_argument("submission_id")
    er = sub.add_parser("export-result", help="write exact stored submission bytes to a file")
    er.add_argument("task_id")
    er.add_argument("submission_id")
    er.add_argument("output", type=Path)
    r = sub.add_parser("review")
    r.add_argument("task_id")
    r.add_argument("submission_id")
    r.add_argument("review_id")
    r.add_argument("reviewer")
    r.add_argument("decision", choices=("accepted", "rejected", "hold"))
    r.add_argument("submission_sha256")
    r.add_argument("reason")
    r.add_argument("--previous-review-sha256")
    resume = sub.add_parser("resume", help="list task states; never prints source or result bodies")
    resume.add_argument("task_id", nargs="?")
    migrate = sub.add_parser("import-legacy", help="one atomic import of frozen reverse-review state")
    migrate.add_argument("--initial-root", type=Path,
        default=Path("data/training/reverse-20260925"))
    migrate.add_argument("--full-root", type=Path,
        default=Path("data/training/reverse-full-20260925"))
    migrate.add_argument("--import-id", default=IMPORT_ID)
    summary = sub.add_parser("legacy-summary", help="fixed release counts, no source or result body")
    summary.add_argument("--import-id", default=IMPORT_ID)
    status = sub.add_parser("legacy-status", help="reviewed/held selection and revision state, no bodies")
    status.add_argument("--import-id", default=IMPORT_ID)
    status.add_argument("--work")
    status.add_argument("--selection-id")
    ds = sub.add_parser("release-dataset", help="freeze one reviewed role without repartitioning splits")
    ds.add_argument("--import-id", default=IMPORT_ID)
    ds.add_argument("--role", choices=("gemma_style", "sota_planning"), required=True)
    ds_show = sub.add_parser("dataset-summary", help="show immutable dataset identity and counts")
    ds_show.add_argument("release_id")
    packet = sub.add_parser("export-style-packet", help="write one reviewed style packet to a new private file")
    packet.add_argument("release_id")
    packet.add_argument("output", type=Path)
    request = sub.add_parser("request-training", help="register one pinned offline run attempt")
    request.add_argument("input", type=Path, help="request JSON file; payload is not printed")
    imported = sub.add_parser("import-training-result", help="verify and import an offline attempt result")
    imported.add_argument("input", type=Path, help="result JSON file; payload is not printed")
    run = sub.add_parser("training-status", help="show run/attempt state without artifact payloads")
    run.add_argument("run_id")
    args = parser.parse_args(argv)
    store = SQLiteAnalysisStore(args.db)
    flow = analysis_workflow(args.db)
    try:
        if args.command == "init":
            store.init()
            result = {"db": str(args.db), "analysis_schema": 1}
        elif args.command == "register-window":
            result = store.register_window(window_id=args.window_id, work_id=args.work,
                source_revision_id=args.source_revision, source_sha256=args.source_sha,
                segmentation_id=args.segmentation, start_cp=args.start_cp, end_cp=args.end_cp,
                text_sha256=args.text_sha, role=args.role, split=args.split,
                workflow_kind=args.workflow_kind, approval_ref=args.approval_ref,
                approved_by=args.approved_by)
        elif args.command == "prepare":
            kind = "chapter" if args.chapter is not None else "window"
            result = _prepared(flow.prepare_analysis_input(Selection(args.work,
                args.source_revision, args.source_sha, args.segmentation, kind,
                args.chapter if kind == "chapter" else args.window_id,
                args.workflow_kind or ("chapter_analysis" if kind == "chapter" else "reverse_window"))))
        elif args.command == "prepare-window":
            result = _prepared(store.prepare_window_id(args.window_id))
        elif args.command == "view-input":
            result = _prepared(store.get_input(args.task_id))
        elif args.command == "export-input":
            prepared = store.get_input(args.task_id)
            if args.output.exists():
                raise ValueError("output already exists")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(prepared.body.encode("utf-8"))
            result = {**_prepared(prepared, include_body=False), "output": str(args.output)}
        elif args.command == "submit":
            result = flow.submit_result(args.task_id, args.submission_id, args.actor,
                                        args.input.read_bytes().decode("utf-8"))
        elif args.command == "view-result":
            result = flow.get_submission(args.task_id, args.submission_id)
        elif args.command == "export-result":
            submission = flow.get_submission(args.task_id, args.submission_id)
            if args.output.exists():
                raise ValueError("output already exists")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(submission.pop("payload_json").encode("utf-8"))
            result = {**submission, "output": str(args.output)}
        elif args.command == "review":
            result = flow.review_result(args.task_id, args.submission_id, args.review_id,
                args.reviewer, args.decision, args.reason, args.submission_sha256,
                args.previous_review_sha256)
        elif args.command == "import-legacy":
            result = import_legacy_release(args.db, args.initial_root,
                                           args.full_root, args.import_id)
        elif args.command == "legacy-summary":
            release = read_accepted_release(args.db, args.import_id)
            result = {"import_id": release["release_id"],
                      "accepted": release["accepted_count"],
                      "source_hashes": release["source_hashes"]}
        elif args.command == "legacy-status":
            result = read_legacy_status(args.db, args.import_id,
                                        args.work, args.selection_id)
        elif args.command == "release-dataset":
            release = publish_dataset_release(args.db, args.import_id, args.role)
            result = {k: v for k, v in release.items() if k != "items"}
            result["item_count"] = len(release["items"])
        elif args.command == "dataset-summary":
            release = read_dataset_release(args.db, args.release_id)
            result = {k: v for k, v in release.items() if k != "items"}
            result["item_count"] = len(release["items"])
        elif args.command == "export-style-packet":
            if args.output.exists():
                raise ValueError("style packet output already exists")
            packet = prepare_style_packet(args.db, args.release_id)
            raw = canonical(packet)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(raw)
            result = {"dataset_release_id": args.release_id, "packet_sha256": sha(raw),
                      "samples": len(packet["samples"]), "output": str(args.output)}
        elif args.command == "request-training":
            result = request_training_attempt(args.db, json.loads(args.input.read_bytes()))
        elif args.command == "import-training-result":
            result = import_training_result(args.db, json.loads(args.input.read_bytes()))
        elif args.command == "training-status":
            result = read_training_run(args.db, args.run_id)
        else:
            result = flow.resume(args.task_id)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, sqlite3.Error, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
