#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_state_to_sqlite.py - 데이터 마이그레이션 스크립트 (v5.4)

state.json의 대용량 데이터를 SQLite (index.db)로 마이그레이션:
- entities_v3 → entities 테이블
- alias_index → aliases 테이블
- state_changes → state_changes 테이블
- structured_relationships → relationships 테이블

마이그레이션 후 state.json은 경량 데이터만 유지 (< 5KB):
- progress
- protagonist_state
- strand_tracker
- disambiguation_warnings/pending
- project_info
- world_settings (골격)
- plot_threads
- relationships (간소화 버전)
- review_checkpoints

사용법:
    python -m data_modules.migrate_state_to_sqlite --project-root "D:/wk/투파창궁"
    python -m data_modules.migrate_state_to_sqlite --project-root "." --dry-run
    python -m data_modules.migrate_state_to_sqlite --project-root "." --backup
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from .config import get_config, DataModulesConfig
from .sql_state_manager import SQLStateManager, EntityData


def migrate_state_to_sqlite(
    config: DataModulesConfig,
    dry_run: bool = False,
    backup: bool = True,
    verbose: bool = True
) -> Dict[str, int]:
    """
    마이그레이션 실행

    매개변수:
    - config: 설정 객체
    - dry_run: 분석만 하고 실제 기록하지 않음
    - backup: 마이그레이션 전 state.json 백업
    - verbose: 상세 로그 출력

    반환: 마이그레이션 통계
    """
    stats = {
        "entities": 0,
        "aliases": 0,
        "state_changes": 0,
        "relationships": 0,
        "skipped": 0,
        "errors": 0
    }

    # state.json 읽기
    state_file = config.state_file
    if not state_file.exists():
        if verbose:
            print(f"❌ state.json 존재하지 않음: {state_file}")
        return stats

    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)

    if verbose:
        file_size = state_file.stat().st_size / 1024
        print(f"📄 state.json 읽기 ({file_size:.1f} KB)")

    # 백업
    if backup and not dry_run:
        backup_file = state_file.with_suffix(f".json.backup-{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy(state_file, backup_file)
        if verbose:
            print(f"💾 백업 완료: {backup_file}")

    # 초기화 SQLStateManager
    sql_manager = SQLStateManager(config)

    # 1. entities_v3 마이그레이션
    entities_v3 = state.get("entities_v3", {})
    if verbose:
        print(f"\n🔄 entities_v3 마이그레이션...")

    for entity_type, entities in entities_v3.items():
        if not isinstance(entities, dict):
            continue

        for entity_id, entity_data in entities.items():
            if not isinstance(entity_data, dict):
                stats["skipped"] += 1
                continue

            try:
                entity = EntityData(
                    id=entity_id,
                    type=entity_type,
                    name=entity_data.get("canonical_name", entity_data.get("name", entity_id)),
                    tier=entity_data.get("tier", "장식"),
                    desc=entity_data.get("desc", ""),
                    current=entity_data.get("current", {}),
                    aliases=[],  # 별칭은 별도 처리
                    first_appearance=entity_data.get("first_appearance", 0),
                    last_appearance=entity_data.get("last_appearance", 0),
                    is_protagonist=entity_data.get("is_protagonist", False)
                )

                if not dry_run:
                    sql_manager.upsert_entity(entity)
                stats["entities"] += 1

                if verbose and stats["entities"] % 50 == 0:
                    print(f"  {stats['entities']}개 엔티티 마이그레이션 완료...")

            except Exception as e:
                stats["errors"] += 1
                if verbose:
                    print(f"  ⚠️ 엔티티 마이그레이션 실패 {entity_id}: {e}")

    if verbose:
        print(f"  ✅ 엔티티: {stats['entities']}개")

    # 2. alias_index 마이그레이션
    alias_index = state.get("alias_index", {})
    if verbose:
        print(f"\n🔄 alias_index 마이그레이션...")

    for alias, entries in alias_index.items():
        if not isinstance(entries, list):
            continue

        for entry in entries:
            if not isinstance(entry, dict):
                stats["skipped"] += 1
                continue

            entity_id = entry.get("id")
            entity_type = entry.get("type")
            if not entity_id or not entity_type:
                stats["skipped"] += 1
                continue

            try:
                if not dry_run:
                    sql_manager.register_alias(alias, entity_id, entity_type)
                stats["aliases"] += 1

            except Exception as e:
                stats["errors"] += 1
                if verbose:
                    print(f"  ⚠️ 별칭 마이그레이션 실패 {alias}: {e}")

    if verbose:
        print(f"  ✅ 별칭: {stats['aliases']}개")

    # 3. state_changes 마이그레이션
    state_changes = state.get("state_changes", [])
    if verbose:
        print(f"\n🔄 state_changes 마이그레이션...")

    for change in state_changes:
        if not isinstance(change, dict):
            stats["skipped"] += 1
            continue

        try:
            entity_id = change.get("entity_id", "")
            if not entity_id:
                stats["skipped"] += 1
                continue

            if not dry_run:
                sql_manager.record_state_change(
                    entity_id=entity_id,
                    field=change.get("field", ""),
                    old_value=change.get("old", change.get("old_value", "")),
                    new_value=change.get("new", change.get("new_value", "")),
                    reason=change.get("reason", ""),
                    chapter=change.get("chapter", 0)
                )
            stats["state_changes"] += 1

        except Exception as e:
            stats["errors"] += 1
            if verbose:
                print(f"  ⚠️ 상태 변화 마이그레이션 실패: {e}")

    if verbose:
        print(f"  ✅ 상태 변화: {stats['state_changes']} 건")

    # 4. structured_relationships 마이그레이션
    relationships = state.get("structured_relationships", [])
    if verbose:
        print(f"\n🔄 structured_relationships 마이그레이션...")

    for rel in relationships:
        if not isinstance(rel, dict):
            stats["skipped"] += 1
            continue

        try:
            from_entity = rel.get("from", rel.get("from_entity", ""))
            to_entity = rel.get("to", rel.get("to_entity", ""))
            if not from_entity or not to_entity:
                stats["skipped"] += 1
                continue

            if not dry_run:
                sql_manager.upsert_relationship(
                    from_entity=from_entity,
                    to_entity=to_entity,
                    type=rel.get("type", "아는 사이"),
                    description=rel.get("description", ""),
                    chapter=rel.get("chapter", 0)
                )
            stats["relationships"] += 1

        except Exception as e:
            stats["errors"] += 1
            if verbose:
                print(f"  ⚠️ 관계 마이그레이션 실패: {e}")

    if verbose:
        print(f"  ✅ 관계: {stats['relationships']} 건")

    # 5. state.json 경량화 (마이그레이션 완료 필드 제거)
    if not dry_run:
        if verbose:
            print(f"\n🔄 state.json 경량화...")

        # 유지할 필드
        slim_state = {
            "project_info": state.get("project_info", {}),
            "progress": state.get("progress", {}),
            "protagonist_state": state.get("protagonist_state", {}),
            "strand_tracker": state.get("strand_tracker", {}),
            "world_settings": _slim_world_settings(state.get("world_settings", {})),
            "plot_threads": state.get("plot_threads", {}),
            "relationships": _slim_relationships(state.get("relationships", {})),
            "review_checkpoints": state.get("review_checkpoints", [])[-10:],  # 최근 10개만 유지
            "disambiguation_warnings": state.get("disambiguation_warnings", [])[-20:],
            "disambiguation_pending": state.get("disambiguation_pending", [])[-10:],
            # v5.1 도입 표시
            "_migrated_to_sqlite": True,
            "_migration_timestamp": datetime.now().isoformat()
        }

        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(slim_state, f, ensure_ascii=False, indent=2)

        new_size = state_file.stat().st_size / 1024
        if verbose:
            print(f"  ✅ 경량화 후: {new_size:.1f} KB")

    # 통계 출력
    if verbose:
        print(f"\n" + "=" * 50)
        print(f"📊 마이그레이션 통계:")
        print(f"  엔티티: {stats['entities']}")
        print(f"  별칭: {stats['aliases']}")
        print(f"  상태 변화: {stats['state_changes']}")
        print(f"  관계: {stats['relationships']}")
        print(f"  건너뜀: {stats['skipped']}")
        print(f"  오류: {stats['errors']}")
        if dry_run:
            print(f"\n⚠️ dry-run 모드입니다. 실제로 데이터가 기록되지 않았습니다")

    return stats


def _slim_world_settings(world_settings: Dict) -> Dict:
    """world_settings 경량화, 골격만 유지"""
    if not isinstance(world_settings, dict):
        return {}

    slim = {}

    # power_system: 등급 이름만 유지
    power_system = world_settings.get("power_system", [])
    if isinstance(power_system, list):
        slim["power_system"] = [
            p.get("name") if isinstance(p, dict) else p
            for p in power_system[:20]  # 최대 20개 등급
        ]

    # factions: 이름과 간략 설명만 유지
    factions = world_settings.get("factions", [])
    if isinstance(factions, list):
        slim["factions"] = [
            {"name": f.get("name"), "type": f.get("type")}
            if isinstance(f, dict) else f
            for f in factions[:30]  # 최대 30개 세력
        ]

    # locations: 이름만 유지
    locations = world_settings.get("locations", [])
    if isinstance(locations, list):
        slim["locations"] = [
            loc.get("name") if isinstance(loc, dict) else loc
            for loc in locations[:50]  # 최대 50개 장소
        ]

    return slim


def _slim_relationships(relationships: Dict) -> Dict:
    """relationships 경량화, 핵심 관계만 유지"""
    if not isinstance(relationships, dict):
        return {}

    # relationships 딕셔너리 자체만 유지, 추가 경량화 불필요
    # 이 필드 자체가 비교적 작기 때문
    return relationships


def main():
    import argparse
    from .cli_output import print_success, print_error
    from .index_manager import IndexManager

    parser = argparse.ArgumentParser(description="state.json을 SQLite로 마이그레이션 (v5.4)")
    parser.add_argument("--project-root", type=str, required=True, help="프로젝트 루트 디렉토리")
    parser.add_argument("--dry-run", action="store_true", help="분석만 하고 실제 기록하지 않음")
    parser.add_argument("--backup", action="store_true", default=True, help="마이그레이션 전 백업")
    parser.add_argument("--no-backup", action="store_true", help="백업하지 않음")
    parser.add_argument("--quiet", action="store_true", help="조용한 모드")

    args = parser.parse_args()

    # “작업 공간 루트 디렉토리”를 전달받아, 실제 book project_root로 통합 해석 (반드시 .webnovel/state.json 포함)
    from project_locator import resolve_project_root

    resolved_root = resolve_project_root(args.project_root)
    config = DataModulesConfig.from_project_root(resolved_root)
    backup = not args.no_backup
    logger = IndexManager(config)
    tool_name = "migrate_state_to_sqlite"

    try:
        stats = migrate_state_to_sqlite(
            config=config,
            dry_run=args.dry_run,
            backup=backup,
            verbose=False,
        )
    except Exception as exc:
        print_error("MIGRATE_FAILED", str(exc), suggestion="state.json과 index.db 권한을 확인하세요")
        try:
            logger.log_tool_call(tool_name, False, error_code="MIGRATE_FAILED", error_message=str(exc))
        except Exception:
            pass
        raise SystemExit(1)

    if stats.get("errors", 0) > 0:
        print_error("MIGRATE_ERRORS", "마이그레이션 중 오류 발생", details=stats)
        try:
            logger.log_tool_call(tool_name, False, error_code="MIGRATE_ERRORS", error_message="마이그레이션 중 오류 발생")
        except Exception:
            pass
        raise SystemExit(1)

    print_success({"project": str(config.project_root), **stats}, message="migrated")
    try:
        logger.log_tool_call(tool_name, True)
    except Exception:
        pass


if __name__ == "__main__":
    main()
