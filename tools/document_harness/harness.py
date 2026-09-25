#!/usr/bin/env python3
"""Small local document lifecycle CLI. The SQLite database is its own canon store."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
import uuid
from datetime import datetime, timezone

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data/document_harness/documents.sqlite3"
SCHEMA_VERSION = 1
FIELDS = (
    "category_id", "lineage_id", "document_id", "parent_lineage_id", "abstract",
    "version", "created_at", "updated_at", "tags",
)
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY NOT NULL,
    lineage_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    parent_lineage_id TEXT,
    version TEXT,
    created_at TEXT,
    updated_at TEXT,
    abstract TEXT NOT NULL,
    title TEXT NOT NULL,
    tags BLOB NOT NULL CHECK(json_valid(tags, 8) = 1 AND json_type(tags) = 'array'),
    body TEXT NOT NULL,
    source_path TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    observed_commit_id TEXT,
    legacy INTEGER NOT NULL DEFAULT 0 CHECK(legacy IN (0,1)),
    canon INTEGER NOT NULL DEFAULT 0 CHECK(canon IN (0,1)),
    imported_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS documents_one_canon_per_lineage
    ON documents(lineage_id) WHERE canon = 1;
CREATE INDEX IF NOT EXISTS documents_noncanon_by_lineage_date
    ON documents(lineage_id, updated_at) WHERE canon = 0;
CREATE INDEX IF NOT EXISTS documents_category ON documents(category_id);
CREATE INDEX IF NOT EXISTS documents_source ON documents(source_path);
CREATE TABLE IF NOT EXISTS selection_log (
    id INTEGER PRIMARY KEY,
    lineage_id TEXT NOT NULL,
    previous_document_id TEXT,
    selected_document_id TEXT,
    action TEXT NOT NULL CHECK(action IN ('adopt','retain','withdraw')),
    message TEXT NOT NULL,
    observed_commit_id TEXT,
    recorded_at TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    document_id UNINDEXED, title, body, tokenize='unicode61'
);
"""


class HarnessError(Exception):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def observed_head() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def source_path(path: Path) -> str:
    absolute = path.resolve()
    if not absolute.is_relative_to(ROOT):
        raise HarnessError("source must be inside the project")
    return absolute.relative_to(ROOT).as_posix()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def normalize_tags(value: object) -> list[str]:
    if not isinstance(value, list):
        raise HarnessError("tags must be a list")
    result = []
    for item in value:
        if not isinstance(item, str):
            raise HarnessError("each tag must be a string")
        tag = unicodedata.normalize("NFC", item.strip())
        if tag and tag not in result:
            result.append(tag)
    return result


def check_abstract(value: str) -> str:
    if not isinstance(value, str):
        raise HarnessError("abstract must be a string")
    value = unicodedata.normalize("NFC", value.strip())
    if not value or len(value) > 300:
        raise HarnessError("abstract must contain 1–300 Unicode characters")
    return value


def check_time(value: object, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.endswith("Z"):
        raise HarnessError(f"{name} must be an ISO 8601 UTC string or null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HarnessError(f"invalid {name}") from exc
    if parsed.utcoffset().total_seconds() != 0:
        raise HarnessError(f"{name} must be UTC")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def open_db(path: Path, *, create: bool = False) -> sqlite3.Connection:
    if not create and not path.is_file():
        raise HarnessError(f"database does not exist: {path}; run init")
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 10000")
    if not create:
        try:
            version = con.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        except sqlite3.DatabaseError as exc:
            con.close()
            raise HarnessError("invalid document harness database") from exc
        if not version or version[0] != str(SCHEMA_VERSION):
            con.close()
            raise HarnessError("unsupported document harness schema")
    return con


def init_db(path: Path) -> dict:
    if path.exists():
        raise HarnessError(f"database already exists: {path}")
    if sqlite3.sqlite_version_info < (3, 45, 0):
        raise HarnessError("SQLite 3.45+ JSONB support is required")
    path.parent.mkdir(parents=True, exist_ok=True)
    con = open_db(path, create=True)
    try:
        con.executescript(SCHEMA)
        con.execute("INSERT INTO meta VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))
        con.commit()
    except Exception:
        con.close()
        path.unlink(missing_ok=True)
        raise
    con.close()
    return {"database": str(path), "schema_version": SCHEMA_VERSION}


def parse_markdown(raw: bytes) -> tuple[dict, str]:
    text = raw.decode("utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not match:
        raise HarnessError("managed document requires YAML front matter")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        raise HarnessError("front matter must be a mapping")
    return data, text[match.end():]


def encode_markdown(data: dict, body: str) -> bytes:
    header = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    return ("---\n" + header + "---\n" + body).encode("utf-8")


def validate_metadata(data: dict) -> dict:
    missing = [key for key in FIELDS if key not in data]
    if missing:
        raise HarnessError("missing front matter: " + ", ".join(missing))
    for key in ("category_id", "lineage_id", "document_id"):
        if not isinstance(data[key], str) or not data[key].strip():
            raise HarnessError(f"{key} must be a non-empty string")
    if data["parent_lineage_id"] is not None and not isinstance(data["parent_lineage_id"], str):
        raise HarnessError("parent_lineage_id must be a string or null")
    if data["parent_lineage_id"] == data["lineage_id"]:
        raise HarnessError("a document cannot parent itself")
    if not isinstance(data["version"], str) or not re.fullmatch(r"\d+\.\d+\.\d+", data["version"]):
        raise HarnessError("version must be MAJOR.MINOR.PATCH")
    data = dict(data)
    data["abstract"] = check_abstract(data["abstract"])
    data["created_at"] = check_time(data["created_at"], "created_at")
    data["updated_at"] = check_time(data["updated_at"], "updated_at")
    if data["created_at"] and data["updated_at"] and data["created_at"] > data["updated_at"]:
        raise HarnessError("created_at is later than updated_at")
    data["tags"] = normalize_tags(data["tags"])
    return data


def current(con: sqlite3.Connection, lineage: str) -> sqlite3.Row | None:
    return con.execute(
        "SELECT * FROM documents WHERE lineage_id=? AND canon=1", (lineage,)
    ).fetchone()


def assert_parent(con: sqlite3.Connection, parent: str | None, lineage: str) -> None:
    if parent is None:
        return
    if not current(con, parent):
        raise HarnessError(f"parent lineage has no canon document: {parent}")
    seen = {lineage}
    cursor = parent
    while cursor:
        if cursor in seen:
            raise HarnessError("parent lineage cycle")
        seen.add(cursor)
        row = current(con, cursor)
        cursor = row["parent_lineage_id"] if row else None


def record(con: sqlite3.Connection, path: Path, *, legacy: bool = False,
           category: str | None = None) -> dict:
    raw = path.read_bytes()
    spath = source_path(path)
    content_hash = digest(raw)
    if legacy:
        existing = con.execute(
            "SELECT * FROM documents WHERE source_path=? AND legacy=1", (spath,)
        ).fetchall()
        if existing:
            if existing[0]["source_hash"] != content_hash:
                raise HarnessError(f"legacy source changed; revise explicitly: {spath}")
            return {"document_id": existing[0]["document_id"], "lineage_id": existing[0]["lineage_id"], "status": "unchanged"}
        lineage = "legacy-" + str(uuid.uuid5(uuid.NAMESPACE_URL, "novel/" + spath))
        data = {
            "category_id": category or path.parent.name,
            "lineage_id": lineage,
            "document_id": "doc-" + str(uuid.uuid5(uuid.NAMESPACE_URL, "novel/" + spath + "/" + content_hash)),
            "parent_lineage_id": None,
            "version": None,
            "created_at": None,
            "updated_at": None,
            "abstract": check_abstract(path.stem[:300]),
            "tags": [],
        }
        body = raw.decode("utf-8")
    else:
        data, body = parse_markdown(raw)
        data = validate_metadata(data)
        prior = con.execute("SELECT * FROM documents WHERE document_id=?", (data["document_id"],)).fetchone()
        if prior:
            if prior["source_hash"] != content_hash or prior["source_path"] != spath:
                raise HarnessError("document_id already identifies different content; create a revision")
            return {"document_id": prior["document_id"], "lineage_id": prior["lineage_id"], "status": "unchanged"}
        previous_rows = con.execute(
            "SELECT version, created_at FROM documents WHERE lineage_id=? AND version IS NOT NULL",
            (data["lineage_id"],),
        ).fetchall()
        if previous_rows:
            previous = max(previous_rows, key=lambda row: tuple(map(int, row["version"].split("."))))
            if tuple(map(int, data["version"].split("."))) <= tuple(map(int, previous["version"].split("."))):
                raise HarnessError("new revision version must increase")
            if previous["created_at"] != data["created_at"]:
                raise HarnessError("created_at must stay fixed in a lineage")
        elif data["version"] != "0.0.1":
            raise HarnessError("new managed lineage must start at version 0.0.1")
        assert_parent(con, data["parent_lineage_id"], data["lineage_id"])
    title = next((line.lstrip("# ").strip() for line in body.splitlines() if line.startswith("# ")), path.stem)
    con.execute(
        """INSERT INTO documents(document_id,lineage_id,category_id,parent_lineage_id,
           version,created_at,updated_at,abstract,title,tags,body,source_path,source_hash,
           observed_commit_id,legacy,imported_at)
           VALUES (?,?,?,?,?,?,?,?,?,jsonb(?),?,?,?,?,?,?)""",
        (data["document_id"], data["lineage_id"], data["category_id"], data["parent_lineage_id"],
         data["version"], data["created_at"], data["updated_at"], data["abstract"], title,
         json.dumps(data["tags"], ensure_ascii=False), body, spath, content_hash, observed_head(),
         int(legacy), now()),
    )
    con.execute("INSERT INTO documents_fts(document_id,title,body) VALUES (?,?,?)",
                (data["document_id"], title, body))
    # Every ingest finishes with an explicit retain decision and a DB re-read.
    finalize(con, data["lineage_id"], None, "retain", "Imported without automatic adoption", None)
    return {"document_id": data["document_id"], "lineage_id": data["lineage_id"], "status": "imported"}


def finalized_result(con: sqlite3.Connection, item: dict) -> dict:
    """Re-read committed selection and edition state for every ingested output."""
    selected = current(con, item["lineage_id"])
    document = con.execute(
        "SELECT canon FROM documents WHERE document_id=? AND lineage_id=?",
        (item["document_id"], item["lineage_id"]),
    ).fetchone()
    if document is None:
        raise HarnessError("post-commit document re-read failed")
    return {**item, "finalization": "retain", "canon_document_id": selected["document_id"] if selected else None,
            "document_canon": bool(document["canon"])}


def finalize(con: sqlite3.Connection, lineage: str, target: str | None,
             action: str, message: str, expected: str | None) -> dict:
    if action not in ("adopt", "retain", "withdraw"):
        raise HarnessError("action must be adopt, retain, or withdraw")
    previous = current(con, lineage)
    previous_id = previous["document_id"] if previous else None
    if action in ("adopt", "withdraw"):
        if expected != previous_id:
            raise HarnessError(f"current selection changed: expected {expected!r}, found {previous_id!r}")
        if action == "adopt":
            target_row = con.execute("SELECT * FROM documents WHERE document_id=?", (target,)).fetchone()
            if not target_row or target_row["lineage_id"] != lineage:
                raise HarnessError("target document does not exist in the requested lineage")
            assert_parent(con, target_row["parent_lineage_id"], lineage)
        elif previous_id:
            child = con.execute("SELECT document_id FROM documents WHERE parent_lineage_id=? AND canon=1 LIMIT 1", (lineage,)).fetchone()
            if child:
                raise HarnessError("cannot withdraw a parent with adopted children")
        if previous_id != target:
            if previous:
                count = con.execute("UPDATE documents SET canon=0 WHERE document_id=? AND canon=1", (previous_id,)).rowcount
                if count != 1:
                    raise HarnessError("previous selection update affected wrong row count")
            if action == "adopt":
                count = con.execute("UPDATE documents SET canon=1 WHERE document_id=? AND lineage_id=? AND canon=0", (target, lineage)).rowcount
                if count != 1:
                    raise HarnessError("target selection update affected wrong row count")
            con.execute("INSERT INTO selection_log(lineage_id,previous_document_id,selected_document_id,action,message,observed_commit_id,recorded_at) VALUES (?,?,?,?,?,?,?)",
                        (lineage, previous_id, target, action, message, observed_head(), now()))
    selected = current(con, lineage)
    selected_id = selected["document_id"] if selected else None
    desired = target if action == "adopt" else (None if action == "withdraw" else previous_id)
    if selected_id != desired:
        raise HarnessError("selection verification failed")
    return {"lineage_id": lineage, "canon_document_id": selected_id, "action": action,
            "status": "unchanged" if previous_id == selected_id else "changed"}


def rows_json(rows) -> list[dict]:
    result = []
    for row in rows:
        item = dict(row)
        if "tags" in item:
            item["tags"] = json.loads(sqlite_json(item["tags"]))
        result.append(item)
    return result


def sqlite_json(value: bytes) -> str:
    con = sqlite3.connect(":memory:")
    try:
        return con.execute("SELECT json(?)", (value,)).fetchone()[0]
    finally:
        con.close()


def bump(version: str, level: str) -> str:
    major, minor, patch = map(int, version.split("."))
    if level == "major":
        return f"{major+1}.0.0"
    if level == "minor":
        return f"{major}.{minor+1}.0"
    return f"{major}.{minor}.{patch+1}"


def print_json(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def cli(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    create = sub.add_parser("create")
    create.add_argument("path", type=Path)
    create.add_argument("--category", required=True)
    create.add_argument("--parent-lineage")
    create.add_argument("--abstract", required=True)
    create.add_argument("--tag", action="append", default=[])
    create.add_argument("--title", required=True)
    revise = sub.add_parser("revise")
    revise.add_argument("path", type=Path)
    revise.add_argument("--bump", choices=("patch", "minor", "major"), required=True)
    manage = sub.add_parser("manage")
    manage.add_argument("path", type=Path)
    manage.add_argument("--category", required=True)
    manage.add_argument("--abstract", required=True)
    manage.add_argument("--tag", action="append", default=[])
    manage.add_argument("--parent-lineage")
    imp = sub.add_parser("import")
    imp.add_argument("paths", nargs="+", type=Path)
    imp.add_argument("--legacy", action="store_true")
    imp.add_argument("--category")
    listing = sub.add_parser("list")
    listing.add_argument("--all", action="store_true")
    listing.add_argument("--category")
    listing.add_argument("--lineage")
    listing.add_argument("--tag")
    listing.add_argument("--history", action="store_true")
    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--all", action="store_true")
    search.add_argument("--category")
    search.add_argument("--lineage")
    show = sub.add_parser("show")
    show.add_argument("document_id")
    show.add_argument("--body", action="store_true")
    diff = sub.add_parser("diff")
    diff.add_argument("old_id")
    diff.add_argument("new_id")
    sub.add_parser("candidates")
    sub.add_parser("no-canon")
    sub.add_parser("unknown-date")
    fin = sub.add_parser("finalize")
    fin.add_argument("lineage_id")
    fin.add_argument("--action", choices=("adopt", "retain", "withdraw"), required=True)
    fin.add_argument("--document-id")
    fin.add_argument("--expected-current", help="ID or literal 'none'; required for adopt")
    fin.add_argument("--message", default="Manual document selection")
    sub.add_parser("health")
    sub.add_parser("verify")
    backup = sub.add_parser("backup")
    backup.add_argument("destination", type=Path)
    restore = sub.add_parser("restore")
    restore.add_argument("backup", type=Path)
    args = p.parse_args(argv)
    db = args.db.resolve()
    try:
        if args.command == "init":
            print_json(init_db(db)); return 0
        if args.command == "restore":
            if db.exists():
                raise HarnessError("restore destination already exists")
            source = open_db(args.backup.resolve())
            if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise HarnessError("backup integrity check failed")
            db.parent.mkdir(parents=True, exist_ok=True)
            target = sqlite3.connect(db)
            source.backup(target)
            target.close(); source.close()
            print_json({"restored": str(db)}); return 0
        con = open_db(db)
        try:
            if args.command == "create":
                path = args.path.resolve()
                source_path(path)
                if path.exists():
                    raise HarnessError("create refuses to overwrite an existing path")
                assert_parent(con, args.parent_lineage, "new")
                stamp = now()
                data = {"category_id": args.category, "lineage_id": "lin-"+str(uuid.uuid4()),
                        "document_id": "doc-"+str(uuid.uuid4()), "parent_lineage_id": args.parent_lineage,
                        "abstract": check_abstract(args.abstract), "version": "0.0.1", "created_at": stamp,
                        "updated_at": stamp, "tags": normalize_tags(args.tag)}
                raw = encode_markdown(data, "# "+args.title+"\n")
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("xb") as handle:
                    handle.write(raw)
                try:
                    con.execute("BEGIN IMMEDIATE")
                    result = record(con, path)
                    con.commit()
                except Exception:
                    con.rollback()
                    path.unlink()
                    raise
                print_json(finalized_result(con, result)); return 0
            if args.command == "revise":
                path = args.path.resolve()
                spath = source_path(path)
                original = path.read_bytes()
                data, body = parse_markdown(original)
                data = validate_metadata(data)
                prior = con.execute("SELECT * FROM documents WHERE document_id=?", (data["document_id"],)).fetchone()
                if not prior or prior["source_path"] != spath or prior["lineage_id"] != data["lineage_id"] or prior["version"] != data["version"]:
                    raise HarnessError("revise requires an imported document_id, lineage, version, and source path")
                data["document_id"] = "doc-"+str(uuid.uuid4())
                data["version"] = bump(data["version"], args.bump)
                data["updated_at"] = now()
                updated = encode_markdown(data, body)
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                    handle.write(updated); temp = Path(handle.name)
                os.replace(temp, path)
                try:
                    con.execute("BEGIN IMMEDIATE")
                    result = record(con, path)
                    con.commit()
                except Exception:
                    con.rollback()
                    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                        handle.write(original); restore = Path(handle.name)
                    os.replace(restore, path)
                    raise
                print_json(finalized_result(con, result)); return 0
            if args.command == "manage":
                path = args.path.resolve()
                spath = source_path(path)
                original = path.read_bytes()
                if path.suffix.lower() != ".md":
                    raise HarnessError("manage requires a Markdown file")
                if con.execute("SELECT 1 FROM documents WHERE source_path=? AND legacy=0 LIMIT 1", (spath,)).fetchone():
                    raise HarnessError("this path is already managed; use revise")
                legacy = con.execute("SELECT * FROM documents WHERE source_path=? AND legacy=1", (spath,)).fetchone()
                lineage = legacy["lineage_id"] if legacy else "lin-"+str(uuid.uuid4())
                parent = args.parent_lineage if args.parent_lineage is not None else (legacy["parent_lineage_id"] if legacy else None)
                assert_parent(con, parent, lineage)
                stamp = now()
                data = {"category_id": args.category, "lineage_id": lineage,
                        "document_id": "doc-"+str(uuid.uuid4()), "parent_lineage_id": parent,
                        "abstract": check_abstract(args.abstract), "version": "0.0.1",
                        "created_at": legacy["created_at"] if legacy else None,
                        "updated_at": stamp, "tags": normalize_tags(args.tag)}
                updated = encode_markdown(data, original.decode("utf-8"))
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                    handle.write(updated); temp = Path(handle.name)
                os.replace(temp, path)
                try:
                    con.execute("BEGIN IMMEDIATE")
                    result = record(con, path)
                    con.commit()
                except Exception:
                    con.rollback()
                    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                        handle.write(original); restore = Path(handle.name)
                    os.replace(restore, path)
                    raise
                print_json(finalized_result(con, result)); return 0
            if args.command == "import":
                if args.category and not args.legacy:
                    raise HarnessError("--category applies only to legacy imports")
                results = []
                con.execute("BEGIN IMMEDIATE")
                for path in args.paths:
                    if path.suffix.lower() != ".md":
                        raise HarnessError("only Markdown files can be imported")
                    results.append(record(con, path.resolve(), legacy=args.legacy, category=args.category))
                con.commit()
                print_json([finalized_result(con, item) for item in results]); return 0
            if args.command in ("list", "search"):
                where = [] if args.all or (args.command == "list" and args.history) else ["d.canon=1"]
                params = []
                for key in ("category", "lineage"):
                    value = getattr(args, key, None)
                    if value:
                        where.append(f"d.{key+'_id' if key=='category' else 'lineage_id'}=?"); params.append(value)
                if args.command == "list" and args.tag:
                    where.append("EXISTS (SELECT 1 FROM json_each(d.tags) AS tag WHERE tag.value=? AND tag.type='text')")
                    params.append(args.tag)
                if args.command == "search":
                    where.append("(d.title LIKE ? OR d.abstract LIKE ? OR d.body LIKE ? OR EXISTS (SELECT 1 FROM documents_fts WHERE documents_fts.document_id=d.document_id AND documents_fts MATCH ?))")
                    escaped = args.query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                    where[-1] = where[-1].replace("LIKE ?", "LIKE ? ESCAPE '\\'")
                    params.extend(["%"+escaped+"%"]*3 + ['"'+args.query.replace('"','""')+'"'])
                sql = "SELECT d.document_id,d.lineage_id,d.category_id,d.version,d.updated_at,d.abstract,d.title,d.canon,d.source_path,json(d.tags) AS tags FROM documents d"
                if where:
                    sql += " WHERE " + " AND ".join(where)
                sql += " ORDER BY d.category_id,d.lineage_id,d.updated_at,d.document_id"
                result = [dict(r) for r in con.execute(sql, params).fetchall()]
                for row in result: row["tags"] = json.loads(row["tags"])
                print_json(result); return 0
            if args.command == "show":
                row = con.execute("SELECT document_id,lineage_id,category_id,parent_lineage_id,version,created_at,updated_at,abstract,title,source_path,source_hash,observed_commit_id,legacy,canon,json(tags) AS tags,body FROM documents WHERE document_id=?", (args.document_id,)).fetchone()
                if not row: raise HarnessError("document not found")
                result = dict(row); result["tags"] = json.loads(result["tags"])
                if not args.body: result.pop("body")
                print_json(result); return 0
            if args.command == "diff":
                rows = [con.execute("SELECT body,lineage_id FROM documents WHERE document_id=?", (ident,)).fetchone() for ident in (args.old_id,args.new_id)]
                if not all(rows): raise HarnessError("one or both documents not found")
                if rows[0]["lineage_id"] != rows[1]["lineage_id"]: raise HarnessError("diff requires one lineage")
                print("".join(difflib.unified_diff(rows[0]["body"].splitlines(True), rows[1]["body"].splitlines(True), fromfile=args.old_id, tofile=args.new_id)), end="")
                return 0
            if args.command == "candidates":
                rows = con.execute("""SELECT n.document_id,n.lineage_id,n.version,n.updated_at,n.abstract,
                    c.document_id AS current_id,c.version AS current_version,c.updated_at AS current_updated_at
                    FROM documents n JOIN documents c ON c.lineage_id=n.lineage_id AND c.canon=1
                    WHERE n.canon=0 AND n.updated_at IS NOT NULL AND c.updated_at IS NOT NULL
                      AND n.updated_at>c.updated_at ORDER BY n.lineage_id,n.updated_at""").fetchall()
                print_json([dict(r) for r in rows]); return 0
            if args.command == "no-canon":
                rows = con.execute("SELECT DISTINCT d.lineage_id FROM documents d WHERE NOT EXISTS (SELECT 1 FROM documents c WHERE c.lineage_id=d.lineage_id AND c.canon=1) ORDER BY d.lineage_id").fetchall()
                print_json([r[0] for r in rows]); return 0
            if args.command == "unknown-date":
                rows = con.execute("SELECT document_id,lineage_id,canon FROM documents WHERE updated_at IS NULL ORDER BY lineage_id,document_id").fetchall()
                print_json([dict(r) for r in rows]); return 0
            if args.command == "finalize":
                if args.action == "adopt" and not args.document_id:
                    raise HarnessError("adopt requires --document-id")
                if args.action in ("adopt", "withdraw") and args.expected_current is None:
                    raise HarnessError("adopt/withdraw requires --expected-current (ID or none)")
                if args.action == "withdraw" and args.document_id:
                    raise HarnessError("withdraw does not accept --document-id")
                expected = None if args.expected_current == "none" else args.expected_current
                con.execute("BEGIN IMMEDIATE")
                result = finalize(con,args.lineage_id,args.document_id,args.action,args.message,expected)
                con.commit()
                actual = current(con,args.lineage_id)
                if (actual["document_id"] if actual else None) != result["canon_document_id"]:
                    raise HarnessError("post-commit selection re-read failed")
                print_json(result); return 0
            if args.command in ("health", "verify"):
                integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
                duplicate = con.execute("SELECT lineage_id FROM documents WHERE canon=1 GROUP BY lineage_id HAVING count(*)>1").fetchall()
                fts_count = con.execute("SELECT count(*) FROM documents_fts").fetchone()[0]
                document_count = con.execute("SELECT count(*) FROM documents").fetchone()[0]
                json_bad = con.execute("SELECT count(*) FROM documents WHERE json_valid(tags,8)=0").fetchone()[0]
                result = {"integrity":integrity,"documents":document_count,"canon":con.execute("SELECT count(*) FROM documents WHERE canon=1").fetchone()[0],
                          "duplicate_canon_lineages":len(duplicate),"invalid_tags":json_bad,"fts_rows":fts_count,
                          "ok":integrity=="ok" and not duplicate and not json_bad and fts_count==document_count}
                print_json(result)
                return 0 if result["ok"] else 1
            if args.command == "backup":
                destination = args.destination.resolve()
                if destination.exists(): raise HarnessError("backup destination already exists")
                destination.parent.mkdir(parents=True, exist_ok=True)
                target = sqlite3.connect(destination)
                con.backup(target)
                target.close()
                print_json({"backup":str(destination)}); return 0
            raise HarnessError("unknown command")
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
    except (HarnessError,sqlite3.Error,UnicodeError,OSError,yaml.YAMLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(cli())
