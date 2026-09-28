"""PostgreSQL source/candidate/vector adapter for the bounded trial."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Callable

import psycopg
from psycopg.rows import dict_row

from novel_factory.reality.application import CheckedCandidate, can_schedule_attempt, prompt_sha
from novel_factory.reality.domain import SourceUnit, digest


def key(*parts: object) -> str:
    return sha256("\x1f".join(str(p) for p in parts).encode("utf-8")).hexdigest()


def _as_unit(row: dict) -> SourceUnit:
    return SourceUnit(
        unit_id=row["unit_id"], wiki_id=row["wiki_id"], page_id=row["page_id"],
        revision_id=row["revision_id"], slot=row["slot"], language=row["language"],
        title=row["title"], start_byte=row["start_byte"], end_byte=row["end_byte"],
        text=row["text"], text_sha256=row["text_sha256"],
    )


class PgRealityStore:
    def __init__(self, dsn: str, extract_model: str, extract_revision: str,
                 prompt_digest: Callable[[SourceUnit], str] = prompt_sha):
        self.dsn = dsn
        self.extract_model = extract_model
        self.extract_revision = extract_revision
        self.prompt_digest = prompt_digest

    def connect(self):
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def init_schema(self, schema_path: Path) -> None:
        with self.connect() as conn:
            conn.execute(schema_path.read_text(encoding="utf-8"))

    def ingest(self, source: dict, conn=None) -> dict:
        if conn is None:
            with self.connect() as opened:
                return self.ingest(source, opened)
        required = ("wiki_id", "page_id", "revision_id", "slot", "language", "title", "wikitext", "content_sha256", "units")
        if any(k not in source for k in required):
            raise ValueError("Source file is missing pinned identity/body/units")
        body = source["wikitext"]
        raw = body.encode("utf-8")
        if digest(raw) != source["content_sha256"]:
            raise ValueError("Full slot body hash mismatch")
        page_key = ":".join(str(source[k]) for k in ("wiki_id", "page_id", "revision_id", "slot"))
        units: list[SourceUnit] = []
        for item in source["units"]:
            unit = SourceUnit(
                unit_id=item["unit_id"], wiki_id=source["wiki_id"],
                page_id=int(source["page_id"]), revision_id=int(source["revision_id"]),
                slot=source["slot"], language=source["language"], title=source["title"],
                start_byte=int(item["start_byte"]), end_byte=int(item["end_byte"]),
                text=item["text"], text_sha256=item["sha256"],
            )
            unit.validate()
            if raw[unit.start_byte:unit.end_byte] != unit.text.encode("utf-8"):
                raise ValueError("Unit byte span does not match pinned full slot")
            units.append(unit)
        existing = conn.execute("SELECT body_sha256, body FROM reality_source_pages WHERE page_key=%s", (page_key,)).fetchone()
        if existing and (existing["body_sha256"] != source["content_sha256"] or existing["body"] != body):
            raise ValueError("Same source identity has different body")
        conn.execute("""INSERT INTO reality_source_pages
            (page_key,wiki_id,page_id,revision_id,slot,language,title,source_kind,snapshot_id,
             revision_timestamp,source_url,retrieved_at,body,body_sha256)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (page_key) DO NOTHING""",
            (page_key,source["wiki_id"],int(source["page_id"]),int(source["revision_id"]),
             source["slot"],source["language"],source["title"],source.get("source_kind","unspecified"),
             source.get("snapshot_id"),source.get("revision_timestamp"),source.get("source_url"),
             source.get("retrieved_at"),body,source["content_sha256"]))
        for unit in units:
            old = conn.execute("SELECT page_key,start_byte,end_byte,text_sha256,text FROM reality_source_units WHERE unit_id=%s", (unit.unit_id,)).fetchone()
            if old and (old["page_key"],old["start_byte"],old["end_byte"],old["text_sha256"],old["text"]) != (page_key,unit.start_byte,unit.end_byte,unit.text_sha256,unit.text):
                raise ValueError("Same unit ID has different source span")
            conn.execute("""INSERT INTO reality_source_units
                (unit_id,page_key,start_byte,end_byte,text,text_sha256) VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (unit_id) DO NOTHING""",
                (unit.unit_id,page_key,unit.start_byte,unit.end_byte,unit.text,unit.text_sha256))
        return {"page_key": page_key, "units": len(units), "body_sha256": source["content_sha256"]}

    def units(self) -> list[SourceUnit]:
        with self.connect() as conn:
            rows = conn.execute("""SELECT u.*,p.wiki_id,p.page_id,p.revision_id,p.slot,p.language,p.title
                FROM reality_source_units u JOIN reality_source_pages p ON p.page_key=u.page_key
                ORDER BY p.wiki_id,p.page_id,u.start_byte""").fetchall()
        return [_as_unit(row) for row in rows]

    def pending_units(self, limit: int, retry_failed: bool = False) -> list[SourceUnit]:
        pending = []
        for unit in self.units():
            state = self.attempt_record(unit)
            if can_schedule_attempt(state["status"] if state else None,
                                    state["raw_response"] is not None if state else False,
                                    retry_failed):
                pending.append(unit)
            if len(pending) >= limit:
                break
        return pending

    def attempt_id(self, unit: SourceUnit) -> str:
        return key("extract-v1",unit.unit_id,unit.text_sha256,self.extract_model,self.extract_revision,self.prompt_digest(unit))

    def attempt_record(self, unit: SourceUnit) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT status,raw_response FROM reality_extract_attempts WHERE attempt_id=%s", (self.attempt_id(unit),)).fetchone()
        return dict(row) if row else None

    def begin_attempt(self, unit: SourceUnit, retry_failed: bool) -> str:
        attempt_id = self.attempt_id(unit)
        with self.connect() as conn:
            row = conn.execute("SELECT status,raw_response FROM reality_extract_attempts WHERE attempt_id=%s FOR UPDATE", (attempt_id,)).fetchone()
            if row:
                if row["status"] == "completed" or not retry_failed or row["raw_response"] is not None:
                    raise ValueError("Attempt already exists; completed inputs are never rerun")
                conn.execute("UPDATE reality_extract_attempts SET status='running',error=NULL WHERE attempt_id=%s", (attempt_id,))
            else:
                conn.execute("""INSERT INTO reality_extract_attempts
                    (attempt_id,unit_id,model,model_revision,prompt_sha256,status)
                    VALUES (%s,%s,%s,%s,%s,'running')""",
                    (attempt_id,unit.unit_id,self.extract_model,self.extract_revision,self.prompt_digest(unit)))
        return attempt_id

    def fail_attempt(self, attempt_id: str, error: str, raw: str | None = None) -> None:
        with self.connect() as conn:
            conn.execute("""UPDATE reality_extract_attempts SET status='failed',error=%s,
                raw_response=%s,raw_sha256=%s,finished_at=now() WHERE attempt_id=%s AND status='running'""",
                (error[:1000],raw,digest(raw.encode("utf-8")) if raw is not None else None,attempt_id))

    def complete_attempt(self, unit: SourceUnit, raw: str, candidates: list[CheckedCandidate], notes: list[str]) -> dict:
        attempt_id = self.attempt_id(unit)
        with self.connect() as conn:
            row = conn.execute("SELECT status FROM reality_extract_attempts WHERE attempt_id=%s FOR UPDATE", (attempt_id,)).fetchone()
            if not row or row["status"] != "running":
                raise ValueError("Attempt is not running")
            for checked in candidates:
                item = checked.payload
                related = item.get("related_candidate_index")
                related_id = key(attempt_id,related) if (checked.status == "candidate_unreviewed"
                    and isinstance(related,int) and not isinstance(related,bool) and 0 <= related < len(candidates)
                    and candidates[related].status == "candidate_unreviewed") else None
                conn.execute("""INSERT INTO reality_candidates
                    (candidate_id,attempt_id,unit_id,ordinal,layer,mapping_refs,subject_text,predicate_text,
                     object_text,time_text,uncertainty,related_candidate_id,evidence_quote,
                     evidence_start_byte,evidence_end_byte,status,problems,payload)
                    VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)""",
                    (key(attempt_id,checked.ordinal),attempt_id,unit.unit_id,checked.ordinal,str(item.get("layer")),
                     json.dumps(item.get("mapping_refs")),item.get("subject"),item.get("predicate"),
                     item.get("object"),item.get("time_text"),item.get("uncertainty"),related_id,
                     item.get("evidence_quote"),checked.evidence_start_byte,checked.evidence_end_byte,
                     checked.status,json.dumps(checked.problems),json.dumps(item,ensure_ascii=False)))
            conn.execute("""UPDATE reality_extract_attempts SET status='completed',raw_response=%s,
                raw_sha256=%s,unmapped_notes=%s::jsonb,finished_at=now() WHERE attempt_id=%s""",
                (raw,digest(raw.encode("utf-8")),json.dumps(notes,ensure_ascii=False),attempt_id))
        return {"attempt_id":attempt_id,"candidates":len(candidates),
                "held":sum(c.status=="held" for c in candidates)}

    def has_embedding(self, unit: SourceUnit, model: str, revision: str) -> bool:
        with self.connect() as conn:
            row=conn.execute("""SELECT 1 FROM reality_embeddings WHERE target_kind='source_unit'
                AND target_id=%s AND model=%s AND model_revision=%s AND input_sha256=%s""",
                (unit.unit_id,model,revision,unit.text_sha256)).fetchone()
        return row is not None

    def save_embedding(self, unit: SourceUnit, model: str, revision: str, values: list[float]) -> None:
        if len(values) != 384:
            raise ValueError("Embedding has wrong dimension")
        vector = "[" + ",".join(format(v,".9g") for v in values) + "]"
        with self.connect() as conn:
            conn.execute("""INSERT INTO reality_embeddings
                (target_kind,target_id,model,model_revision,dimension,input_sha256,vector)
                VALUES ('source_unit',%s,%s,%s,384,%s,%s::vector)
                ON CONFLICT DO NOTHING""",
                (unit.unit_id,model,revision,unit.text_sha256,vector))

    def search(self, vector: list[float], model: str, revision: str, limit: int) -> list[dict]:
        literal = "[" + ",".join(format(v,".9g") for v in vector) + "]"
        with self.connect() as conn:
            rows=conn.execute("""SELECT u.unit_id,p.wiki_id,p.page_id,p.slot,p.language,p.title,
                p.source_kind,p.snapshot_id,p.source_url,p.revision_id,
                u.start_byte,u.end_byte,u.text_sha256,e.vector <=> %s::vector AS distance,
                (SELECT count(*) FROM reality_candidates c WHERE c.unit_id=u.unit_id) AS candidate_count,
                ev.evidence_quote,ev.evidence_start_byte,ev.evidence_end_byte,ev.candidate_id
                FROM reality_embeddings e JOIN reality_source_units u ON u.unit_id=e.target_id
                JOIN reality_source_pages p ON p.page_key=u.page_key
                LEFT JOIN LATERAL (SELECT c.evidence_quote,c.evidence_start_byte,c.evidence_end_byte,c.candidate_id
                    FROM reality_candidates c WHERE c.unit_id=u.unit_id AND c.status='candidate_unreviewed'
                    AND c.evidence_start_byte IS NOT NULL ORDER BY c.ordinal LIMIT 1) ev ON true
                WHERE e.target_kind='source_unit' AND e.model=%s AND e.model_revision=%s
                AND e.input_sha256=u.text_sha256 ORDER BY distance,u.unit_id LIMIT %s""",
                (literal,model,revision,limit)).fetchall()
        return [dict(row) for row in rows]

    def summary(self) -> dict:
        with self.connect() as conn:
            counts={name:conn.execute(f"SELECT count(*) AS n FROM {name}").fetchone()["n"]
                    for name in ("reality_source_pages","reality_source_units","reality_extract_attempts","reality_candidates","reality_embeddings")}
            by_lang=[dict(row) for row in conn.execute("""SELECT p.language,c.status,count(*) AS n
                FROM reality_candidates c JOIN reality_source_units u ON u.unit_id=c.unit_id
                JOIN reality_source_pages p ON p.page_key=u.page_key
                GROUP BY p.language,c.status ORDER BY p.language,c.status""").fetchall()]
            attempts=[dict(row) for row in conn.execute("""SELECT status,count(*) AS n FROM reality_extract_attempts GROUP BY status ORDER BY status""").fetchall()]
        return {"counts":counts,"candidates_by_language_status":by_lang,"attempts":attempts}

    def candidate_rows(self, limit: int = 20) -> list[dict]:
        with self.connect() as conn:
            rows=conn.execute("""SELECT c.candidate_id,c.layer,c.mapping_refs,c.subject_text,c.predicate_text,c.object_text,
                c.time_text,c.status,c.problems,c.evidence_quote,c.evidence_start_byte,c.evidence_end_byte,
                c.related_candidate_id,u.unit_id,p.wiki_id,p.page_id,p.slot,p.language,p.revision_id,
                p.source_kind,p.snapshot_id,p.source_url
                FROM reality_candidates c JOIN reality_source_units u ON u.unit_id=c.unit_id
                JOIN reality_source_pages p ON p.page_key=u.page_key
                ORDER BY p.wiki_id,c.ordinal LIMIT %s""",(limit,)).fetchall()
        return [dict(row) for row in rows]

    def verify_integrity(self) -> dict:
        with self.connect() as conn:
            pages=conn.execute("SELECT page_key,body,body_sha256 FROM reality_source_pages").fetchall()
            units=conn.execute("""SELECT u.*,p.body FROM reality_source_units u
                JOIN reality_source_pages p ON p.page_key=u.page_key""").fetchall()
            attempts=conn.execute("SELECT attempt_id,raw_response,raw_sha256 FROM reality_extract_attempts").fetchall()
            candidates=conn.execute("""SELECT c.candidate_id,c.status,c.related_candidate_id,c.evidence_quote,
                c.evidence_start_byte,c.evidence_end_byte,p.body FROM reality_candidates c
                JOIN reality_source_units u ON u.unit_id=c.unit_id
                JOIN reality_source_pages p ON p.page_key=u.page_key""").fetchall()
        problems=[]
        for p in pages:
            if digest(p["body"].encode("utf-8")) != p["body_sha256"]:
                problems.append("page_hash:"+p["page_key"])
        for u in units:
            raw=u["body"].encode("utf-8")
            if raw[u["start_byte"]:u["end_byte"]] != u["text"].encode("utf-8") or digest(u["text"].encode("utf-8")) != u["text_sha256"]:
                problems.append("unit_span:"+u["unit_id"])
        for a in attempts:
            if a["raw_response"] is not None and digest(a["raw_response"].encode("utf-8")) != a["raw_sha256"]:
                problems.append("attempt_hash:"+a["attempt_id"])
        candidate_by_id = {candidate["candidate_id"]:candidate for candidate in candidates}
        for c in candidates:
            if c["status"] == "candidate_unreviewed":
                start,end=c["evidence_start_byte"],c["evidence_end_byte"]
                if start is None or end is None or c["body"].encode("utf-8")[start:end] != c["evidence_quote"].encode("utf-8"):
                    problems.append("candidate_span:"+c["candidate_id"])
            if c["status"] == "candidate_unreviewed" and c["related_candidate_id"] is not None:
                related=candidate_by_id.get(c["related_candidate_id"])
                if related is None or related["status"] != "candidate_unreviewed":
                    problems.append("candidate_relation:"+c["candidate_id"])
        return {"pages":len(pages),"units":len(units),"attempts":len(attempts),
                "candidates":len(candidates),"problems":problems}
