#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Modules 단위 테스트
"""

import pytest
import asyncio
import json
import tempfile
import sys
from pathlib import Path

from data_modules import (
    DataModulesConfig,
    EntityLinker,
    StateManager,
    IndexManager,
    RAGAdapter,
    StyleSampler,
    EntityState,
    ChapterMeta,
    SceneMeta,
    StyleSample,
)
import data_modules.index_manager as index_manager_module
from data_modules.index_manager import (
    EntityMeta,
    StateChangeMeta,
    RelationshipMeta,
    OverrideContractMeta,
    ChaseDebtMeta,
    ChapterReadingPowerMeta,
    ReviewMetrics,
    WritingChecklistScoreMeta,
)


@pytest.fixture
def temp_project():
    """임시 프로젝트 디렉토리 생성"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = DataModulesConfig.from_project_root(tmpdir)
        config.ensure_dirs()
        yield config


class TestEntityLinker:
    """엔티티 링커 테스트"""

    def test_register_and_lookup_alias(self, temp_project):
        linker = EntityLinker(temp_project)
        # 먼저 엔티티를 등록해야 aliases JOIN이 반환됨
        IndexManager(temp_project).upsert_entity(
            EntityMeta(
                id="xiaoyan",
                type="캐릭터",
                canonical_name="소염",
                current={},
                first_appearance=1,
                last_appearance=1,
            )
        )

        # 등록별칭
        assert linker.register_alias("xiaoyan", "소염")
        assert linker.register_alias("xiaoyan", "소염자")

        # 조회
        assert linker.lookup_alias("소염") == "xiaoyan"
        assert linker.lookup_alias("소염자") == "xiaoyan"
        assert linker.lookup_alias("존재하지 않음") is None

    def test_alias_one_to_many(self, temp_project):
        """v5.0: 동일별칭가능매핑여러 엔티티(일대다)"""
        linker = EntityLinker(temp_project)

        idx = IndexManager(temp_project)
        idx.upsert_entity(
            EntityMeta(
                id="xiaoyan",
                type="캐릭터",
                canonical_name="소염",
                current={},
                first_appearance=1,
                last_appearance=1,
            )
        )
        idx.upsert_entity(
            EntityMeta(
                id="other_person",
                type="캐릭터",
                canonical_name="소염",
                current={},
                first_appearance=1,
                last_appearance=1,
            )
        )

        linker.register_alias("xiaoyan", "소염", "캐릭터")
        # v5.0: 동일별칭가능다른 엔티티에 바인딩(일대다)
        assert linker.register_alias("other_person", "소염", "캐릭터")

        # 조회모든 매칭
        entries = linker.lookup_alias_all("소염")
        assert len(entries) == 2

    def test_get_all_aliases(self, temp_project):
        linker = EntityLinker(temp_project)
        IndexManager(temp_project).upsert_entity(
            EntityMeta(
                id="xiaoyan",
                type="캐릭터",
                canonical_name="소염",
                current={},
                first_appearance=1,
                last_appearance=1,
            )
        )

        linker.register_alias("xiaoyan", "소염")
        linker.register_alias("xiaoyan", "소염자")
        linker.register_alias("xiaoyan", "염형")

        aliases = linker.get_all_aliases("xiaoyan")
        assert len(aliases) == 3
        assert "소염" in aliases

    def test_confidence_evaluation(self, temp_project):
        linker = EntityLinker(temp_project)

        # 높은 신뢰도
        action, adopt, warning = linker.evaluate_confidence(0.9)
        assert action == "auto"
        assert adopt is True
        assert warning is None

        # 중간 신뢰도
        action, adopt, warning = linker.evaluate_confidence(0.6)
        assert action == "warn"
        assert adopt is True
        assert warning is not None

        # 낮은 신뢰도
        action, adopt, warning = linker.evaluate_confidence(0.3)
        assert action == "manual"
        assert adopt is False

    def test_process_uncertain(self, temp_project):
        linker = EntityLinker(temp_project)

        result = linker.process_uncertain(
            mention="그 선배",
            candidates=["yaolao", "elder_zhang"],
            suggested="yaolao",
            confidence=0.7
        )

        assert result.mention == "그 선배"
        assert result.entity_id == "yaolao"
        assert result.adopted is True
        assert result.warning is not None


class TestStateManager:
    """상태매니저 테스트"""

    def test_add_and_get_entity(self, temp_project):
        manager = StateManager(temp_project)

        entity = EntityState(
            id="xiaoyan",
            name="소염",
            type="캐릭터",
            tier="핵심"
        )
        assert manager.add_entity(entity)

        # 엔티티 가져오기
        result = manager.get_entity("xiaoyan")
        assert result is not None
        assert result["canonical_name"] == "소염"

    def test_update_entity(self, temp_project):
        manager = StateManager(temp_project)

        entity = EntityState(id="xiaoyan", name="소염", type="캐릭터")
        manager.add_entity(entity)

        # 속성 업데이트 (v5.0: attributes는 current 필드에 존재)
        manager.update_entity("xiaoyan", {"current": {"realm": "투사"}})

        result = manager.get_entity("xiaoyan")
        assert result["current"]["realm"] == "투사"

    def test_record_state_change(self, temp_project):
        manager = StateManager(temp_project)

        entity = EntityState(id="xiaoyan", name="소염", type="캐릭터")
        manager.add_entity(entity)

        manager.record_state_change(
            entity_id="xiaoyan",
            field="realm",
            old_value="투자",
            new_value="투사",
            reason="돌파",
            chapter=100
        )

        changes = manager.get_state_changes("xiaoyan")
        assert len(changes) == 1
        assert changes[0]["new_value"] == "투사"

    def test_add_relationship(self, temp_project):
        manager = StateManager(temp_project)

        manager.add_relationship(
            from_entity="xiaoyan",
            to_entity="yaolao",
            rel_type="사제",
            description="약로가 소염을 제자로 받아들임",
            chapter=10
        )

        rels = manager.get_relationships("xiaoyan")
        assert len(rels) == 1
        assert rels[0]["type"] == "사제"

    def test_process_chapter_result(self, temp_project):
        manager = StateManager(temp_project)

        result = {
            "entities_appeared": [
                {"id": "xiaoyan", "mentions": ["소염", "그"]}
            ],
            "entities_new": [
                {"suggested_id": "hongyi_girl", "name": "홍의여자", "type": "캐릭터", "tier": "장식"}
            ],
            "state_changes": [
                {"entity_id": "xiaoyan", "field": "realm", "old": "투자", "new": "투사", "reason": "돌파"}
            ],
            "relationships_new": [
                {"from": "xiaoyan", "to": "hongyi_girl", "type": "상면", "description": "첫 만남"}
            ]
        }

        # 먼저 추가소염
        manager.add_entity(EntityState(id="xiaoyan", name="소염", type="캐릭터"))

        warnings = manager.process_chapter_result(100, result)

        # 검증새 엔티티 추가됨
        assert manager.get_entity("hongyi_girl") is not None

        # 검증상태 변화
        changes = manager.get_state_changes("xiaoyan")
        assert len(changes) == 1

        # 검증진행 업데이트
        assert manager.get_current_chapter() == 100

    def test_save_state_with_init_project_schema(self, temp_project):
        """회귀: init_project가 생성한 state.json에 StateManager가 여전히 쓸 수 있어야 함. (v5.1 SQLite-only)"""
        # v5.1: state.json에 더 이상 entities_v3/alias_index 포함하지 않음, 엔티티 데이터는 SQLite에 저장
        init_state = {
            "project_info": {"title": "테스트 책 제목", "genre": "선협/현환", "created_at": "2026-01-01"},
            "progress": {"current_chapter": 0, "total_words": 0, "last_updated": "2026-01-01 00:00:00"},
            "protagonist_state": {"name": "테스트 주인공"},
            "relationships": {},
            "world_settings": {"power_system": [], "factions": [], "locations": []},
            "plot_threads": {"active_threads": [], "foreshadowing": []},
            "review_checkpoints": [],
            "strand_tracker": {"current_dominant": "quest", "history": []},
        }
        temp_project.state_file.write_text(json.dumps(init_state, ensure_ascii=False, indent=2), encoding="utf-8")

        manager = StateManager(temp_project)
        manager.update_progress(5, words=100)
        manager.save_state()

        saved = json.loads(temp_project.state_file.read_text(encoding="utf-8"))
        assert "meta" not in saved
        assert saved["progress"]["current_chapter"] == 5
        assert saved["progress"]["total_words"] == 100
        # v5.1: entities_v3/alias_index는 더 이상 state.json에 없음

    def test_save_state_preserves_unrelated_fields(self, temp_project):
        """회귀: 증분만 쓰며 다른 모듈이 유지하는 필드를 덮어쓰기/분실하지 않아야 하는필드。(v5.1 SQLite-only)"""
        init_state = {
            "project_info": {"title": "테스트 책 제목", "genre": "선협/현환", "created_at": "2026-01-01"},
            "progress": {"current_chapter": 10, "total_words": 1000, "last_updated": "2026-01-01 00:00:00"},
            "protagonist_state": {"name": "테스트 주인공"},
            "relationships": {"allies": ["약로"], "enemies": []},
            "world_settings": {"power_system": [], "factions": [], "locations": []},
            "plot_threads": {"active_threads": [{"id": "t1", "title": "메인 스토리"}], "foreshadowing": []},
            "review_checkpoints": [],
            "strand_tracker": {"current_dominant": "quest", "history": []},
            "custom_field": {"keep": True},
        }
        temp_project.state_file.write_text(json.dumps(init_state, ensure_ascii=False, indent=2), encoding="utf-8")

        manager = StateManager(temp_project)
        manager.add_entity(EntityState(id="xiaoyan", name="소염", type="캐릭터", tier="핵심"))
        manager.save_state()

        saved = json.loads(temp_project.state_file.read_text(encoding="utf-8"))
        assert saved.get("custom_field", {}).get("keep") is True
        assert saved.get("plot_threads", {}).get("active_threads", [])[0].get("id") == "t1"
        assert isinstance(saved.get("relationships"), dict)

    def test_disambiguation_feedback_persisted(self, temp_project):
        """회귀: 중/낮은 신뢰도 모호성 해소가 Writer에 보여야 함 (state.json에 기록)."""
        manager = StateManager(temp_project)

        result = {
            "entities_appeared": [],
            "entities_new": [],
            "state_changes": [],
            "relationships_new": [],
            "uncertain": [
                {
                    "mention": "그 선배",
                    "context": "그 선배그를 한번 바라봤다",
                    "candidates": [{"type": "캐릭터", "id": "yaolao"}, {"type": "캐릭터", "id": "elder_zhang"}],
                    "suggested": "yaolao",
                    "confidence": 0.6,
                },
                {
                    "mention": "종주",
                    "context": "종주혈살비경에 나타남",
                    "candidates": ["xueshazonzhu", "lintian"],
                    "suggested": "xueshazonzhu",
                    "confidence": 0.4,
                },
            ],
        }

        warnings = manager.process_chapter_result(100, result)
        manager.save_state()

        state = json.loads(temp_project.state_file.read_text(encoding="utf-8"))
        assert isinstance(state.get("disambiguation_warnings"), list)
        assert isinstance(state.get("disambiguation_pending"), list)

        assert len(state["disambiguation_warnings"]) == 1
        assert len(state["disambiguation_pending"]) == 1

        warn = state["disambiguation_warnings"][0]
        assert warn.get("chapter") == 100
        assert warn.get("mention") == "그 선배"
        assert warn.get("chosen_id") == "yaolao"

        pending = state["disambiguation_pending"][0]
        assert pending.get("chapter") == 100
        assert pending.get("mention") == "종주"

        # 반환값에도 보이는 경고가 포함되어야 함, CLI/로그 출력 용이
        assert any("모호성해소경고" in w for w in warnings)
        assert any("수동 확인 필요" in w for w in warnings)


class TestIndexManager:
    """인덱스매니저 테스트"""

    def test_add_and_get_chapter(self, temp_project):
        manager = IndexManager(temp_project)

        meta = ChapterMeta(
            chapter=100,
            title="돌파",
            location="천운종",
            word_count=3500,
            characters=["xiaoyan", "yaolao"]
        )
        manager.add_chapter(meta)

        result = manager.get_chapter(100)
        assert result is not None
        assert result["title"] == "돌파"
        assert "xiaoyan" in result["characters"]

    def test_add_scenes(self, temp_project):
        manager = IndexManager(temp_project)

        scenes = [
            SceneMeta(chapter=100, scene_index=1, start_line=1, end_line=50,
                     location="천운종·폐관실", summary="소염폐관돌파", characters=["xiaoyan"]),
            SceneMeta(chapter=100, scene_index=2, start_line=51, end_line=100,
                     location="천운종·연무장", summary="실력 과시", characters=["xiaoyan", "lintian"])
        ]
        manager.add_scenes(100, scenes)

        result = manager.get_scenes(100)
        assert len(result) == 2
        assert result[0]["location"] == "천운종·폐관실"

    def test_record_appearance(self, temp_project):
        manager = IndexManager(temp_project)

        manager.record_appearance("xiaoyan", 100, ["소염", "그"], 0.95)
        manager.record_appearance("yaolao", 100, ["약로"], 0.92)

        appearances = manager.get_chapter_appearances(100)
        assert len(appearances) == 2

        entity_history = manager.get_entity_appearances("xiaoyan")
        assert len(entity_history) == 1

    def test_search_scenes_by_location(self, temp_project):
        manager = IndexManager(temp_project)

        scenes = [
            SceneMeta(chapter=100, scene_index=1, start_line=1, end_line=50,
                     location="천운종·폐관실", summary="폐관", characters=[]),
            SceneMeta(chapter=101, scene_index=1, start_line=1, end_line=50,
                     location="천운종·대전", summary="회의", characters=[])
        ]
        manager.add_scenes(100, scenes[:1])
        manager.add_scenes(101, scenes[1:])

        results = manager.search_scenes_by_location("천운종")
        assert len(results) == 2

    def test_get_stats(self, temp_project):
        manager = IndexManager(temp_project)

        manager.upsert_entity(
            EntityMeta(
                id="xiaoyan",
                type="캐릭터",
                canonical_name="소염",
                current={},
                first_appearance=1,
                last_appearance=1,
            )
        )
        manager.add_chapter(ChapterMeta(chapter=1, title="", location="", word_count=1000, characters=[]))
        manager.add_scenes(1, [SceneMeta(chapter=1, scene_index=1, start_line=1, end_line=50,
                                        location="", summary="", characters=[])])
        manager.record_appearance("xiaoyan", 1, [], 1.0)

        stats = manager.get_stats()
        assert stats["chapters"] == 1
        assert stats["scenes"] == 1
        assert stats["entities"] == 1

    def test_entity_alias_and_relationships(self, temp_project):
        manager = IndexManager(temp_project)

        entity_main = EntityMeta(
            id="xiaoyan",
            type="캐릭터",
            canonical_name="소염",
            tier="핵심",
            desc="주인공",
            current={"realm": "투자"},
            first_appearance=1,
            last_appearance=1,
            is_protagonist=True,
        )
        entity_other = EntityMeta(
            id="yaolao",
            type="캐릭터",
            canonical_name="약로",
            tier="중요",
            current={},
            first_appearance=1,
            last_appearance=2,
        )

        assert manager.upsert_entity(entity_main) is True
        assert manager.upsert_entity(entity_other) is True

        # 업데이트 current
        assert manager.update_entity_current("xiaoyan", {"realm": "투사"}) is True
        entity = manager.get_entity("xiaoyan")
        assert entity["current_json"]["realm"] == "투사"

        # 메타데이터업데이트
        entity_main.desc = "주인공(업데이트)"
        entity_main.last_appearance = 3
        assert manager.upsert_entity(entity_main, update_metadata=True) is False

        # 별칭 관리
        assert manager.register_alias("염제", "xiaoyan", "캐릭터")
        assert "염제" in manager.get_entity_aliases("xiaoyan")
        assert manager.get_entities_by_alias("염제")[0]["id"] == "xiaoyan"
        assert manager.remove_alias("염제", "xiaoyan")
        assert manager.get_entities_by_alias("염제") == []

        # 유형/등급/핵심/주인공쿼리
        assert len(manager.get_entities_by_type("캐릭터")) == 2
        assert any(e["id"] == "xiaoyan" for e in manager.get_entities_by_tier("핵심"))
        assert any(e["id"] == "xiaoyan" for e in manager.get_core_entities())
        assert manager.get_protagonist()["id"] == "xiaoyan"

        # 엔티티 아카이브
        assert manager.archive_entity("yaolao") is True
        assert all(e["id"] != "yaolao" for e in manager.get_entities_by_type("캐릭터"))
        assert any(
            e["id"] == "yaolao"
            for e in manager.get_entities_by_type("캐릭터", include_archived=True)
        )

        # 관계관리 (신규 + 업데이트)
        rel = RelationshipMeta(
            from_entity="xiaoyan",
            to_entity="yaolao",
            type="사제",
            description="제자 수련",
            chapter=1,
        )
        assert manager.upsert_relationship(rel) is True
        rel.description = "제자 수련(업데이트)"
        rel.chapter = 2
        assert manager.upsert_relationship(rel) is False

        assert len(manager.get_entity_relationships("xiaoyan", "from")) == 1
        assert len(manager.get_entity_relationships("yaolao", "to")) == 1
        assert len(manager.get_entity_relationships("xiaoyan", "both")) >= 1
        assert len(manager.get_relationship_between("xiaoyan", "yaolao")) == 1
        assert len(manager.get_recent_relationships(limit=5)) >= 1

    def test_state_changes_and_appearances(self, temp_project):
        manager = IndexManager(temp_project)

        entity = EntityMeta(
            id="xiaoyan",
            type="캐릭터",
            canonical_name="소염",
            current={},
            first_appearance=1,
            last_appearance=1,
        )
        manager.upsert_entity(entity)

        change = StateChangeMeta(
            entity_id="xiaoyan",
            field="realm",
            old_value="투자",
            new_value="투사",
            reason="돌파",
            chapter=2,
        )
        change_id = manager.record_state_change(change)
        assert change_id > 0

        assert len(manager.get_entity_state_changes("xiaoyan")) == 1
        assert len(manager.get_recent_state_changes(limit=5)) == 1
        assert len(manager.get_chapter_state_changes(2)) == 1

        # 출연 기록 (skip_if_exists 분기 포함)
        manager.record_appearance("xiaoyan", 2, ["소염"], 1.0)
        manager.record_appearance("xiaoyan", 2, ["소염"], 1.0, skip_if_exists=True)
        manager.record_appearance("xiaoyan", 3, ["소염"], 1.0)

        assert len(manager.get_entity_appearances("xiaoyan")) == 2
        assert len(manager.get_recent_appearances(limit=5)) >= 1
        assert len(manager.get_chapter_appearances(2)) == 1

    def test_chapter_queries_and_bulk(self, temp_project):
        manager = IndexManager(temp_project)

        manager.add_chapter(
            ChapterMeta(
                chapter=1,
                title="시작점",
                location="천운종",
                word_count=1000,
                characters=["xiaoyan"],
            )
        )
        manager.add_chapter(
            ChapterMeta(
                chapter=2,
                title="돌파",
                location="천운종",
                word_count=1200,
                characters=["xiaoyan", "yaolao"],
            )
        )

        recent = manager.get_recent_chapters()
        assert recent[0]["chapter"] == 2

        scenes = [
            SceneMeta(
                chapter=1,
                scene_index=1,
                start_line=1,
                end_line=50,
                location="천운종·폐관실",
                summary="폐관",
                characters=["xiaoyan"],
            ),
            SceneMeta(
                chapter=1,
                scene_index=2,
                start_line=51,
                end_line=80,
                location="천운종·연무장",
                summary="연습",
                characters=["xiaoyan"],
            ),
        ]
        manager.add_scenes(1, scenes)
        assert len(manager.get_scenes(1)) == 2

        results = manager.search_scenes_by_location("천운종")
        assert len(results) >= 2

        stats = manager.process_chapter_data(
            chapter=10,
            title="시련",
            location="비경",
            word_count=1500,
            entities=[{"id": "xiaoyan", "type": "캐릭터", "mentions": ["소염"]}],
            scenes=[{"index": 1, "start_line": 1, "end_line": 20, "location": "비경", "summary": "오프닝", "characters": ["xiaoyan"]}],
        )
        assert stats["chapters"] == 1
        assert stats["scenes"] == 1
        assert stats["appearances"] == 1

    def test_debt_and_override_flow(self, temp_project):
        manager = IndexManager(temp_project)

        contract = OverrideContractMeta(
            chapter=1,
            constraint_type="SOFT_MICROPAYOFF",
            constraint_id="micropayoff_count",
            rationale_type="TRANSITIONAL_SETUP",
            rationale_text="복선필요",
            payback_plan="다음 챕터 보상",
            due_chapter=3,
            status="pending",
        )
        contract_id = manager.create_override_contract(contract)
        assert contract_id > 0

        # pending 상태허용업데이트
        contract.rationale_text = "조정 사유"
        contract.due_chapter = 4
        assert manager.create_override_contract(contract) == contract_id
        updated = manager.get_chapter_overrides(1)[0]
        assert updated["rationale_text"] == "조정 사유"
        assert updated["due_chapter"] == 4

        # 최종 상태 동결
        contract.status = "fulfilled"
        contract.rationale_text = "최종 사유"
        contract.due_chapter = 5
        manager.create_override_contract(contract)
        frozen = manager.get_chapter_overrides(1)[0]
        assert frozen["status"] == "fulfilled"
        assert frozen["rationale_text"] == "최종 사유"

        # pending으로 되돌리기 시도, 최종 상태 필드 변경 불가필드
        contract.status = "pending"
        contract.rationale_text = "적용되지 않아야 함"
        contract.due_chapter = 99
        manager.create_override_contract(contract)
        frozen_again = manager.get_chapter_overrides(1)[0]
        assert frozen_again["status"] == "fulfilled"
        assert frozen_again["rationale_text"] == "최종 사유"
        assert frozen_again["due_chapter"] == 5

        debt_contract_id = manager.create_override_contract(
            OverrideContractMeta(
                chapter=2,
                constraint_type="SOFT_HOOK_STRENGTH",
                constraint_id="hook_strength",
                rationale_type="ARC_TIMING",
                rationale_text="리듬 배치",
                payback_plan="후속 보강",
                due_chapter=4,
                status="pending",
            )
        )

        debt1 = ChaseDebtMeta(
            debt_type="hook_strength",
            original_amount=1.0,
            current_amount=1.0,
            interest_rate=0.1,
            source_chapter=1,
            due_chapter=2,
            override_contract_id=debt_contract_id,
            status="active",
        )
        debt2 = ChaseDebtMeta(
            debt_type="micropayoff",
            original_amount=2.0,
            current_amount=2.0,
            interest_rate=0.2,
            source_chapter=1,
            due_chapter=2,
            override_contract_id=debt_contract_id,
            status="active",
        )
        debt_id_1 = manager.create_debt(debt1)
        debt_id_2 = manager.create_debt(debt2)
        assert len(manager.get_active_debts()) == 2
        assert manager.get_total_debt_balance() > 0

        # 이자 계산와멱등성 보호
        result = manager.accrue_interest(current_chapter=2)
        assert result["debts_processed"] == 2
        result_again = manager.accrue_interest(current_chapter=2)
        assert result_again["skipped_already_processed"] == 2

        # 연체 표시
        result_overdue = manager.accrue_interest(current_chapter=3)
        assert result_overdue["new_overdues"] >= 1
        overdue = manager.get_overdue_debts(current_chapter=3)
        assert any(d["status"] == "overdue" for d in overdue)
        history = manager.get_debt_history(debt_id_1)
        assert any(h["event_type"] == "interest_accrued" for h in history)

        # 금액 검증
        error = manager.pay_debt(debt_id_1, 0, chapter=3)
        assert "error" in error

        # 부분 상환
        partial = manager.pay_debt(debt_id_1, 0.5, chapter=3)
        assert partial["fully_paid"] is False

        # 완전 상환 (다른 채무가 남아있을 때 fulfilled 되지 않아야 함)
        full = manager.pay_debt(debt_id_1, 100, chapter=3)
        assert full["fully_paid"] is True
        assert full["override_fulfilled"] is False

        # 마지막 채무 정산 -> fulfilled
        full2 = manager.pay_debt(debt_id_2, 100, chapter=3)
        assert full2["fully_paid"] is True
        assert full2["override_fulfilled"] is True

    def test_reading_power_and_debt_summary(self, temp_project):
        manager = IndexManager(temp_project)

        # 추독력메타데이터
        manager.save_chapter_reading_power(
            ChapterReadingPowerMeta(
                chapter=1,
                hook_type="갈망훅",
                hook_strength="strong",
                coolpoint_patterns=["권위 뒤집기", "신분정체폭로"],
                micropayoffs=["능력 실현"],
                hard_violations=[],
                soft_suggestions=["SOFT_HOOK_STRENGTH"],
                is_transition=False,
                override_count=1,
                debt_balance=1.5,
            )
        )
        manager.save_chapter_reading_power(
            ChapterReadingPowerMeta(
                chapter=2,
                hook_type="서스펜스훅",
                hook_strength="medium",
                coolpoint_patterns=["신분정체폭로"],
                micropayoffs=["정보 실현"],
                hard_violations=["HARD-004"],
                soft_suggestions=[],
                is_transition=True,
                override_count=0,
                debt_balance=0.0,
            )
        )

        record = manager.get_chapter_reading_power(1)
        assert record["hook_type"] == "갈망훅"
        assert "신분정체폭로" in record["coolpoint_patterns"]
        assert record["is_transition"] == 0  # SQLite 스토리지는 0/1
        assert manager.get_chapter_reading_power(999) is None

        recent = manager.get_recent_reading_power(limit=2)
        assert len(recent) == 2

        pattern_stats = manager.get_pattern_usage_stats(last_n_chapters=5)
        assert pattern_stats.get("신분정체폭로") == 2

        hook_stats = manager.get_hook_type_stats(last_n_chapters=5)
        assert hook_stats.get("갈망훅") == 1

        # 채무 요약
        contract_id = manager.create_override_contract(
            OverrideContractMeta(
                chapter=3,
                constraint_type="SOFT_HOOK_STRENGTH",
                constraint_id="hook_strength",
                rationale_type="ARC_TIMING",
                rationale_text="리듬 배치",
                payback_plan="후속 보강",
                due_chapter=5,
                status="pending",
            )
        )
        manager.create_debt(
            ChaseDebtMeta(
                debt_type="hook_strength",
                original_amount=1.0,
                current_amount=1.0,
                interest_rate=0.1,
                source_chapter=3,
                due_chapter=4,
                override_contract_id=contract_id,
                status="active",
            )
        )
        manager.create_debt(
            ChaseDebtMeta(
                debt_type="micropayoff",
                original_amount=2.0,
                current_amount=2.0,
                interest_rate=0.1,
                source_chapter=3,
                due_chapter=4,
                override_contract_id=0,
                status="overdue",
            )
        )

        summary = manager.get_debt_summary()
        assert summary["active_debts"] == 1
        assert summary["overdue_debts"] == 1
        assert summary["pending_overrides"] >= 1
        assert summary["total_balance"] == summary["active_total"] + summary["overdue_total"]

        pending = manager.get_pending_overrides()
        assert any(o["id"] == contract_id for o in pending)
        pending_before = manager.get_pending_overrides(before_chapter=10)
        assert any(o["id"] == contract_id for o in pending_before)
        overdue_overrides = manager.get_overdue_overrides(current_chapter=6)
        assert any(o["id"] == contract_id for o in overdue_overrides)

        other_id = manager.create_override_contract(
            OverrideContractMeta(
                chapter=4,
                constraint_type="SOFT_EXPECTATION_OVERLOAD",
                constraint_id="expectation_count",
                rationale_type="EDITORIAL_INTENT",
                rationale_text="작가인텐트",
                payback_plan="후속 보충",
                due_chapter=6,
                status="pending",
            )
        )
        assert manager.fulfill_override(other_id) is True
        assert manager.get_chapter_overrides(4)[0]["status"] == "fulfilled"

    def test_review_metrics_and_trends(self, temp_project):
        manager = IndexManager(temp_project)

        manager.save_review_metrics(
            ReviewMetrics(
                start_chapter=1,
                end_chapter=1,
                overall_score=48,
                dimension_scores={
                    "카타르시스 밀도": 8,
                    "설정 일관성": 7,
                    "리듬 조절": 7,
                    "인물 조형": 8,
                    "연속성": 9,
                    "추독력": 9,
                },
                severity_counts={"critical": 0, "high": 1, "medium": 2, "low": 0},
                critical_issues=[],
                report_file="reviews/review_ch1-1.md",
            )
        )
        manager.save_review_metrics(
            ReviewMetrics(
                start_chapter=2,
                end_chapter=2,
                overall_score=42,
                dimension_scores={
                    "카타르시스 밀도": 6,
                    "설정 일관성": 8,
                    "리듬 조절": 7,
                    "인물 조형": 7,
                    "연속성": 7,
                    "추독력": 7,
                },
                severity_counts={"critical": 1, "high": 0, "medium": 1, "low": 2},
                critical_issues=["설정 자기모순"],
                report_file="reviews/review_ch2-2.md",
            )
        )

        recent = manager.get_recent_review_metrics(limit=2)
        assert len(recent) == 2

        trends = manager.get_review_trend_stats(last_n=5)
        assert trends["count"] == 2
        assert trends["overall_avg"] > 0
        assert "카타르시스 밀도" in trends["dimension_avg"]

    def test_writing_checklist_score_persistence_and_trend(self, temp_project):
        manager = IndexManager(temp_project)

        manager.save_writing_checklist_score(
            WritingChecklistScoreMeta(
                chapter=10,
                template="plot",
                total_items=6,
                required_items=4,
                completed_items=4,
                completed_required=3,
                total_weight=6.2,
                completed_weight=4.1,
                completion_rate=0.6667,
                score=78.5,
                score_breakdown={"weighted_completion_rate": 0.66},
                pending_items=["단락 끝 훅 남기기"],
            )
        )
        manager.save_writing_checklist_score(
            WritingChecklistScoreMeta(
                chapter=11,
                template="plot",
                total_items=6,
                required_items=4,
                completed_items=5,
                completed_required=4,
                total_weight=6.2,
                completed_weight=5.4,
                completion_rate=0.8333,
                score=86.0,
                score_breakdown={"weighted_completion_rate": 0.87},
                pending_items=[],
            )
        )

        one = manager.get_writing_checklist_score(10)
        assert one is not None
        assert one["chapter"] == 10
        assert one["score"] == 78.5

        recent = manager.get_recent_writing_checklist_scores(limit=2)
        assert len(recent) == 2
        assert recent[0]["chapter"] == 11

        trend = manager.get_writing_checklist_score_trend(last_n=5)
        assert trend["count"] == 2
        assert trend["score_avg"] > 0
        assert trend["completion_avg"] > 0

    def test_index_manager_cli(self, temp_project, monkeypatch, capsys):
        root = str(temp_project.project_root)
        manager = IndexManager(temp_project)

        # 기초 데이터
        manager.upsert_entity(
            EntityMeta(
                id="xiaoyan",
                type="캐릭터",
                canonical_name="소염",
                tier="핵심",
                current={"realm": "투자"},
                first_appearance=1,
                last_appearance=1,
                is_protagonist=True,
            )
        )
        manager.upsert_entity(
            EntityMeta(
                id="yaolao",
                type="캐릭터",
                canonical_name="약로",
                tier="중요",
                current={},
                first_appearance=1,
                last_appearance=2,
            )
        )

        manager.register_alias("염제", "xiaoyan", "캐릭터")
        manager.add_chapter(
            ChapterMeta(
                chapter=1,
                title="시작점",
                location="천운종",
                word_count=1000,
                characters=["xiaoyan"],
            )
        )
        manager.add_scenes(
            1,
            [
                SceneMeta(
                    chapter=1,
                    scene_index=1,
                    start_line=1,
                    end_line=20,
                    location="천운종·폐관실",
                    summary="폐관",
                    characters=["xiaoyan"],
                )
            ],
        )
        manager.record_appearance("xiaoyan", 1, ["소염"], 1.0)
        manager.record_state_change(
            StateChangeMeta(
                entity_id="xiaoyan",
                field="realm",
                old_value="투자",
                new_value="투사",
                reason="돌파",
                chapter=1,
            )
        )
        manager.upsert_relationship(
            RelationshipMeta(
                from_entity="xiaoyan",
                to_entity="yaolao",
                type="사제",
                description="제자 수련",
                chapter=1,
            )
        )

        # 추독력와채무
        manager.save_chapter_reading_power(
            ChapterReadingPowerMeta(
                chapter=1,
                hook_type="갈망훅",
                hook_strength="medium",
                coolpoint_patterns=["신분정체폭로"],
                micropayoffs=["능력 실현"],
                hard_violations=[],
                soft_suggestions=[],
            )
        )
        contract_id = manager.create_override_contract(
            OverrideContractMeta(
                chapter=1,
                constraint_type="SOFT_HOOK_STRENGTH",
                constraint_id="hook_strength",
                rationale_type="ARC_TIMING",
                rationale_text="리듬 배치",
                payback_plan="후속 보강",
                due_chapter=2,
                status="pending",
            )
        )
        debt_id = manager.create_debt(
            ChaseDebtMeta(
                debt_type="hook_strength",
                original_amount=1.0,
                current_amount=1.0,
                interest_rate=0.1,
                source_chapter=1,
                due_chapter=2,
                override_contract_id=contract_id,
                status="active",
            )
        )

        def run_cli(args):
            monkeypatch.setattr(sys, "argv", ["index_manager"] + args)
            index_manager_module.main()

        # 기본 명령
        run_cli(["--project-root", root, "stats"])
        run_cli(["--project-root", root, "get-chapter", "--chapter", "1"])
        run_cli(["--project-root", root, "get-chapter", "--chapter", "99"])
        run_cli(["--project-root", root, "recent-appearances", "--limit", "5"])
        run_cli(["--project-root", root, "entity-appearances", "--entity", "xiaoyan", "--limit", "5"])
        run_cli(["--project-root", root, "search-scenes", "--location", "천운종", "--limit", "5"])

        # 처리챕터
        run_cli(
            [
                "--project-root",
                root,
                "process-chapter",
                "--chapter",
                "2",
                "--title",
                "시련",
                "--location",
                "비경",
                "--word-count",
                "1200",
                "--entities",
                json.dumps([{"id": "xiaoyan", "mentions": ["소염"]}], ensure_ascii=False),
                "--scenes",
                json.dumps(
                    [
                        {
                            "index": 1,
                            "start_line": 1,
                            "end_line": 10,
                            "location": "비경",
                            "summary": "오프닝",
                            "characters": ["xiaoyan"],
                        }
                    ],
                    ensure_ascii=False,
                ),
            ]
        )

        # v5.1 명령
        run_cli(["--project-root", root, "get-entity", "--id", "xiaoyan"])
        run_cli(["--project-root", root, "get-entity", "--id", "missing"])
        run_cli(["--project-root", root, "get-core-entities"])
        run_cli(["--project-root", root, "get-protagonist"])
        run_cli(
            ["--project-root", root, "get-entities-by-type", "--type", "캐릭터", "--include-archived"]
        )
        run_cli(["--project-root", root, "get-by-alias", "--alias", "염제"])
        run_cli(["--project-root", root, "get-by-alias", "--alias", "존재하지 않음"])
        run_cli(["--project-root", root, "get-aliases", "--entity", "xiaoyan"])
        run_cli(["--project-root", root, "register-alias", "--alias", "염형", "--entity", "xiaoyan", "--type", "캐릭터"])
        run_cli(["--project-root", root, "get-relationships", "--entity", "xiaoyan", "--direction", "from"])
        run_cli(["--project-root", root, "get-state-changes", "--entity", "xiaoyan", "--limit", "20"])
        run_cli(
            [
                "--project-root",
                root,
                "upsert-entity",
                "--data",
                json.dumps(
                    {
                        "id": "lintian",
                        "type": "캐릭터",
                        "canonical_name": "임천",
                        "tier": "장식",
                        "current": {"realm": "투자"},
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        run_cli(
            [
                "--project-root",
                root,
                "upsert-relationship",
                "--data",
                json.dumps(
                    {
                        "from_entity": "xiaoyan",
                        "to_entity": "lintian",
                        "type": "상면",
                        "description": "첫 만남",
                        "chapter": 2,
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        run_cli(
            [
                "--project-root",
                root,
                "record-state-change",
                "--data",
                json.dumps(
                    {
                        "entity_id": "xiaoyan",
                        "field": "realm",
                        "old_value": "투자",
                        "new_value": "투사",
                        "reason": "돌파",
                        "chapter": 2,
                    },
                    ensure_ascii=False,
                ),
            ]
        )

        # v5.3 명령
        run_cli(["--project-root", root, "get-debt-summary"])
        run_cli(["--project-root", root, "get-recent-reading-power", "--limit", "5"])
        run_cli(["--project-root", root, "get-chapter-reading-power", "--chapter", "1"])
        run_cli(["--project-root", root, "get-chapter-reading-power", "--chapter", "99"])
        run_cli(["--project-root", root, "get-pattern-usage-stats", "--last-n", "5"])
        run_cli(["--project-root", root, "get-hook-type-stats", "--last-n", "5"])
        run_cli(["--project-root", root, "get-pending-overrides"])
        run_cli(["--project-root", root, "get-overdue-overrides", "--current-chapter", "3"])
        run_cli(["--project-root", root, "get-active-debts"])
        run_cli(["--project-root", root, "get-overdue-debts", "--current-chapter", "3"])
        run_cli(["--project-root", root, "accrue-interest", "--current-chapter", "3"])
        run_cli(["--project-root", root, "pay-debt", "--debt-id", str(debt_id), "--amount", "0", "--chapter", "3"])
        run_cli(["--project-root", root, "pay-debt", "--debt-id", str(debt_id), "--amount", "5", "--chapter", "3"])
        run_cli(
            [
                "--project-root",
                root,
                "create-override-contract",
                "--data",
                json.dumps(
                    {
                        "chapter": 3,
                        "constraint_type": "SOFT_MICROPAYOFF",
                        "constraint_id": "micropayoff_count",
                        "rationale_type": "TRANSITIONAL_SETUP",
                        "rationale_text": "복선",
                        "payback_plan": "후속 보상",
                        "due_chapter": 4,
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        run_cli(
            [
                "--project-root",
                root,
                "create-debt",
                "--data",
                json.dumps(
                    {
                        "debt_type": "micropayoff",
                        "original_amount": 1.0,
                        "current_amount": 1.0,
                        "interest_rate": 0.1,
                        "source_chapter": 3,
                        "due_chapter": 4,
                        "override_contract_id": contract_id,
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        run_cli(["--project-root", root, "fulfill-override", "--contract-id", str(contract_id)])
        run_cli(
            [
                "--project-root",
                root,
                "save-chapter-reading-power",
                "--data",
                json.dumps(
                    {
                        "chapter": 3,
                        "hook_type": "서스펜스훅",
                        "hook_strength": "medium",
                        "coolpoint_patterns": ["권위 뒤집기"],
                        "micropayoffs": ["정보 실현"],
                        "hard_violations": [],
                        "soft_suggestions": [],
                        "is_transition": False,
                        "override_count": 0,
                        "debt_balance": 0.0,
                    },
                    ensure_ascii=False,
                ),
            ]
        )

        review_payload = {
            "start_chapter": 1,
            "end_chapter": 1,
            "overall_score": 50,
            "dimension_scores": {
                "카타르시스 밀도": 8,
                "설정 일관성": 7,
                "리듬 조절": 8,
                "인물 조형": 8,
                "연속성": 9,
                "추독력": 10,
            },
            "severity_counts": {"critical": 0, "high": 1, "medium": 2, "low": 0},
            "critical_issues": [],
            "report_file": "reviews/review_ch1-1.md",
        }
        run_cli(
            [
                "--project-root",
                root,
                "save-review-metrics",
                "--data",
                json.dumps(review_payload, ensure_ascii=False),
            ]
        )
        run_cli(["--project-root", root, "get-recent-review-metrics", "--limit", "5"])
        run_cli(["--project-root", root, "get-review-trend-stats", "--last-n", "5"])

        checklist_payload = {
            "chapter": 5,
            "template": "plot",
            "total_items": 6,
            "required_items": 4,
            "completed_items": 4,
            "completed_required": 3,
            "total_weight": 6.5,
            "completed_weight": 4.8,
            "completion_rate": 0.6667,
            "score": 79.2,
            "score_breakdown": {"weighted_completion_rate": 0.73},
            "pending_items": ["훅 차별화"],
            "source": "context_manager",
        }
        run_cli(
            [
                "--project-root",
                root,
                "save-writing-checklist-score",
                "--data",
                json.dumps(checklist_payload, ensure_ascii=False),
            ]
        )
        run_cli(["--project-root", root, "get-writing-checklist-score", "--chapter", "5"])
        run_cli(["--project-root", root, "get-writing-checklist-score", "--chapter", "99"])
        run_cli(["--project-root", root, "get-recent-writing-checklist-scores", "--limit", "5"])
        run_cli(["--project-root", root, "get-writing-checklist-score-trend", "--last-n", "5"])

        capsys.readouterr()


class TestStyleSampler:
    """스타일 샘플 테스트"""

    def test_add_and_get_sample(self, temp_project):
        sampler = StyleSampler(temp_project)

        sample = StyleSample(
            id="ch100_s1",
            chapter=100,
            scene_type="전투",
            content="소염주먹을 날렸다...",
            score=0.85,
            tags=["전투", "격렬"]
        )
        assert sampler.add_sample(sample)

        results = sampler.get_samples_by_type("전투")
        assert len(results) == 1
        assert results[0].id == "ch100_s1"

    def test_extract_candidates(self, temp_project):
        sampler = StyleSampler(temp_project)

        scenes = [
            {"index": 1, "summary": "전투장면", "content": "소염주먹을 날렸다，투기가 무지개처럼 뻗어나가 상대를 삼장이나 밀어냈고 주변 공기가 웅웅 울렸다..." + "a" * 200}
        ]

        # 낮은 점수 미추출
        candidates = sampler.extract_candidates(100, "", 70, scenes)
        assert len(candidates) == 0

        # 높은 점수추출
        candidates = sampler.extract_candidates(100, "", 85, scenes)
        assert len(candidates) == 1
        assert candidates[0].scene_type == "전투"

    def test_select_samples_for_chapter(self, temp_project):
        sampler = StyleSampler(temp_project)

        # 몇 가지 샘플 추가
        for i in range(3):
            sampler.add_sample(StyleSample(
                id=f"battle_{i}",
                chapter=i,
                scene_type="전투",
                content=f"전투내용 {i}",
                score=0.9,
                tags=[]
            ))

        samples = sampler.select_samples_for_chapter("이번 챕터에는 격렬한전투")
        assert len(samples) <= 3
        assert all(s.scene_type == "전투" for s in samples)


class TestRAGAdapter:
    """RAG 어댑터 테스트 (API 호출 미포함)"""

    def test_bm25_search(self, temp_project):
        adapter = RAGAdapter(temp_project)

        # 수동으로 테스트 데이터 삽입
        with adapter._get_conn() as conn:
            cursor = conn.cursor()

            # 벡터 레코드 삽입 (빈 벡터, BM25만 테스트)
            cursor.execute("""
                INSERT INTO vectors (chunk_id, chapter, scene_index, content, embedding)
                VALUES (?, ?, ?, ?, ?)
            """, ("ch1_s1", 1, 1, "소염천운종에서 투기를 수련하다", b""))

            cursor.execute("""
                INSERT INTO vectors (chunk_id, chapter, scene_index, content, embedding)
                VALUES (?, ?, ?, ?, ?)
            """, ("ch1_s2", 1, 2, "약로연단 기술을 전수하다", b""))

            conn.commit()

            # 업데이트 BM25 인덱스
            adapter._update_bm25_index(cursor, "ch1_s1", "소염천운종에서 투기를 수련하다")
            adapter._update_bm25_index(cursor, "ch1_s2", "약로연단 기술을 전수하다")
            conn.commit()

        # BM25 검색
        results = adapter.bm25_search("소염수련", top_k=5)
        assert len(results) >= 1
        assert results[0].chunk_id == "ch1_s1"

    def test_tokenize(self, temp_project):
        adapter = RAGAdapter(temp_project)

        tokens = adapter._tokenize("소염hello세계world")
        assert "소" in tokens
        assert "염" in tokens
        assert "hello" in tokens
        assert "world" in tokens


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
