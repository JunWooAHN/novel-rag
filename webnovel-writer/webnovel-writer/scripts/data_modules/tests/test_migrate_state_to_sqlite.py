#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_state_to_sqlite tests
"""

import json

import pytest

import data_modules.migrate_state_to_sqlite as migrate_module
from data_modules.migrate_state_to_sqlite import (
    migrate_state_to_sqlite,
    _slim_world_settings,
    _slim_relationships,
)
from data_modules.config import DataModulesConfig
from data_modules.index_manager import IndexManager


@pytest.fixture
def temp_project(tmp_path):
    cfg = DataModulesConfig.from_project_root(tmp_path)
    cfg.ensure_dirs()
    return cfg


def test_migrate_state_missing_file(tmp_path):
    cfg = DataModulesConfig.from_project_root(tmp_path)
    stats = migrate_state_to_sqlite(cfg, dry_run=True, backup=False, verbose=False)
    assert stats["entities"] == 0


def test_migrate_state_to_sqlite_flow(temp_project):
    state = {
        "entities_v3": {
            "캐릭터": {
                "xiaoyan": {
                    "canonical_name": "소염",
                    "tier": "핵심",
                    "desc": "주인공",
                    "current": {"realm": "투자"},
                    "first_appearance": 1,
                    "last_appearance": 2,
                    "is_protagonist": True,
                }
            }
        },
        "alias_index": {
            "소염": [{"type": "캐릭터", "id": "xiaoyan"}]
        },
        "state_changes": [
            {"entity_id": "xiaoyan", "field": "realm", "old": "투자", "new": "투사", "reason": "돌파", "chapter": 2}
        ],
        "structured_relationships": [
            {"from_entity": "xiaoyan", "to_entity": "yaolao", "type": "사제", "description": "제자 수련", "chapter": 1}
        ],
        "world_settings": {
            "power_system": [{"name": "투자"}, {"name": "투사"}],
            "factions": [{"name": "천운종", "type": "종문"}],
            "locations": [{"name": "천운종"}],
        },
        "plot_threads": {"active_threads": [], "foreshadowing": []},
        "relationships": {},
        "review_checkpoints": [],
        "project_info": {"title": "테스트 책 제목"},
    }
    temp_project.state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    stats = migrate_state_to_sqlite(temp_project, dry_run=True, backup=False, verbose=False)
    assert stats["entities"] == 1
    assert stats["aliases"] == 1

    stats = migrate_state_to_sqlite(temp_project, dry_run=False, backup=False, verbose=False)
    assert stats["entities"] == 1

    # state.json 간소화됨
    saved = json.loads(temp_project.state_file.read_text(encoding="utf-8"))
    assert saved.get("_migrated_to_sqlite") is True
    assert "entities_v3" not in saved

    # SQLite 에서 엔티티 쿼리 가능
    idx = IndexManager(temp_project)
    entity = idx.get_entity("xiaoyan")
    assert entity is not None


def test_slim_helpers():
    world = {
        "power_system": [{"name": "투자"}],
        "factions": [{"name": "천운종", "type": "종문"}],
        "locations": [{"name": "천운종"}],
    }
    slim = _slim_world_settings(world)
    assert slim["power_system"][0] == "투자"

    rels = _slim_relationships({"a": 1})
    assert rels["a"] == 1


def test_slim_helpers_non_dict():
    assert _slim_world_settings("bad") == {}
    assert _slim_relationships("bad") == {}


def test_migrate_state_verbose_and_dry_run(temp_project, capsys):
    state = {
        "entities_v3": {},
        "alias_index": {},
        "state_changes": [],
        "structured_relationships": [],
        "world_settings": {},
        "plot_threads": {},
        "relationships": {},
        "review_checkpoints": [],
        "project_info": {},
    }
    temp_project.state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    stats = migrate_state_to_sqlite(temp_project, dry_run=True, backup=False, verbose=True)
    output = capsys.readouterr().out
    assert stats["errors"] == 0
    assert "dry-run" in output or "dry run" in output


def test_migrate_state_cli_main(tmp_path, monkeypatch, capsys):
    project_root = tmp_path
    args = [
        "migrate_state_to_sqlite",
        "--project-root",
        str(project_root),
        "--dry-run",
        "--no-backup",
    ]
    monkeypatch.setattr("sys.argv", args)
    migrate_module.main()
    output = json.loads(capsys.readouterr().out or "{}")
    assert output.get("status") == "success"

def test_migrate_state_backup_and_skips(temp_project):
    state = {
        "entities_v3": {
            "캐릭터": {
                "good": {"canonical_name": "좋은명"},
                "bad": "not-dict",
            }
        },
        "alias_index": {
            "좋은명": [{"type": "캐릭터", "id": "good"}],
            "나쁜항목": ["oops", {"type": "캐릭터"}],
        },
        "state_changes": ["bad", {"field": "realm"}],
        "structured_relationships": ["bad", {"from_entity": "", "to_entity": ""}],
        "relationships": {},
        "world_settings": {},
        "plot_threads": {},
        "review_checkpoints": [],
        "project_info": {},
    }
    temp_project.state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    stats = migrate_state_to_sqlite(temp_project, dry_run=False, backup=True, verbose=False)
    assert stats["entities"] == 1
    assert stats["skipped"] >= 3

    backups = list(temp_project.state_file.parent.glob("state.json.backup-*"))
    assert backups


def test_migrate_state_error_branches(tmp_path, monkeypatch):
    cfg = DataModulesConfig.from_project_root(tmp_path)
    cfg.ensure_dirs()
    state = {
        "entities_v3": {"캐릭터": {"boom": {"canonical_name": "폭"}}},
        "alias_index": {"폭": [{"type": "캐릭터", "id": "boom"}]},
        "state_changes": [
            {"entity_id": "boom", "field": "realm", "old": "", "new": "투자", "reason": "테스트", "chapter": 1}
        ],
        "structured_relationships": [
            {"from_entity": "boom", "to_entity": "yao", "type": "상면", "description": "테스트", "chapter": 1}
        ],
        "relationships": {},
        "world_settings": {},
        "plot_threads": {},
        "review_checkpoints": [],
        "project_info": {},
    }
    cfg.state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    class BoomSQL:
        def __init__(self, *args, **kwargs):
            pass

        def upsert_entity(self, *args, **kwargs):
            raise RuntimeError("boom")

        def register_alias(self, *args, **kwargs):
            raise RuntimeError("boom")

        def record_state_change(self, *args, **kwargs):
            raise RuntimeError("boom")

        def upsert_relationship(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(migrate_module, "SQLStateManager", BoomSQL)

    stats = migrate_state_to_sqlite(cfg, dry_run=False, backup=False, verbose=False)
    assert stats["errors"] >= 4
