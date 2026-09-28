"""PostgreSQL ledger for one immutable, five-target RealityRelease pilot."""

from __future__ import annotations

import json
from hashlib import sha256

import psycopg
from psycopg.rows import dict_row

from novel_factory.reality.sot import RELEASE_ID


SCHEMA = """
CREATE TABLE IF NOT EXISTS sot_entity (id text PRIMARY KEY, payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS sot_source_statement (id text PRIMARY KEY, payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS sot_source_meta (id text PRIMARY KEY, payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS sot_claim (
    id text PRIMARY KEY, source_id text NOT NULL REFERENCES sot_source_statement(id), payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS sot_decision (
    id text PRIMARY KEY, claim_id text NOT NULL REFERENCES sot_claim(id), payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS sot_member (
    release_id text NOT NULL, claim_id text NOT NULL REFERENCES sot_claim(id),
    PRIMARY KEY (release_id, claim_id)
);
CREATE TABLE IF NOT EXISTS sot_release (
    id text PRIMARY KEY, payload jsonb NOT NULL, published_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sot_release_scope (
    release_id text PRIMARY KEY, payload jsonb NOT NULL
);
CREATE OR REPLACE FUNCTION sot_refuse_published_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF TG_TABLE_NAME = 'sot_member' THEN
            IF EXISTS (SELECT 1 FROM sot_release WHERE id = NEW.release_id) THEN
                RAISE EXCEPTION 'Published release membership is immutable';
            END IF;
        END IF;
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'SoT ledger rows are append-only';
END $$;
DO $$
DECLARE name text;
BEGIN
    FOREACH name IN ARRAY ARRAY['sot_entity','sot_source_statement','sot_source_meta',
                                 'sot_claim','sot_decision','sot_member','sot_release',
                                 'sot_release_scope'] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS sot_immutable ON %I', name);
        EXECUTE format('CREATE TRIGGER sot_immutable BEFORE INSERT OR UPDATE OR DELETE ON %I '
                       || 'FOR EACH ROW EXECUTE FUNCTION sot_refuse_published_mutation()', name);
    END LOOP;
END $$;
"""


def _json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class PgSotStore:
    def __init__(self, dsn: str):
        self.dsn = dsn

    def connect(self):
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def init(self) -> None:
        with self.connect() as conn:
            conn.execute(SCHEMA)

    @staticmethod
    def _expected(prepared: dict) -> dict:
        release = dict(prepared["release"])
        claims = sorted(prepared["claims"], key=lambda x: x["claim_id"])
        release["member_ids"] = [x["claim_id"] for x in claims]
        result = {"release": release, "member_ids": release["member_ids"]}
        for key, id_key in (("entities", "trial_entity_id"),
                            ("source_statements", "statement_id"),
                            ("source_meta", "meta_statement_id"),
                            ("decisions", "decision_id")):
            result[key] = sorted(prepared[key], key=lambda x: x[id_key])
        result["claims"] = claims
        if (len(set(result["member_ids"])) != len(claims)
                or {x["claim_id"] for x in result["decisions"]} != set(result["member_ids"])):
            raise ValueError("Claim and decision identities must be unique and paired")
        return result

    @staticmethod
    def _scope(expected: dict) -> dict:
        return {
            "entity_ids": [x["trial_entity_id"] for x in expected["entities"]],
            "source_statement_ids": [x["statement_id"] for x in expected["source_statements"]],
            "source_meta_ids": [x["meta_statement_id"] for x in expected["source_meta"]],
            "claim_ids": [x["claim_id"] for x in expected["claims"]],
            "decision_ids": [x["decision_id"] for x in expected["decisions"]],
            "payload_sha256": sha256(_json(expected).encode("utf-8")).hexdigest(),
        }

    @staticmethod
    def _all_rows(conn, table: str) -> list[dict]:
        return [r["payload"] for r in conn.execute(f"SELECT payload FROM {table} ORDER BY id")]

    def _snapshot(self, conn, release_id: str) -> dict:
        release_row = conn.execute("SELECT payload FROM sot_release WHERE id=%s", (release_id,)).fetchone()
        if release_row is None:
            raise ValueError("Unknown RealityRelease ID")
        scope_row = conn.execute("SELECT payload FROM sot_release_scope WHERE release_id=%s", (release_id,)).fetchone()
        if scope_row is None:
            raise ValueError("Release scope manifest missing; migrate the original pilot release")
        scope = scope_row["payload"]
        specification = (
            ("entities", "sot_entity", "entity_ids"),
            ("source_statements", "sot_source_statement", "source_statement_ids"),
            ("source_meta", "sot_source_meta", "source_meta_ids"),
            ("claims", "sot_claim", "claim_ids"),
            ("decisions", "sot_decision", "decision_ids"),
        )
        snapshot = {"release": release_row["payload"]}
        for key, table, scope_key in specification:
            ids = scope[scope_key]
            snapshot[key] = [r["payload"] for r in conn.execute(
                f"SELECT payload FROM {table} WHERE id = ANY(%s) ORDER BY id", (ids,))]
            if len(snapshot[key]) != len(ids):
                raise ValueError("Release-scoped ledger row missing")
        snapshot["member_ids"] = [r["claim_id"] for r in conn.execute(
            "SELECT claim_id FROM sot_member WHERE release_id=%s ORDER BY claim_id", (release_id,))]
        if snapshot["member_ids"] != snapshot["release"]["member_ids"]:
            raise ValueError("Release membership differs from immutable manifest")
        members = set(snapshot["member_ids"])
        if ({x["claim_id"] for x in snapshot["claims"]} != members
                or {x["claim_id"] for x in snapshot["decisions"]} != members
                or len(snapshot["claims"]) != len(members)
                or len(snapshot["decisions"]) != len(members)):
            raise ValueError("Release claim/decision identity differs from membership")
        if self._scope(snapshot) != scope:
            raise ValueError("Release-scoped payload hash or IDs differ from manifest")
        return snapshot

    def read(self, release_id: str = RELEASE_ID) -> dict:
        with self.connect() as conn:
            return self._snapshot(conn, release_id)

    def publish(self, prepared: dict) -> dict:
        expected = self._expected(prepared)
        release = expected["release"]
        scope = self._scope(expected)
        with self.connect() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtext('novel_factory_reality_sot_pilot'))")
            current = conn.execute("SELECT id FROM sot_release WHERE id=%s", (release["release_id"],)).fetchone()
            if current is not None:
                if conn.execute("SELECT 1 FROM sot_release_scope WHERE release_id=%s", (release["release_id"],)).fetchone() is None:
                    # The first pilot release predates release-scoped manifests.
                    # Its complete original tables must equal the pinned input
                    # before one append-only scope row can be attached.
                    if release["release_id"] != RELEASE_ID:
                        raise ValueError("Unscoped release cannot be migrated automatically")
                    old = {"release": conn.execute("SELECT payload FROM sot_release WHERE id=%s",
                                                    (RELEASE_ID,)).fetchone()["payload"]}
                    for key, table in (("entities", "sot_entity"),
                                       ("source_statements", "sot_source_statement"),
                                       ("source_meta", "sot_source_meta"),
                                       ("claims", "sot_claim"), ("decisions", "sot_decision")):
                        old[key] = self._all_rows(conn, table)
                    old["member_ids"] = [r["claim_id"] for r in conn.execute(
                        "SELECT claim_id FROM sot_member WHERE release_id=%s ORDER BY claim_id", (RELEASE_ID,))]
                    if old != expected:
                        raise ValueError("Original published pilot differs from pinned foundation")
                    conn.execute("INSERT INTO sot_release_scope (release_id,payload) VALUES (%s,%s::jsonb)",
                                 (RELEASE_ID, _json(scope)))
                if self._snapshot(conn, release["release_id"]) != expected:
                    raise ValueError("Published release differs from requested input; new release required")
                return {"release_id": release["release_id"], "created": False,
                        "source_statements": len(expected["source_statements"]), "claims": len(expected["claims"])}
            rows = (
                ("sot_entity", "trial_entity_id", expected["entities"]),
                ("sot_source_statement", "statement_id", expected["source_statements"]),
                ("sot_source_meta", "meta_statement_id", expected["source_meta"]),
            )
            for table, id_key, items in rows:
                for item in items:
                    old = conn.execute(f"SELECT payload FROM {table} WHERE id=%s", (item[id_key],)).fetchone()
                    if old is None:
                        conn.execute(f"INSERT INTO {table} (id,payload) VALUES (%s,%s::jsonb)",
                                     (item[id_key], _json(item)))
                    elif old["payload"] != item:
                        raise ValueError("Existing immutable source/entity ID has changed content")
            for item in expected["claims"]:
                old = conn.execute("SELECT source_id,payload FROM sot_claim WHERE id=%s", (item["claim_id"],)).fetchone()
                if old is None:
                    conn.execute("INSERT INTO sot_claim (id,source_id,payload) VALUES (%s,%s,%s::jsonb)",
                                 (item["claim_id"], item["source_statement_id"], _json(item)))
                elif old["source_id"] != item["source_statement_id"] or old["payload"] != item:
                    raise ValueError("Existing immutable claim ID has changed content; use a revision ID")
            for item in expected["decisions"]:
                old = conn.execute("SELECT claim_id,payload FROM sot_decision WHERE id=%s", (item["decision_id"],)).fetchone()
                if old is None:
                    conn.execute("INSERT INTO sot_decision (id,claim_id,payload) VALUES (%s,%s,%s::jsonb)",
                                 (item["decision_id"], item["claim_id"], _json(item)))
                elif old["claim_id"] != item["claim_id"] or old["payload"] != item:
                    raise ValueError("Existing immutable decision ID has changed content; use a revision ID")
            for claim_id in release["member_ids"]:
                conn.execute("INSERT INTO sot_member (release_id,claim_id) VALUES (%s,%s)",
                             (release["release_id"], claim_id))
            conn.execute("INSERT INTO sot_release_scope (release_id,payload) VALUES (%s,%s::jsonb)",
                         (release["release_id"], _json(scope)))
            conn.execute("INSERT INTO sot_release (id,payload) VALUES (%s,%s::jsonb)",
                         (release["release_id"], _json(release)))
            if self._snapshot(conn, release["release_id"]) != expected:
                raise ValueError("PostgreSQL release readback differs from prepared data")
        return {"release_id": release["release_id"], "created": True,
                "source_statements": len(expected["source_statements"]), "claims": len(expected["claims"])}
