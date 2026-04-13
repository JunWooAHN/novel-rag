#!/usr/bin/env python3
"""
시각화 상태 보고서 시스템 (Status Reporter)

핵심 개념: 1000개 챕터를 마주하면 작가는 방향을 잃는다. "거시적 조감" 능력이 필요하다.

기능:
1. 캐릭터 활동도 분석: 너무 오래 미등장한 캐릭터(이탈 통계)
2. 복선 깊이 분석: 너무 오래 방치된 복선（20만 자 이상 미회수）+ 긴급도 정렬
3. 카타르시스 리듬 분포: 전체 책의 클라이맥스 분포 빈도(히트맵)
4. 글자 수 분포 통계: 각 권, 각 편의 글자 수 분포
5. 인간관계 그래프: 호감도/적대도 트렌드
6. Strand Weave 리듬 분석: Quest/Fire/Constellation 3라인 비율 통계
7. 복선 긴급도 정렬: 3단계 시스템 기반（핵심/서브/장식）우선순위 계산

출력 형식:
  - Markdown 보고서（.webnovel/health_report.md）
  - Mermaid 차트 포함（캐릭터 관계도, 카타르시스 히트맵）

사용 방법:
  # 전체 건강 보고서 생성
  python status_reporter.py --output .webnovel/health_report.md

  # 캐릭터 활동도만 분석
  python status_reporter.py --focus characters

  # 복선만 분석
  python status_reporter.py --focus foreshadowing

  # 카타르시스 리듬만 분석
  python status_reporter.py --focus pacing

  # Strand Weave 리듬 분석
  python status_reporter.py --focus strand

보고서 예시：
  # 전체 책 건강 보고서

  ## 📊 기본 데이터

  - **총 챕터 수**: 450 챕터
  - **총 글자 수**: 1,985,432 자
  - **평균 챕터 글자 수**: 4,412 자
  - **창작 진행률**: 99.3%（목표 200만 자）

  ## ⚠️ 캐릭터 이탈（3명）

  | 캐릭터 | 마지막 등장 | 부재 챕터 | 상태 |
  |------|---------|---------|------|
  | 이설 | chapter 350 | 100 챕터 | 🔴 심각한 이탈 |
  | 혈살문주 | chapter 300 | 150 챕터 | 🔴 심각한 이탈 |
  | 천운종종주 | chapter 400 | 50 챕터 | 🟡 경미한 이탈 |

  ## ⚠️ 복선 시간 초과（2건）

  | 복선 내용 | 설치 챕터 | 경과 챕터 | 상태 |
  |---------|---------|---------|------|
  | "임가보고 명문의 비밀" | chapter 200 | 250 챕터 | 🔴 심각한 시간 초과 |
  | "신비한 옥패의 내력" | chapter 270 | 180 챕터 | 🟡 경미한 시간 초과 |

  ## 📈 카타르시스 리듬 분포

  ```
  chapter 1-100    ████████████ 우수（1200자/카타르시스）
  chapter 101-200  ██████████ 양호（1500자/카타르시스）
  chapter 201-300  ████████ 양호（1600자/카타르시스）
  chapter 301-400  ████ 낮음（2200자/카타르시스）⚠️
  chapter 401-450  ██████ 양호（1550자/카타르시스）
  ```

  ## 💑 인간관계 트렌드

  ```mermaid
  graph LR
    주인공 -->|호감도95| 이설
    주인공 -->|호감도60| 모용설
    주인공 -->|적대도100| 혈살문
  ```
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from collections import defaultdict
from project_locator import resolve_project_root
from chapter_paths import extract_chapter_num_from_filename
from runtime_compat import enable_windows_utf8_stdio

# 설정 임포트
try:
    from data_modules.config import get_config, DataModulesConfig
    from data_modules.index_manager import IndexManager
    from data_modules.state_validator import (
        get_chapter_meta_entry,
        is_resolved_foreshadowing_status,
        normalize_foreshadowing_tier,
        normalize_state_runtime_sections,
        resolve_chapter_field,
        to_positive_int,
    )
except ImportError:
    from scripts.data_modules.config import get_config, DataModulesConfig
    from scripts.data_modules.index_manager import IndexManager
    from scripts.data_modules.state_validator import (
        get_chapter_meta_entry,
        is_resolved_foreshadowing_status,
        normalize_foreshadowing_tier,
        normalize_state_runtime_sections,
        resolve_chapter_field,
        to_positive_int,
    )

def _is_resolved_foreshadowing_status(raw_status: Any) -> bool:
    """복선 회수 여부 판단（과거 필드 및 동의어 호환）."""
    return is_resolved_foreshadowing_status(raw_status)

def _enable_windows_utf8_stdio() -> None:
    """Windows에서 UTF-8 출력 활성화; pytest 환경에서는 캡처 충돌 방지를 위해 건너뜀."""
    enable_windows_utf8_stdio(skip_in_pytest=True)


class StatusReporter:
    """상태 보고서 생성기"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.config = get_config(self.project_root)
        self.state_file = self.project_root / ".webnovel/state.json"
        self.chapters_dir = self.project_root / "chapters"

        self.state = None
        self.chapters_data = []
        self._reading_power_cache: Dict[int, Optional[Dict[str, Any]]] = {}

        # v5.1 도입: IndexManager를 사용하여 엔티티 읽기
        self._index_manager = IndexManager(self.config)

    def _extract_stats_field(self, content: str, field_name: str) -> str:
        """
        “이번 챕터 통계” 블록에서 필드 값을 추출. 예시:
        - **주도Strand**: quest
        """
        pattern = rf"^\s*-\s*\*\*{re.escape(field_name)}\*\*\s*:\s*(.+?)\s*$"
        for line in content.splitlines():
            m = re.match(pattern, line)
            if m:
                return m.group(1).strip()
        return ""

    def load_state(self) -> bool:
        """state.json 로드"""
        if not self.state_file.exists():
            print(f"❌ 상태 파일 미존재: {self.state_file}")
            return False

        with open(self.state_file, 'r', encoding='utf-8') as f:
            self.state = json.load(f)

        if isinstance(self.state, dict):
            self.state = normalize_state_runtime_sections(self.state)

        return True

    def _to_positive_int(self, value: Any) -> Optional[int]:
        """입력을 양의 정수로 파싱; 실패 시 None 반환."""
        return to_positive_int(value)

    def _normalize_foreshadowing_tier(self, raw_tier: Any) -> Tuple[str, float]:
        """복선 등급을 표준화하고 대응하는 가중치를 반환."""
        tier = normalize_foreshadowing_tier(raw_tier)

        if tier == "핵심":
            return "핵심", self.config.foreshadowing_tier_weight_core
        if tier == "장식":
            return "장식", self.config.foreshadowing_tier_weight_decor
        return "서브", self.config.foreshadowing_tier_weight_sub

    def _resolve_chapter_field(self, item: Dict[str, Any], keys: List[str]) -> Optional[int]:
        """후보 키 순서대로 챕터 번호를 읽음."""
        return resolve_chapter_field(item, keys)

    def _collect_foreshadowing_records(self) -> List[Dict[str, Any]]:
        """미회수 복선을 수집하고, 실제 필드 기반으로 분석 레코드를 구성."""
        if not self.state:
            return []

        current_chapter = self.state.get("progress", {}).get("current_chapter", 0)
        plot_threads = self.state.get("plot_threads", {}) if isinstance(self.state.get("plot_threads"), dict) else {}
        foreshadowing = plot_threads.get("foreshadowing", [])
        if not isinstance(foreshadowing, list):
            return []

        records: List[Dict[str, Any]] = []
        for item in foreshadowing:
            if not isinstance(item, dict):
                continue
            if _is_resolved_foreshadowing_status(item.get("status")):
                continue

            content = str(item.get("content") or "").strip() or "[이름 없는 복선]"
            tier, weight = self._normalize_foreshadowing_tier(item.get("tier"))

            planted_chapter = self._resolve_chapter_field(
                item,
                [
                    "planted_chapter",
                    "added_chapter",
                    "source_chapter",
                    "start_chapter",
                    "chapter",
                ],
            )
            target_chapter = self._resolve_chapter_field(
                item,
                [
                    "target_chapter",
                    "due_chapter",
                    "deadline_chapter",
                    "resolve_by_chapter",
                    "target",
                ],
            )

            elapsed = None
            if planted_chapter is not None:
                elapsed = max(0, current_chapter - planted_chapter)

            remaining = None
            if target_chapter is not None:
                remaining = target_chapter - current_chapter

            if remaining is not None and remaining < 0:
                overtime_status = "🔴 만료됨"
            elif elapsed is None:
                overtime_status = "⚪ 데이터 부족"
            else:
                overtime_status = self._get_foreshadowing_status(elapsed)

            urgency: Optional[float] = None
            if (
                planted_chapter is not None
                and target_chapter is not None
                and target_chapter > planted_chapter
                and elapsed is not None
            ):
                urgency = round((elapsed / (target_chapter - planted_chapter)) * weight, 2)
            elif (
                planted_chapter is not None
                and target_chapter is not None
                and target_chapter <= planted_chapter
                and elapsed is not None
            ):
                urgency = round(weight * 2.0, 2)

            if remaining is not None and remaining < 0:
                urgency_status = "🔴 만료됨"
            elif urgency is None:
                urgency_status = "⚪ 데이터 부족"
            else:
                urgency_status = self._get_urgency_status(urgency, remaining if remaining is not None else 0)

            records.append(
                {
                    "content": content,
                    "tier": tier,
                    "weight": weight,
                    "planted_chapter": planted_chapter,
                    "target_chapter": target_chapter,
                    "elapsed": elapsed,
                    "remaining": remaining,
                    "status": overtime_status,
                    "urgency": urgency,
                    "urgency_status": urgency_status,
                }
            )

        return records

    def _get_chapter_meta(self, chapter: int) -> Dict[str, Any]:
        """지정 챕터의 chapter_meta를 읽음（0001/1 두 가지 키 지원）."""
        if not self.state:
            return {}
        return get_chapter_meta_entry(self.state, chapter)

    def _parse_pattern_count(self, raw_value: Any) -> Optional[int]:
        """카타르시스 패턴 수량을 파싱; 실패 시 None 반환."""
        if raw_value is None:
            return None

        if isinstance(raw_value, list):
            patterns = [str(x).strip() for x in raw_value if str(x).strip()]
            return len(set(patterns))

        if isinstance(raw_value, str):
            text = raw_value.strip()
            if not text:
                return None
            parts = [p.strip() for p in re.split(r"[、,，/|+；;]+", text) if p.strip()]
            if parts:
                return len(set(parts))
            return 1

        return None

    def _get_chapter_reading_power_cached(self, chapter: int) -> Optional[Dict[str, Any]]:
        """chapter_reading_power를 읽고 캐싱."""
        if chapter in self._reading_power_cache:
            return self._reading_power_cache[chapter]

        try:
            record = self._index_manager.get_chapter_reading_power(chapter)
        except Exception:
            record = None

        self._reading_power_cache[chapter] = record
        return record

    def _get_chapter_cool_points(self, chapter: int, chapter_data: Dict[str, Any]) -> Tuple[Optional[int], str]:
        """단일 챕터 카타르시스 수 조회(실제 메타데이터 우선)."""
        reading_power = self._get_chapter_reading_power_cached(chapter)
        if isinstance(reading_power, dict):
            count = self._parse_pattern_count(reading_power.get("coolpoint_patterns"))
            if count is not None:
                return count, "chapter_reading_power"

        chapter_meta = self._get_chapter_meta(chapter)
        for key in ("coolpoint_patterns", "coolpoint_pattern", "cool_point_patterns", "cool_point_pattern", "patterns", "pattern"):
            count = self._parse_pattern_count(chapter_meta.get(key))
            if count is not None:
                return count, "chapter_meta"

        count = self._parse_pattern_count(chapter_data.get("cool_point"))
        if count is not None:
            return count, "chapter_stats"

        return None, "none"

    def scan_chapters(self):
        """모든 챕터 파일 스캔"""
        if not self.chapters_dir.exists():
            print(f"⚠️  본문 디렉토리 미존재: {self.chapters_dir}")
            return

        # 두 가지 디렉토리 구조 지원:
        # 1) chapters/chapter_0001.md (legacy: 제0001장.md)
        # 2) chapters/vol_1/chapter_001-title.md (legacy: 제1권/제001장-제목.md)
        # NOTE: glob pattern uses legacy Chinese prefix for backward compatibility
        chapter_files = sorted(self.chapters_dir.rglob("제*.md"))

        # v5.1 도입: SQLite에서 알려진 캐릭터 이름 조회
        known_character_names: List[str] = []
        protagonist_name = ""
        if self.state:
            protagonist_name = self.state.get("protagonist_state", {}).get("name", "") or ""

        # SQLite에서 모든 캐릭터의 canonical_name 조회
        try:
            characters_from_db = self._index_manager.get_entities_by_type("캐릭터")
            known_character_names = [
                c.get("canonical_name", c.get("id", ""))
                for c in characters_from_db
                if c.get("canonical_name")
            ]
        except Exception:
            known_character_names = []

        for chapter_file in chapter_files:
            chapter_num = extract_chapter_num_from_filename(chapter_file.name)
            if not chapter_num:
                continue

            # 챕터 내용 읽기
            with open(chapter_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 글자 수 통계(Markdown 마크 제거)
            text = re.sub(r'```[\s\S]*?```', '', content)  # 코드 블록 제거
            text = re.sub(r'#+ .+', '', text)  # 제목 제거
            text = re.sub(r'---', '', text)  # 구분선 제거
            word_count = len(text.strip())

            # 주도 Strand / 카타르시스 유형（우선 "이번 챕터 통계"에서 파싱）
            # NOTE: legacy Chinese field names kept as fallback for backward compatibility
            dominant_strand = (self._extract_stats_field(content, "주도Strand") or self._extract_stats_field(content, "주도 Strand") or "").lower()
            cool_point_type = self._extract_stats_field(content, "카타르시스") or self._extract_stats_field(content, "카타르시스 유형")

            # v5.1 도입: 캐릭터 추출을 SQLite chapters 테이블에서 읽기
            characters: List[str] = []
            try:
                chapter_info = self._index_manager.get_chapter(chapter_num)
                if chapter_info and chapter_info.get("characters"):
                    stored = chapter_info["characters"]
                    if isinstance(stored, str):
                        stored = json.loads(stored)
                    if isinstance(stored, list):
                        for entity_id in stored:
                            entity_id = str(entity_id).strip()
                            if not entity_id:
                                continue
                            # canonical_name 조회 시도
                            entity = self._index_manager.get_entity(entity_id)
                            name = entity.get("canonical_name", entity_id) if entity else entity_id
                            characters.append(name)
            except Exception:
                characters = []

            if not characters and (protagonist_name or known_character_names):
                # 후보 규모 제한, 초대형 캐릭터 라이브러리에서의 속도 저하 방지
                candidates = []
                if protagonist_name:
                    candidates.append(protagonist_name)
                candidates.extend(known_character_names[:self.config.character_candidates_limit])

                seen = set()
                for name in candidates:
                    if not name or name in seen:
                        continue
                    if name in content:
                        characters.append(name)
                        seen.add(name)

            self.chapters_data.append({
                "chapter": chapter_num,
                "file": chapter_file,
                "word_count": word_count,
                "characters": characters,
                "dominant": dominant_strand,
                "cool_point": cool_point_type,
            })

    def analyze_characters(self) -> Dict:
        """캐릭터 활동도 분석（v5.1 도입, v5.4 유지）"""
        if not self.state:
            return {}

        current_chapter = self.state.get("progress", {}).get("current_chapter", 0)

        # v5.1 도입: SQLite에서 모든 캐릭터 조회
        try:
            characters_list = self._index_manager.get_entities_by_type("캐릭터")
        except Exception:
            characters_list = []

        # 각 캐릭터의 마지막 등장 챕터 통계
        character_activity = {}

        for char in characters_list:
            char_name = char.get("canonical_name", char.get("id", ""))
            if not char_name:
                continue

            # 마지막 등장 챕터 검색
            last_appearance = char.get("last_appearance", 0) or 0

            # chapters_data에서도 확인
            for ch_data in self.chapters_data:
                if char_name in ch_data.get("characters", []):
                    last_appearance = max(last_appearance, ch_data["chapter"])

            absence = current_chapter - last_appearance

            character_activity[char_name] = {
                "last_appearance": last_appearance,
                "absence": absence,
                "status": self._get_absence_status(absence)
            }

        return character_activity

    def _get_absence_status(self, absence: int) -> str:
        """이탈 상태 판단"""
        if absence == 0:
            return "✅ 활성"
        elif absence < self.config.character_absence_warning:
            return "🟢 정상"
        elif absence < self.config.character_absence_critical:
            return "🟡 경미한 이탈"
        else:
            return "🔴 심각한 이탈"

    def analyze_foreshadowing(self) -> List[Dict]:
        """복선 깊이 분석"""
        records = self._collect_foreshadowing_records()
        return [
            {
                "content": item["content"],
                "planted_chapter": item["planted_chapter"],
                "estimated_chapter": item["planted_chapter"],
                "target_chapter": item["target_chapter"],
                "elapsed": item["elapsed"],
                "status": item["status"],
            }
            for item in records
        ]

    def _get_foreshadowing_status(self, elapsed: int) -> str:
        """복선 시간 초과 상태 판단"""
        if elapsed < self.config.foreshadowing_urgency_pending_medium:
            return "🟢 정상"
        elif elapsed < self.config.foreshadowing_urgency_pending_high + 50:
            return "🟡 경미한 시간 초과"
        else:
            return "🔴 심각한 시간 초과"

    def analyze_foreshadowing_urgency(self) -> List[Dict]:
        """
        복선 긴급도 분석(3단계 시스템 기반)

        3단계 가중치：
        - 핵심(Core): 가중치 3.0 - 반드시 회수해야 하며, 그렇지 않으면 스토리 붕괴
        - 서브(Sub): 가중치 2.0 - 회수해야 하며, 그렇지 않으면 작가가 잊은 것처럼 보임
        - 장식(Decor): 가중치 1.0 - 회수하거나 안 해도 됨, 현실감만 증가

        긴급도 계산 공식：
        urgency = (경과 챕터 / 목표 회수 챕터) × 단계 가중치
        """
        records = self._collect_foreshadowing_records()
        urgency_list = [
            {
                "content": item["content"],
                "tier": item["tier"],
                "weight": item["weight"],
                "planted_chapter": item["planted_chapter"],
                "target_chapter": item["target_chapter"],
                "elapsed": item["elapsed"],
                "remaining": item["remaining"],
                "urgency": item["urgency"],
                "status": item["urgency_status"],
            }
            for item in records
        ]

        # “계산 가능 여부” 우선, 그 다음 긴급도 내림차순
        return sorted(
            urgency_list,
            key=lambda x: (x["urgency"] is None, -(x["urgency"] if x["urgency"] is not None else -1)),
        )

    def _get_urgency_status(self, urgency: float, remaining: int) -> str:
        """긴급도 상태 판단"""
        if remaining < 0:
            return "🔴 만료됨"
        elif urgency >= self.config.foreshadowing_tier_weight_sub:
            return "🔴 긴급"
        elif urgency >= 1.0:
            return "🟡 경고"
        else:
            return "🟢 정상"

    def analyze_strand_weave(self) -> Dict:
        """
        Strand Weave 리듬 분포 분석

        3라인 정의：
        - Quest（메인 스토리）: 전투, 퀘스트, 레벨업 - 목표 55-65%
        - Fire（감정）: 감정 라인, 인간관계 상호작용 - 목표 20-30%
        - Constellation（세계관）: 세계관 전개, 세력 배경 - 목표 10-20%

        검사 규칙：
        - Quest 라인 연속 5챕터 이하
        - Fire 라인 부재 10챕터 이하
        - Constellation 라인 부재 15챕터 이하
        """
        if not self.state:
            return {}

        strand_tracker = self.state.get("strand_tracker", {})
        history = strand_tracker.get("history", [])

        if not history:
            return {
                "has_data": False,
                "message": "Strand Weave 데이터 없음"
            }

        # 각 라인 비율 통계
        quest_count = 0
        fire_count = 0
        constellation_count = 0
        total = len(history)

        for entry in history:
            strand = (entry.get("strand") or entry.get("dominant") or "").lower()
            if strand in ["quest", "메인 스토리", "전투", "퀘스트"]:
                quest_count += 1
            elif strand in ["fire", "감정", "감정 라인", "상호작용"]:
                fire_count += 1
            elif strand in ["constellation", "세계관", "배경", "세력"]:
                constellation_count += 1

        # 비율 계산
        quest_ratio = (quest_count / total * 100) if total > 0 else 0
        fire_ratio = (fire_count / total * 100) if total > 0 else 0
        constellation_ratio = (constellation_count / total * 100) if total > 0 else 0

        # 위반 검사
        violations = []

        # Quest 연속 5챕터 초과 검사
        quest_streak = 0
        max_quest_streak = 0
        for entry in history:
            strand = (entry.get("strand") or entry.get("dominant") or "").lower()
            if strand in ["quest", "메인 스토리", "전투", "퀘스트"]:
                quest_streak += 1
                max_quest_streak = max(max_quest_streak, quest_streak)
            else:
                quest_streak = 0

        if max_quest_streak > self.config.strand_quest_max_consecutive:
            violations.append(f"Quest 라인 연속 {max_quest_streak} 챕터(초과 {self.config.strand_quest_max_consecutive} 챕터 제한)")

        # Fire 부재 10챕터 초과 검사
        fire_gap = 0
        max_fire_gap = 0
        for entry in history:
            strand = (entry.get("strand") or entry.get("dominant") or "").lower()
            if strand in ["fire", "감정", "감정 라인", "상호작용"]:
                max_fire_gap = max(max_fire_gap, fire_gap)
                fire_gap = 0
            else:
                fire_gap += 1
        max_fire_gap = max(max_fire_gap, fire_gap)

        if max_fire_gap > self.config.strand_fire_max_gap:
            violations.append(f"Fire 라인 부재 {max_fire_gap} 챕터(초과 {self.config.strand_fire_max_gap} 챕터 제한)")

        # Constellation 부재 15챕터 초과 검사
        const_gap = 0
        max_const_gap = 0
        for entry in history:
            strand = (entry.get("strand") or entry.get("dominant") or "").lower()
            if strand in ["constellation", "세계관", "배경", "세력"]:
                max_const_gap = max(max_const_gap, const_gap)
                const_gap = 0
            else:
                const_gap += 1
        max_const_gap = max(max_const_gap, const_gap)

        if max_const_gap > self.config.strand_constellation_max_gap:
            violations.append(f"Constellation 라인 부재 {max_const_gap} 챕터(초과 {self.config.strand_constellation_max_gap} 챕터 제한)")

        # 비율이 합리적 범위 내인지 검사
        cfg = self.config
        if quest_ratio < cfg.strand_quest_ratio_min:
            violations.append(f"Quest 비율 {quest_ratio:.1f}% 낮음(목표 {cfg.strand_quest_ratio_min}-{cfg.strand_quest_ratio_max}%）")
        elif quest_ratio > cfg.strand_quest_ratio_max:
            violations.append(f"Quest 비율 {quest_ratio:.1f}% 높음(목표 {cfg.strand_quest_ratio_min}-{cfg.strand_quest_ratio_max}%）")

        if fire_ratio < cfg.strand_fire_ratio_min:
            violations.append(f"Fire 비율 {fire_ratio:.1f}% 낮음(목표 {cfg.strand_fire_ratio_min}-{cfg.strand_fire_ratio_max}%）")
        elif fire_ratio > cfg.strand_fire_ratio_max:
            violations.append(f"Fire 비율 {fire_ratio:.1f}% 높음(목표 {cfg.strand_fire_ratio_min}-{cfg.strand_fire_ratio_max}%）")

        if constellation_ratio < cfg.strand_constellation_ratio_min:
            violations.append(f"Constellation 비율 {constellation_ratio:.1f}% 낮음(목표 {cfg.strand_constellation_ratio_min}-{cfg.strand_constellation_ratio_max}%）")
        elif constellation_ratio > cfg.strand_constellation_ratio_max:
            violations.append(f"Constellation 비율 {constellation_ratio:.1f}% 높음(목표 {cfg.strand_constellation_ratio_min}-{cfg.strand_constellation_ratio_max}%）")

        return {
            "has_data": True,
            "total_chapters": total,
            "quest": {"count": quest_count, "ratio": quest_ratio},
            "fire": {"count": fire_count, "ratio": fire_ratio},
            "constellation": {"count": constellation_count, "ratio": constellation_ratio},
            "violations": violations,
            "max_quest_streak": max_quest_streak,
            "max_fire_gap": max_fire_gap,
            "max_const_gap": max_const_gap,
            "health": "✅ 건강" if not violations else f"⚠️ {len(violations)} 개 문제"
        }

    def analyze_pacing(self) -> List[Dict]:
        """카타르시스 리듬 분포 분석（N챕터를 하나의 구간으로）"""
        segment_size = self.config.pacing_segment_size
        segments = []

        for i in range(0, len(self.chapters_data), segment_size):
            segment_chapters = self.chapters_data[i:i+segment_size]

            if not segment_chapters:
                continue

            start_ch = segment_chapters[0]["chapter"]
            end_ch = segment_chapters[-1]["chapter"]
            total_words = sum(ch["word_count"] for ch in segment_chapters)

            cool_points = 0
            chapters_with_data = 0
            source_counter: Dict[str, int] = {}

            for chapter_data in segment_chapters:
                chapter = chapter_data["chapter"]
                count, source = self._get_chapter_cool_points(chapter, chapter_data)
                source_counter[source] = source_counter.get(source, 0) + 1
                if count is None:
                    continue
                chapters_with_data += 1
                cool_points += count

            words_per_point = None
            if cool_points > 0:
                words_per_point = total_words / cool_points

            rating = self._get_pacing_rating(words_per_point)
            missing_chapters = len(segment_chapters) - chapters_with_data
            dominant_source = "none"
            if source_counter:
                dominant_source = max(source_counter.items(), key=lambda x: x[1])[0]

            segments.append({
                "start": start_ch,
                "end": end_ch,
                "total_words": total_words,
                "cool_points": cool_points,
                "words_per_point": words_per_point,
                "rating": rating,
                "missing_chapters": missing_chapters,
                "data_coverage": (chapters_with_data / len(segment_chapters)) if segment_chapters else 0.0,
                "dominant_source": dominant_source,
            })

        return segments

    def _get_pacing_rating(self, words_per_point: Optional[float]) -> str:
        """리듬 등급 판단"""
        if words_per_point is None:
            return "데이터 부족"
        if words_per_point < self.config.pacing_words_per_point_excellent:
            return "우수"
        elif words_per_point < self.config.pacing_words_per_point_good:
            return "양호"
        elif words_per_point < self.config.pacing_words_per_point_acceptable:
            return "합격"
        else:
            return "낮음⚠️"

    def _resolve_protagonist_entity_id(self) -> Optional[str]:
        """주인공 엔티티 ID 파싱（index.db 우선）."""
        protagonist = self._index_manager.get_protagonist()
        if protagonist and protagonist.get("id"):
            return str(protagonist["id"])

        if not self.state:
            return None
        name = str(self.state.get("protagonist_state", {}).get("name", "") or "").strip()
        if not name:
            return None
        hits = self._index_manager.get_entities_by_alias(name)
        if hits:
            return str(hits[0].get("id") or "")
        return None

    def _generate_relationship_graph_from_index(self) -> str:
        """index.db 기반으로 관계 그래프 생성."""
        protagonist_id = self._resolve_protagonist_entity_id()
        if not protagonist_id:
            return ""

        current_chapter = 0
        if self.state:
            current_chapter = int(self.state.get("progress", {}).get("current_chapter", 0) or 0)
        chapter = current_chapter if current_chapter > 0 else None

        graph = self._index_manager.build_relationship_subgraph(
            center_entity=protagonist_id,
            depth=2,
            chapter=chapter,
            top_edges=40,
        )
        if not graph.get("nodes"):
            return ""
        return self._index_manager.render_relationship_subgraph_mermaid(graph)

    def generate_relationship_graph(self) -> str:
        """인간관계 Mermaid 차트 생성"""
        if not self.state:
            return ""

        # v5.5: index.db 관계 그래프 우선 사용(설정으로 비활성화 가능)
        if bool(getattr(self.config, "relationship_graph_from_index_enabled", True)):
            try:
                graph = self._generate_relationship_graph_from_index()
                if graph:
                    return graph
            except Exception:
                # 이전 로직으로 폴백, 보고서 생성 중단 방지
                pass

        # 이전 버전 state.json relationships 구조 호환
        relationships = self.state.get("relationships", {})
        protagonist_name = self.state.get("protagonist_state", {}).get("name", "주인공")

        lines = ["```mermaid", "graph LR"]

        # 두 가지 형식 지원:
        # 형식1（신）: {"allies": [...], "enemies": [...]}
        # 형식2（구）: {"캐릭터명": {"affection": X, "hatred": Y}}

        allies = relationships.get("allies", [])
        enemies = relationships.get("enemies", [])

        if allies or enemies:
            # 새 형식
            for ally in allies:
                if isinstance(ally, dict):
                    name = ally.get("name", "알 수 없음")
                    relation = ally.get("relation", "우호")
                    lines.append(f"    {protagonist_name} -->|{relation}| {name}")

            for enemy in enemies:
                if isinstance(enemy, dict):
                    name = enemy.get("name", "알 수 없음")
                    relation = enemy.get("relation", "적대")
                    lines.append(f"    {protagonist_name} -.->|{relation}| {name}")
        else:
            # 이전 형식 호환
            for char_name, rel_data in relationships.items():
                if isinstance(rel_data, dict):
                    affection = rel_data.get("affection", 0)
                    hatred = rel_data.get("hatred", 0)

                    if affection > 0:
                        lines.append(f"    {protagonist_name} -->|호감도{affection}| {char_name}")

                    if hatred > 0:
                        lines.append(f"    {protagonist_name} -.->|적대도{hatred}| {char_name}")

        lines.append("```")

        return "\n".join(lines)

    def generate_report(self, focus: str = "all") -> str:
        """건강 보고서 생성(Markdown 형식)"""

        report_lines = [
            "# 전체 책 건강 보고서",
            "",
            f"> **생성 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            ""
        ]

        # 기본 데이터
        if focus in ["all", "basic"]:
            report_lines.extend(self._generate_basic_stats())

        # 캐릭터 활동도
        if focus in ["all", "characters"]:
            report_lines.extend(self._generate_character_section())

        # 복선 깊이
        if focus in ["all", "foreshadowing"]:
            report_lines.extend(self._generate_foreshadowing_section())

        # 복선 긴급도(신규)
        if focus in ["all", "foreshadowing", "urgency"]:
            report_lines.extend(self._generate_urgency_section())

        # 카타르시스 리듬
        if focus in ["all", "pacing"]:
            report_lines.extend(self._generate_pacing_section())

        # Strand Weave 리듬(신규)
        if focus in ["all", "strand", "pacing"]:
            report_lines.extend(self._generate_strand_section())

        # 인간관계
        if focus in ["all", "relationships"]:
            report_lines.extend(self._generate_relationship_section())

        return "\n".join(report_lines)

    def _generate_basic_stats(self) -> List[str]:
        """기본 통계 생성"""
        if not self.state:
            return []

        progress = self.state.get("progress", {})
        current_chapter = progress.get("current_chapter", 0)
        total_words = progress.get("total_words", 0)
        target_words = self.state.get("project_info", {}).get("target_words", 2000000)

        avg_words = total_words / current_chapter if current_chapter > 0 else 0
        completion = (total_words / target_words * 100) if target_words > 0 else 0

        return [
            "## 📊 기본 데이터",
            "",
            f"- **총 챕터 수**: {current_chapter} 챕터",
            f"- **총 글자 수**: {total_words:,} 자",
            f"- **평균 챕터 글자 수**: {avg_words:,.0f} 자",
            f"- **창작 진행률**: {completion:.1f}%（목표 {target_words:,} 자）",
            "",
            "---",
            ""
        ]

    def _generate_character_section(self) -> List[str]:
        """캐릭터 분석 섹션 생성"""
        activity = self.analyze_characters()

        if not activity:
            return []

        # 이탈 캐릭터 필터링
        dropped = {name: data for name, data in activity.items()
                  if "이탈" in data["status"]}

        lines = [
            f"## ⚠️ 캐릭터 이탈（{len(dropped)}명）",
            ""
        ]

        if dropped:
            lines.extend([
                "| 캐릭터 | 마지막 등장 | 부재 챕터 | 상태 |",
                "|------|---------|---------|------|"
            ])

            for char_name, data in sorted(dropped.items(),
                                         key=lambda x: x[1]["absence"],
                                         reverse=True):
                lines.append(
                    f"| {char_name} | chapter {data['last_appearance']} | "
                    f"{data['absence']} 챕터 | {data['status']} |"
                )
        else:
            lines.append("✅ 모든 캐릭터 활동도 정상")

        lines.extend(["", "---", ""])

        return lines

    def _generate_foreshadowing_section(self) -> List[str]:
        """복선 분석 섹션 생성"""
        overdue = self.analyze_foreshadowing()

        # 시간 초과 복선 필터링
        overdue_items = [
            item for item in overdue if "시간 초과" in item["status"]
        ]
        unknown_items = [item for item in overdue if item["status"] == "⚪ 데이터 부족"]

        lines = [
            f"## ⚠️ 복선 시간 초과（{len(overdue_items)}건）",
            ""
        ]

        if overdue_items:
            lines.extend([
                "| 복선 내용 | 설치 챕터 | 경과 챕터 | 상태 |",
                "|---------|---------|---------|------|"
            ])

            for item in sorted(overdue_items, key=lambda x: (x["elapsed"] if x["elapsed"] is not None else -1), reverse=True):
                planted = item["planted_chapter"] if item["planted_chapter"] is not None else "알 수 없음"
                elapsed = item["elapsed"] if item["elapsed"] is not None else "알 수 없음"
                lines.append(
                    f"| {item['content'][:30]}... | chapter {planted} | "
                    f"{elapsed} 챕터 | {item['status']} |"
                )
        else:
            lines.append("✅ 모든 복선 진행 정상")

        if unknown_items:
            lines.append("")
            lines.append(f"⚪ 추가 {len(unknown_items)} 건의 복선이 챕터 정보 부족으로 시간 초과 여부 판단 불가")

        lines.extend(["", "---", ""])

        return lines

    def _generate_urgency_section(self) -> List[str]:
        """복선 긴급도 섹션 생성(3단계 시스템 기반)"""
        urgency_list = self.analyze_foreshadowing_urgency()

        # 긴급 복선 필터링
        urgent_items = [
            item
            for item in urgency_list
            if (item["urgency"] is not None and item["urgency"] >= 1.0) or item["status"] == "🔴 만료됨"
        ]

        lines = [
            f"## 🚨 복선긴급도 정렬（{len(urgent_items)}건 주의 필요）",
            "",
            "> 3단계 시스템 기반: 핵심(×3) / 서브(×2) / 장식(×1)",
            "> 긴급도 = (경과 챕터 / (목표챕터-설치 챕터)) × 단계 가중치",
            ""
        ]

        unknown_items = [item for item in urgency_list if item["urgency"] is None]
        if unknown_items:
            lines.append(f"> {len(unknown_items)} 건의 복선이 설치/목표 챕터 부족으로 긴급도 N/A")
            lines.append("")

        if urgency_list:
            lines.extend([
                "| 복선 내용 | 등급 | 설치 | 목표 | 긴급도 | 상태 |",
                "|---------|------|------|------|--------|------|"
            ])

            for item in urgency_list[:10]:  # 상위 10건만 표시
                planted = f"chapter {item['planted_chapter']}" if item["planted_chapter"] is not None else "알 수 없음"
                target = f"chapter {item['target_chapter']}" if item["target_chapter"] is not None else "알 수 없음"
                urgency_text = f"{item['urgency']:.2f}" if item["urgency"] is not None else "N/A"
                lines.append(
                    f"| {item['content'][:20]}... | {item['tier']} | "
                    f"{planted} | {target} | "
                    f"{urgency_text} | {item['status']} |"
                )
        else:
            lines.append("✅ 복선 데이터 없음")

        lines.extend(["", "---", ""])

        return lines

    def _generate_strand_section(self) -> List[str]:
        """Strand Weave 리듬 섹션 생성"""
        strand_data = self.analyze_strand_weave()

        lines = [
            "## 🎭 Strand Weave 리듬 분석",
            ""
        ]

        if not strand_data.get("has_data"):
            lines.append(f"⚠️ {strand_data.get('message', '데이터 없음')}")
            lines.extend(["", "---", ""])
            return lines

        # 비율통계
        cfg = self.config
        lines.extend([
            "### 3라인 비율",
            "",
            "| Strand | 챕터 수 | 비율 | 목표 범위 | 상태 |",
            "|--------|--------|------|----------|------|"
        ])

        q = strand_data["quest"]
        q_status = "✅" if cfg.strand_quest_ratio_min <= q["ratio"] <= cfg.strand_quest_ratio_max else "⚠️"
        lines.append(f"| Quest（메인 스토리） | {q['count']} | {q['ratio']:.1f}% | {cfg.strand_quest_ratio_min}-{cfg.strand_quest_ratio_max}% | {q_status} |")

        f = strand_data["fire"]
        f_status = "✅" if cfg.strand_fire_ratio_min <= f["ratio"] <= cfg.strand_fire_ratio_max else "⚠️"
        lines.append(f"| Fire（감정） | {f['count']} | {f['ratio']:.1f}% | {cfg.strand_fire_ratio_min}-{cfg.strand_fire_ratio_max}% | {f_status} |")

        c = strand_data["constellation"]
        c_status = "✅" if cfg.strand_constellation_ratio_min <= c["ratio"] <= cfg.strand_constellation_ratio_max else "⚠️"
        lines.append(f"| Constellation（세계관） | {c['count']} | {c['ratio']:.1f}% | {cfg.strand_constellation_ratio_min}-{cfg.strand_constellation_ratio_max}% | {c_status} |")

        lines.append("")

        # 연속성 검사
        lines.extend([
            "### 연속성 검사",
            "",
            f"- Quest 최대 연속: {strand_data['max_quest_streak']} 챕터（제한 ≤5）",
            f"- Fire 최대 부재: {strand_data['max_fire_gap']} 챕터（제한 ≤10）",
            f"- Constellation 최대 부재: {strand_data['max_const_gap']} 챕터（제한 ≤15）",
            ""
        ])

        # 위반 목록
        if strand_data["violations"]:
            lines.extend([
                "### ⚠️ 위반 목록",
                ""
            ])
            for v in strand_data["violations"]:
                lines.append(f"- {v}")
        else:
            lines.append("### ✅ 위반 없음")

        lines.extend(["", f"**종합 건강도**: {strand_data['health']}", "", "---", ""])

        return lines

    def _generate_pacing_section(self) -> List[str]:
        """리듬 분석 섹션 생성"""
        segments = self.analyze_pacing()

        lines = [
            "## 📈 카타르시스 리듬 분포",
            "",
            "```"
        ]

        for seg in segments:
            words_per_point = seg["words_per_point"]
            if words_per_point is None:
                lines.append(
                    f"chapter {seg['start']}-{seg['end']}  ░ 데이터 부족"
                    f"（카타르시스 데이터 부족 {seg['missing_chapters']} 챕터）"
                )
                continue

            bar_length = int(12 - (words_per_point / 2000 * 12))
            bar_length = max(1, min(12, bar_length))
            bar = "█" * bar_length

            suffix = ""
            if seg["missing_chapters"] > 0:
                suffix = f", 카타르시스 데이터 부족 {seg['missing_chapters']} 챕터"

            lines.append(
                f"chapter {seg['start']}-{seg['end']}  {bar} {seg['rating']}"
                f"（{words_per_point:.0f}자/카타르시스, 기록 {seg['cool_points']} 개 카타르시스{suffix}）"
            )

        lines.extend(["```", "", "---", ""])

        return lines

    def _generate_relationship_section(self) -> List[str]:
        """인간관계 섹션 생성"""
        graph = self.generate_relationship_graph()

        lines = [
            "## 💑 인간관계 트렌드",
            "",
            graph,
            "",
            "---",
            ""
        ]

        return lines

def main():
    import argparse

    _enable_windows_utf8_stdio()

    parser = argparse.ArgumentParser(
        description="시각화 상태 보고서 생성기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시：
  # 전체 건강 보고서 생성
  python status_reporter.py --output .webnovel/health_report.md

  # 캐릭터 활동도만 분석
  python status_reporter.py --focus characters

  # 복선만 분석
  python status_reporter.py --focus foreshadowing

  # 카타르시스 리듬만 분석
  python status_reporter.py --focus pacing
        """
    )

    parser.add_argument('--output', default='.webnovel/health_report.md',
                       help='출력 파일 경로')
    parser.add_argument('--focus', choices=['all', 'basic', 'characters',
                                            'foreshadowing', 'urgency', 'pacing',
                                            'strand', 'relationships'],
                       default='all', help='분석 초점（신규 urgency, strand）')
    parser.add_argument('--project-root', default='.', help='프로젝트 루트 디렉토리')

    args = parser.parse_args()

    # 프로젝트 루트 디렉토리 분석（”워크스페이스 루트”를 전달할 수 있으며, 실제 book project_root로 통일 파싱）
    try:
        project_root = str(resolve_project_root(args.project_root))
    except FileNotFoundError as exc:
        print(f"❌ 프로젝트 루트 디렉토리를 찾을 수 없음(.webnovel/state.json 포함 필요): {exc}", file=sys.stderr)
        sys.exit(1)

    # 보고서 생성기 생성
    reporter = StatusReporter(project_root)

    # 상태 로드
    if not reporter.load_state():
        sys.exit(1)

    print("📖 챕터 파일 스캔 중...")
    reporter.scan_chapters()

    print(f"✅ 스캔 완료 {len(reporter.chapters_data)} 개 챕터")

    print("\n📊 분석 중...")

    # 보고서 생성
    report = reporter.generate_report(args.focus)

    # 보고서 저장
    output_file = Path(args.output)
    if args.output == '.webnovel/health_report.md' and project_root != '.':
        output_file = Path(project_root) / '.webnovel' / 'health_report.md'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✅ 건강 보고서 생성 완료: {output_file}")

    # 보고서 미리보기（처음 30행）
    print("\n" + "="*60)
    print("📄 보고서 미리보기：\n")
    print("\n".join(report.split("\n")[:30]))
    print("\n...")
    print("="*60)

if __name__ == "__main__":
    main()
