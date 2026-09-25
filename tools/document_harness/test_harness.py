import contextlib
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest

import harness


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.old_root = harness.ROOT
        harness.ROOT = self.root
        self.addCleanup(setattr, harness, "ROOT", self.old_root)
        self.db = self.root / "documents.sqlite3"
        harness.init_db(self.db)

    def command(self, *args, ok=True):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = harness.cli(["--db", str(self.db), *map(str, args)])
        if ok:
            self.assertEqual(code, 0, err.getvalue())
        else:
            self.assertNotEqual(code, 0)
        return out.getvalue(), err.getvalue()

    def make(self, name, lineage, document, *, parent=None, version="0.0.1",
             updated="2026-09-25T00:00:00Z", body="# Title\nText\n"):
        path = self.root / name
        data = {"category_id": "design", "lineage_id": lineage, "document_id": document,
                "parent_lineage_id": parent, "abstract": "Read for a design decision",
                "version": version, "created_at": "2026-09-24T00:00:00Z",
                "updated_at": updated, "tags": ["역사"]}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(harness.encode_markdown(data, body))
        return path

    def test_legacy_idempotent_exact_body_and_null_dates(self):
        path = self.root / "plan" / "strange.md"
        path.parent.mkdir()
        raw = b"---\nnot: [valid YAML\n---\nOriginal body\n"
        path.write_bytes(raw)
        first, _ = self.command("import", "--legacy", path)
        second, _ = self.command("import", "--legacy", path)
        self.assertIn('"status": "imported"', first)
        self.assertIn('"status": "unchanged"', second)
        self.assertIn('"finalization": "retain"', first)
        self.assertIn('"canon_document_id": null', first)
        con = harness.open_db(self.db)
        row = con.execute("SELECT body,updated_at,canon,source_hash FROM documents").fetchone()
        self.assertEqual(row["body"].encode(), raw)
        self.assertIsNone(row["updated_at"])
        self.assertEqual(row["canon"], 0)
        self.assertEqual(row["source_hash"], harness.digest(raw))
        con.close()

    def test_canon_unique_candidate_and_rollback(self):
        old = self.make("doc.md", "L", "old")
        self.command("import", old)
        self.command("finalize", "L", "--action", "adopt", "--document-id", "old",
                     "--expected-current", "none")
        newer = self.make("draft.md", "L", "new", version="0.0.2",
                          updated="2026-09-25T02:00:00Z")
        imported, _ = self.command("import", newer)
        self.assertIn('"canon_document_id": "old"', imported)
        self.assertIn('"document_canon": false', imported)
        candidates, _ = self.command("candidates")
        self.assertIn('"document_id": "new"', candidates)
        _, error = self.command("finalize", "L", "--action", "adopt", "--document-id", "absent",
                                "--expected-current", "old", ok=False)
        self.assertIn("target document does not exist", error)
        con = harness.open_db(self.db)
        self.assertEqual(harness.current(con, "L")["document_id"], "old")
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("UPDATE documents SET canon=1 WHERE document_id='new'")
        con.rollback(); con.close()
        self.command("finalize", "L", "--action", "adopt", "--document-id", "new",
                     "--expected-current", "old")
        self.command("finalize", "L", "--action", "adopt", "--document-id", "new",
                     "--expected-current", "new")
        con = harness.open_db(self.db)
        self.assertEqual(harness.current(con, "L")["document_id"], "new")
        self.assertEqual(con.execute("SELECT count(*) FROM selection_log").fetchone()[0], 2)
        con.close()

    def test_parent_and_separate_lineages(self):
        child = self.make("child.md", "child", "child-a", parent="parent")
        self.command("import", child, ok=False)
        parent = self.make("parent.md", "parent", "parent-a")
        self.command("import", parent)
        self.command("finalize", "parent", "--action", "adopt", "--document-id", "parent-a",
                     "--expected-current", "none")
        self.command("import", child)
        self.command("finalize", "child", "--action", "adopt", "--document-id", "child-a",
                     "--expected-current", "none")
        con = harness.open_db(self.db)
        self.assertEqual(con.execute("SELECT count(*) FROM documents WHERE canon=1").fetchone()[0], 2)
        con.close()

    def test_backup_restore_and_search(self):
        path = self.make("a.md", "A", "a")
        self.command("import", path)
        self.command("finalize", "A", "--action", "adopt", "--document-id", "a",
                     "--expected-current", "none")
        listing, _ = self.command("list", "--tag", "역사")
        self.assertIn('"document_id": "a"', listing)
        search, _ = self.command("search", "Text")
        self.assertIn('"document_id": "a"', search)
        backup = self.root / "backup.sqlite3"
        self.command("backup", backup)
        restored = self.root / "restored.sqlite3"
        self.command_with_db(restored, "restore", backup)
        self.command_with_db(restored, "verify")
        con = harness.open_db(restored)
        self.assertEqual(harness.current(con, "A")["document_id"], "a")
        con.close()

    def test_revise_modified_body_and_restore_on_failure(self):
        path = self.make("draft.md", "L", "first")
        self.command("import", path)
        changed = path.read_text().replace("Text", "Edited body")
        path.write_text(changed)
        self.command("revise", path, "--bump", "patch")
        con = harness.open_db(self.db)
        editions = con.execute("SELECT document_id,version,body FROM documents WHERE lineage_id='L' ORDER BY version").fetchall()
        self.assertEqual([row["version"] for row in editions], ["0.0.1", "0.0.2"])
        self.assertIn("Text", editions[0]["body"])
        self.assertIn("Edited body", editions[1]["body"])
        con.close()

        # Make the current source point at the old edition, then force a duplicate version.
        path = self.make("draft.md", "L", "first")
        original = path.read_bytes()
        self.command("revise", path, "--bump", "patch", ok=False)
        self.assertEqual(path.read_bytes(), original)
        con = harness.open_db(self.db)
        self.assertEqual(con.execute("SELECT count(*) FROM documents WHERE lineage_id='L'").fetchone()[0], 2)
        con.close()

    def test_withdraw_and_child_guard(self):
        parent = self.make("p.md", "P", "p")
        child = self.make("c.md", "C", "c", parent="P")
        self.command("import", parent)
        self.command("finalize", "P", "--action", "adopt", "--document-id", "p", "--expected-current", "none")
        self.command("import", child)
        self.command("finalize", "C", "--action", "adopt", "--document-id", "c", "--expected-current", "none")
        self.command("finalize", "P", "--action", "withdraw", "--expected-current", "p", ok=False)
        con = harness.open_db(self.db)
        self.assertEqual(harness.current(con, "P")["document_id"], "p")
        con.close()
        self.command("finalize", "C", "--action", "withdraw", "--expected-current", "c")
        self.command("finalize", "P", "--action", "withdraw", "--expected-current", "p")
        no_canon, _ = self.command("no-canon")
        self.assertIn('"P"', no_canon)
        self.assertIn('"C"', no_canon)

    def test_manage_legacy_preserves_lineage_and_canon(self):
        path = self.root / "old.md"
        path.write_text("# Legacy\nOriginal\n")
        self.command("import", "--legacy", path)
        con = harness.open_db(self.db)
        legacy = con.execute("SELECT document_id,lineage_id FROM documents").fetchone()
        old_id, lineage = legacy["document_id"], legacy["lineage_id"]
        con.close()
        self.command("finalize", lineage, "--action", "adopt", "--document-id", old_id,
                     "--expected-current", "none")
        path.write_text("# Legacy\nEdited before management\n")
        output, _ = self.command("manage", path, "--category", "notes", "--abstract", "Read this note")
        self.assertIn('"lineage_id": "'+lineage+'"', output)
        self.assertIn('"canon_document_id": "'+old_id+'"', output)
        self.assertIn('"document_canon": false', output)
        con = harness.open_db(self.db)
        old = con.execute("SELECT body,canon FROM documents WHERE document_id=?", (old_id,)).fetchone()
        self.assertEqual(old["body"], "# Legacy\nOriginal\n")
        self.assertEqual(old["canon"], 1)
        self.assertEqual(con.execute("SELECT count(*) FROM documents WHERE lineage_id=?", (lineage,)).fetchone()[0], 2)
        con.close()

    def command_with_db(self, db, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = harness.cli(["--db", str(db), *map(str, args)])
        self.assertEqual(code, 0, err.getvalue())


if __name__ == "__main__":
    unittest.main()
