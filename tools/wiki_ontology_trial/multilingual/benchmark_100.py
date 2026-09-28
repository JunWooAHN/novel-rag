"""Fixed 100-source-unit vLLM trial; never writes the ontology source database.

The setup commands are ``preflight`` (CPU/DB only) and ``probe`` (synthetic
one-line completions). ``run-arm`` is the separate, bounded 100-call measurement.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import aiohttp

from benchmark_vllm_adapter import CompletionHTTPError, completion, local_base, parse_completion
from novel_factory.reality.domain import SourceUnit
from novel_factory.reality.expanded import check_indexed_response, make_indexed_prompt


SELECTION_SHA256 = "45f58bccc92f7b0455bd3c7902da200c24b579d3b706a495721132eeb9b856f0"
YAGO_MANIFEST_SHA256 = "da0d761331e3ccb070bfebbc5ecf4ad5db4165eac0ef5bc619444d95f78a70bb"
YAGO_TARGETS = {"Munjong of Joseon": "yago:Munjong_of_Joseon",
                "Danjong of Joseon": "yago:Danjong_of_Joseon",
                "Sejo of Joseon": "yago:Sejo_of_Joseon",
                "Hangul": "yago:Hangul", "Bloomery": "yago:Bloomery"}
MAX_OUTPUT_TOKENS = 2600
ARM_ENGINES = {"A": 1, "B2": 2, "B3": 3}
ARM_MODELS = {"A": "benchmark-bf16", "B2": "benchmark-fp8", "B3": "benchmark-fp8"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def selection(path: Path, expected_sha: str = SELECTION_SHA256) -> dict:
    raw = path.read_bytes()
    if sha(raw) != expected_sha:
        raise ValueError("Fixed 100-unit selection SHA differs")
    data = json.loads(raw)
    rows = data["units"]
    if len(rows) != 100 or len({row["unit_id"] for row in rows}) != 100:
        raise ValueError("Selection must contain exactly 100 distinct source units")
    if [row["rank"] for row in rows] != list(range(1, 101)):
        raise ValueError("Selection rank is not ordered 1..100")
    return data


def mapping_ids(path: Path) -> set[str]:
    files = sorted(path.glob("*.csv"))
    if len(files) != 7:
        raise ValueError("The fixed mapping directory must contain exactly seven CSVs")
    ids: set[str] = set()
    for file in files:
        with file.open(encoding="utf-8", newline="") as stream:
            ids.update(row[0] for row in csv.reader(stream) if row)
    if not ids:
        raise ValueError("No mapping IDs")
    return ids


def fixed_units(dsn: str, rows: list[dict]) -> list[SourceUnit]:
    """Read the 100 DB rows and verify their page and unit identities in memory."""
    import psycopg
    from psycopg.rows import dict_row

    ids = [row["unit_id"] for row in rows]
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        db_rows = {r["unit_id"]: r for r in conn.execute("""SELECT u.unit_id,u.start_byte,u.end_byte,u.text,u.text_sha256,
            p.page_key,p.wiki_id,p.page_id,p.revision_id,p.slot,p.language,p.title,p.body,p.body_sha256
            FROM reality_source_units u JOIN reality_source_pages p USING(page_key)
            WHERE u.unit_id = ANY(%s)""", (ids,))}
        links = {(r["page_key"], r["target"]) for r in conn.execute("""SELECT page_key,target FROM reality_target_links
            WHERE page_key = ANY(%s) AND ingest_status='ingested'""",
            (list({r["page_key"] for r in db_rows.values()}),))}
    if len(db_rows) != 100:
        raise ValueError("A selected unit is missing from the live source database")
    result = []
    for spec in rows:
        r = db_rows[spec["unit_id"]]
        for key, db_key in (("wiki_id", "wiki_id"), ("page_id", "page_id"),
                            ("revision_id", "revision_id"), ("slot", "slot"),
                            ("language", "language"), ("page_title", "title"),
                            ("start_byte", "start_byte"), ("end_byte", "end_byte"),
                            ("unit_sha256", "text_sha256"), ("page_sha256", "body_sha256")):
            if str(spec[key]) != str(r[db_key]):
                raise ValueError(f"Selection/DB {key} mismatch: {spec['unit_id']}")
        if (r["page_key"], spec["target"]) not in links:
            raise ValueError("Target/page relation differs from selected source")
        body = r["body"].encode("utf-8")
        text = r["text"].encode("utf-8")
        if (sha(body) != spec["page_sha256"] or sha(text) != spec["unit_sha256"]
            or body[r["start_byte"]:r["end_byte"]] != text or not text.strip()):
            raise ValueError(f"Source byte/hash/usable-text mismatch: {spec['unit_id']}")
        unit = SourceUnit(spec["unit_id"], r["wiki_id"], r["page_id"], r["revision_id"],
                          r["slot"], r["language"], r["title"], r["start_byte"],
                          r["end_byte"], r["text"], r["text_sha256"])
        unit.validate()
        result.append(unit)
    return result


def _token_ids(processor, prompt: str) -> list[int]:
    encoded = processor.apply_chat_template(
        [{"role": "user", "content": prompt}], tokenize=True,
        add_generation_prompt=True, enable_thinking=False, return_dict=True,
    )
    ids = encoded["input_ids"]
    if hasattr(ids, "tolist"):
        ids = ids.tolist()
    if ids and isinstance(ids[0], list):
        if len(ids) != 1:
            raise ValueError("Expected one tokenized prompt")
        ids = ids[0]
    return list(ids)


@dataclass(frozen=True)
class Prepared:
    unit: SourceUnit
    target: str
    prompt: str
    prompt_sha256: str
    input_tokens: int
    input_ids: list[int]
    baseline_input_tokens: int = 0
    kg_statement_ids: tuple[str, ...] = ()
    kg_context_status: str = "none"


def kg_context(path: Path | None) -> dict | None:
    if path is None:
        return None
    raw = path.read_bytes()
    data = json.loads(raw)
    if (data.get("schema") != "yago-5-target-kg-only-v1"
            or data.get("selection_sha256") != SELECTION_SHA256
            or data.get("yago_manifest_sha256") != YAGO_MANIFEST_SHA256
            or {name: item.get("yago_id") for name, item in data.get("targets", {}).items()} != YAGO_TARGETS):
        raise ValueError("KG-only context does not match the fixed five-target selection")
    for target in data["targets"].values():
        if target.get("mapping_status") not in {"entity_facts", "class_only", "no_direct_fact"}:
            raise ValueError("Invalid YAGO target mapping status")
        if any(item.get("source_kind") not in {"yago_fact", "yago_taxonomy"}
               for item in target.get("statements", [])):
            raise ValueError("Invalid YAGO source kind")
    data["context_sha256"] = sha(raw)
    return data


def prepare(rows: list[dict], units: list[SourceUnit], ids: set[str],
            base_processor: Path, fp8_processor: Path, context: dict | None = None,
            model_len: int = 14592) -> list[Prepared]:
    from transformers import AutoProcessor

    base = AutoProcessor.from_pretrained(str(base_processor), local_files_only=True)
    quant = AutoProcessor.from_pretrained(str(fp8_processor), local_files_only=True)
    output = []
    for spec, unit in zip(rows, units, strict=True):
        source_prompt = make_indexed_prompt(unit, ids)
        source_ids = _token_ids(base, source_prompt)
        if source_ids != _token_ids(quant, source_prompt):
            raise ValueError(f"BF16/FP8 tokenizer or no-thinking template differs: {unit.unit_id}")
        if len(source_ids) + MAX_OUTPUT_TOKENS > model_len:
            raise ValueError(f"Original source prompt exceeds context: {unit.unit_id}")
        selected: list[dict] = []
        status = "none"
        prompt = source_prompt
        if context is not None:
            target = context["targets"][spec["target"]]
            by_id = {s["statement_id"]: s for s in target["statements"]}
            for statement_id in target["eligible_statement_ids"]:
                statement = by_id[statement_id]
                if not isinstance(statement.get("prompt_text"), str):
                    raise ValueError(f"Incomplete KG statement: {statement_id}")
                proposed = selected + [statement]
                proposal = source_prompt + "\nYAGO_CONTEXT (context only; cite SOURCE_SPANS, not KG):\n" + "\n".join(
                    s["prompt_text"] for s in proposed)
                if len(_token_ids(base, proposal)) + MAX_OUTPUT_TOKENS <= model_len:
                    selected = proposed
                    prompt = proposal
            status = (target["mapping_status"] if selected else
                      "budget_omitted" if target["eligible_statement_ids"] else
                      "no_direct_fact" if target["direct_fact_count"] == 0 else "no_eligible_fact")
        conversation = [{"role": "user", "content": prompt}]
        text = base.apply_chat_template(conversation, tokenize=False,
                                        add_generation_prompt=True, enable_thinking=False)
        quant_text = quant.apply_chat_template(conversation, tokenize=False,
                                               add_generation_prompt=True, enable_thinking=False)
        tokens = _token_ids(base, prompt)
        if text != quant_text or tokens != _token_ids(quant, prompt):
            raise ValueError(f"BF16/FP8 final tokenizer/template differs: {unit.unit_id}")
        if len(tokens) + MAX_OUTPUT_TOKENS > model_len:
            raise ValueError(f"Final prompt exceeds context: {unit.unit_id}")
        output.append(Prepared(unit, spec["target"], text,
                               sha(text.encode("utf-8")), len(tokens), tokens,
                               len(source_ids), tuple(s["statement_id"] for s in selected), status))
    return output


def preflight(args) -> None:
    started = time.perf_counter()
    fixed = selection(args.selection)
    rows = fixed["units"]
    units = fixed_units(args.dsn, rows)
    source_check_seconds = time.perf_counter() - started
    context = kg_context(getattr(args, "kg_context", None))
    prepare_started = time.perf_counter()
    prepared = prepare(rows, units, mapping_ids(args.mapping_dir),
                       args.base_processor, args.fp8_processor, context)
    prompt_prepare_seconds = time.perf_counter() - prepare_started
    maximum = max(item.input_tokens for item in prepared)
    required = maximum + MAX_OUTPUT_TOKENS
    model_len = 14592 if context is not None else (required + 255) // 256 * 256
    report = {"schema": "ontology-benchmark-100-preflight-v1", "created_at_utc": now(),
              "selection_sha256": SELECTION_SHA256, "unit_count": 100,
              "source_db_check": "100/100 page revision, target relation, byte bounds, unit/page SHA",
              "processor_check": "100/100 BF16/FP8 no-thinking template text and token IDs equal",
              "kg_context_sha256": context["context_sha256"] if context else None,
              "source_check_seconds": round(source_check_seconds, 3),
              "prompt_prepare_seconds": round(prompt_prepare_seconds, 3),
              "preflight_seconds": round(time.perf_counter() - started, 3),
              "max_input_tokens": maximum, "max_output_tokens": MAX_OUTPUT_TOKENS,
              "required_model_len": required, "configured_model_len": model_len,
              "units": [{"unit_id": p.unit.unit_id, "prompt_sha256": p.prompt_sha256,
                         "input_tokens": p.input_tokens,
                         "baseline_input_tokens": p.baseline_input_tokens,
                         "kg_context_status": p.kg_context_status,
                         "kg_statement_ids": list(p.kg_statement_ids)} for p in prepared]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "units"}, ensure_ascii=False))


async def probe(args) -> None:
    from transformers import AutoProcessor

    processor = AutoProcessor.from_pretrained(str(args.base_processor), local_files_only=True)
    prompt_ids = _token_ids(processor, "Reply with exactly READY.")
    if len(args.urls) != ARM_ENGINES[args.arm] or len(set(args.urls)) != len(args.urls):
        raise ValueError("Incorrect number of distinct localhost engines for arm")
    for url in args.urls:
        local_base(url)
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        results = []
        # All engines of one arm stay loaded and receive the synthetic request
        # together; the result stays associated with its URL, not finish order.
        responses = await asyncio.gather(*[
            completion(session, url, ARM_MODELS[args.arm], prompt_ids, 16)
            for url in args.urls], return_exceptions=True)
        for url, raw in zip(args.urls, responses, strict=True):
            if isinstance(raw, BaseException):
                results.append({"endpoint": url, "error_type": type(raw).__name__,
                                "response_nonempty": False})
                continue
            try:
                answer = parse_completion(raw)
                results.append({"endpoint": url, "elapsed_seconds": raw.elapsed_seconds,
                                "prompt_tokens": answer.prompt_tokens,
                                "completion_tokens": answer.completion_tokens,
                                "response_sha256": sha(raw.body),
                                "response_nonempty": bool(answer.text.strip())})
            except Exception as exc:
                results.append({"endpoint": url, "elapsed_seconds": raw.elapsed_seconds,
                                "http_status": raw.status, "response_sha256": sha(raw.body),
                                "error_type": type(exc).__name__, "response_nonempty": False})
    report = {"schema": "ontology-benchmark-synthetic-probe-v1", "arm": args.arm,
              "at_utc": now(), "model": ARM_MODELS[args.arm], "source_unit_calls": 0, "engines": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    if not all(row["response_nonempty"] for row in results):
        raise ValueError("A synthetic completion was empty; setup probe did not pass")


def _ledger(path: Path, run_id: str, arm: str, rows: list[dict], prepared: list[Prepared]) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    # This one-writer experiment file sits on NFS Storage; avoid SQLite WAL.
    db.execute("PRAGMA journal_mode=DELETE")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("""CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY, arm TEXT NOT NULL, selection_sha256 TEXT NOT NULL,
        model TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS results (
        run_id TEXT NOT NULL, unit_id TEXT NOT NULL, rank INTEGER NOT NULL,
        target TEXT NOT NULL, engine_index INTEGER NOT NULL, source_sha256 TEXT NOT NULL,
        prompt_sha256 TEXT NOT NULL, input_tokens INTEGER NOT NULL,
        baseline_input_tokens INTEGER NOT NULL, kg_context_status TEXT NOT NULL,
        kg_statement_ids_json TEXT NOT NULL,
        status TEXT NOT NULL, queued_at TEXT, started_at TEXT, finished_at TEXT,
        response_bytes BLOB, response_bytes_size INTEGER, response_sha256 TEXT,
        http_status INTEGER, raw_text TEXT, raw_sha256 TEXT, validation_json TEXT,
        output_tokens INTEGER, elapsed_seconds REAL, queue_wait_seconds REAL,
        end_to_end_seconds REAL, error_type TEXT, error_detail TEXT,
        PRIMARY KEY(run_id, unit_id))""")
    if db.execute("SELECT 1 FROM runs WHERE run_id=?", (run_id,)).fetchone():
        db.close()
        raise ValueError("Run ID already exists; no automatic resume or retry")
    with db:
        db.execute("INSERT INTO runs VALUES (?,?,?,?,?,NULL)",
                   (run_id, arm, SELECTION_SHA256, ARM_MODELS[arm], now()))
        for spec, case in zip(rows, prepared, strict=True):
            db.execute("""INSERT INTO results(run_id,unit_id,rank,target,engine_index,source_sha256,
                prompt_sha256,input_tokens,baseline_input_tokens,kg_context_status,
                kg_statement_ids_json,status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, case.unit.unit_id, spec["rank"], spec["target"],
                 (spec["rank"] - 1) % ARM_ENGINES[arm], case.unit.text_sha256,
                 case.prompt_sha256, case.input_tokens, case.baseline_input_tokens,
                 case.kg_context_status, json.dumps(case.kg_statement_ids), "pending"))
    return db


def save_received_response(db: sqlite3.Connection, run_id: str, unit_id: str,
                           response, end_to_end_seconds: float):
    """Persist HTTP bytes before parsing; return None for an empty generation."""
    with db:
        db.execute("""UPDATE results SET status='raw_received',finished_at=?,response_bytes=?,
            response_bytes_size=?,response_sha256=?,http_status=?,elapsed_seconds=?,
            end_to_end_seconds=? WHERE run_id=? AND unit_id=?""",
            (now(), response.body, len(response.body), sha(response.body),
             response.status, response.elapsed_seconds, end_to_end_seconds, run_id, unit_id))
    answer = parse_completion(response)
    generated = bool(answer.text.strip())
    with db:
        db.execute("""UPDATE results SET status=?,raw_text=?,raw_sha256=?,output_tokens=?
            WHERE run_id=? AND unit_id=?""",
            ("raw_received" if generated else "zero_output", answer.text,
             sha(answer.text.encode("utf-8")), answer.completion_tokens, run_id, unit_id))
    return answer if generated else None


async def run_arm(args) -> None:
    fixed = selection(args.selection)
    rows = fixed["units"]
    prior = json.loads(args.preflight.read_text())
    if prior["selection_sha256"] != SELECTION_SHA256 or prior["unit_count"] != 100:
        raise ValueError("Preflight does not match the fixed selection")
    units = fixed_units(args.dsn, rows)
    context = kg_context(getattr(args, "kg_context", None))
    if prior.get("kg_context_sha256") != (context["context_sha256"] if context else None):
        raise ValueError("KG context differs from pinned CPU preflight")
    prepared = prepare(rows, units, mapping_ids(args.mapping_dir),
                       args.base_processor, args.fp8_processor, context,
                       prior["configured_model_len"])
    by_id = {r["unit_id"]: r for r in prior["units"]}
    if any(by_id[p.unit.unit_id]["prompt_sha256"] != p.prompt_sha256 or
           by_id[p.unit.unit_id].get("kg_statement_ids", []) != list(p.kg_statement_ids)
           for p in prepared):
        raise ValueError("Prompt differs from pinned CPU preflight")
    if max(p.input_tokens for p in prepared) + MAX_OUTPUT_TOKENS > prior["configured_model_len"]:
        raise ValueError("Configured model length would truncate a fixed prompt")
    if len(args.urls) != ARM_ENGINES[args.arm] or len(set(args.urls)) != len(args.urls):
        raise ValueError("Incorrect number of distinct localhost engines for arm")
    for url in args.urls:
        local_base(url)
    if args.request_timeout <= 0 or args.cutoff_seconds <= 0:
        raise ValueError("Timeouts must be positive")
    db = _ledger(args.sqlite, args.run_id, args.arm, rows, prepared)
    semaphores = [asyncio.Semaphore(6 // ARM_ENGINES[args.arm]) for _ in args.urls]
    started = time.perf_counter()
    timeout = aiohttp.ClientTimeout(total=args.request_timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async def one(spec: dict, case: Prepared):
            engine = (spec["rank"] - 1) % len(args.urls)
            queued_at = now()
            queued_clock = time.perf_counter()
            with db:
                db.execute("UPDATE results SET queued_at=? WHERE run_id=? AND unit_id=?",
                           (queued_at, args.run_id, case.unit.unit_id))
            async with semaphores[engine]:
                queue_wait = time.perf_counter() - queued_clock
                with db:
                    db.execute("""UPDATE results SET status='running',started_at=?,queue_wait_seconds=?
                        WHERE run_id=? AND unit_id=?""",
                        (now(), queue_wait, args.run_id, case.unit.unit_id))
                try:
                    response = await completion(session, args.urls[engine], ARM_MODELS[args.arm],
                                                case.input_ids, MAX_OUTPUT_TOKENS)
                    checked_response = save_received_response(
                        db, args.run_id, case.unit.unit_id, response,
                        time.perf_counter() - queued_clock)
                    if checked_response is None:
                        return
                    checked, notes = check_indexed_response(checked_response.text, case.unit, mapping_ids_cache)
                    validation = {"candidates": [asdict(c) for c in checked], "notes": notes}
                    with db:
                        db.execute("UPDATE results SET status='validated',validation_json=? WHERE run_id=? AND unit_id=?",
                                   (json.dumps(validation, ensure_ascii=False), args.run_id, case.unit.unit_id))
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    detail = exc.body[:2000] if isinstance(exc, CompletionHTTPError) else str(exc)[:500]
                    with db:
                        db.execute("""UPDATE results SET status='failed',finished_at=?,error_type=?,error_detail=?,
                            end_to_end_seconds=COALESCE(end_to_end_seconds,?)
                            WHERE run_id=? AND unit_id=?""",
                            (now(), type(exc).__name__, detail, time.perf_counter() - queued_clock,
                             args.run_id, case.unit.unit_id))

        mapping_ids_cache = mapping_ids(args.mapping_dir)
        tasks = [asyncio.create_task(one(spec, case)) for spec, case in zip(rows, prepared, strict=True)]
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=args.cutoff_seconds)
        except TimeoutError:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    with db:
        db.execute("UPDATE runs SET finished_at=? WHERE run_id=?", (now(), args.run_id))
    db.close()
    counts = verify_ledger(args.sqlite, args.run_id)
    report = {"run_id": args.run_id, "arm": args.arm, "selection_sha256": SELECTION_SHA256,
              "requested_units": 100, "engine_assignment": [50, 50] if args.arm == "B2" else [34, 33, 33] if args.arm == "B3" else [100],
              "wall_seconds": round(time.perf_counter() - started, 3), "status_counts": counts,
              "checked_nonempty": counts.get("validated", 0),
              "zero_output": counts.get("zero_output", 0),
              "missing_or_incomplete": 100 - counts.get("validated", 0) - counts.get("zero_output", 0) - counts.get("failed", 0)}
    print(json.dumps(report, ensure_ascii=False))


def verify_ledger(path: Path, run_id: str) -> dict[str, int]:
    """Read the committed experiment file again, including raw bytes and hashes."""
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Experiment SQLite quick_check failed")
        rows = db.execute("""SELECT status,response_bytes,response_bytes_size,response_sha256
            FROM results WHERE run_id=?""", (run_id,)).fetchall()
        if len(rows) != 100:
            raise ValueError("Experiment ledger lost a source-unit row")
        counts: dict[str, int] = {}
        for status, raw, size, digest in rows:
            counts[status] = counts.get(status, 0) + 1
            if raw is not None and (len(raw) != size or sha(raw) != digest):
                raise ValueError("Persisted HTTP response byte/hash mismatch")
            if status in {"raw_received", "validated", "zero_output"} and raw is None:
                raise ValueError("Response status has no persisted HTTP body")
        return counts


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--selection", type=Path, required=True)
    p.add_argument("--base-processor", type=Path, required=True)
    p.add_argument("--fp8-processor", type=Path, required=True)
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("preflight")
    prep.add_argument("--dsn", required=True)
    prep.add_argument("--mapping-dir", type=Path, required=True)
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--kg-context", type=Path)
    probe_cmd = sub.add_parser("probe")
    probe_cmd.add_argument("--arm", choices=ARM_ENGINES, required=True)
    probe_cmd.add_argument("--urls", nargs="+", required=True)
    probe_cmd.add_argument("--output", type=Path, required=True)
    run = sub.add_parser("run-arm")
    run.add_argument("--dsn", required=True)
    run.add_argument("--mapping-dir", type=Path, required=True)
    run.add_argument("--preflight", type=Path, required=True)
    run.add_argument("--arm", choices=ARM_ENGINES, required=True)
    run.add_argument("--urls", nargs="+", required=True)
    run.add_argument("--run-id", required=True)
    run.add_argument("--sqlite", type=Path, required=True)
    run.add_argument("--kg-context", type=Path)
    run.add_argument("--request-timeout", type=float, default=900)
    run.add_argument("--cutoff-seconds", type=float, default=7200)
    return p


if __name__ == "__main__":
    args = parser().parse_args()
    if args.command == "preflight":
        preflight(args)
    elif args.command == "probe":
        asyncio.run(probe(args))
    else:
        asyncio.run(run_arm(args))
