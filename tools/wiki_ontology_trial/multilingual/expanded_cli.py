"""Five-target full-page multilingual trial, with explicit DB status and resume."""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

from novel_factory.reality.adapters.e5 import E5Embedder
from novel_factory.reality.adapters.expanded_postgres import ExpandedRealityStore
from novel_factory.reality.adapters.gemma import MODEL, MODEL_REVISION
from novel_factory.reality.domain import digest
from novel_factory.reality.expanded import (
    check_indexed_response, indexed_prompt_sha, make_indexed_prompt,
    plan_embedding_spans, validate_fixture_inventory,
)


def mapping_ids(folder: Path) -> set[str]:
    ids = set()
    for file in folder.glob("*.csv"):
        with file.open(newline="", encoding="utf-8") as stream:
            for row in csv.reader(stream):
                if row:
                    ids.add(row[0])
    if not ids:
        raise ValueError("Mapping CSV directory is empty")
    return ids


def read_source(source_root: Path, relative: str, expected_sha: str) -> dict:
    path = (source_root / relative).resolve()
    if not path.is_relative_to(source_root.resolve()):
        raise ValueError("Source path escapes fixed bundle")
    raw = path.read_bytes()
    if digest(raw) != expected_sha:
        raise ValueError("Source JSON SHA differs from manifest")
    return json.loads(raw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True, help="Local PostgreSQL connection (omit credentials from logs)")
    parser.add_argument("--mapping-dir", type=Path, required=True,
                        help="Fixed seven mapping CSVs; also selects the current extraction prompt 판")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    ingest = sub.add_parser("ingest")
    ingest.add_argument("--source-root", type=Path, required=True)
    ingest.add_argument("--manifest", type=Path, required=True)
    ingest.add_argument("--receipts", type=Path, required=True)
    ingest.add_argument("--expected-sitelinks", type=Path, required=True)
    ingest.add_argument("--unit-bytes", type=int, default=3200)
    extract = sub.add_parser("extract")
    extract.add_argument("--model-cache", required=True)
    extract.add_argument("--limit", type=int, default=8)
    extract.add_argument("--max-new-tokens", type=int, default=2600)
    extract.add_argument("--retry-no-raw-failure", action="store_true")
    embed = sub.add_parser("embed")
    embed.add_argument("--model-cache", required=True)
    embed.add_argument("--limit", type=int, default=8)
    embed.add_argument("--retry-failed", action="store_true")
    search = sub.add_parser("search")
    search.add_argument("--model-cache", required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=5)
    sub.add_parser("status")
    sub.add_parser("verify")
    candidates = sub.add_parser("candidates")
    candidates.add_argument("--limit", type=int, default=10)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    ids = mapping_ids(args.mapping_dir)
    store = ExpandedRealityStore(args.dsn, MODEL, MODEL_REVISION,
                                 prompt_digest=lambda unit: indexed_prompt_sha(unit, ids))
    if args.command == "init":
        directory = Path(__file__).parent
        store.init_expanded_schema(directory / "schema.sql", directory / "expanded_schema.sql")
        result = {"schema": "ready", "reality_release": "not_created"}
    elif args.command == "ingest":
        manifest = json.loads(args.manifest.read_bytes())
        receipts = json.loads(args.receipts.read_bytes())
        expected_links = json.loads(args.expected_sitelinks.read_bytes())
        if not isinstance(manifest, list) or not isinstance(receipts, list):
            raise ValueError("Manifest/receipt roots must be lists")
        denominator = validate_fixture_inventory(expected_links, receipts, manifest)
        if not 128 <= args.unit_bytes <= 10000:
            raise ValueError("Unit byte size outside bounded extraction range")
        seen = set()
        pages = []
        failures = {}
        for item in manifest:
            source = read_source(args.source_root, item["source_file"], item["source_sha256"])
            page_key = ":".join(str(source[k]) for k in ("wiki_id", "page_id", "revision_id", "slot"))
            if page_key in seen:
                raise ValueError("Duplicate source page in manifest")
            seen.add(page_key)
            if source["content_sha256"] != item["content_sha256"]:
                raise ValueError("Source content SHA differs from manifest")
            try:
                pages.append(store.ingest_full_page(source, args.unit_bytes))
            except Exception as exc:
                failures[item["source_file"]] = type(exc).__name__
        links = store.ingest_links(receipts, args.source_root, expected_links, failures)
        result = {**denominator,"pages_ingested": len(pages), "units_ingested": sum(x["units"] for x in pages),
                  "target_relations": links["relations"], "unit_bytes": args.unit_bytes,
                  "pages_failed": len(failures), "failed_page_files": sorted(failures),
                  "full_coverage": store.verify_full_coverage()}
    elif args.command == "extract":
        if not 1 <= args.limit <= 10000 or not 128 <= args.max_new_tokens <= 4096:
            raise ValueError("Extraction limit or output cap is invalid")
        units = store.pending_units(args.limit, args.retry_no_raw_failure)
        if not units:
            result = {"requested": 0, "model_loaded": False, "reality_release": "not_created"}
        else:
            from novel_factory.reality.adapters.gemma import GemmaExtractor
            model = GemmaExtractor(args.model_cache)
            completed = failed = 0
            for unit in units:
                started = time.perf_counter()
                attempt_id = None
                raw = None
                try:
                    attempt_id = store.begin_attempt(unit, args.retry_no_raw_failure)
                    raw = model.extract(make_indexed_prompt(unit, ids), args.max_new_tokens)
                    candidates, notes = check_indexed_response(raw, unit, ids)
                    outcome = store.complete_attempt(unit, raw, candidates, notes)
                    completed += 1
                    outcome.update({"status": "completed", "unit_id": unit.unit_id,
                                    "input_tokens": model.last_input_tokens,
                                    "generated_tokens": model.last_generated_tokens,
                                    "elapsed_seconds": round(time.perf_counter() - started, 2)})
                except Exception as exc:
                    if attempt_id is not None:
                        store.fail_attempt(attempt_id, f"{type(exc).__name__}: {exc}", raw)
                    failed += 1
                    outcome = {"status": "failed", "unit_id": unit.unit_id,
                               "attempt_id": attempt_id, "error_type": type(exc).__name__,
                               "elapsed_seconds": round(time.perf_counter() - started, 2)}
                print(json.dumps(outcome, ensure_ascii=False, sort_keys=True), flush=True)
            result = {"requested": len(units), "completed": completed, "failed": failed,
                      "model_loaded": True, "reality_release": "not_created"}
    elif args.command == "embed":
        if not 1 <= args.limit <= 10000:
            raise ValueError("Embedding limit is invalid")
        model = E5Embedder(args.model_cache)
        prior_failures = store.embedding_failure_units(model.model, model.revision)
        added = failed = selected = 0
        for unit,evidence_start,evidence_end,evidence_text in store.eligible_evidence_spans():
            if unit.unit_id in prior_failures and not args.retry_failed:
                continue
            try:
                evidence_unit = type(unit)(
                    unit_id=unit.unit_id,wiki_id=unit.wiki_id,page_id=unit.page_id,
                    revision_id=unit.revision_id,slot=unit.slot,language=unit.language,
                    title=unit.title,start_byte=evidence_start,end_byte=evidence_end,
                    text=evidence_text,text_sha256=digest(evidence_text.encode("utf-8")))
                planned = plan_embedding_spans(evidence_unit, model.passage_token_length)
                missing = [(start,end,text) for start,end,text in planned
                           if not store.has_span_embedding(unit.unit_id,start,end,model.model,model.revision,
                                                           digest(text.encode("utf-8")))]
                if not missing:
                    continue
                selected += 1
                for start,end,text in missing:
                    store.save_span_embedding(unit,start,end,text,model.model,model.revision,
                                              model.passage(text))
                    added += 1
                store.clear_embedding_failure(unit,model.model,model.revision)
            except Exception as exc:
                failed += 1
                store.record_embedding_failure(unit,model.model,model.revision,type(exc).__name__)
                print(json.dumps({"unit_id":unit.unit_id,"status":"embedding_failed",
                                  "error_type":type(exc).__name__}), flush=True)
            if selected >= args.limit:
                break
        result = {"evidence_spans_selected":selected,"embedding_spans_added":added,"spans_failed":failed,
                  "model":model.model,"revision":model.revision}
    elif args.command == "search":
        if not 1 <= args.limit <= 100:
            raise ValueError("Search limit is invalid")
        model = E5Embedder(args.model_cache)
        result = {"hits":store.search_spans(model.query(args.query),model.model,model.revision,args.limit),
                  "scope":"exact source spans; ranking and claim relevance unreviewed"}
    elif args.command == "status":
        result = store.expanded_summary()
    elif args.command == "verify":
        result = {"source_and_candidates":store.verify_integrity(),
                  "full_body_and_relations":store.verify_full_coverage()}
    elif args.command == "candidates":
        result = {"rows":store.candidate_rows(args.limit),"status":"unreviewed_or_held_only"}
    else:
        raise AssertionError(args.command)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, default=str), flush=True)


if __name__ == "__main__":
    main()
