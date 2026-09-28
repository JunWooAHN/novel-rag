"""Explicit H200 PostgreSQL integration probe; synthetic v2 stays in a test DB."""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile

import psycopg

from novel_factory.reality.adapters.sot_postgres import PgSotStore
from novel_factory.reality.sot import RELEASE_ID, load_foundation, make_release


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def reject_sql(store: PgSotStore, sql: str, params: tuple) -> str:
    conn = store.connect()
    try:
        try:
            conn.execute(sql, params)
        except psycopg.Error as exc:
            conn.rollback()
            return exc.sqlstate or type(exc).__name__
        conn.rollback()
        raise AssertionError("Mutation unexpectedly succeeded: " + sql.split()[0])
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operating-dsn", required=True)
    parser.add_argument("--test-dsn", required=True)
    parser.add_argument("--foundation", type=Path, required=True)
    args = parser.parse_args()
    prepared = make_release(load_foundation(args.foundation))
    operating = PgSotStore(args.operating_dsn)
    before = operating.read(RELEASE_ID)
    original_hash = sha256(canonical(before)).hexdigest()
    repeated = operating.publish(prepared)
    if repeated["created"]:
        raise AssertionError("Exact re-import was not idempotent")
    changed = deepcopy(prepared)
    changed["release"]["scope"] = "changed-same-ID-must-fail"
    try:
        operating.publish(changed)
    except ValueError:
        same_id_rejected = True
    else:
        raise AssertionError("Changed same release ID accepted")
    with tempfile.TemporaryDirectory() as directory:
        tampered = Path(directory) / "foundation.sqlite3"
        tampered.write_bytes(args.foundation.read_bytes() + b"tamper")
        try:
            load_foundation(tampered)
        except ValueError:
            bad_hash_rejected = True
        else:
            raise AssertionError("Tampered source accepted")
    rows = {
        "entity_update": ("UPDATE sot_entity SET payload=payload WHERE id=%s", before["entities"][0]["trial_entity_id"]),
        "source_update": ("UPDATE sot_source_statement SET payload=payload WHERE id=%s", before["source_statements"][0]["statement_id"]),
        "meta_update": ("UPDATE sot_source_meta SET payload=payload WHERE id=%s", before["source_meta"][0]["meta_statement_id"]),
        "claim_update": ("UPDATE sot_claim SET payload=payload WHERE id=%s", before["claims"][0]["claim_id"]),
        "decision_update": ("UPDATE sot_decision SET payload=payload WHERE id=%s", before["decisions"][0]["decision_id"]),
        "member_delete": ("DELETE FROM sot_member WHERE release_id=%s", RELEASE_ID),
        "release_update": ("UPDATE sot_release SET payload=payload WHERE id=%s", RELEASE_ID),
        "scope_update": ("UPDATE sot_release_scope SET payload=payload WHERE release_id=%s", RELEASE_ID),
    }
    mutation_rejections = {name: reject_sql(operating, sql, (ident,)) for name, (sql, ident) in rows.items()}
    after = operating.read(RELEASE_ID)
    after_hash = sha256(canonical(after)).hexdigest()
    if original_hash != after_hash:
        raise AssertionError("Operating release changed during negative probes")

    test = PgSotStore(args.test_dsn)
    test.init()
    test_v1 = deepcopy(prepared)
    test_v1["release"]["release_id"] = "test:reality:yago46:five:v1"
    test_v1["release"]["test_only"] = True
    test.publish(test_v1)
    test_v1_before = test.read(test_v1["release"]["release_id"])
    test_v1_hash = sha256(canonical(test_v1_before)).hexdigest()
    test_v2 = deepcopy(test_v1)
    test_v2["release"]["release_id"] = "test:reality:yago46:five:v2-synthetic"
    test_v2["release"]["synthetic_correction"] = "claim metadata revision only; source triple unchanged"
    old_claim_id = test_v2["claims"][0]["claim_id"]
    new_claim_id = old_claim_id + ":test-revision-2"
    test_v2["claims"][0]["claim_id"] = new_claim_id
    test_v2["claims"][0]["test_revision_note"] = "synthetic metadata correction; not historical evidence"
    decision = next(x for x in test_v2["decisions"] if x["claim_id"] == old_claim_id)
    decision["claim_id"] = new_claim_id
    decision["decision_id"] += ":test-revision-2"
    decision["rationale"] = "Synthetic test revision; not a newly reviewed source claim"
    test_v2_published = test.publish(test_v2)
    test_v2_read = test.read(test_v2["release"]["release_id"])
    test_v1_after = test.read(test_v1["release"]["release_id"])
    if sha256(canonical(test_v1_after)).hexdigest() != test_v1_hash:
        raise AssertionError("Test v1 changed when v2 was published")
    if new_claim_id not in test_v2_read["member_ids"] or new_claim_id in test_v1_after["member_ids"]:
        raise AssertionError("Release-scoped synthetic revision isolation failed")
    member_append_rejection = reject_sql(test,
        "INSERT INTO sot_member (release_id,claim_id) VALUES (%s,%s)",
        (test_v1["release"]["release_id"], new_claim_id))
    report = {
        "schema": "yago-sot-postgres-verification-v1",
        "operating_release_id": RELEASE_ID,
        "operating_pg_readback_sha256": original_hash,
        "operating_after_negative_probe_sha256": after_hash,
        "exact_reimport_created": repeated["created"],
        "changed_same_release_id_rejected": same_id_rejected,
        "tampered_input_hash_rejected_before_publish": bad_hash_rejected,
        "operating_mutation_rejections": mutation_rejections,
        "synthetic_test_db": "separate explicitly supplied test DB",
        "synthetic_v1_readback_sha256_before_after_v2": test_v1_hash,
        "synthetic_v2_readback_sha256": sha256(canonical(test_v2_read)).hexdigest(),
        "synthetic_v2_created": test_v2_published["created"],
        "synthetic_revision_claim_id": new_claim_id,
        "published_v1_member_append_rejection": member_append_rejection,
        "source_capture_sha256": prepared["release"]["foundation_sha256"],
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
