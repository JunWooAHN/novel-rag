import contextlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

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
             updated="2026-09-25T00:00:00Z", body="# Title\nText\n",
             created="2026-09-24T00:00:00Z", canon=False):
        path = self.root / name
        data = {"category_id": "design", "lineage_id": lineage, "document_id": document,
                "parent_lineage_id": parent, "abstract": "Read for a design decision",
                "version": version, "created_at": created,
                "updated_at": updated, "tags": ["역사"], "canon": canon}
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

    def test_created_at_first_content_and_blank_then_content(self):
        created, _ = self.command("create", self.root / "new.md", "--category", "design",
                                  "--title", "New", "--abstract", "A new document")
        made = json.loads(created)
        data, body = harness.parse_markdown((self.root / "new.md").read_bytes())
        self.assertEqual(body, "# New\n")
        self.assertEqual(data["created_at"], data["updated_at"])
        self.assertIs(data["canon"], False)
        self.assertEqual(made["document_canon"], False)

        blank = self.root / "blank.md"
        blank.write_text(" \n")
        output, _ = self.command("manage", blank, "--category", "design", "--abstract", "Blank draft")
        lineage = json.loads(output)["lineage_id"]
        data, _ = harness.parse_markdown(blank.read_bytes())
        self.assertIsNone(data["created_at"])
        blank.write_bytes(blank.read_bytes() + b"# First content\n")
        self.command("revise", blank, "--bump", "patch")
        first_date = harness.parse_markdown(blank.read_bytes())[0]["created_at"]
        self.assertIsNotNone(first_date)
        self.command("revise", blank, "--bump", "patch")
        con = harness.open_db(self.db)
        rows = con.execute("SELECT created_at,updated_at FROM documents WHERE lineage_id=? ORDER BY version", (lineage,)).fetchall()
        self.assertIsNone(rows[0]["created_at"])
        self.assertEqual(rows[1]["created_at"], harness.check_time(first_date, "created_at"))
        self.assertEqual(rows[2]["created_at"], harness.check_time(first_date, "created_at"))
        con.close()

    def test_import_upgrade_missing_canon_and_created_then_reject_tampering(self):
        path = self.make("old-managed.md", "L", "first", created=None)
        raw = path.read_bytes().replace(b"canon: false\n", b"")
        path.write_bytes(raw)
        self.command("import", path)
        data, body = harness.parse_markdown(path.read_bytes())
        self.assertEqual(body, "# Title\nText\n")
        self.assertEqual(harness.check_time(data["created_at"], "created_at"), "2026-09-25T00:00:00.000000Z")
        self.assertIs(data["canon"], False)
        self.command("import", path)
        self.command("finalize", "L", "--action", "adopt", "--document-id", "first",
                     "--expected-current", "none")
        self.assertIs(harness.parse_markdown(path.read_bytes())[0]["canon"], True)
        path.write_bytes(harness.patch_display(path.read_bytes(), canon=False))
        _, err = self.command("import", path, ok=False)
        self.assertIn("canon mismatch", err)
        report = self.root / "canon-repair.json"
        self.command("sync-metadata", "--report", report)
        self.assertIs(harness.parse_markdown(path.read_bytes())[0]["canon"], True)
        self.assertEqual(json.loads(report.read_text())["mirrors"][0]["old_canon_display"], False)

    def test_shared_path_old_adoption_and_new_revision_mirror(self):
        path = self.make("same.md", "L", "old")
        self.command("import", path)
        self.command("finalize", "L", "--action", "adopt", "--document-id", "old",
                     "--expected-current", "none")
        path.write_bytes(path.read_bytes().replace(b"Text", b"Edited"))
        self.command("revise", path, "--bump", "patch")
        new_id = harness.parse_markdown(path.read_bytes())[0]["document_id"]
        self.assertIs(harness.parse_markdown(path.read_bytes())[0]["canon"], False)
        self.command("finalize", "L", "--action", "adopt", "--document-id", new_id,
                     "--expected-current", "old")
        self.assertIs(harness.parse_markdown(path.read_bytes())[0]["canon"], True)
        con = harness.open_db(self.db)
        self.assertEqual(con.execute("SELECT canon FROM documents WHERE document_id='old'").fetchone()[0], 0)
        self.assertEqual(con.execute("SELECT canon FROM documents WHERE document_id=?", (new_id,)).fetchone()[0], 1)
        self.assertEqual(con.execute("SELECT source_hash FROM documents WHERE document_id=?", (new_id,)).fetchone()[0], harness.digest(path.read_bytes()))
        con.close()
        self.command("finalize", "L", "--action", "adopt", "--document-id", "old",
                     "--expected-current", new_id)
        self.assertIs(harness.parse_markdown(path.read_bytes())[0]["canon"], False)

    def test_write_failure_rolls_back_selection_and_files(self):
        old = self.make("old.md", "L", "old")
        new = self.make("new.md", "L", "new", version="0.0.2")
        self.command("import", old)
        self.command("import", new)
        self.command("finalize", "L", "--action", "adopt", "--document-id", "old",
                     "--expected-current", "none")
        originals = {old: old.read_bytes(), new: new.read_bytes()}
        real_write = harness.write_bytes
        attempts = 0
        def fail_second(path, raw):
            nonlocal attempts
            attempts += 1
            if attempts == 2:
                raise OSError("injected file write failure")
            real_write(path, raw)
        with mock.patch.object(harness, "write_bytes", side_effect=fail_second):
            _, err = self.command("finalize", "L", "--action", "adopt", "--document-id", "new",
                                  "--expected-current", "old", ok=False)
        self.assertIn("injected file write failure", err)
        self.assertEqual(old.read_bytes(), originals[old])
        self.assertEqual(new.read_bytes(), originals[new])
        con = harness.open_db(self.db)
        self.assertEqual(harness.current(con, "L")["document_id"], "old")
        self.assertEqual(con.execute("SELECT count(*) FROM selection_log").fetchone()[0], 1)
        con.close()

    def test_sync_metadata_repairs_old_null_and_preserves_body(self):
        path = self.make("repair.md", "L", "old")
        self.command("import", path)
        path.write_bytes(path.read_bytes().replace(b"Text", b"Second"))
        self.command("revise", path, "--bump", "patch")
        latest_id = harness.parse_markdown(path.read_bytes())[0]["document_id"]
        before_body = harness.parse_markdown(path.read_bytes())[1]
        con = harness.open_db(self.db)
        old_hashes = {r["document_id"]: r["source_hash"] for r in con.execute("SELECT document_id,source_hash FROM documents WHERE lineage_id='L'")}
        con.execute("UPDATE documents SET created_at=NULL WHERE lineage_id='L'")
        con.commit(); con.close()
        path.write_bytes(harness.patch_display(path.read_bytes(), created_at=None, set_created=True))
        report = self.root / "repair-report.json"
        self.command("sync-metadata", "--report", report)
        record = json.loads(report.read_text())
        self.assertEqual(len(record["repaired"]), 2)
        self.assertEqual({r["old_source_hash"] for r in record["repaired"]}, set(old_hashes.values()))
        self.assertEqual(harness.parse_markdown(path.read_bytes())[1], before_body)
        con = harness.open_db(self.db)
        dates = {r[0] for r in con.execute("SELECT created_at FROM documents WHERE lineage_id='L'")}
        self.assertEqual(dates, {"2026-09-25T00:00:00.000000Z"})
        self.assertEqual(con.execute("SELECT source_hash FROM documents WHERE document_id=?", (latest_id,)).fetchone()[0], harness.digest(path.read_bytes()))
        con.close()
        second = self.root / "second-report.json"
        output, _ = self.command("sync-metadata", "--report", second)
        self.assertIn('"repaired": 0', output)
        verification, _ = self.command("verify", "--files")
        self.assertTrue(json.loads(verification)["ok"])

    def test_dirty_body_date_repair_preserves_edit_for_new_revision(self):
        path = self.make("dirty.md", "L", "old")
        self.command("import", path)
        con = harness.open_db(self.db)
        old_hash = con.execute("SELECT source_hash FROM documents WHERE document_id='old'").fetchone()[0]
        con.execute("UPDATE documents SET created_at=NULL WHERE document_id='old'")
        con.commit(); con.close()
        raw = harness.patch_display(path.read_bytes(), created_at=None, set_created=True)
        path.write_bytes(raw.replace(b"Text", b"Unregistered edit"))
        edited = path.read_bytes()
        report = self.root / "dirty-report.json"
        self.command("sync-metadata", "--report", report)
        self.assertEqual(path.read_bytes(), edited)
        self.assertIn("dirty.md", json.loads(report.read_text())["dirty_files_not_mirrored"][0])
        con = harness.open_db(self.db)
        self.assertEqual(con.execute("SELECT source_hash FROM documents WHERE document_id='old'").fetchone()[0], old_hash)
        con.close()
        self.command("revise", path, "--bump", "patch")
        new_data, new_body = harness.parse_markdown(path.read_bytes())
        self.assertIn("Unregistered edit", new_body)
        self.assertEqual(new_data["created_at"], "2026-09-25T00:00:00.000000Z")
        result, _ = self.command("verify", "--files")
        self.assertTrue(json.loads(result)["ok"])

    def test_manual_metadata_change_blocks_selection(self):
        path = self.make("tampered.md", "L", "one")
        self.command("import", path)
        original = path.read_bytes()
        path.write_bytes(original.replace(b"Read for a design decision", b"Changed by hand"))
        _, error = self.command("finalize", "L", "--action", "adopt", "--document-id", "one",
                                "--expected-current", "none", ok=False)
        self.assertIn("abstract mismatch", error)
        self.assertIn(b"Changed by hand", path.read_bytes())
        con = harness.open_db(self.db)
        self.assertIsNone(harness.current(con, "L"))
        con.close()

    def test_import_blank_successor_keeps_first_content_date(self):
        first = self.make("first.md", "L", "first")
        self.command("import", first)
        blank = self.make("blank-successor.md", "L", "blank", version="0.0.2",
                          body=" \n", created="2026-09-24T00:00:00Z")
        self.command("import", blank)
        con = harness.open_db(self.db)
        dates = {row[0] for row in con.execute("SELECT created_at FROM documents WHERE lineage_id='L'")}
        self.assertEqual(dates, {"2026-09-24T00:00:00.000000Z"})
        con.close()

    def test_sync_repairs_canon_even_when_date_anchor_unknown(self):
        path = self.make("unknown-date.md", "L", "first")
        self.command("import", path)
        con = harness.open_db(self.db)
        con.execute("UPDATE documents SET created_at=NULL,updated_at=NULL WHERE document_id='first'")
        con.commit(); con.close()
        raw = harness.patch_display(path.read_bytes(), created_at=None, set_created=True)
        raw = raw.replace(b"updated_at: '2026-09-25T00:00:00Z'", b"updated_at: null")
        path.write_bytes(harness.patch_display(raw, canon=True))
        report = self.root / "unknown-date-report.json"
        self.command("sync-metadata", "--report", report)
        result = json.loads(report.read_text())
        self.assertIn("no updated_at", result["skipped"][0]["reason"])
        self.assertIs(harness.parse_markdown(path.read_bytes())[0]["canon"], False)
        self.assertIsNone(harness.parse_markdown(path.read_bytes())[0]["created_at"])
        self.assertEqual(result["mirrors"][0]["old_canon_display"], True)

    def test_finalize_persists_mirror_hashes_for_adopt_and_retain(self):
        path = self.make("hashes.md", "L", "first")
        self.command("import", path)
        original_hash = harness.digest(path.read_bytes())
        self.command("finalize", "L", "--action", "adopt", "--document-id", "first",
                     "--expected-current", "none")
        con = harness.open_db(self.db)
        first_log = json.loads(con.execute("SELECT message FROM selection_log ORDER BY id DESC LIMIT 1").fetchone()[0])
        self.assertEqual(first_log["file_mirrors"][0]["old_source_hash"], original_hash)
        self.assertEqual(first_log["file_mirrors"][0]["new_source_hash"], harness.digest(path.read_bytes()))
        con.close()
        path.write_bytes(path.read_bytes().replace(b"canon: true\n", b""))
        self.command("finalize", "L", "--action", "retain")
        con = harness.open_db(self.db)
        row = con.execute("SELECT action,message FROM selection_log ORDER BY id DESC LIMIT 1").fetchone()
        self.assertEqual(row["action"], "retain")
        self.assertEqual(json.loads(row["message"])["file_mirrors"][0]["new_source_hash"], harness.digest(path.read_bytes()))
        con.close()

    def test_same_id_import_records_display_hash_change(self):
        path = self.make("format.md", "L", "first")
        self.command("import", path)
        before = harness.digest(path.read_bytes())
        path.write_bytes(path.read_bytes().replace(b"abstract: Read for a design decision",
                                                  b"abstract: 'Read for a design decision'"))
        self.command("import", path)
        con = harness.open_db(self.db)
        self.assertEqual(con.execute("SELECT count(*) FROM documents WHERE lineage_id='L'").fetchone()[0], 1)
        row = con.execute("SELECT action,message FROM selection_log ORDER BY id DESC LIMIT 1").fetchone()
        self.assertEqual(row["action"], "retain")
        mirror = json.loads(row["message"])["file_mirrors"][0]
        self.assertEqual(mirror["old_source_hash"], before)
        self.assertEqual(mirror["new_source_hash"], harness.digest(path.read_bytes()))
        con.close()

    def command_with_db(self, db, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = harness.cli(["--db", str(db), *map(str, args)])
        self.assertEqual(code, 0, err.getvalue())


if __name__ == "__main__":
    unittest.main()
