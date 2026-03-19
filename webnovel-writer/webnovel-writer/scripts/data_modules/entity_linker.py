#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entity Linker - 엔티티 소명 보조 모듈 (v5.4)

Data Agent에 엔티티 소명 보조 기능 제공：
- 신뢰도 판단
- 별칭 인덱스 관리 (통과 index.db aliases 表)
- 소명 결과 기록

v5.1 변경（v5.4 유지）:
- 별칭 저장소가 state.json에서 index.db aliases 테이블로 마이그레이션
- IndexManager를 사용한 별칭 읽기/쓰기
- state.json에 대한 직접 조작 제거
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from .config import get_config
from .index_manager import IndexManager
from .observability import safe_log_tool_call


@dataclass
class DisambiguationResult:
    """소명 결과"""
    mention: str
    entity_id: Optional[str]
    confidence: float
    candidates: List[str] = field(default_factory=list)
    adopted: bool = False
    warning: Optional[str] = None


class EntityLinker:
    """엔티티 링커 - Data Agent의 엔티티 소명 보조 (v5.1 SQLite，v5.4 유지)"""

    def __init__(self, config=None):
        self.config = config or get_config()
        self._index_manager = IndexManager(self.config)

    # ==================== 별칭 관리 (v5.1 SQLite，v5.4 유지) ====================

    def register_alias(self, entity_id: str, alias: str, entity_type: str = "캐릭터") -> bool:
        """새 별칭 등록（v5.1 도입：index.db aliases 테이블에 쓰기）"""
        if not alias or not entity_id:
            return False
        return self._index_manager.register_alias(alias, entity_id, entity_type)

    def lookup_alias(self, mention: str, entity_type: str = None) -> Optional[str]:
        """별칭에 해당하는 엔티티 ID 검색(첫 번째 매치 반환, 유형별 필터링 선택)"""
        entries = self._index_manager.get_entities_by_alias(mention)
        if not entries:
            return None

        if entity_type:
            for entry in entries:
                if entry.get("type") == entity_type:
                    return entry.get("id")
            return None
        else:
            return entries[0].get("id") if entries else None

    def lookup_alias_all(self, mention: str) -> List[Dict]:
        """별칭에 해당하는 모든 엔티티 검색(1:N)"""
        entries = self._index_manager.get_entities_by_alias(mention)
        return [{"type": e.get("type"), "id": e.get("id")} for e in entries]

    def get_all_aliases(self, entity_id: str, entity_type: str = None) -> List[str]:
        """엔티티의 모든 별칭 조회"""
        return self._index_manager.get_entity_aliases(entity_id)

    # ==================== 신뢰도 판단 ====================

    def evaluate_confidence(self, confidence: float) -> Tuple[str, bool, Optional[str]]:
        """
        신뢰도 평가, 반환 (action, adopt, warning)

        - action: "auto" | "warn" | "manual"
        - adopt: 채택 여부
        - warning: 경고 정보
        """
        if confidence >= self.config.extraction_confidence_high:
            return ("auto", True, None)
        elif confidence >= self.config.extraction_confidence_medium:
            return ("warn", True, f"중간 신뢰도 매칭 (confidence: {confidence:.2f})")
        else:
            return ("manual", False, f"수동 확인 필요 (confidence: {confidence:.2f})")

    def process_uncertain(
        self,
        mention: str,
        candidates: List[str],
        suggested: str,
        confidence: float,
        context: str = ""
    ) -> DisambiguationResult:
        """
        불확실한 엔티티 매칭 처리

        소명 결과 반환, 채택 여부, 경고 정보 등 포함
        """
        action, adopt, warning = self.evaluate_confidence(confidence)

        result = DisambiguationResult(
            mention=mention,
            entity_id=suggested if adopt else None,
            confidence=confidence,
            candidates=candidates,
            adopted=adopt,
            warning=warning
        )

        return result

    # ==================== 일괄 처리 ====================

    def process_extraction_result(
        self,
        uncertain_items: List[Dict]
    ) -> Tuple[List[DisambiguationResult], List[str]]:
        """
        AI 추출 결과의 uncertain 항목 처리

        반환 (results, warnings)
        """
        results = []
        warnings = []

        for item in uncertain_items:
            result = self.process_uncertain(
                mention=item.get("mention", ""),
                candidates=item.get("candidates", []),
                suggested=item.get("suggested", ""),
                confidence=item.get("confidence", 0.0),
                context=item.get("context", "")
            )
            results.append(result)

            if result.warning:
                warnings.append(f"{result.mention} → {result.entity_id}: {result.warning}")

        return results, warnings

    def register_new_entities(
        self,
        new_entities: List[Dict]
    ) -> List[str]:
        """
        새 엔티티의 별칭 등록 (v5.1 도입,v5.4 유지)

        등록된 엔티티 ID 목록 반환
        """
        registered = []

        for entity in new_entities:
            entity_id = entity.get("suggested_id") or entity.get("id")
            if not entity_id or entity_id == "NEW":
                continue

            entity_type = entity.get("type", "캐릭터")

            # 주요 이름 등록
            name = entity.get("name", "")
            if name:
                self.register_alias(entity_id, name, entity_type)

            # 언급 방식 등록
            for mention in entity.get("mentions", []):
                if mention and mention != name:
                    self.register_alias(entity_id, mention, entity_type)

            registered.append(entity_id)

        return registered


# ==================== CLI 인터페이스 ====================

def main():
    import argparse
    import sys
    from .cli_output import print_success, print_error
    from .cli_args import normalize_global_project_root
    from .index_manager import IndexManager

    parser = argparse.ArgumentParser(description="Entity Linker CLI (v5.4 SQLite)")
    parser.add_argument("--project-root", type=str, help="프로젝트 루트 디렉토리")

    subparsers = parser.add_subparsers(dest="command")

    # 注册별칭
    register_parser = subparsers.add_parser("register-alias")
    register_parser.add_argument("--entity", required=True, help="엔티티 ID")
    register_parser.add_argument("--alias", required=True, help="별칭")
    register_parser.add_argument("--type", default="캐릭터", help="엔티티 유형(기본: 캐릭터)")

    # 查找별칭
    lookup_parser = subparsers.add_parser("lookup")
    lookup_parser.add_argument("--mention", required=True, help="언급 텍스트")
    lookup_parser.add_argument("--type", help="유형별 필터링")

    # 查找所有匹配（一对多）
    lookup_all_parser = subparsers.add_parser("lookup-all")
    lookup_all_parser.add_argument("--mention", required=True, help="언급 텍스트")

    # 列出별칭
    list_parser = subparsers.add_parser("list-aliases")
    list_parser.add_argument("--entity", required=True, help="엔티티 ID")
    list_parser.add_argument("--type", help="实体类型")

    argv = normalize_global_project_root(sys.argv[1:])
    args = parser.parse_args(argv)

    # 초기화
    config = None
    if args.project_root:
        # 允许传入“工作区根目录”，统一解析到真正的 book project_root（必须포함 .webnovel/state.json）
        from project_locator import resolve_project_root
        from .config import DataModulesConfig

        resolved_root = resolve_project_root(args.project_root)
        config = DataModulesConfig.from_project_root(resolved_root)

    linker = EntityLinker(config)
    logger = IndexManager(config)
    tool_name = f"entity_linker:{args.command or 'unknown'}"

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

    if args.command == "register-alias":
        entity_type = getattr(args, "type", "캐릭터")
        success = linker.register_alias(args.entity, args.alias, entity_type)
        if success:
            emit_success({"entity": args.entity, "alias": args.alias, "type": entity_type}, message="alias_registered")
        else:
            emit_error("ALIAS_EXISTS", "등록 실패 또는 이미 존재")

    elif args.command == "lookup":
        entity_type = getattr(args, "type", None)
        entity_id = linker.lookup_alias(args.mention, entity_type)
        if entity_id:
            emit_success({"mention": args.mention, "entity": entity_id}, message="lookup")
        else:
            emit_error("NOT_FOUND", f"별칭을 찾을 수 없음: {args.mention}")

    elif args.command == "lookup-all":
        matches = linker.lookup_alias_all(args.mention)
        emit_success(matches, message="lookup_all")

    elif args.command == "list-aliases":
        entity_type = getattr(args, "type", None)
        aliases = linker.get_all_aliases(args.entity, entity_type)
        emit_success(aliases, message="aliases")

    else:
        emit_error("UNKNOWN_COMMAND", "유효한 명령이 지정되지 않음", suggestion="--help를 참조하세요")


if __name__ == "__main__":
    main()
