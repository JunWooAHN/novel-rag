"""Offline guards for the fixed, no-retry experiment boundary."""

from __future__ import annotations

import asyncio
import json
import hashlib
import sqlite3
import signal
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from benchmark_arm_control import pid_file, stop
from benchmark_100 import ARM_ENGINES, Prepared, _ledger, kg_context, mapping_ids, prepare, run_arm, save_received_response, selection, verify_ledger
from benchmark_vllm_adapter import RawCompletion, local_base, parse_completion
from novel_factory.reality.domain import SourceUnit


ROOT = Path(__file__).resolve().parents[3]
FIXED = ROOT / "data/analysis/private/ontology-benchmark-100-20260928/selection.json"
MAPPING = ROOT / "docs/plans/wikipedia-history-sot-mapping"
YAGO_CONTEXT = ROOT / "data/analysis/private/yago-benchmark-100-20260928/kg-only-context.json"


class BenchmarkBoundaryTest(unittest.TestCase):
    def test_fixed_manifest_and_mapping_directory(self):
        data = selection(FIXED)
        self.assertEqual(len(data["units"]), 100)
        self.assertEqual(len({row["unit_id"] for row in data["units"]}), 100)
        self.assertEqual(sum(row["priority33"] for row in data["units"]), 33)
        self.assertEqual(len({row["target"] for row in data["units"]}), 5)
        self.assertTrue(mapping_ids(MAPPING))

    def test_only_localhost_endpoints(self):
        self.assertEqual(local_base("http://127.0.0.1:8101/v1"), "http://127.0.0.1:8101/v1")
        for url in ("https://127.0.0.1:8101", "http://192.0.2.1:8101", "http://localhost:8101/other"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                local_base(url)

    def test_yago_context_uses_complete_statements_or_explicitly_omits(self):
        class FakeProcessor:
            @staticmethod
            def apply_chat_template(messages, *, tokenize, **_kwargs):
                prompt = messages[0]["content"]
                return {"input_ids": list(range(len(prompt.split())))} if tokenize else "CHAT " + prompt

        fake_transformers = SimpleNamespace(AutoProcessor=SimpleNamespace(
            from_pretrained=lambda *_args, **_kwargs: FakeProcessor()))
        raw = b"source"
        unit = SourceUnit("fixed:1", "enwiki", 1, 1, "main", "en", "Bloomery", 0,
                          len(raw), raw.decode(), hashlib.sha256(raw).hexdigest())
        statement = {"statement_id": "taxonomy:192004", "prompt_text":
                     "taxonomy:192004 yago:Bloomery rdfs:subClassOf yago:Metallurgical_furnace"}
        context = {"targets": {"Bloomery": {"mapping_status": "class_only",
                    "direct_fact_count": 0, "eligible_statement_ids": ["taxonomy:192004"],
                    "statements": [statement]}}}
        with patch.dict(sys.modules, {"transformers": fake_transformers}), \
             patch("benchmark_100.make_indexed_prompt", return_value="SOURCE_SPANS source"), \
             patch("benchmark_100.MAX_OUTPUT_TOKENS", 5):
            included = prepare([{"target": "Bloomery"}], [unit], {"x"}, Path("/base"),
                               Path("/quant"), context, model_len=22)[0]
            omitted = prepare([{"target": "Bloomery"}], [unit], {"x"}, Path("/base"),
                              Path("/quant"), context, model_len=9)[0]
        self.assertEqual(included.kg_statement_ids, ("taxonomy:192004",))
        self.assertEqual(included.kg_context_status, "class_only")
        self.assertIn(statement["prompt_text"], included.prompt)
        self.assertEqual(omitted.kg_statement_ids, ())
        self.assertEqual(omitted.kg_context_status, "budget_omitted")
        self.assertNotIn("YAGO_CONTEXT", omitted.prompt)

    def test_yago_context_is_pinned_to_release_and_exact_targets(self):
        context = kg_context(YAGO_CONTEXT)
        self.assertEqual(context["targets"]["Bloomery"]["mapping_status"], "class_only")
        self.assertEqual(context["targets"]["Bloomery"]["direct_fact_count"], 0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "context.json"
            changed = json.loads(YAGO_CONTEXT.read_text())
            changed["yago_manifest_sha256"] = "0" * 64
            path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                kg_context(path)
            changed["yago_manifest_sha256"] = context["yago_manifest_sha256"]
            changed["targets"]["Bloomery"]["yago_id"] = "yago:Bloomery_Hampshire_County_West_Virginia"
            path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                kg_context(path)

    def test_one_writer_ledger_uses_all_100_without_wal_or_retry(self):
        rows = selection(FIXED)["units"]
        prepared = []
        for row in rows:
            unit = SourceUnit(row["unit_id"], row["wiki_id"], row["page_id"], int(row["revision_id"]),
                              row["slot"], row["language"], row["page_title"], row["start_byte"],
                              row["end_byte"], "x", row["unit_sha256"])
            prepared.append(Prepared(unit, row["target"], "prompt", "a" * 64, 10, list(range(10))))
        with tempfile.TemporaryDirectory() as directory:
            for arm, expected in (("A", [100]), ("B2", [50, 50]), ("B3", [34, 33, 33])):
                file = Path(directory) / (arm + ".sqlite3")
                db = _ledger(file, arm + "-run", arm, rows, prepared)
                self.assertEqual(db.execute("PRAGMA journal_mode").fetchone()[0], "delete")
                counts = [db.execute("SELECT count(*) FROM results WHERE engine_index=?", (n,)).fetchone()[0]
                          for n in range(ARM_ENGINES[arm])]
                self.assertEqual(counts, expected)
                self.assertEqual(db.execute("SELECT count(*) FROM results WHERE status='pending'").fetchone()[0], 100)
                with self.assertRaises(ValueError):
                    _ledger(file, arm + "-run", arm, rows, prepared)
                db.close()
                self.assertEqual(verify_ledger(file, arm + "-run"), {"pending": 100})

    def test_malformed_http_body_is_kept_before_parsing(self):
        bad = RawCompletion(200, b"{broken-json", 0.1)
        with self.assertRaises(ValueError):
            parse_completion(bad)
        rows = selection(FIXED)["units"]
        prepared = []
        for row in rows:
            unit = SourceUnit(row["unit_id"], row["wiki_id"], row["page_id"], int(row["revision_id"]),
                              row["slot"], row["language"], row["page_title"], row["start_byte"],
                              row["end_byte"], "x", row["unit_sha256"])
            prepared.append(Prepared(unit, row["target"], "prompt", "a" * 64, 10, list(range(10))))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raw.sqlite3"
            db = _ledger(path, "bad-raw", "A", rows, prepared)
            with self.assertRaises(ValueError):
                save_received_response(db, "bad-raw", rows[0]["unit_id"], bad, 0.1)
            db.close()
            self.assertEqual(verify_ledger(path, "bad-raw"), {"raw_received": 1, "pending": 99})

    def test_run_arm_bounds_six_requests_and_excludes_empty_output(self):
        rows = selection(FIXED)["units"]
        prepared = []
        for row in rows:
            unit = SourceUnit(row["unit_id"], row["wiki_id"], row["page_id"], int(row["revision_id"]),
                              row["slot"], row["language"], row["page_title"], row["start_byte"],
                              row["end_byte"], "x", row["unit_sha256"])
            prepared.append(Prepared(unit, row["target"], "prompt", "a" * 64, 10, list(range(10))))
        active = peak = calls = 0

        async def fake_completion(*_args):
            nonlocal active, peak, calls
            calls += 1
            call_number = calls
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.001)
            active -= 1
            text = "" if call_number == 1 else "[]"
            return RawCompletion(200, json.dumps({"choices": [{"text": text}],
                                                  "usage": {"prompt_tokens": 10, "completion_tokens": len(text)}}).encode(), 0.001)

        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            prior = folder / "preflight.json"
            prior.write_text(json.dumps({"selection_sha256": "45f58bccc92f7b0455bd3c7902da200c24b579d3b706a495721132eeb9b856f0",
                                         "unit_count": 100, "configured_model_len": 14592,
                                         "units": [{"unit_id": row["unit_id"], "prompt_sha256": "a" * 64} for row in rows]}))
            args = SimpleNamespace(selection=FIXED, preflight=prior, dsn="unused", mapping_dir=MAPPING,
                                   base_processor=folder, fp8_processor=folder, arm="A",
                                   urls=["http://127.0.0.1:8101/v1"], request_timeout=10,
                                   cutoff_seconds=30, sqlite=folder / "results.sqlite3", run_id="fixed-A")
            with patch("benchmark_100.fixed_units", return_value=[case.unit for case in prepared]), \
                 patch("benchmark_100.prepare", return_value=prepared), \
                 patch("benchmark_100.mapping_ids", return_value={"x"}), \
                 patch("benchmark_100.completion", side_effect=fake_completion), \
                 patch("benchmark_100.check_indexed_response", return_value=([], [])):
                asyncio.run(run_arm(args))
            self.assertEqual(calls, 100)
            self.assertEqual(peak, 6)
            self.assertEqual(verify_ledger(args.sqlite, "fixed-A"), {"validated": 99, "zero_output": 1})
            with sqlite3.connect(args.sqlite) as db:
                stats = db.execute("""SELECT count(*),min(queue_wait_seconds),max(queue_wait_seconds),
                    min(end_to_end_seconds) FROM results WHERE run_id=?""", ("fixed-A",)).fetchone()
            self.assertEqual(stats[0], 100)
            self.assertGreaterEqual(stats[1], 0)
            self.assertGreater(stats[2], 0)
            self.assertGreater(stats[3], 0)

    def test_stop_keeps_ownership_record_for_live_orphan_port(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "setup").mkdir()
            record = pid_file(root, "A", 0)
            record.write_text('{"pid":123,"port":8101,"model":"/model"}')
            with patch("benchmark_arm_control.belongs", return_value=False), \
                 patch("benchmark_arm_control.health", return_value=True):
                with self.assertRaises(RuntimeError):
                    stop(root, "A")
            self.assertTrue(record.exists())

    def test_stop_escalates_only_same_verified_group(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "setup").mkdir()
            record = pid_file(root, "A", 0)
            record.write_text('{"pid":123,"port":8101,"model":"/model"}')
            calls = []
            killed = False

            def group_signal(pid, sig):
                nonlocal killed
                calls.append((pid, sig))
                if sig == signal.SIGKILL:
                    killed = True

            with patch("benchmark_arm_control.owned_group", return_value=True), \
                 patch("benchmark_arm_control.belongs", side_effect=lambda *_: not killed), \
                 patch("benchmark_arm_control.health", side_effect=lambda *_: not killed), \
                 patch("benchmark_arm_control.os.killpg", side_effect=group_signal), \
                 patch("benchmark_arm_control.time.sleep"):
                stop(root, "A")
            self.assertEqual(calls, [(123, signal.SIGTERM), (123, signal.SIGKILL)])
            self.assertFalse(record.exists())


if __name__ == "__main__":
    unittest.main()
