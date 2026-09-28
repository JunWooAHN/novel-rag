"""Fixed full-page/target ledger on top of the small PostgreSQL reality store."""

from __future__ import annotations

from pathlib import Path
from collections import Counter

from novel_factory.reality.adapters.postgres import PgRealityStore
from novel_factory.reality.application import can_schedule_attempt
from novel_factory.reality.domain import SourceUnit, digest
from novel_factory.reality.expanded import SEGMENTATION_VERSION, split_full_slot


class ExpandedRealityStore(PgRealityStore):
    def init_expanded_schema(self, base: Path, expanded: Path) -> None:
        self.init_schema(base)
        self.init_schema(expanded)

    def ingest_full_page(self, source: dict, max_bytes: int = 1800) -> dict:
        units = split_full_slot(source, max_bytes)
        segmentation_version = f"{SEGMENTATION_VERSION}:{max_bytes}"
        page_key = ":".join(str(source[k]) for k in ("wiki_id","page_id","revision_id","slot"))
        pinned = dict(source)
        pinned["units"] = [
            {"unit_id": u.unit_id, "start_byte": u.start_byte,
             "end_byte": u.end_byte, "text": u.text, "sha256": u.text_sha256}
            for u in units
        ]
        with self.connect() as conn:
            old = conn.execute("SELECT * FROM reality_full_pages WHERE page_key=%s FOR UPDATE", (page_key,)).fetchone()
            expected = (segmentation_version, source["content_sha256"], len(units))
            if old and (old["segmentation_version"],old["body_sha256"],old["unit_count"]) != expected:
                raise ValueError("Full-page segmentation changed under fixed identity")
            if not old and conn.execute("SELECT 1 FROM reality_source_pages WHERE page_key=%s", (page_key,)).fetchone():
                raise ValueError("Page already exists without full-page segmentation marker")
            result = self.ingest(pinned, conn)
            conn.execute("""INSERT INTO reality_full_pages
                (page_key,segmentation_version,body_sha256,unit_count)
                VALUES (%s,%s,%s,%s) ON CONFLICT (page_key) DO NOTHING""",
                (result["page_key"], *expected))
        return result

    def ingest_links(self, receipts: list[dict], source_root: Path,
                     expected_links: dict, ingest_failures: dict[str,str] | None = None) -> dict:
        ingest_failures = ingest_failures or {}
        seen: set[tuple[str, str, str]] = set()
        rows = []
        for item in receipts:
            identity = (item["target"], item["wiki_id"], item["requested_title"])
            if identity in seen:
                raise ValueError("Duplicate target/wiki/title receipt")
            seen.add(identity)
            status = item["status"]
            page_key = None
            ingest_status = "not_applicable"
            ingest_error_type = None
            if status == "success":
                source_file = item.get("source_file")
                if not source_file:
                    raise ValueError("Successful relation lacks a source file")
                source_path = (source_root / source_file).resolve()
                if not source_path.is_relative_to(source_root.resolve()):
                    raise ValueError("Source receipt path escapes fixture directory")
                raw = source_path.read_bytes()
                if digest(raw) != item["source_sha256"]:
                    raise ValueError("Successful source file SHA differs from receipt")
                if item.get("page_id") is None or item.get("revision_id") is None:
                    raise ValueError("Successful receipt lacks a fixed page revision")
                import json
                source = json.loads(raw)
                for field in ("wiki_id", "page_id", "revision_id"):
                    if str(source.get(field)) != str(item[field]):
                        raise ValueError("Source identity differs from successful receipt")
                if source.get("content_sha256") != item.get("content_sha256"):
                    raise ValueError("Source body SHA differs from successful receipt")
                expected_page_key = ":".join(str(source[k]) for k in ("wiki_id", "page_id", "revision_id", "slot"))
                if source_file in ingest_failures:
                    ingest_status = "failed"
                    ingest_error_type = ingest_failures[source_file]
                else:
                    ingest_status = "ingested"
                    page_key = expected_page_key
            rows.append((*identity, item.get("qid"), status, item.get("reason"),
                         item.get("source_sha256"), page_key, ingest_status, ingest_error_type))
        expected: set[tuple[str,str,str]] = set()
        for target in expected_links["targets"]:
            for wiki_id, link in target["wikipedia_sitelinks"].items():
                expected.add((target["target"],wiki_id,link["title"]))
        if seen != expected:
            raise ValueError(f"Receipt keys differ from frozen sitelinks: missing={len(expected-seen)}, extra={len(seen-expected)}")
        with self.connect() as conn:
            for target, wiki_id, title, qid, status, reason, source_sha, page_key, ingest_status, ingest_error_type in rows:
                old = conn.execute("""SELECT qid,fetch_status,fetch_reason,source_file_sha256,page_key,ingest_status,ingest_error_type
                    FROM reality_target_links WHERE target=%s AND wiki_id=%s AND requested_title=%s""",
                    (target, wiki_id, title)).fetchone()
                expected = (qid,status,reason,source_sha,page_key,ingest_status,ingest_error_type)
                if old:
                    if tuple(old.values())[:4] != expected[:4]:
                        raise ValueError("Same target relation has a different fetch receipt")
                    if tuple(old.values())[4:] == expected[4:]:
                        continue
                    if old["ingest_status"] == "failed" and ingest_status == "ingested":
                        conn.execute("""UPDATE reality_target_links SET page_key=%s,
                            ingest_status='ingested',ingest_error_type=NULL
                            WHERE target=%s AND wiki_id=%s AND requested_title=%s""",
                            (page_key,target,wiki_id,title))
                        continue
                    raise ValueError("Illegal target relation ingest-state transition")
                conn.execute("""INSERT INTO reality_target_links
                    (target,wiki_id,requested_title,qid,fetch_status,fetch_reason,source_file_sha256,page_key,ingest_status,ingest_error_type)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (target,wiki_id,title,qid,status,reason,source_sha,page_key,ingest_status,ingest_error_type))
        return {"relations": len(rows)}

    def pending_units(self, limit: int, retry_failed: bool = False) -> list[SourceUnit]:
        # Whitespace-only chunks stay in full-byte inventory but do not call the model.
        with self.connect() as conn:
            states = {row["attempt_id"]: row for row in conn.execute(
                "SELECT attempt_id,status,raw_response IS NOT NULL AS has_raw FROM reality_extract_attempts")}
        pending = []
        for unit in self.units():
            if not unit.text.strip():
                continue
            state = states.get(self.attempt_id(unit))
            if can_schedule_attempt(state["status"] if state else None,
                                    state["has_raw"] if state else False, retry_failed):
                pending.append(unit)
                if len(pending) >= limit:
                    break
        return pending

    def expanded_summary(self) -> dict:
        base = self.summary()
        with self.connect() as conn:
            receipts = [dict(row) for row in conn.execute("""SELECT fetch_status,count(*) AS n
                FROM reality_target_links GROUP BY fetch_status ORDER BY fetch_status""")]
            receipt_ingest = [dict(row) for row in conn.execute("""SELECT ingest_status,count(*) AS n
                FROM reality_target_links GROUP BY ingest_status ORDER BY ingest_status""")]
            full_pages = conn.execute("SELECT count(*) AS n FROM reality_full_pages").fetchone()["n"]
            vectors = conn.execute("SELECT count(*) AS n FROM reality_span_embeddings").fetchone()["n"]
            embed_failures = conn.execute("SELECT count(*) AS n FROM reality_embed_failures").fetchone()["n"]
            attempt_rows = {row["attempt_id"]: row for row in conn.execute(
                "SELECT attempt_id,status,unmapped_notes FROM reality_extract_attempts")}
            candidate_counts = {row["attempt_id"]: row["n"] for row in conn.execute(
                "SELECT attempt_id,count(*) AS n FROM reality_candidates GROUP BY attempt_id")}
        outcomes = Counter()
        for unit in self.units():
            if not unit.text.strip():
                outcomes["skipped_whitespace"] += 1
                continue
            row = attempt_rows.get(self.attempt_id(unit))
            if row is None:
                outcomes["pending"] += 1
            elif row["status"] != "completed":
                outcomes[row["status"]] += 1
            elif "LANGUAGE_UNSUPPORTED" in row["unmapped_notes"]:
                outcomes["unsupported_deferred"] += 1
            elif "LANGUAGE_UNCERTAIN" in row["unmapped_notes"]:
                outcomes["language_uncertain_deferred"] += 1
            elif candidate_counts.get(row["attempt_id"], 0) == 0:
                outcomes["no_candidate"] += 1
            else:
                outcomes["candidate_generated"] += 1
        return {**base,"target_receipts":receipts,"receipt_ingest":receipt_ingest,"full_pages":full_pages,
                "blank_units_not_model_input":outcomes["skipped_whitespace"],"span_embeddings":vectors,
                "embedding_failures":embed_failures,
                "unit_outcomes":[{"outcome":k,"n":v} for k,v in sorted(outcomes.items())]}

    def embedding_failure_units(self, model: str, revision: str) -> set[str]:
        with self.connect() as conn:
            return {row["unit_id"] for row in conn.execute("""SELECT unit_id FROM reality_embed_failures
                WHERE model=%s AND model_revision=%s""", (model,revision))}

    def record_embedding_failure(self, unit: SourceUnit, model: str,
                                 revision: str, error_type: str) -> None:
        with self.connect() as conn:
            conn.execute("""INSERT INTO reality_embed_failures (unit_id,model,model_revision,error_type)
                VALUES (%s,%s,%s,%s) ON CONFLICT (unit_id,model,model_revision)
                DO UPDATE SET error_type=EXCLUDED.error_type""",
                (unit.unit_id,model,revision,error_type))

    def clear_embedding_failure(self, unit: SourceUnit, model: str, revision: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM reality_embed_failures WHERE unit_id=%s AND model=%s AND model_revision=%s",
                         (unit.unit_id,model,revision))

    def has_span_embedding(self, unit_id: str, start: int, end: int,
                           model: str, revision: str, text_sha: str) -> bool:
        with self.connect() as conn:
            return conn.execute("""SELECT 1 FROM reality_span_embeddings WHERE
                unit_id=%s AND start_byte=%s AND end_byte=%s AND model=%s
                AND model_revision=%s AND input_sha256=%s""",
                (unit_id,start,end,model,revision,text_sha)).fetchone() is not None

    def eligible_evidence_spans(self) -> list[tuple[SourceUnit,int,int,str]]:
        """Only pre-1950 unreviewed candidate evidence enters the active vector index."""
        by_id = {unit.unit_id:unit for unit in self.units()}
        with self.connect() as conn:
            rows = conn.execute("""SELECT DISTINCT unit_id,evidence_start_byte,evidence_end_byte,
                evidence_quote FROM reality_candidates WHERE status='candidate_unreviewed'
                AND payload->>'temporal_scope'='pre_1950'
                AND evidence_start_byte IS NOT NULL AND evidence_end_byte IS NOT NULL
                ORDER BY unit_id,evidence_start_byte,evidence_end_byte,evidence_quote""").fetchall()
        result=[]
        for row in rows:
            unit=by_id[row["unit_id"]]
            start,end=row["evidence_start_byte"],row["evidence_end_byte"]
            quote=row["evidence_quote"]
            if (not isinstance(quote,str) or not unit.start_byte <= start < end <= unit.end_byte
                or unit.text.encode("utf-8")[start-unit.start_byte:end-unit.start_byte] != quote.encode("utf-8")):
                raise ValueError("Candidate evidence is not a fixed source span")
            result.append((unit,start,end,quote))
        return result

    def save_span_embedding(self, unit: SourceUnit, start: int, end: int,
                            text: str, model: str, revision: str, values: list[float]) -> None:
        if len(values) != 384 or not (unit.start_byte <= start < end <= unit.end_byte):
            raise ValueError("Invalid embedding dimension or source span")
        raw = unit.text.encode("utf-8")
        if raw[start-unit.start_byte:end-unit.start_byte] != text.encode("utf-8"):
            raise ValueError("Embedding text differs from fixed source bytes")
        literal = "[" + ",".join(format(v,".9g") for v in values) + "]"
        with self.connect() as conn:
            conn.execute("""INSERT INTO reality_span_embeddings
                (unit_id,start_byte,end_byte,model,model_revision,dimension,input_sha256,vector)
                VALUES (%s,%s,%s,%s,%s,384,%s,%s::vector) ON CONFLICT DO NOTHING""",
                (unit.unit_id,start,end,model,revision,digest(text.encode("utf-8")),literal))

    def search_spans(self, vector: list[float], model: str, revision: str,
                     limit: int) -> list[dict]:
        if len(vector) != 384:
            raise ValueError("Query embedding has wrong dimension")
        literal = "[" + ",".join(format(v,".9g") for v in vector) + "]"
        with self.connect() as conn:
            rows = conn.execute("""SELECT e.unit_id,e.start_byte,e.end_byte,
                e.input_sha256,p.wiki_id,p.page_id,p.revision_id,p.slot,p.language,
                p.title,p.source_url,e.vector <=> %s::vector AS distance,
                ARRAY(SELECT c.candidate_id FROM reality_candidates c
                      WHERE c.unit_id=e.unit_id AND c.evidence_start_byte=e.start_byte
                      AND c.evidence_end_byte=e.end_byte AND c.status='candidate_unreviewed'
                      AND c.payload->>'temporal_scope'='pre_1950'
                      ORDER BY c.candidate_id) AS source_claim_ids
                FROM reality_span_embeddings e JOIN reality_source_units u ON u.unit_id=e.unit_id
                JOIN reality_source_pages p ON p.page_key=u.page_key
                WHERE e.model=%s AND e.model_revision=%s
                ORDER BY distance,e.unit_id,e.start_byte LIMIT %s""",
                (literal,model,revision,limit)).fetchall()
            results=[]
            for row in rows:
                start,end=row["start_byte"],row["end_byte"]
                source = conn.execute("SELECT body FROM reality_source_pages WHERE wiki_id=%s AND page_id=%s AND revision_id=%s AND slot=%s",
                                      (row["wiki_id"],row["page_id"],row["revision_id"],row["slot"])).fetchone()
                snippet=source["body"].encode("utf-8")[start:end].decode("utf-8")
                if digest(snippet.encode("utf-8")) != row["input_sha256"]:
                    raise ValueError("Search hit span SHA differs from pinned source")
                result=dict(row)
                result["source_excerpt"] = snippet[:300]
                result["excerpt_truncated"] = len(snippet) > 300
                result["evidence_status"] = "unit_span_retrieved_not_query_specific_candidate"
                results.append(result)
        return results

    def verify_full_coverage(self) -> dict:
        problems = []
        with self.connect() as conn:
            pages = conn.execute("""SELECT f.page_key,f.segmentation_version,f.body_sha256,
                f.unit_count,p.body,p.body_sha256 AS source_sha
                FROM reality_full_pages f JOIN reality_source_pages p USING(page_key)""").fetchall()
            for page in pages:
                units = conn.execute("""SELECT start_byte,end_byte,text,text_sha256 FROM reality_source_units
                    WHERE page_key=%s ORDER BY start_byte""", (page["page_key"],)).fetchall()
                raw = page["body"].encode("utf-8")
                at = 0
                for unit in units:
                    if unit["start_byte"] != at or unit["end_byte"] > len(raw):
                        problems.append("coverage_gap_or_overlap:" + page["page_key"])
                        break
                    content = raw[at:unit["end_byte"]]
                    if content != unit["text"].encode("utf-8") or digest(content) != unit["text_sha256"]:
                        problems.append("coverage_bytes:" + page["page_key"])
                        break
                    at = unit["end_byte"]
                if (at != len(raw) or len(units) != page["unit_count"]
                    or digest(raw) != page["body_sha256"] or page["source_sha"] != page["body_sha256"]
                    or not page["segmentation_version"].startswith(SEGMENTATION_VERSION + ":")):
                    problems.append("coverage_incomplete:" + page["page_key"])
            missing = conn.execute("""SELECT count(*) AS n FROM reality_target_links l
                WHERE l.ingest_status='ingested' AND NOT EXISTS
                (SELECT 1 FROM reality_full_pages f WHERE f.page_key=l.page_key)""").fetchone()["n"]
        if missing:
            problems.append(f"fetched_relations_without_full_page:{missing}")
        with self.connect() as conn:
            vector_rows=conn.execute("""SELECT e.unit_id,e.start_byte,e.end_byte,e.input_sha256,
                p.body FROM reality_span_embeddings e
                JOIN reality_source_units u ON u.unit_id=e.unit_id
                JOIN reality_source_pages p ON p.page_key=u.page_key""").fetchall()
            for row in vector_rows:
                data=row["body"].encode("utf-8")[row["start_byte"]:row["end_byte"]]
                if digest(data) != row["input_sha256"]:
                    problems.append("embedding_source_span:"+row["unit_id"])
            inactive=conn.execute("""SELECT count(*) AS n FROM reality_span_embeddings e
                WHERE NOT EXISTS (SELECT 1 FROM reality_candidates c
                    WHERE c.unit_id=e.unit_id AND c.evidence_start_byte<=e.start_byte
                    AND c.evidence_end_byte>=e.end_byte AND c.status='candidate_unreviewed'
                    AND c.payload->>'temporal_scope'='pre_1950')""").fetchone()["n"]
            if inactive:
                problems.append(f"indexed_without_pre1950_candidate:{inactive}")
        return {"full_pages":len(pages),"problems":problems}
