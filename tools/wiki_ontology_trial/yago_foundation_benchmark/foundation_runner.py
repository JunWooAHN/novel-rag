"""Fixed-100 residual prompt on top of an already loaded YAGO foundation.

This isolated trial composes the existing fixed source check, vLLM request loop,
raw response ledger, and indexed wiki-span validator. It changes the prompt,
not the old baseline/context experiment files.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sqlite3

import benchmark_100 as fixed
from novel_factory.reality.application import _decode
from novel_factory.reality.expanded import evidence_spans


KG_LEDGER_SHA = "b8984492124dcb8d767fd7f58d0cc4e8125064017019854bc51b2d204be26349"
POLICY_SHA = "17c06d60d3948b06b012c112d210f5d2b3f892d2b09455cc37260e95688e0b07"
FOUNDATION_INSTRUCTION = (
    'FOUNDATION_MODE: Listed KG rows are external claims. Output residual wiki-supported H/K/B only. '
    'Exact same subject/relation/object/role/time: omit candidate and report '
    'foundation_links [{statement_id,evidence_span_id,source_claim,relation:"same",candidate_ordinal:null}]. '
    'Difference: keep candidate and link extends/conflicts to its ordinal. '
    'Unknown identity/time: keep both. Always include foundation_links array (empty if none). '
    'At most 10 links; unlisted KG cannot cover source.'
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_foundation(path: Path, expected_sha: str) -> set[str]:
    if sha(path) != expected_sha:
        raise ValueError("Foundation SQLite SHA differs")
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Foundation SQLite quick_check failed")
        pins = dict(db.execute("SELECT key,value FROM input_pin"))
        if (pins.get("kg_ledger_sha256") != KG_LEDGER_SHA
                or pins.get("mapping_policy_sha256") != POLICY_SHA
                or pins.get("yago_manifest_sha256") != fixed.YAGO_MANIFEST_SHA256):
            raise ValueError("Foundation source/mapping pins differ")
        if db.execute("SELECT count(*) FROM source_statement").fetchone()[0] != 152:
            raise ValueError("Foundation source statement count differs")
        if db.execute("SELECT count(*) FROM source_meta").fetchone()[0] != 40:
            raise ValueError("Foundation Meta accounting differs")
        rows = db.execute("""SELECT s.statement_id FROM source_statement s
            JOIN structural_assertion a USING(statement_id) WHERE s.prompt_eligible=1""").fetchall()
        if len(rows) != 44:
            raise ValueError("Foundation prompt-eligible assertion count differs")
    return {row[0] for row in rows}


def make_prepare(eligible_assertions: set[str], preflight_rows: dict | None,
                 render_receipt: dict[str, dict]):
    def prepare(rows, units, mapping_ids, base_processor, fp8_processor,
                context=None, model_len=14592):
        from transformers import AutoProcessor

        if context is None or context["context_sha256"] != KG_LEDGER_SHA:
            raise ValueError("Residual trial requires the fixed KG ledger")
        base = AutoProcessor.from_pretrained(str(base_processor), local_files_only=True)
        quant = AutoProcessor.from_pretrained(str(fp8_processor), local_files_only=True)
        output = []
        for spec, unit in zip(rows, units, strict=True):
            source = fixed.make_indexed_prompt(unit, mapping_ids)
            marker = "\nSOURCE_SPANS:\n"
            if source.count(marker) != 1:
                raise ValueError("Indexed prompt source marker differs")
            original_ids = fixed._token_ids(base, source)
            if original_ids != fixed._token_ids(quant, source):
                raise ValueError("Original BF16/FP8 token IDs differ")
            # The brief residual contract is retained even when no KG row fits.
            prefix, spans = source.split(marker, 1)
            source_plus_contract = (prefix + "\n" + FOUNDATION_INSTRUCTION
                                    + "\nFOUNDATION_ROWS:\n" + marker + spans)
            residual_mode = (len(fixed._token_ids(base, source_plus_contract))
                             + fixed.MAX_OUTPUT_TOKENS <= model_len)
            target = context["targets"][spec["target"]]
            by_id = {s["statement_id"]: s for s in target["statements"]}
            selected = []
            prompt = source_plus_contract if residual_mode else source
            for sid in target["eligible_statement_ids"] if residual_mode else []:
                if sid not in eligible_assertions or sid not in by_id:
                    raise ValueError(f"Eligible ID absent from loaded foundation: {sid}")
                statement = by_id[sid]
                line = statement["prompt_text"]
                if not isinstance(line, str) or not line:
                    raise ValueError(f"Incomplete displayed foundation row: {sid}")
                proposed = selected + [statement]
                rendered = "\n".join(s["prompt_text"] for s in proposed)
                proposal = (prefix + "\n" + FOUNDATION_INSTRUCTION
                            + "\nFOUNDATION_ROWS:\n" + rendered + marker + spans)
                if len(fixed._token_ids(base, proposal)) + fixed.MAX_OUTPUT_TOKENS <= model_len:
                    selected = proposed
                    prompt = proposal
            status = (target["mapping_status"] if selected else "budget_omitted"
                      if target["eligible_statement_ids"] else "no_direct_fact")
            conversation = [{"role": "user", "content": prompt}]
            text = base.apply_chat_template(conversation, tokenize=False,
                                            add_generation_prompt=True, enable_thinking=False)
            quant_text = quant.apply_chat_template(conversation, tokenize=False,
                                                   add_generation_prompt=True, enable_thinking=False)
            token_ids = fixed._token_ids(base, prompt)
            if (text != quant_text or token_ids != fixed._token_ids(quant, prompt)
                    or len(token_ids) + fixed.MAX_OUTPUT_TOKENS > model_len):
                raise ValueError(f"Final BF16/FP8 prompt differs or truncates: {unit.unit_id}")
            selected_ids = tuple(s["statement_id"] for s in selected)
            rendered_bytes = "\n".join(s["prompt_text"] for s in selected).encode("utf-8")
            render_sha = hashlib.sha256(rendered_bytes).hexdigest()
            render_receipt[unit.unit_id] = {
                "foundation_render_sha256": render_sha,
                "displayed_statement_ids": list(selected_ids),
                "foundation_context_status": status,
                "residual_mode": residual_mode,
                "budget_omitted_reason": ("instruction_and_rows_exceed_context"
                                          if not residual_mode else
                                          "whole_rows_exceed_context" if not selected and target["eligible_statement_ids"]
                                          else None),
                "source_span_ids": [s.span_id for s in evidence_spans(unit)],
            }
            if preflight_rows is not None:
                prior = preflight_rows[unit.unit_id]
                if (prior["foundation_render_sha256"] != render_sha
                        or prior["displayed_statement_ids"] != list(selected_ids)
                        or prior["foundation_context_status"] != status
                        or prior["residual_mode"] != residual_mode
                        or prior["budget_omitted_reason"] != render_receipt[unit.unit_id]["budget_omitted_reason"]
                        or prior["source_span_ids"] != render_receipt[unit.unit_id]["source_span_ids"]):
                    raise ValueError(f"Displayed foundation differs from CPU preflight: {unit.unit_id}")
            output.append(fixed.Prepared(unit, spec["target"], text,
                                         hashlib.sha256(text.encode("utf-8")).hexdigest(),
                                         len(token_ids), token_ids, len(original_ids),
                                         selected_ids, status))
        return output

    return prepare


def audit_links(results_path: Path, run_id: str, preflight_path: Path) -> dict:
    """Persist every link proposal and invalid/missing-link decision beside raw results."""
    preflight = json.loads(preflight_path.read_text())
    specs = {row["unit_id"]: row for row in preflight["units"]}
    if len(specs) != 100:
        raise ValueError("Link audit has no fixed 100-unit preflight")
    counts = {"units": 0, "valid_links": 0, "invalid_links": 0,
              "same_proposals_needing_review": 0, "missing_link_fields": 0,
              "not_exposed_units": 0, "overflow_units": 0, "parse_error_units": 0}
    with sqlite3.connect(results_path) as db:
        db.row_factory = sqlite3.Row
        db.execute("""CREATE TABLE IF NOT EXISTS foundation_link_audit (
            run_id TEXT NOT NULL, unit_id TEXT NOT NULL, rank INTEGER NOT NULL,
            result_status TEXT NOT NULL, field_status TEXT NOT NULL,
            displayed_statement_ids_json TEXT NOT NULL, source_span_ids_json TEXT NOT NULL,
            valid_link_count INTEGER NOT NULL, invalid_link_count INTEGER NOT NULL,
            PRIMARY KEY (run_id, unit_id))""")
        db.execute("""CREATE TABLE IF NOT EXISTS foundation_link_proposal (
            run_id TEXT NOT NULL, unit_id TEXT NOT NULL, link_index INTEGER NOT NULL,
            statement_id TEXT, evidence_span_id TEXT, source_claim TEXT,
            relation TEXT, candidate_ordinal INTEGER, reason TEXT,
            status TEXT NOT NULL, problems_json TEXT NOT NULL, raw_json TEXT NOT NULL,
            PRIMARY KEY (run_id, unit_id, link_index))""")
        if db.execute("SELECT 1 FROM foundation_link_audit WHERE run_id=? LIMIT 1", (run_id,)).fetchone():
            raise ValueError("Link audit already exists for run; never overwrite")
        rows = db.execute("""SELECT unit_id,rank,status,raw_text,prompt_sha256,validation_json
            FROM results WHERE run_id=? ORDER BY rank""", (run_id,)).fetchall()
        if len(rows) != 100:
            raise ValueError("Link audit run has fewer than 100 rows")
        for row in rows:
            unit_id = row["unit_id"]
            spec = specs[unit_id]
            if row["prompt_sha256"] != spec["prompt_sha256"]:
                raise ValueError(f"Link audit prompt differs: {unit_id}")
            displayed = set(spec["displayed_statement_ids"])
            spans = set(spec["source_span_ids"])
            links, field_status, candidates = [], "ok", []
            if row["raw_text"] is None:
                field_status = "no_raw_text"
            else:
                try:
                    parsed = _decode(row["raw_text"])
                    candidates = parsed.get("candidates")
                    if not isinstance(candidates, list) or len(candidates) > 10:
                        candidates = []
                    field = parsed.get("foundation_links", None)
                    if field is None:
                        if not spec["residual_mode"]:
                            field_status = "not_exposed_budget_omitted"
                            counts["not_exposed_units"] += 1
                        else:
                            field_status = "missing_field"
                            counts["missing_link_fields"] += 1
                    elif not isinstance(field, list):
                        field_status = "invalid_field_type"
                    else:
                        links = field
                        if len(links) > 10:
                            field_status = "overflow"
                            counts["overflow_units"] += 1
                except (ValueError, TypeError):
                    field_status = "parse_error"
                    counts["parse_error_units"] += 1
            seen = set()
            valid = invalid = 0
            for index, link in enumerate(links):
                problems = []
                if field_status != "ok":
                    problems.append("link_field_" + field_status)
                if not isinstance(link, dict):
                    problems.append("link_not_object")
                    link = {}
                sid = link.get("statement_id")
                span = link.get("evidence_span_id")
                claim = link.get("source_claim")
                relation = link.get("relation")
                ordinal = link.get("candidate_ordinal")
                if not isinstance(sid, str) or sid not in displayed:
                    problems.append("statement_not_displayed")
                if not isinstance(span, str) or span not in spans:
                    problems.append("span_not_in_source")
                if not isinstance(claim, str) or not claim.strip() or len(claim) > 500:
                    problems.append("claim_missing_or_oversized")
                if not isinstance(relation, str) or relation not in {"same", "extends", "conflicts"}:
                    problems.append("unknown_relation")
                if relation == "same" and ordinal is not None:
                    problems.append("same_must_not_point_to_residual")
                if isinstance(relation, str) and relation in {"extends", "conflicts"}:
                    if (not isinstance(ordinal, int) or isinstance(ordinal, bool)
                            or ordinal < 0 or ordinal >= len(candidates)):
                        problems.append("residual_ordinal_missing_or_invalid")
                    elif not isinstance(candidates[ordinal], dict) or candidates[ordinal].get("evidence_span_id") != span:
                        problems.append("residual_span_differs")
                key = (sid if isinstance(sid, str) else None,
                       span if isinstance(span, str) else None,
                       claim.strip() if isinstance(claim, str) else None,
                       relation if isinstance(relation, str) else None,
                       ordinal if isinstance(ordinal, int) and not isinstance(ordinal, bool) else None)
                if key in seen:
                    problems.append("duplicate_link")
                seen.add(key)
                if row["status"] != "validated":
                    problems.append("source_result_not_validated")
                status = "valid_proposal_needs_review" if not problems else "invalid_hold"
                valid += not problems
                invalid += bool(problems)
                counts["same_proposals_needing_review"] += not problems and relation == "same"
                db.execute("INSERT INTO foundation_link_proposal VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                           (run_id, unit_id, index, sid if isinstance(sid, str) else None,
                            span if isinstance(span, str) else None,
                            claim if isinstance(claim, str) else None,
                            relation if isinstance(relation, str) else None,
                            ordinal if isinstance(ordinal, int) and not isinstance(ordinal, bool) else None,
                            link.get("reason") if isinstance(link.get("reason"), str) else None,
                            status, json.dumps(problems), json.dumps(link, ensure_ascii=False)))
            db.execute("INSERT INTO foundation_link_audit VALUES (?,?,?,?,?,?,?,?,?)",
                       (run_id, unit_id, row["rank"], row["status"], field_status,
                        json.dumps(spec["displayed_statement_ids"]), json.dumps(spec["source_span_ids"]),
                        valid, invalid))
            counts["units"] += 1
            counts["valid_links"] += valid
            counts["invalid_links"] += invalid
        db.commit()
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Link-audited results SQLite quick_check failed")
    if counts["units"] != 100:
        raise ValueError("Link audit unit accounting differs")
    return counts


def main() -> None:
    parser = fixed.parser()
    parser.add_argument("--foundation-sqlite", type=Path, required=True)
    parser.add_argument("--foundation-sha256", required=True)
    parser.add_argument("--mapping-policy", type=Path, required=True)
    args = parser.parse_args()
    if sha(args.mapping_policy) != POLICY_SHA:
        raise ValueError("Fixed mapping policy SHA differs")
    if args.command not in {"preflight", "run-arm"}:
        raise ValueError("Residual trial supports preflight/run-arm only")
    if sha(args.kg_context) != KG_LEDGER_SHA:
        raise ValueError("Fixed KG ledger SHA differs")
    eligible = load_foundation(args.foundation_sqlite, args.foundation_sha256)
    prior = None
    if args.command == "run-arm":
        report = json.loads(args.preflight.read_text())
        if (report.get("foundation_sqlite_sha256") != args.foundation_sha256
                or report.get("mapping_policy_sha256") != POLICY_SHA
                or report.get("instruction_sha256") != hashlib.sha256(
                    FOUNDATION_INSTRUCTION.encode("utf-8")).hexdigest()):
            raise ValueError("Residual preflight source/contract pins differ")
        prior = {row["unit_id"]: row for row in report["units"]}
        if len(prior) != 100:
            raise ValueError("Residual preflight missing fixed units")
    render_receipt = {}
    fixed.prepare = make_prepare(eligible, prior, render_receipt)
    if args.command == "preflight":
        fixed.preflight(args)
        report = json.loads(args.output.read_text())
        report["foundation_sqlite_sha256"] = args.foundation_sha256
        report["mapping_policy_sha256"] = POLICY_SHA
        report["instruction_sha256"] = hashlib.sha256(FOUNDATION_INSTRUCTION.encode("utf-8")).hexdigest()
        for row in report["units"]:
            row.update(render_receipt[row["unit_id"]])
        if len(render_receipt) != 100 or report["configured_model_len"] != 14592:
            raise ValueError("Residual CPU preflight incomplete or model length differs")
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    else:
        asyncio.run(fixed.run_arm(args))
        if len(render_receipt) != 100:
            raise ValueError("Residual run prepared fewer than 100 units")
        print(json.dumps({"run_id": args.run_id, "foundation_link_audit":
                          audit_links(args.sqlite, args.run_id, args.preflight)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
