#!/usr/bin/env python3
"""
Chapter file path helpers.

This project has seen multiple chapter filename conventions:
1) Legacy flat layout: chapters/chapter_0007.md
2) Volume layout:    chapters/vol_1/chapter_007-title.md

To keep scripts robust, always resolve chapter files via these helpers instead of hardcoding a format.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


_CHAPTER_NUM_RE = re.compile(r"chapter_(?P<num>\d+)")
_OUTLINE_HEADING_RE = re.compile(r"^#{1,6}\s*chapter\s*(?P<num>\d+)[：:]\s*(?P<title>.+?)\s*$", re.MULTILINE)
_SPLIT_OUTLINE_FILENAME_RE = re.compile(r"^chapter_0*(?P<num>\d+)[-—_ ]+(?P<title>.+?)\.md$")


def volume_num_for_chapter(chapter_num: int, *, chapters_per_volume: int = 50) -> int:
    if chapter_num <= 0:
        raise ValueError("chapter_num must be >= 1")
    return (chapter_num - 1) // chapters_per_volume + 1


def extract_chapter_num_from_filename(filename: str) -> Optional[int]:
    m = _CHAPTER_NUM_RE.search(filename)
    if not m:
        return None
    try:
        return int(m.group("num"))
    except ValueError:
        return None


def _safe_title_for_filename(title: str) -> str:
    cleaned = title.strip()
    if not cleaned:
        return ""

    try:
        from security_utils import sanitize_filename
    except ImportError:  # pragma: no cover
        from scripts.security_utils import sanitize_filename

    safe_title = sanitize_filename(cleaned, max_length=60)
    return "" if safe_title == "unnamed_entity" else safe_title


def _extract_title_from_outline_text(outline_text: str, chapter_num: int) -> str:
    for match in _OUTLINE_HEADING_RE.finditer(outline_text):
        if int(match.group("num")) != chapter_num:
            continue
        return _safe_title_for_filename(match.group("title"))
    return ""


def _extract_title_from_split_outline_filename(outline_dir: Path, chapter_num: int) -> str:
    patterns = [
        f"chapter_{chapter_num}*.md",
        f"chapter_{chapter_num:02d}*.md",
        f"chapter_{chapter_num:03d}*.md",
        f"chapter_{chapter_num:04d}*.md",
    ]
    for pattern in patterns:
        for path in sorted(outline_dir.glob(pattern)):
            match = _SPLIT_OUTLINE_FILENAME_RE.match(path.name)
            if not match:
                continue
            if int(match.group("num")) != chapter_num:
                continue
            title = _safe_title_for_filename(match.group("title"))
            if title:
                return title
    return ""


def extract_chapter_title(project_root: Path, chapter_num: int) -> str:
    """상세 개요에서 챕터 제목을 추출하여 보다 직관적인 챕터 파일명을 생성."""
    try:
        from chapter_outline_loader import load_chapter_outline
    except ImportError:  # pragma: no cover
        from scripts.chapter_outline_loader import load_chapter_outline

    outline_text = load_chapter_outline(project_root, chapter_num, max_chars=None)
    if not outline_text.startswith("⚠️"):
        title = _extract_title_from_outline_text(outline_text, chapter_num)
        if title:
            return title

    outline_dir = project_root / "outline"
    if outline_dir.exists():
        return _extract_title_from_split_outline_filename(outline_dir, chapter_num)
    return ""


def _build_chapter_filename(project_root: Path, chapter_num: int, *, use_volume_layout: bool) -> str:
    padded = f"{chapter_num:03d}" if use_volume_layout else f"{chapter_num:04d}"
    title = extract_chapter_title(project_root, chapter_num)
    if title:
        return f"chapter_{padded}-{title}.md"
    return f"chapter_{padded}.md"


def find_chapter_file(project_root: Path, chapter_num: int) -> Optional[Path]:
    """
    Find an existing chapter file for chapter_num under project_root/chapters.
    Returns the first match (stable sorted order) or None if not found.
    """
    chapters_dir = project_root / "chapters"
    if not chapters_dir.exists():
        return None

    legacy = chapters_dir / f"chapter_{chapter_num:04d}.md"
    if legacy.exists():
        return legacy

    vol_dir = chapters_dir / f"vol_{volume_num_for_chapter(chapter_num)}"
    if vol_dir.exists():
        candidates = sorted(vol_dir.glob(f"chapter_{chapter_num:03d}*.md")) + sorted(vol_dir.glob(f"chapter_{chapter_num:04d}*.md"))
        for c in candidates:
            if c.is_file():
                return c

    # Fallback: search anywhere under chapters/ (supports custom layouts)
    candidates = sorted(chapters_dir.rglob(f"chapter_{chapter_num:03d}*.md")) + sorted(chapters_dir.rglob(f"chapter_{chapter_num:04d}*.md"))
    for c in candidates:
        if c.is_file():
            return c

    return None


def default_chapter_draft_path(project_root: Path, chapter_num: int, *, use_volume_layout: bool = False) -> Path:
    """
    Preferred draft path when creating a new chapter file.

    Args:
        project_root: 프로젝트 루트 디렉토리
        chapter_num: 챕터 번호
        use_volume_layout: True uses volume layout (chapters/vol_N/chapter_NNN-title.md), False uses flat layout (chapters/chapter_NNNN-title.md)

    Default is flat layout. If the detailed outline already has a chapter title,
    append it to the filename for better discoverability.
    """
    if use_volume_layout:
        vol_dir = project_root / "chapters" / f"vol_{volume_num_for_chapter(chapter_num)}"
        return vol_dir / _build_chapter_filename(project_root, chapter_num, use_volume_layout=True)
    else:
        return project_root / "chapters" / _build_chapter_filename(project_root, chapter_num, use_volume_layout=False)

