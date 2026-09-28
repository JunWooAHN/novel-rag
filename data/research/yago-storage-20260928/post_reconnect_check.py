"""Read-only, metadata-only check after reconnecting to H200 Storage."""

import json
import os
from pathlib import Path
import stat
import subprocess
from datetime import datetime, timezone


base = Path("/home/work/novel-toy-tune")
root = base / "sources/original/yago/4.6"
mount = json.loads(subprocess.check_output(
    ["findmnt", "-J", "-T", str(root), "-o", "TARGET,SOURCE,FSTYPE,OPTIONS"], text=True
))["filesystems"][0]
manifest = json.loads((root / "manifest.json").read_text())
expected_zips = set(manifest["files"])
actual_zips = {p.name for p in (root / "zip").iterdir() if p.suffix == ".zip"}
auxiliary_zip_entries = sorted(p.name for p in (root / "zip").iterdir() if p.suffix != ".zip")
expected_members = set()
actual_members = set()
problems = []
zip_bytes = 0
member_bytes = 0

if mount["target"] != str(base) or mount["fstype"] != "nfs" or "rw" not in mount["options"].split(","):
    problems.append("unexpected Storage mount")
if manifest["status"] != "complete" or len(expected_zips) != 12:
    problems.append("incomplete manifest")
if actual_zips != expected_zips:
    problems.append("ZIP filename set differs")

for name, item in manifest["files"].items():
    path = root / "zip" / name
    if not path.is_file() or path.is_symlink():
        problems.append(f"ZIP missing or symlink: {name}")
        continue
    info = path.stat()
    zip_bytes += info.st_size
    if info.st_size != item["compressed_bytes"] or stat.S_IMODE(info.st_mode) != 0o444:
        problems.append(f"ZIP size/mode differs: {name}")
    for entry in item["entries"]:
        member = root / "extracted" / name.removesuffix(".zip") / entry["path"]
        expected_members.add(str(member.relative_to(root / "extracted")))
        if not member.is_file() or member.is_symlink():
            problems.append(f"member missing or symlink: {member.name}")
            continue
        info = member.stat()
        member_bytes += info.st_size
        if info.st_size != entry["bytes"] or stat.S_IMODE(info.st_mode) != 0o444:
            problems.append(f"member size/mode differs: {member.name}")

for parent, dirs, files in os.walk(root / "extracted", followlinks=False):
    if any((Path(parent) / directory).is_symlink() for directory in dirs):
        problems.append(f"symlink directory under {parent}")
    for filename in files:
        path = Path(parent) / filename
        actual_members.add(str(path.relative_to(root / "extracted")))
if actual_members != expected_members:
    problems.append("extracted filename set differs")

marker = root / "ORIGINAL_UPSTREAM.txt"
if not marker.is_file() or "original" not in marker.read_text().lower():
    problems.append("original marker missing")

du = subprocess.check_output(["du", "-sb", str(root)], text=True).split()[0]
vfs = os.statvfs(base)
print(json.dumps({
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "mount": mount,
    "root": str(root),
    "manifest_status": manifest["status"],
    "manifest_completed_at": manifest.get("completed_at"),
    "zip_count": len(expected_zips),
    "zip_names": sorted(actual_zips),
    "auxiliary_zip_entries": auxiliary_zip_entries,
    "extracted_file_count": len(actual_members),
    "zip_bytes": zip_bytes,
    "extracted_bytes": member_bytes,
    "du_bytes": int(du),
    "storage_free_bytes": vfs.f_bavail * vfs.f_frsize,
    "completed_file_mode": "0444",
    "original_marker_present": marker.is_file(),
    "problems": problems,
}, ensure_ascii=False, indent=2))
if problems:
    raise SystemExit(1)
