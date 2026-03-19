#!/usr/bin/env python3
"""
안전한 state.json 업데이트 스크립트

功能：
1. 구조화된 state.json 업데이트 인터페이스 제공
2. JSON 형식 및 데이터 무결성 자동 검증
3. 자동 백업(타임스탬프 포함)
4. 부분 업데이트 지원(다른 필드에 영향 없음)
5. 원자적 작업(전부 성공 아니면 전부 롤백)

使用方式：
  # 주인공 상태 업데이트
  python update_state.py --protagonist-power "金丹" 3 "雷劫"

  # 인간관계 업데이트
  python update_state.py --relationship "李雪" affection 95

  # 복선 기록
  python update_state.py --add-foreshadowing "神秘玉佩的秘密" "미회수"

  # 복선 회수
  python update_state.py --resolve-foreshadowing "天雷果的下落" 45

  # 진행 업데이트
  python update_state.py --progress 45 198765

  # 권 계획 완료 표시
  python update_state.py --volume-planned 1 --chapters-range 1-100

  # 조합 업데이트(원자적)
  python update_state.py \
    --protagonist-power "金丹" 3 "雷劫" \
    --progress 45 198765 \
    --relationship "李雪" affection 95 \
    --add-foreshadowing "神秘玉佩" "미회수"

보안 특성：
  - 원본 파일 자동 백업（.backup_TIMESTAMP.json）
  - JSON 格式검증
  - Schema 무결성 검사
  - 원자적 작업(실패 시 자동 롤백)
  - Dry-run 모드（--dry-run）
"""

import json
import os
import sys
import argparse
import shutil
from pathlib import Path

from runtime_compat import enable_windows_utf8_stdio
from datetime import datetime
from typing import Dict, Any, Optional

# ============================================================================
# 보안 수정: 보안 유틸리티 함수 임포트(P1 MEDIUM)
# ============================================================================
from security_utils import create_secure_directory, atomic_write_json, restore_from_backup
from project_locator import resolve_state_file
from data_modules.state_validator import (
    normalize_foreshadowing_status,
    normalize_state_runtime_sections,
)

# Windows 인코딩 호환성 수정
if sys.platform == "win32":
    enable_windows_utf8_stdio()

class StateUpdater:
    """state.json 안전 업데이터"""

    def __init__(self, state_file: str, dry_run: bool = False):
        self.state_file = state_file
        self.dry_run = dry_run
        self.backup_file = None
        self.state = None

    def _validate_schema(self, state: Dict) -> bool:
        """state.json의 기본 구조 검증（v5.0 도입,v5.4 유지）"""
        required_keys = [
            "project_info",
            "progress",
            "protagonist_state",
            "relationships",
            "world_settings",
            "plot_threads",
            "review_checkpoints"
        ]

        for key in required_keys:
            if key not in state:
                print(f"❌ 필수 필드 누락: {key}")
                return False

        # 중첩 구조 검증(두 가지 형식 지원: 중첩 및 플랫)
        ps = state["protagonist_state"]
        # power 필드：지원 power.realm 或直接 realm
        has_nested_power = "power" in ps and isinstance(ps.get("power"), dict)
        has_flat_power = "realm" in ps
        if not (has_nested_power or has_flat_power):
            print(f"❌ 누락 protagonist_state.power 或 protagonist_state.realm 필드")
            return False

        # location 필드：지원 location.current 或直接 location
        has_nested_location = isinstance(ps.get("location"), dict) and "current" in ps.get("location", {})
        has_flat_location = isinstance(ps.get("location"), str)
        if not (has_nested_location or has_flat_location):
            print(f"❌ 누락 protagonist_state.location 필드")
            return False

        # strand_tracker 구조 검증 및 보충(이전 state.json 호환)
        tracker = state.get("strand_tracker")
        if tracker is None or not isinstance(tracker, dict):
            if tracker is None:
                print("⚠️ strand_tracker 누락, 기본 구조로 자동 보충됨")
            else:
                print("⚠️ strand_tracker 유형 이상, 기본 구조로 재설정됨")
            state["strand_tracker"] = {
                "last_quest_chapter": 0,
                "last_fire_chapter": 0,
                "last_constellation_chapter": 0,
                "current_dominant": "quest",
                "chapters_since_switch": 0,
                "history": [],
            }
        else:
            tracker.setdefault("last_quest_chapter", 0)
            tracker.setdefault("last_fire_chapter", 0)
            tracker.setdefault("last_constellation_chapter", 0)
            tracker.setdefault("current_dominant", "quest")
            tracker.setdefault("chapters_since_switch", 0)
            tracker.setdefault("history", [])

        normalize_state_runtime_sections(state)
        return True

    def load(self) -> bool:
        """state.json 로드 및 검증"""
        if not os.path.exists(self.state_file):
            print(f"❌ 상태 파일 미존재: {self.state_file}")
            return False

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                self.state = json.load(f)

            if not self._validate_schema(self.state):
                print("❌ state.json 구조 불완전, 확인 필요")
                return False

            return True

        except json.JSONDecodeError as e:
            print(f"❌ JSON 형식 오류: {e}")
            return False

    def backup(self) -> bool:
        """현재 state.json 백업"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path(self.state_file).parent / "backups"
        # ============================================================================
        # 보안 수정: 보안 디렉토리 생성 함수 사용(P1 MEDIUM)
        # 원본 코드: backup_dir.mkdir(exist_ok=True)
        # 취약점: 권한 미설정, OS 기본값 사용(755일 수 있으며, 같은 그룹 사용자의 읽기 허용)
        # ============================================================================
        create_secure_directory(str(backup_dir))

        self.backup_file = backup_dir / f"state.backup_{timestamp}.json"

        try:
            shutil.copy2(self.state_file, self.backup_file)
            print(f"✅ 백업 완료: {self.backup_file}")
            return True
        except Exception as e:
            print(f"❌ 백업 실패: {e}")
            return False

    def save(self) -> bool:
        """업데이트된 state.json 저장(원자적 쓰기)"""
        if self.dry_run:
            print("\n⚠️  Dry-run 모드，不执行实际写入")
            print("\n📄 업데이트 후 내용 미리보기：")
            print(json.dumps(self.state, ensure_ascii=False, indent=2))
            return True

        try:
            # 중앙화된 원자적 쓰기 사용(filelock + 자동 백업 포함)
            atomic_write_json(self.state_file, self.state, use_lock=True, backup=True)
            print(f"✅ 저장 완료(원자적): {self.state_file}")
            return True

        except Exception as e:
            print(f"❌ 저장 실패: {e}")
            # 백업에서 복구 시도
            if restore_from_backup(self.state_file):
                print(f"✅ 백업에서 복구 완료")
            return False

    def update_protagonist_power(self, realm: str, layer: int, bottleneck: str):
        """주인공 전투력 업데이트(중첩 및 플랫 두 가지 형식 지원)"""
        ps = self.state["protagonist_state"]
        # 현재 형식 감지
        if "power" in ps and isinstance(ps.get("power"), dict):
            # 중첩 형식
            ps["power"] = {
                "realm": realm,
                "layer": layer,
                "bottleneck": bottleneck if bottleneck != "null" else None
            }
        else:
            # 플랫 형식
            ps["realm"] = realm
            ps["layer"] = layer
            ps["bottleneck"] = bottleneck if bottleneck != "null" else None
        print(f"📝 주인공 전투력 업데이트: {realm} {layer}층, 병목: {bottleneck}")

    def update_protagonist_location(self, location: str, chapter: int):
        """주인공 위치 업데이트(중첩 및 플랫 두 가지 형식 지원)"""
        ps = self.state["protagonist_state"]
        # 현재 형식 감지
        if isinstance(ps.get("location"), dict):
            # 중첩 형식
            ps["location"] = {
                "current": location,
                "last_chapter": chapter
            }
        else:
            # 플랫 형식
            ps["location"] = location
            ps["location_since_chapter"] = chapter
        print(f"📝 주인공 위치 업데이트: {location}（第{chapter}章）")

    def update_golden_finger(self, name: str, level: int, cooldown: int):
        """골든핑거 상태 업데이트"""
        ps = self.state.setdefault("protagonist_state", {})
        golden_finger = ps.get("golden_finger")
        if not isinstance(golden_finger, dict):
            golden_finger = {}
            ps["golden_finger"] = golden_finger

        golden_finger.setdefault("skills", [])
        golden_finger["name"] = name
        golden_finger["level"] = level
        golden_finger["cooldown"] = cooldown
        print(f"📝 골든핑거 업데이트: {name} Lv.{level}, 쿨다운: {cooldown}天")

    def update_relationship(self, char_name: str, key: str, value: Any):
        """인간관계 업데이트"""
        if char_name not in self.state["relationships"]:
            self.state["relationships"][char_name] = {}

        self.state["relationships"][char_name][key] = value
        print(f"📝 관계 업데이트: {char_name}.{key} = {value}")

    def add_foreshadowing(self, content: str, status: str = "미회수"):
        """복선 추가"""
        if "foreshadowing" not in self.state["plot_threads"]:
            self.state["plot_threads"]["foreshadowing"] = []

        # 检查是否완료存在
        for item in self.state["plot_threads"]["foreshadowing"]:
            if item.get("content") == content:
                print(f"⚠️  복선이 이미 존재: {content}")
                return

        # 상태 정규화, 방지 "待회수/进行中/active/pending" 등의 혼용으로 인한 다운스트림 필터링 누락
        status = normalize_foreshadowing_status(status)

        planted_chapter = int(self.state.get("progress", {}).get("current_chapter", 0) or 0)
        if planted_chapter <= 0:
            planted_chapter = 1
            print("? 유효한 것을 찾을 수 없음 progress.current_chapter，기본값 planted_chapter=1")

        target_chapter = planted_chapter + 100

        self.state["plot_threads"]["foreshadowing"].append({
            "content": content,
            "status": status,
            "added_at": datetime.now().strftime("%Y-%m-%d"),
            "planted_chapter": planted_chapter,
            "target_chapter": target_chapter,
            "tier": "서브"
        })
        print(f"📝 복선 추가: {content}（{status}）")

    def resolve_foreshadowing(self, content: str, chapter: int):
        """복선 회수"""
        if "foreshadowing" not in self.state["plot_threads"]:
            print(f"❌ 복선 목록을 찾을 수 없음")
            return

        for item in self.state["plot_threads"]["foreshadowing"]:
            if item.get("content") == content:
                item["status"] = "회수됨"
                item["resolved_chapter"] = chapter
                item["resolved_at"] = datetime.now().strftime("%Y-%m-%d")
                normalize_state_runtime_sections(self.state)
                print(f"📝 복선 회수: {content}（第{chapter}章）")
                return

        print(f"⚠️  복선을 찾을 수 없음: {content}")

    def update_progress(self, current_chapter: int, total_words: int):
        """更新창작 진행률"""
        self.state["progress"]["current_chapter"] = current_chapter
        self.state["progress"]["total_words"] = total_words
        self.state["progress"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"📝 진행 업데이트: 第{current_chapter}章, 총 글자 수: {total_words}")

    def mark_volume_planned(self, volume: int, chapters_range: str):
        """권 계획 완료 표시"""
        if "volumes_planned" not in self.state["progress"]:
            self.state["progress"]["volumes_planned"] = []

        # 检查是否완료存在
        for item in self.state["progress"]["volumes_planned"]:
            if item.get("volume") == volume:
                print(f"⚠️  第{volume}卷계획됨, 챕터 범위 업데이트")
                item["chapters_range"] = chapters_range
                item["updated_at"] = datetime.now().strftime("%Y-%m-%d")
                return

        self.state["progress"]["volumes_planned"].append({
            "volume": volume,
            "chapters_range": chapters_range,
            "planned_at": datetime.now().strftime("%Y-%m-%d")
        })
        print(f"📝 제{volume}권 계획 완료: 第{chapters_range}章")

    def add_review_checkpoint(self, chapters_range: str, report_file: str):
        """검토 기록 추가"""
        if "review_checkpoints" not in self.state:
            self.state["review_checkpoints"] = []

        self.state["review_checkpoints"].append({
            "chapters": chapters_range,
            "report": report_file,
            "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        print(f"📝 검토 기록 추가: 第{chapters_range}章 → {report_file}")

    def update_strand_tracker(self, strand: str, chapter: int):
        """주도적 스토리 라인 업데이트(Strand Weave 시스템)"""
        # strand 매개변수 검증
        valid_strands = ["quest", "fire", "constellation"]
        if strand.lower() not in valid_strands:
            print(f"❌ 잘못된 스토리 라인 유형: {strand}（유효한 값: quest, fire, constellation）")
            return False

        strand = strand.lower()

        # strand_tracker 초기화(존재하지 않는 경우)
        if "strand_tracker" not in self.state:
            self.state["strand_tracker"] = {
                "last_quest_chapter": 0,
                "last_fire_chapter": 0,
                "last_constellation_chapter": 0,
                "current_dominant": None,
                "chapters_since_switch": 0,
                "history": []
            }

        tracker = self.state["strand_tracker"]

        # 해당 strand의 마지막 챕터 업데이트
        tracker[f"last_{strand}_chapter"] = chapter

        # strand 전환 여부 판단
        if tracker.get("current_dominant") != strand:
            tracker["current_dominant"] = strand
            tracker["chapters_since_switch"] = 1
        else:
            tracker["chapters_since_switch"] += 1

        # 이력에 추가
        tracker["history"].append({
            "chapter": chapter,
            "dominant": strand
        })

        # 최근 50챕터의 이력만 유지(파일이 너무 커지는 것 방지)
        if len(tracker["history"]) > 50:
            tracker["history"] = tracker["history"][-50:]

        print(f"✅ strand_tracker 업데이트 완료")
        print(f"   - 第{chapter}챕터 주도적 스토리 라인: {strand}")
        print(f"   - 해당 스토리 라인 연속{tracker['chapters_since_switch']}章")

        return True

def main():
    parser = argparse.ArgumentParser(
        description="state.json 안전 업데이트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시：
  # 주인공 전투력 업데이트
  python update_state.py --protagonist-power "金丹" 3 "雷劫"

  # 인간관계 업데이트
  python update_state.py --relationship "李雪" affection 95

  # 복선 추가
  python update_state.py --add-foreshadowing "神秘玉佩的秘密" "미회수"

  # 복선 회수
  python update_state.py --resolve-foreshadowing "天雷果的下落" 45

  # 진행 업데이트
  python update_state.py --progress 45 198765

  # 권 계획 완료 표시
  python update_state.py --volume-planned 1 --chapters-range "1-100"

  # 조합 업데이트(원자적)
  python update_state.py \
    --protagonist-power "金丹" 3 "雷劫" \
    --progress 45 198765 \
    --relationship "李雪" affection 95
        """
    )

    parser.add_argument(
        '--project-root',
        default=None,
        help='프로젝트 루트 디렉토리(.webnovel/state.json 포함). 미제공 시 자동 검색(webnovel-project/ 및 부모 디렉토리 지원).'
    )

    parser.add_argument(
        '--state-file',
        default=None,
        help='state.json 파일 경로(선택사항). 미제공 시 프로젝트 루트에서 .webnovel/state.json으로 자동 탐지.'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='미리보기 모드, 실제 쓰기 미실행'
    )

    # 主角상태更新
    parser.add_argument(
        '--protagonist-power',
        nargs=3,
        metavar=('REALM', 'LAYER', 'BOTTLENECK'),
        help='주인공 전투력 업데이트(경지 층수 병목)'
    )

    parser.add_argument(
        '--protagonist-location',
        nargs=2,
        metavar=('LOCATION', 'CHAPTER'),
        help='주인공 위치 업데이트(장소 챕터 번호)'
    )

    parser.add_argument(
        '--golden-finger',
        nargs=3,
        metavar=('NAME', 'LEVEL', 'COOLDOWN'),
        help='골든핑거 업데이트(이름 등급 쿨다운 일수)'
    )

    # 인간관계更新
    parser.add_argument(
        '--relationship',
        nargs=3,
        action='append',
        metavar=('CHAR_NAME', 'KEY', 'VALUE'),
        help='인간관계 업데이트(캐릭터 이름 속성 값)'
    )

    # 복선管理
    parser.add_argument(
        '--add-foreshadowing',
        nargs=2,
        metavar=('CONTENT', 'STATUS'),
        help='복선 추가(내용 상태)'
    )

    parser.add_argument(
        '--resolve-foreshadowing',
        nargs=2,
        metavar=('CONTENT', 'CHAPTER'),
        help='복선 회수(내용 챕터 번호)'
    )

    # 진행更新
    parser.add_argument(
        '--progress',
        nargs=2,
        type=int,
        metavar=('CHAPTER', 'WORDS'),
        help='진행 업데이트(현재 챕터 총 글자 수)'
    )

    # 卷规划
    parser.add_argument(
        '--volume-planned',
        type=int,
        metavar='VOLUME',
        help='권 계획 완료 표시(권 번호)'
    )

    parser.add_argument(
        '--chapters-range',
        metavar='RANGE',
        help='챕터 범위（如 "1-100"）'
    )

    # 审查记录
    parser.add_argument(
        '--add-review',
        nargs=2,
        metavar=('CHAPTERS_RANGE', 'REPORT_FILE'),
        help='검토 기록 추가(챕터 범위 보고서 파일)'
    )

    # Strand Tracker 업데이트
    parser.add_argument(
        '--strand-dominant',
        nargs=2,
        metavar=('STRAND', 'CHAPTER'),
        help='주도적 스토리 라인 업데이트(quest/fire/constellation 챕터 번호)'
    )

    args = parser.parse_args()

    # 업데이트 매개변수가 없으면 도움말 표시 후 종료
    if not any([
        args.protagonist_power,
        args.protagonist_location,
        args.golden_finger,
        args.relationship,
        args.add_foreshadowing,
        args.resolve_foreshadowing,
        args.progress,
        args.volume_planned,
        args.add_review,
        args.strand_dominant
    ]):
        parser.print_help()
        sys.exit(1)

    # state.json 경로 분석(저장소 루트에서 실행 지원)
    state_file_path = resolve_state_file(args.state_file, explicit_project_root=args.project_root)

    # 업데이터 생성
    updater = StateUpdater(str(state_file_path), args.dry_run)

    # 상태 파일 로드
    if not updater.load():
        sys.exit(1)

    # 백업(dry-run이 아닌 경우)
    if not args.dry_run:
        if not updater.backup():
            sys.exit(1)

    print("\n📝 업데이트 시작...")

    # 업데이트 작업 실행
    try:
        if args.protagonist_power:
            realm, layer, bottleneck = args.protagonist_power
            updater.update_protagonist_power(realm, int(layer), bottleneck)

        if args.protagonist_location:
            location, chapter = args.protagonist_location
            updater.update_protagonist_location(location, int(chapter))

        if args.golden_finger:
            name, level, cooldown = args.golden_finger
            updater.update_golden_finger(name, int(level), int(cooldown))

        if args.relationship:
            for char_name, key, value in args.relationship:
                # 숫자로 변환 시도
                try:
                    value = int(value)
                except ValueError:
                    pass
                updater.update_relationship(char_name, key, value)

        if args.add_foreshadowing:
            content, status = args.add_foreshadowing
            updater.add_foreshadowing(content, status)

        if args.resolve_foreshadowing:
            content, chapter = args.resolve_foreshadowing
            updater.resolve_foreshadowing(content, int(chapter))

        if args.progress:
            chapter, words = args.progress
            updater.update_progress(chapter, words)

        if args.volume_planned:
            if not args.chapters_range:
                print("❌ --volume-planned 필요 --chapters-range 매개변수")
                sys.exit(1)
            updater.mark_volume_planned(args.volume_planned, args.chapters_range)

        if args.add_review:
            chapters_range, report_file = args.add_review
            updater.add_review_checkpoint(chapters_range, report_file)

        # Strand Tracker 업데이트
        if args.strand_dominant:
            strand, chapter = args.strand_dominant
            updater.update_strand_tracker(strand, int(chapter))

        # 업데이트 저장
        if not updater.save():
            sys.exit(1)

        print("\n✅ 업데이트 완료!")

        if not args.dry_run:
            print(f"\n💡 팁:")
            print(f"  - 원본 파일 백업 완료: {updater.backup_file}")
            print(f"  - 롤백 필요 시, 백업 파일을 다음 위치에 복사 {updater.state_file}")

    except Exception as e:
        print(f"\n❌ 업데이트 실패: {e}")
        if updater.backup_file and os.path.exists(updater.backup_file):
            print(f"🔄 롤백 중...")
            shutil.copy2(updater.backup_file, updater.state_file)
            print(f"✅ 백업 버전으로 롤백 완료")
        sys.exit(1)

if __name__ == "__main__":
    main()
