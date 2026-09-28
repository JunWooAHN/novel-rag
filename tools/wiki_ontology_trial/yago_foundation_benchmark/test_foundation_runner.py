"""Boundary checks for the separate foundation-link audit ledger."""

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from foundation_runner import audit_links


class LinkAuditTest(unittest.TestCase):
    def test_links_are_preserved_and_never_auto_suppress(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = root / "preflight.json"
            results = root / "results.sqlite3"
            specs = []
            with sqlite3.connect(results) as db:
                db.execute("""CREATE TABLE results (
                    run_id TEXT, unit_id TEXT, rank INTEGER, status TEXT,
                    raw_text TEXT, prompt_sha256 TEXT, validation_json TEXT)""")
                for rank in range(1, 101):
                    unit_id = f"u{rank:03d}"
                    specs.append({"unit_id": unit_id, "prompt_sha256": unit_id,
                                  "residual_mode": rank != 5,
                                  "displayed_statement_ids": [] if rank == 5 else ["kg1"],
                                  "source_span_ids": ["s000"]})
                    raw = {"candidates": [{"evidence_span_id": "s000"}],
                           "foundation_links": []}
                    if rank == 1:
                        raw["foundation_links"] = [
                            {"statement_id": "kg1", "evidence_span_id": "s000",
                             "source_claim": "same claim", "relation": "same",
                             "candidate_ordinal": None},
                            {"statement_id": "hidden", "evidence_span_id": "s000",
                             "source_claim": "unshown claim", "relation": "same",
                             "candidate_ordinal": None}]
                    if rank == 2:
                        raw["foundation_links"] = [
                            {"statement_id": "kg1", "evidence_span_id": "s000",
                             "source_claim": "additional claim", "relation": "extends",
                             "candidate_ordinal": 0}]
                    if rank == 3:
                        del raw["foundation_links"]
                    if rank == 4:
                        raw["foundation_links"] = [
                            {"statement_id": ["kg1"], "evidence_span_id": {"id": "s000"},
                             "source_claim": ["claim"], "relation": ["same"],
                             "candidate_ordinal": {"ordinal": 0}}]
                    if rank == 5:
                        del raw["foundation_links"]
                    db.execute("INSERT INTO results VALUES (?,?,?,?,?,?,?)",
                               ("run", unit_id, rank, "validated", json.dumps(raw),
                                unit_id, "{}"))
            receipt.write_text(json.dumps({"units": specs}))
            counts = audit_links(results, "run", receipt)
            self.assertEqual(counts, {"units": 100, "valid_links": 2,
                                      "invalid_links": 2,
                                      "same_proposals_needing_review": 1,
                                      "missing_link_fields": 1,
                                      "not_exposed_units": 1,
                                      "overflow_units": 0,
                                      "parse_error_units": 0})
            with sqlite3.connect(results) as db:
                proposals = db.execute(
                    "SELECT status,problems_json FROM foundation_link_proposal "
                    "WHERE unit_id='u001' ORDER BY link_index").fetchall()
                self.assertEqual(proposals[0][0], "valid_proposal_needs_review")
                self.assertEqual(proposals[1][0], "invalid_hold")
                self.assertIn("statement_not_displayed", json.loads(proposals[1][1]))
                malformed = db.execute("SELECT status,problems_json FROM foundation_link_proposal "
                                       "WHERE unit_id='u004'").fetchone()
                self.assertEqual(malformed[0], "invalid_hold")
                self.assertIn("span_not_in_source", json.loads(malformed[1]))
                self.assertEqual(db.execute("SELECT count(*) FROM foundation_link_audit").fetchone()[0], 100)
            with self.assertRaisesRegex(ValueError, "already exists"):
                audit_links(results, "run", receipt)


if __name__ == "__main__":
    unittest.main()
