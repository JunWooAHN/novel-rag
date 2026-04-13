#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys


def test_update_state_cli_add_review_writes_checkpoint(tmp_path, monkeypatch):
    import update_state as update_state_module

    webnovel_dir = tmp_path / ".webnovel"
    webnovel_dir.mkdir(parents=True, exist_ok=True)

    state = {
        "project_info": {},
        "progress": {"current_chapter": 1, "total_words": 0},
        "protagonist_state": {
            "power": {"realm": "연기", "layer": 1, "bottleneck": None},
            "location": "마을 입구",
        },
        "relationships": {},
        "world_settings": {},
        "plot_threads": {},
        "review_checkpoints": [],
    }
    state_file = webnovel_dir / "state.json"
    state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    # 테스트에서 백업 디렉토리 생성/권한 변경 등 비핵심 행위
    monkeypatch.setattr(update_state_module.StateUpdater, "backup", lambda self: True)

    report_file = "review/report_1_2.md"
    monkeypatch.setattr(
        sys,
        "argv",
        ["update_state", "--project-root", str(tmp_path), "--add-review", "1-2", report_file],
    )
    update_state_module.main()

    updated = json.loads(state_file.read_text(encoding="utf-8"))
    checkpoints = updated.get("review_checkpoints")
    assert isinstance(checkpoints, list)
    assert checkpoints[-1]["chapters"] == "1-2"
    assert checkpoints[-1]["report"] == report_file

