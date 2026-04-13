#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path


def _load_module():
    scripts_dir = Path(__file__).resolve().parents[2]
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    import chapter_paths

    return chapter_paths


def test_default_chapter_draft_path_uses_outline_heading_title(tmp_path):
    module = _load_module()

    outline_dir = tmp_path / "outline"
    outline_dir.mkdir(parents=True, exist_ok=True)
    (outline_dir / "vol_1-detailed.md").write_text("### chapter 1: 테스트 제목\n테스트 개요", encoding="utf-8")

    draft_path = module.default_chapter_draft_path(tmp_path, 1)

    assert draft_path.name == "chapter_0001-테스트 제목.md"


def test_default_chapter_draft_path_falls_back_to_split_outline_filename(tmp_path):
    module = _load_module()

    outline_dir = tmp_path / "outline"
    outline_dir.mkdir(parents=True, exist_ok=True)
    (outline_dir / "chapter_0002-제목 파일.md").write_text("없음챕터 제목 heading", encoding="utf-8")

    draft_path = module.default_chapter_draft_path(tmp_path, 2)

    assert draft_path.name == "chapter_0002-제목_파일.md"


def test_find_chapter_file_supports_titled_flat_filename(tmp_path):
    module = _load_module()

    chapter_path = tmp_path / "chapters" / "chapter_0003-폭풍전야.md"
    chapter_path.parent.mkdir(parents=True, exist_ok=True)
    chapter_path.write_text("본문", encoding="utf-8")

    found = module.find_chapter_file(tmp_path, 3)

    assert found == chapter_path
