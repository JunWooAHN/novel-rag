#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQL State Manager - SQLite 상태 관리 모듈 (v5.4)

IndexManager를 확장하여 StateManager와 호환되는 고급 인터페이스를 제공하며,
대규모 데이터(엔티티, 별칭, 상태 변화, 관계)를 JSON이 아닌 SQLite에 저장합니다.

목표（v5.1 도입,v5.4 유지）：
- state.json 내 대규모 데이터 필드를 대체
- Data Agent / Context Agent와의 인터페이스 호환성 유지
- 증분 기록 및 필요 시 쿼리 지원
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from .index_manager import (
    IndexManager,
    EntityMeta,
    StateChangeMeta,
    RelationshipMeta,
    RelationshipEventMeta,
)
from .config import get_config
from .observability import safe_log_tool_call


@dataclass
class EntityData:
    """엔티티 데이터 (Data Agent 입력용)"""
    id: str
    type: str  # 캐릭터/장소/물품/세력/초식
    name: str
    tier: str = "장식"
    desc: str = ""
    current: Dict[str, Any] = field(default_factory=dict)
    aliases: List[str] = field(default_factory=list)
    first_appearance: int = 0
    last_appearance: int = 0
    is_protagonist: bool = False


class SQLStateManager:
    """
    SQLite 상태 관리기（v5.1 도입,v5.4 유지）

    StateManager와 호환되는 인터페이스를 제공하지만, 데이터는 SQLite (index.db)에 저장합니다.
    state.json 내 비대해진 데이터 구조를 대체하기 위한 용도입니다.

    사용법:
    ```python
    manager = SQLStateManager(config)

    # 엔티티 기록
    manager.upsert_entity(EntityData(
        id="solyeom",
        type="캐릭터",
        name="소염",
        tier="핵심",
        current={"realm": "투사", "location": "천운종"},
        aliases=["소염자", "폐물"],
        is_protagonist=True
    ))

    # 상태 변화 기록
    manager.record_state_change(
        entity_id="solyeom",
        field="realm",
        old_value="투자",
        new_value="투사",
        reason="폐관 돌파",
        chapter=100
    )

    # 관계 기록
    manager.upsert_relationship(
        from_entity="solyeom",
        to_entity="yakro",
        type="사제",
        description="약로가 소염을 제자로 받아들임",
        chapter=5
    )

    # 조회
    protagonist = manager.get_protagonist()
    core_entities = manager.get_core_entities()
    changes = manager.get_recent_state_changes(limit=50)
    ```
    """

    # v5.0 도입 엔티티 유형
    ENTITY_TYPES = ["캐릭터", "장소", "물품", "세력", "초식"]

    def __init__(self, config=None):
        self.config = config or get_config()
        self._index_manager = IndexManager(config)

    # ==================== 엔티티 조작 ====================

    def upsert_entity(self, entity: EntityData) -> bool:
        """
        엔티티 삽입 또는 수정

        자동 처리:
        - 엔티티 기본 정보를 entities 테이블에 기록
        - 별칭을 aliases 테이블에 기록
        - canonical_name을 자동으로 별칭에 추가

        반환: 신규 엔티티 여부
        """
        # EntityMeta 구성
        meta = EntityMeta(
            id=entity.id,
            type=entity.type,
            canonical_name=entity.name,
            tier=entity.tier,
            desc=entity.desc,
            current=entity.current,
            first_appearance=entity.first_appearance,
            last_appearance=entity.last_appearance,
            is_protagonist=entity.is_protagonist,
            is_archived=False
        )

        is_new = self._index_manager.upsert_entity(meta)

        # 별칭 등록
        # 1. canonical_name 자체를 별칭으로 등록
        self._index_manager.register_alias(entity.name, entity.id, entity.type)

        # 2. 기타 별칭
        for alias in entity.aliases:
            if alias and alias != entity.name:
                self._index_manager.register_alias(alias, entity.id, entity.type)

        return is_new

    def get_entity(self, entity_id: str) -> Optional[Dict]:
        """엔티티 상세 조회"""
        entity = self._index_manager.get_entity(entity_id)
        if entity:
            # 별칭 추가
            entity["aliases"] = self._index_manager.get_entity_aliases(entity_id)
        return entity

    def get_entities_by_type(self, entity_type: str, include_archived: bool = False) -> List[Dict]:
        """유형별 엔티티 조회"""
        entities = self._index_manager.get_entities_by_type(entity_type, include_archived)
        for e in entities:
            e["aliases"] = self._index_manager.get_entity_aliases(e["id"])
        return entities

    def get_core_entities(self) -> List[Dict]:
        """
        핵심 엔티티 조회 (Context Agent 전체 로드용)

        tier=핵심/중요 또는 is_protagonist=1인 모든 엔티티를 반환
        (차요/장식 엔티티는 필요 시 쿼리하며 전체 로드하지 않음)
        """
        entities = self._index_manager.get_core_entities()
        for e in entities:
            e["aliases"] = self._index_manager.get_entity_aliases(e["id"])
        return entities

    def get_protagonist(self) -> Optional[Dict]:
        """주인공 엔티티 조회"""
        protagonist = self._index_manager.get_protagonist()
        if protagonist:
            protagonist["aliases"] = self._index_manager.get_entity_aliases(protagonist["id"])
        return protagonist

    def update_entity_current(self, entity_id: str, updates: Dict) -> bool:
        """엔티티의 current 필드를 증분 수정"""
        return self._index_manager.update_entity_current(entity_id, updates)

    def resolve_alias(self, alias: str) -> List[Dict]:
        """
        별칭으로 엔티티 해석 (일대다)

        매칭되는 모든 엔티티를 반환
        """
        return self._index_manager.get_entities_by_alias(alias)

    def register_alias(self, alias: str, entity_id: str, entity_type: str) -> bool:
        """별칭 등록"""
        return self._index_manager.register_alias(alias, entity_id, entity_type)

    # ==================== 상태 변화 조작 ====================

    def record_state_change(
        self,
        entity_id: str,
        field: str,
        old_value: Any,
        new_value: Any,
        reason: str,
        chapter: int
    ) -> int:
        """
        상태 변화 기록

        반환: 기록 ID
        """
        change = StateChangeMeta(
            entity_id=entity_id,
            field=field,
            old_value=str(old_value) if old_value is not None else "",
            new_value=str(new_value),
            reason=reason,
            chapter=chapter
        )
        return self._index_manager.record_state_change(change)

    def get_entity_state_changes(self, entity_id: str, limit: int = 20) -> List[Dict]:
        """엔티티의 상태 변화 이력 조회"""
        return self._index_manager.get_entity_state_changes(entity_id, limit)

    def get_recent_state_changes(self, limit: int = 50) -> List[Dict]:
        """최근 상태 변화 조회"""
        return self._index_manager.get_recent_state_changes(limit)

    def get_chapter_state_changes(self, chapter: int) -> List[Dict]:
        """특정 챕터의 모든 상태 변화 조회"""
        return self._index_manager.get_chapter_state_changes(chapter)

    # ==================== 관계 조작 ====================

    def upsert_relationship(
        self,
        from_entity: str,
        to_entity: str,
        type: str,
        description: str,
        chapter: int
    ) -> bool:
        """
        관계 삽입 또는 수정

        반환: 신규 관계 여부
        """
        rel = RelationshipMeta(
            from_entity=from_entity,
            to_entity=to_entity,
            type=type,
            description=description,
            chapter=chapter
        )
        return self._index_manager.upsert_relationship(rel)

    def get_entity_relationships(self, entity_id: str, direction: str = "both") -> List[Dict]:
        """엔티티의 관계 조회"""
        return self._index_manager.get_entity_relationships(entity_id, direction)

    def get_relationship_between(self, entity1: str, entity2: str) -> List[Dict]:
        """두 엔티티 사이의 모든 관계 조회"""
        return self._index_manager.get_relationship_between(entity1, entity2)

    def get_recent_relationships(self, limit: int = 30) -> List[Dict]:
        """최근 생성된 관계 조회"""
        return self._index_manager.get_recent_relationships(limit)

    # ==================== 일괄 기록 (Data Agent 사용) ====================

    def process_chapter_entities(
        self,
        chapter: int,
        entities_appeared: List[Dict],
        entities_new: List[Dict],
        state_changes: List[Dict],
        relationships_new: List[Dict]
    ) -> Dict[str, int]:
        """
        챕터의 엔티티 데이터 처리 (Data Agent 주입구)

        매개변수:
        - chapter: 챕터 번호
        - entities_appeared: 등장한 기존 엔티티
          [{"id": "solyeom", "type": "캐릭터", "mentions": ["소염", "그"], "confidence": 0.95}]
        - entities_new: 새로 발견된 엔티티
          [{"suggested_id": "hongui_girl", "name": "홍의여자", "type": "캐릭터", "tier": "장식"}]
        - state_changes: 상태 변화
          [{"entity_id": "solyeom", "field": "realm", "old": "투자", "new": "투사", "reason": "돌파"}]
        - relationships_new: 신규 관계
          [{"from": "solyeom", "to": "hongui_girl", "type": "아는 사이", "description": "첫 만남"}]

        반환: 기록 통계
        """
        stats = {
            "entities_updated": 0,
            "entities_created": 0,
            "state_changes": 0,
            "relationships": 0,
            "aliases": 0
        }

        # 1. 등장 엔티티 처리 (last_appearance 수정)
        for entity in entities_appeared:
            entity_id = entity.get("id")
            if not entity_id:
                continue

            self._index_manager.update_entity_current(entity_id, {})  # updated_at 트리거
            # last_appearance 수정
            existing = self._index_manager.get_entity(entity_id)
            if existing:
                # SQL로 직접 last_appearance 수정
                self._update_last_appearance(entity_id, chapter)
                stats["entities_updated"] += 1

            # 등장 기록 (기존 로직 유지)
            self._index_manager.record_appearance(
                entity_id=entity_id,
                chapter=chapter,
                mentions=entity.get("mentions", []),
                confidence=entity.get("confidence", 1.0)
            )

        # 2. 신규 엔티티 처리
        for entity in entities_new:
            suggested_id = entity.get("suggested_id") or entity.get("id")
            if not suggested_id:
                continue

            entity_data = EntityData(
                id=suggested_id,
                type=entity.get("type", "캐릭터"),
                name=entity.get("name", suggested_id),
                tier=entity.get("tier", "장식"),
                desc=entity.get("desc", ""),
                current=entity.get("current", {}),
                aliases=entity.get("aliases", []),
                first_appearance=chapter,
                last_appearance=chapter,
                is_protagonist=entity.get("is_protagonist", False)
            )
            is_new = self.upsert_entity(entity_data)
            if is_new:
                stats["entities_created"] += 1
            else:
                stats["entities_updated"] += 1

            # 별칭 통계
            stats["aliases"] += 1 + len(entity_data.aliases)

            # 신규 엔티티의 첫 등장 기록 (appearances 누락 문제 해결)
            mentions = entity.get("mentions", [])
            if not mentions:
                mentions = [entity_data.name]  # 최소한 엔티티명을 포함
            self._index_manager.record_appearance(
                entity_id=suggested_id,
                chapter=chapter,
                mentions=mentions,
                confidence=entity.get("confidence", 1.0)
            )

        # 3. 상태 변화 처리
        for change in state_changes:
            entity_id = change.get("entity_id")
            if not entity_id:
                continue

            self.record_state_change(
                entity_id=entity_id,
                field=change.get("field", ""),
                old_value=change.get("old", change.get("old_value", "")),
                new_value=change.get("new", change.get("new_value", "")),
                reason=change.get("reason", ""),
                chapter=chapter
            )
            stats["state_changes"] += 1

            # 엔티티의 current를 동기화 수정
            field_name = change.get("field")
            new_value = change.get("new", change.get("new_value"))
            # 주의: new_value가 0/""/False 등 falsy 값일 수 있으므로 is not None으로 판단 필요
            if field_name and new_value is not None:
                self._index_manager.update_entity_current(entity_id, {field_name: new_value})

        # 4. 신규 관계 처리
        for rel in relationships_new:
            from_entity = rel.get("from", rel.get("from_entity"))
            to_entity = rel.get("to", rel.get("to_entity"))
            if not from_entity or not to_entity:
                continue
            rel_type = rel.get("type", "아는 사이")
            description = rel.get("description", "")

            # v5.5: 먼저 관계 이벤트를 기록하고, 그 다음 관계 스냅샷을 수정
            self._index_manager.record_relationship_event(
                RelationshipEventMeta(
                    from_entity=from_entity,
                    to_entity=to_entity,
                    type=rel_type,
                    chapter=chapter,
                    action=rel.get("action", "update"),
                    polarity=rel.get("polarity", 0),
                    strength=rel.get("strength", 0.5),
                    description=description,
                    scene_index=rel.get("scene_index", 0),
                    evidence=rel.get("evidence", ""),
                    confidence=rel.get("confidence", 1.0),
                )
            )

            self.upsert_relationship(
                from_entity=from_entity,
                to_entity=to_entity,
                type=rel_type,
                description=description,
                chapter=chapter
            )
            stats["relationships"] += 1

        return stats

    def _update_last_appearance(self, entity_id: str, chapter: int):
        """엔티티의 last_appearance 수정"""
        with self._index_manager._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE entities SET
                    last_appearance = MAX(last_appearance, ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (chapter, entity_id))
            conn.commit()

    # ==================== 통계 ====================

    def get_stats(self) -> Dict[str, int]:
        """통계 정보 조회"""
        return self._index_manager.get_stats()

    # ==================== 형식 변환 (호환성) ====================

    def export_to_entities_v3_format(self) -> Dict[str, Dict[str, Dict]]:
        """
        entities_v3 형식으로 내보내기 (호환성용)

        반환: {"캐릭터": {"xiaoyan": {...}}, "장소": {...}, ...}
        """
        result = {t: {} for t in self.ENTITY_TYPES}

        for entity_type in self.ENTITY_TYPES:
            entities = self.get_entities_by_type(entity_type, include_archived=True)
            for e in entities:
                entity_dict = {
                    "canonical_name": e.get("canonical_name"),
                    "name": e.get("canonical_name"),  # 호환성 별칭
                    "tier": e.get("tier", "장식"),
                    "aliases": e.get("aliases", []),
                    "desc": e.get("desc", ""),
                    "current": e.get("current_json", {}),
                    "history": [],  # 이력은 state_changes 테이블에서 쿼리 필요
                    "first_appearance": e.get("first_appearance", 0),
                    "last_appearance": e.get("last_appearance", 0)
                }
                if e.get("is_protagonist"):
                    entity_dict["is_protagonist"] = True
                result[entity_type][e["id"]] = entity_dict

        return result

    def export_to_alias_index_format(self) -> Dict[str, List[Dict[str, str]]]:
        """
        alias_index 형식으로 내보내기 (호환성용)

        반환: {"소염": [{"type": "캐릭터", "id": "solyeom"}], ...}
        """
        result = {}

        with self._index_manager._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT alias, entity_id, entity_type FROM aliases")
            for row in cursor.fetchall():
                alias = row["alias"]
                if alias not in result:
                    result[alias] = []
                result[alias].append({
                    "type": row["entity_type"],
                    "id": row["entity_id"]
                })

        return result


# ==================== CLI 인터페이스 ====================

def main():
    import argparse
    import sys
    from .cli_output import print_success, print_error
    from .cli_args import normalize_global_project_root, load_json_arg
    from .index_manager import IndexManager

    parser = argparse.ArgumentParser(description="SQL State Manager CLI (v5.4)")
    parser.add_argument("--project-root", type=str, help="프로젝트 루트 디렉토리")

    subparsers = parser.add_subparsers(dest="command")

    # 통계 조회
    subparsers.add_parser("stats")

    # 주인공 조회
    subparsers.add_parser("get-protagonist")

    # 핵심 엔티티 조회
    subparsers.add_parser("get-core-entities")

    # entities_v3 형식 내보내기
    subparsers.add_parser("export-entities-v3")

    # alias_index 형식 내보내기
    subparsers.add_parser("export-alias-index")

    # 챕터 데이터 처리
    process_parser = subparsers.add_parser("process-chapter")
    process_parser.add_argument("--chapter", type=int, required=True)
    process_parser.add_argument("--data", required=True, help="JSON 형식의 챕터 데이터")

    argv = normalize_global_project_root(sys.argv[1:])
    args = parser.parse_args(argv)

    # 초기화
    config = None
    if args.project_root:
        # “워크스페이스 루트 디렉토리”를 전달받아 실제 book project_root로 통일 해석 (.webnovel/state.json 포함 필수)
        from project_locator import resolve_project_root
        from .config import DataModulesConfig

        resolved_root = resolve_project_root(args.project_root)
        config = DataModulesConfig.from_project_root(resolved_root)

    manager = SQLStateManager(config)
    logger = IndexManager(config)
    tool_name = f"sql_state_manager:{args.command or 'unknown'}"

    def emit_success(data=None, message: str = "ok"):
        print_success(data, message=message)
        safe_log_tool_call(logger, tool_name=tool_name, success=True)

    def emit_error(code: str, message: str, suggestion: str | None = None):
        print_error(code, message, suggestion=suggestion)
        safe_log_tool_call(
            logger,
            tool_name=tool_name,
            success=False,
            error_code=code,
            error_message=message,
        )

    if args.command == "stats":
        stats = manager.get_stats()
        emit_success(stats, message="stats")

    elif args.command == "get-protagonist":
        protagonist = manager.get_protagonist()
        if protagonist:
            emit_success(protagonist, message="protagonist")
        else:
            emit_error("NOT_FOUND", "주인공이 설정되지 않음")

    elif args.command == "get-core-entities":
        entities = manager.get_core_entities()
        emit_success(entities, message="core_entities")

    elif args.command == "export-entities-v3":
        data = manager.export_to_entities_v3_format()
        emit_success(data, message="entities_v3")

    elif args.command == "export-alias-index":
        data = manager.export_to_alias_index_format()
        emit_success(data, message="alias_index")

    elif args.command == "process-chapter":
        data = load_json_arg(args.data)
        stats = manager.process_chapter_entities(
            chapter=args.chapter,
            entities_appeared=data.get("entities_appeared", []),
            entities_new=data.get("entities_new", []),
            state_changes=data.get("state_changes", []),
            relationships_new=data.get("relationships_new", []),
        )
        emit_success(stats, message="chapter_processed")

    else:
        emit_error("UNKNOWN_COMMAND", "유효한 명령이 지정되지 않음", suggestion="--help를 참조하세요")


if __name__ == "__main__":
    main()
