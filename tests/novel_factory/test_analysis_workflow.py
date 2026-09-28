import contextlib
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from novel_factory.cli import main
from novel_factory.contracts import SceneSpec, SourceSpan
from novel_factory.style.sqlite_store import SQLiteAnalysisStore
from novel_factory.style.workflow import (AnalysisWorkflow, Selection,
    check_review_transition, check_submission_transition)


ROOT = Path(__file__).resolve().parents[2]


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class AnalysisWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "corpus.sqlite3"
        self.first = "1화\r\n앞부분\r\n"
        self.second = "2화\r\n뒤쪽 비밀\r\n"
        raw = self.first + self.second
        self.source_sha = sha(raw)
        with sqlite3.connect(self.db) as conn:
            conn.executescript((ROOT / "tools/novel_corpus/schema.sql").read_text())
            conn.execute("INSERT INTO works(work_id,author,title,drive_file_id,manifest_relative_path) VALUES(?,?,?,?,?)",
                         ("fixture", "a", "t", "d", "fixture.txt"))
            conn.execute("""INSERT INTO source_revisions(work_id,sha256_raw,byte_size,codepoint_length,
                relative_path,drive_file_id,utf8_bom,crlf_count,bare_lf_count,bare_cr_count)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                ("fixture", self.source_sha, len(raw.encode()), len(raw), "fixture.txt", "d", 0, 2, 0, 0))
            self.rev = conn.execute("SELECT id FROM source_revisions").fetchone()[0]
            conn.execute("INSERT INTO segmentations(source_revision_id,rules_sha256) VALUES(?,?)",
                         (self.rev, "a" * 64))
            self.seg = conn.execute("SELECT id FROM segmentations").fetchone()[0]
            for ordinal, body, start in ((1, self.first, 0), (2, self.second, len(self.first))):
                conn.execute("""INSERT INTO segments(segmentation_id,ordinal,kind,boundary_status,
                    number_claimed,number_occurrence,start_cp,end_cp,text_sha256,body)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (self.seg, ordinal, "numbered", "confirmed", ordinal, 1,
                     start, start + len(body), sha(body), body))
            conn.execute("UPDATE works SET current_segmentation_id=? WHERE work_id='fixture'", (self.seg,))
        self.store = SQLiteAnalysisStore(self.db)
        self.store.init()
        self.flow = AnalysisWorkflow(self.store)

    def chapter(self, number=1):
        return Selection("fixture", self.rev, self.source_sha, self.seg,
                         "chapter", number, "chapter_analysis")

    def test_chapter_is_bounded_pinned_and_independently_reviewed(self):
        prepared = self.flow.prepare_analysis_input(self.chapter())
        self.assertEqual(prepared.body, self.first)
        self.assertNotIn("뒤쪽", prepared.body)
        self.assertEqual(prepared.span.text_sha256, sha(self.first))
        self.assertEqual(self.flow.prepare_analysis_input(self.chapter()).task_id, prepared.task_id)
        self.assertEqual(self.flow.resume(prepared.task_id)[0]["state"], "prepared")

        payload = '{"observation":"fixture only"}'
        sent = self.flow.submit_result(prepared.task_id, "s1", "author-sol", payload)
        self.assertTrue(sent["created"])
        self.assertFalse(self.flow.submit_result(prepared.task_id, "s1", "author-sol", payload)["created"])
        with self.assertRaisesRegex(ValueError, "different payload"):
            self.flow.submit_result(prepared.task_id, "s1", "author-sol", '{"changed":true}')
        self.assertEqual(self.flow.resume(prepared.task_id)[0]["state"], "needs_review")
        with self.assertRaisesRegex(ValueError, "cannot independently review"):
            self.flow.review_result(prepared.task_id, "s1", "r1", "author-sol", "accepted",
                                    "self review", sent["submission_sha256"])
        with self.assertRaisesRegex(ValueError, "SHA differs"):
            self.flow.review_result(prepared.task_id, "s1", "r1", "independent-sol", "accepted",
                                    "checked", "0" * 64)
        decision = self.flow.review_result(prepared.task_id, "s1", "r1", "independent-sol",
                                           "accepted", "source checked", sent["submission_sha256"])
        self.assertTrue(decision["created"])
        self.assertFalse(self.flow.review_result(prepared.task_id, "s1", "r1", "independent-sol",
                          "accepted", "source checked", sent["submission_sha256"])["created"])
        self.assertEqual(self.flow.resume(prepared.task_id)[0]["state"], "complete")
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.flow.submit_result(prepared.task_id, "s2", "author-sol", payload)

        # A changed current pointer cannot silently change a pinned input.
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO segmentations(source_revision_id,rules_sha256) VALUES(?,?)",
                         (self.rev, "b" * 64))
            new_seg = conn.execute("SELECT MAX(id) FROM segmentations").fetchone()[0]
            conn.execute("UPDATE works SET current_segmentation_id=? WHERE work_id='fixture'", (new_seg,))
        self.assertEqual(self.store.get_input(prepared.task_id).body, self.first)

    def test_unconfirmed_number_is_not_a_chapter_and_window_is_separate(self):
        with self.assertRaisesRegex(ValueError, "not uniquely mapped"):
            self.flow.prepare_analysis_input(self.chapter(3))
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO segmentations(source_revision_id,rules_sha256) VALUES(?,?)",
                         (self.rev, "h" * 64))
            held_seg = conn.execute("SELECT MAX(id) FROM segmentations").fetchone()[0]
            for ordinal, body, start in ((1, self.first, 0), (2, self.second, len(self.first))):
                conn.execute("""INSERT INTO segments(segmentation_id,ordinal,kind,boundary_status,
                    number_claimed,number_occurrence,start_cp,end_cp,text_sha256,body)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (held_seg, ordinal, "numbered", "hold" if ordinal == 1 else "confirmed",
                     ordinal, 1, start, start + len(body), sha(body), body))
        with self.assertRaisesRegex(ValueError, "not uniquely mapped"):
            self.flow.prepare_analysis_input(Selection("fixture", self.rev, self.source_sha,
                held_seg, "chapter", 1, "chapter_analysis"))
        with self.assertRaisesRegex(ValueError, "approved window missing"):
            self.flow.prepare_analysis_input(Selection("fixture", self.rev, self.source_sha,
                self.seg, "window", "w1", "reverse_window"))
        part = self.second[:4]
        self.store.register_window(window_id="w1", work_id="fixture", source_revision_id=self.rev,
            source_sha256=self.source_sha, segmentation_id=self.seg, start_cp=len(self.first),
            end_cp=len(self.first) + len(part), text_sha256=sha(part), role="sota_planning",
            split="train", workflow_kind="reverse_window", approval_ref="decision:fixture",
            approved_by="independent-sol")
        p = self.store.prepare_window_id("w1")
        self.assertEqual((p.selection_kind, p.role, p.split), ("window", "sota_planning", "train"))
        self.assertEqual(p.body, part)
        self.assertNotIn("뒤쪽 비밀", p.body)
        with self.assertRaisesRegex(ValueError, "different approved selection"):
            self.store.register_window(window_id="w1", work_id="fixture", source_revision_id=self.rev,
                source_sha256=self.source_sha, segmentation_id=self.seg, start_cp=len(self.first),
                end_cp=len(self.first) + len(part), text_sha256=sha(part), role="gemma_style",
                split="train", workflow_kind="reverse_window", approval_ref="decision:fixture",
                approved_by="independent-sol")

    def test_review_correction_changes_completion_and_requires_exact_previous_sha(self):
        p = self.flow.prepare_analysis_input(self.chapter())
        sent = self.flow.submit_result(p.task_id, "s1", "author", "{}")
        first = self.flow.review_result(p.task_id, "s1", "r1", "other", "accepted",
                                        "source checked", sent["submission_sha256"])
        with self.assertRaisesRegex(ValueError, "current review SHA"):
            self.flow.review_result(p.task_id, "s1", "r2", "other", "hold", "correction",
                                    sent["submission_sha256"])
        self.flow.review_result(p.task_id, "s1", "r2", "other", "hold", "correction",
                                sent["submission_sha256"], first["review_sha256"])
        self.assertEqual(self.flow.resume(p.task_id)[0]["state"], "needs_revision")

    def test_later_full_window_cannot_bypass_prior_review_via_cli_or_view(self):
        for window_id, start, end in (("fixture-b01-w01:primary", 0, len(self.first)),
                                      ("fixture-b01-w02:primary", len(self.first), len(self.first) + 4)):
            body = (self.first + self.second)[start:end]
            self.store.register_window(window_id=window_id, work_id="fixture",
                source_revision_id=self.rev, source_sha256=self.source_sha,
                segmentation_id=self.seg, start_cp=start, end_cp=end,
                text_sha256=sha(body), role="sota_planning", split="train",
                workflow_kind="reverse_window", approval_ref="frozen:fixture",
                approved_by="fixture-reviewer")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main(["--db", str(self.db), "prepare-window",
                                   "fixture-b01-w02:primary"]), 1)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("previous DB window", err.getvalue())
        with self.assertRaisesRegex(ValueError, "previous DB window"):
            self.store.prepare_window_id("fixture-b01-w02:primary")
        first = self.store.prepare_window_id("fixture-b01-w01:primary")
        sent = self.flow.submit_result(first.task_id, "s1", "author", "{}")
        with self.assertRaisesRegex(ValueError, "previous DB window"):
            self.store.prepare_window_id("fixture-b01-w02:primary")
        accepted = self.flow.review_result(first.task_id, "s1", "r1", "other",
            "accepted", "source checked", sent["submission_sha256"])
        second = self.store.prepare_window_id("fixture-b01-w02:primary")
        self.assertEqual(second.body, self.second[:4])
        self.flow.review_result(first.task_id, "s1", "r2", "other", "rejected",
            "corrected independent decision", sent["submission_sha256"],
            accepted["review_sha256"])
        with self.assertRaisesRegex(ValueError, "previous DB window"):
            self.store.get_input(second.task_id)
        self.assertEqual(self.flow.resume(second.task_id)[0]["state"], "blocked_prerequisite")

    def test_cli_bounded_view_and_export(self):
        args = ["--db", str(self.db), "prepare", "--work", "fixture",
                "--source-revision", str(self.rev), "--source-sha", self.source_sha,
                "--segmentation", str(self.seg), "--chapter", "1"]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(args), 0)
        prepared = json.loads(out.getvalue())
        self.assertEqual(prepared["body"], self.first)
        self.assertEqual(prepared["source_span"]["text_sha256"], sha(self.first))
        target = Path(self.temp.name) / "bounded.txt"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["--db", str(self.db), "export-input",
                                   prepared["task_id"], str(target)]), 0)
        self.assertEqual(target.read_bytes(), self.first.encode("utf-8"))
        self.assertNotIn("body", json.loads(out.getvalue()))
        raw_result = b'{\r\n  "observation": "fixture"\r\n}\r\n'
        result_path = Path(self.temp.name) / "result.json"
        result_path.write_bytes(raw_result)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["--db", str(self.db), "submit", prepared["task_id"],
                                   "s-crlf", "author", str(result_path)]), 0)
        submitted = json.loads(out.getvalue())
        self.assertEqual(submitted["submission_sha256"],
                         hashlib.sha256(raw_result).hexdigest())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["--db", str(self.db), "view-result",
                                   prepared["task_id"], "s-crlf"]), 0)
        stored = json.loads(out.getvalue())
        self.assertEqual(stored["payload_json"].encode("utf-8"), raw_result)
        self.assertEqual((stored["work_id"], stored["source_revision_id"],
                          stored["selection_kind"], stored["selection_id"]),
                         ("fixture", self.rev, "chapter", "1"))
        self.assertEqual(stored["review_decision"], None)
        exported = Path(self.temp.name) / "result-export.json"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["--db", str(self.db), "export-result",
                                   prepared["task_id"], "s-crlf", str(exported)]), 0)
        self.assertEqual(exported.read_bytes(), raw_result)
        self.assertNotIn("payload_json", json.loads(out.getvalue()))
        other = self.flow.prepare_analysis_input(self.chapter(2))
        with self.assertRaisesRegex(ValueError, "does not belong"):
            self.flow.get_submission(other.task_id, "s-crlf")

    def test_scene_spec_distinguishes_hypothesis_and_locked_plan(self):
        first = SourceSpan("fixture", self.rev, self.source_sha, self.seg, 0, 3, sha(self.first[:3]))
        target = SourceSpan("fixture", self.rev, self.source_sha, self.seg, 3, 6, sha(self.first[3:6]))
        SceneSpec("s", "goal", ("constraint",), "learning_hypothesis", "review:r1",
                  "actor", ("known:1",), ("prior:1",), first, target)
        with self.assertRaisesRegex(ValueError, "precede target"):
            SceneSpec("s", "goal", (), "learning_hypothesis", "review:r1",
                      "actor", (), (), target, first)
        with self.assertRaisesRegex(ValueError, "bounded input"):
            SceneSpec("s", "goal", (), "learning_hypothesis", "review:r1",
                      "actor", (), ())
        SceneSpec("s", "goal", (), "locked_writing", "plan:locked-v1",
                  "actor", (), ())
        with self.assertRaisesRegex(ValueError, "cannot carry training target"):
            SceneSpec("s", "goal", (), "locked_writing", "plan:locked-v1",
                      "actor", (), (), first, target)

    def test_core_review_rules_without_database(self):
        with self.assertRaisesRegex(ValueError, "unreviewed"):
            check_submission_transition(None, True)
        with self.assertRaisesRegex(ValueError, "immutable"):
            check_submission_transition("accepted", False)
        check_submission_transition("hold", False)
        with self.assertRaisesRegex(ValueError, "independently review"):
            check_review_transition("author", "author", "a", "a", None, None)
        with self.assertRaisesRegex(ValueError, "SHA differs"):
            check_review_transition("author", "reviewer", "a", "b", None, None)
        with self.assertRaisesRegex(ValueError, "current review SHA"):
            check_review_transition("author", "reviewer", "a", "a", "prev", None)


if __name__ == "__main__":
    unittest.main()
