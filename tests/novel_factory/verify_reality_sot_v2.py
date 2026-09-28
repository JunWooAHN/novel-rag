"""Readback and mutation gate for the actual, corrected PostgreSQL release."""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import psycopg

from novel_factory.reality.adapters.sot_postgres import PgSotStore
from novel_factory.reality.sot import RELEASE_ID, RELEASE_ID_V2, load_foundation, make_release


def digest(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode("utf-8")).hexdigest()


def expect_sql_rejection(store: PgSotStore, sql: str, params: tuple) -> str:
    conn = store.connect()
    try:
        try:
            conn.execute(sql, params)
        except psycopg.Error as exc:
            conn.rollback()
            return exc.sqlstate or type(exc).__name__
        conn.rollback()
        raise AssertionError("Published data mutation unexpectedly allowed")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", required=True)
    parser.add_argument("--foundation", type=Path, required=True)
    args = parser.parse_args()
    store = PgSotStore(args.dsn)
    original = make_release(load_foundation(args.foundation), revision="v1")
    corrected = make_release(load_foundation(args.foundation), revision="v2")
    old_before = store.read(RELEASE_ID)
    new_before = store.read(RELEASE_ID_V2)
    if store.publish(original)["created"] or store.publish(corrected)["created"]:
        raise AssertionError("Exact release rerun must be idempotent")
    changed = deepcopy(corrected)
    changed["release"]["policy_delta"] = "tampered same-ID request"
    try:
        store.publish(changed)
    except ValueError:
        same_id_rejected = True
    else:
        raise AssertionError("Changed v2 under same ID accepted")
    revised_claim_id = "sot:claim:facts:46623039:r2"
    mutation = {
        "revised_claim_update": expect_sql_rejection(store,
            "UPDATE sot_claim SET payload=payload WHERE id=%s", (revised_claim_id,)),
        "v2_decision_delete": expect_sql_rejection(store,
            "DELETE FROM sot_decision WHERE id=%s", ("sot:decision:facts:46623039:r2",)),
        "v2_member_append": expect_sql_rejection(store,
            "INSERT INTO sot_member (release_id,claim_id) VALUES (%s,%s)",
            (RELEASE_ID_V2, "sot:claim:facts:46623039")),
        "v1_member_append_v2_claim": expect_sql_rejection(store,
            "INSERT INTO sot_member (release_id,claim_id) VALUES (%s,%s)",
            (RELEASE_ID, revised_claim_id)),
    }
    old_after = store.read(RELEASE_ID)
    new_after = store.read(RELEASE_ID_V2)
    if digest(old_before) != digest(old_after) or digest(new_before) != digest(new_after):
        raise AssertionError("One published release changed during verification")
    result = {"schema": "yago-sot-pg-v2-postpublication-v1",
              "v1_release_id": RELEASE_ID, "v2_release_id": RELEASE_ID_V2,
              "v1_readback_sha256_before_after": digest(old_before),
              "v2_readback_sha256_before_after": digest(new_before),
              "exact_v1_v2_rerun_created": False,
              "changed_v2_same_id_rejected": same_id_rejected,
              "mutation_rejections": mutation,
              "source_statement_count": len(new_after["source_statements"]),
              "source_meta_count": len(new_after["source_meta"]),
              "v2_claim_count": len(new_after["claims"])}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
