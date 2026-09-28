"""Bounded source DB → 31B candidates → E5 search trial; never publishes reality."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from novel_factory.reality.application import check_response, make_prompt
from novel_factory.reality.adapters.gemma import MODEL, MODEL_REVISION
from novel_factory.reality.adapters.postgres import PgRealityStore


def mapping_ids(folder: Path) -> set[str]:
    ids = set()
    for file in folder.glob("*.csv"):
        with file.open(newline="", encoding="utf-8") as stream:
            for row in csv.reader(stream):
                if row:
                    ids.add(row[0])
    return ids


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True, help="Local PostgreSQL connection string; do not include credentials in logs")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    ingest = sub.add_parser("ingest")
    ingest.add_argument("--source", type=Path, required=True)
    extract = sub.add_parser("extract")
    extract.add_argument("--limit", type=int, default=2)
    extract.add_argument("--model-cache", required=True)
    extract.add_argument("--mapping-dir", type=Path, required=True)
    extract.add_argument("--retry-no-raw-failure", action="store_true")
    embed = sub.add_parser("embed")
    embed.add_argument("--limit", type=int, default=2)
    embed.add_argument("--model-cache", required=True)
    search = sub.add_parser("search")
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=2)
    search.add_argument("--model-cache", required=True)
    sub.add_parser("status")
    sub.add_parser("verify")
    candidates = sub.add_parser("candidates")
    candidates.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()
    store = PgRealityStore(args.dsn, MODEL, MODEL_REVISION)

    if args.command == "init":
        store.init_schema(Path(__file__).with_name("schema.sql"))
        result = {"schema": "ready", "reality_release": "not_created"}
    elif args.command == "ingest":
        result = store.ingest(json.loads(args.source.read_bytes()))
    elif args.command == "extract":
        if not 1 <= args.limit <= 4:
            raise ValueError("Bounded trial limit must be 1..4")
        units = store.pending_units(args.limit, args.retry_no_raw_failure)
        if not units:
            result = {"requested": 0, "model_loaded": False, "reason": "no_pending_units"}
        else:
            from novel_factory.reality.adapters.gemma import GemmaExtractor
            extractor = GemmaExtractor(args.model_cache)
            known = mapping_ids(args.mapping_dir)
            outcomes=[]
            for unit in units:
                attempt_id = None
                raw = None
                try:
                    attempt_id = store.begin_attempt(unit, args.retry_no_raw_failure)
                    raw = extractor.extract(make_prompt(unit))
                    checked, notes = check_response(raw, unit, known)
                    outcome = store.complete_attempt(unit, raw, checked, notes)
                    outcome["unit_id"] = unit.unit_id
                    outcomes.append(outcome)
                except Exception as exc:
                    if attempt_id is not None:
                        store.fail_attempt(attempt_id, type(exc).__name__ + ": " + str(exc), raw)
                    outcomes.append({"unit_id":unit.unit_id,"attempt_id":attempt_id,"status":"failed","error_type":type(exc).__name__})
            result = {"requested":len(units),"results":outcomes,"reality_release":"not_created"}
    elif args.command == "embed":
        if not 1 <= args.limit <= 4:
            raise ValueError("Bounded trial limit must be 1..4")
        from novel_factory.reality.adapters.e5 import E5Embedder
        embedder = E5Embedder(args.model_cache)
        units = [u for u in store.units() if not store.has_embedding(u,embedder.model,embedder.revision)][:args.limit]
        outcomes=[]
        for unit in units:
            try:
                store.save_embedding(unit,embedder.model,embedder.revision,embedder.passage(unit.text))
                outcomes.append({"unit_id":unit.unit_id,"status":"embedded"})
            except Exception as exc:
                outcomes.append({"unit_id":unit.unit_id,"status":"held","error_type":type(exc).__name__,"reason":str(exc)})
        result = {"model":embedder.model,"revision":embedder.revision,"results":outcomes}
    elif args.command == "search":
        from novel_factory.reality.adapters.e5 import E5Embedder
        embedder = E5Embedder(args.model_cache)
        result = {"model":embedder.model,"revision":embedder.revision,"hits":
                  store.search(embedder.query(args.query),embedder.model,embedder.revision,args.limit),
                  "scope":"two selected source units; ranking is exploratory, not relevance certification"}
    elif args.command == "status":
        result=store.summary()
    elif args.command == "verify":
        result=store.verify_integrity()
    elif args.command == "candidates":
        result={"rows":store.candidate_rows(args.limit),"status":"trial_candidates_only"}
    else:
        raise AssertionError(args.command)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True,default=str))


if __name__ == "__main__":
    main()
