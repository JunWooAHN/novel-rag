#!/usr/bin/env python3
"""
state.json 데이터 아카이브 관리 스크립트

목표: state.json의 무한 증가를 방지하고, 200만 자 장기 연재의 안정적 운영을 보장

기능:
1. 장기간 미사용 데이터의 스마트 아카이브(캐릭터/복선/검토 보고서)
2. 자동 트리거 조건 감지(파일 크기/챕터 수)
3. 안전한 백업 및 복구 메커니즘
4. 아카이브 데이터는 언제든지 복구 가능

아카이브 전략:
- 캐릭터: 50챕터 이상 미등장 보조 캐릭터 → archive/characters.json
- 복선: status="회수됨"이며 20챕터 이상 경과한 복선 → archive/plot_threads.json
- 검토 보고서: 50챕터 이상 경과한 이전 보고서 → archive/reviews.json

사용 방법:
  # 자동 아카이브 검사(update_state.py 이후 호출 권장)
  python archive_manager.py --auto-check

  # 강제 아카이브(트리거 조건 무시)
  python archive_manager.py --force

  # 특정 캐릭터 복구
  python archive_manager.py --restore-character "李雪"

  # 아카이브 통계 조회
  python archive_manager.py --stats

  # Dry-run 모드(아카이브될 데이터만 표시)
  python archive_manager.py --auto-check --dry-run
"""

import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

from runtime_compat import enable_windows_utf8_stdio

# ============================================================================
# 보안 수정: 보안 유틸리티 함수 임포트(P1 MEDIUM)
# ============================================================================
from security_utils import create_secure_directory, atomic_write_json
from project_locator import resolve_project_root

# v5.1 도입: IndexManager를 사용하여 엔티티 읽기
try:
    from data_modules.index_manager import IndexManager
    from data_modules.config import get_config
except ImportError:
    from scripts.data_modules.index_manager import IndexManager
    from scripts.data_modules.config import get_config

# Windows UTF-8 인코딩 수정
if sys.platform == "win32":
    enable_windows_utf8_stdio()


class ArchiveManager:
    """state.json 데이터 아카이브 관리자"""

    def __init__(self, project_root=None):
        if project_root is None:
            # 기본적으로 현재 디렉토리 사용
            project_root = Path.cwd()
        else:
            project_root = Path(project_root)

        self.project_root = project_root
        self.state_file = project_root / ".webnovel" / "state.json"
        self.archive_dir = project_root / ".webnovel" / "archive"

        # v5.1 도입: 엔티티 읽기용 IndexManager
        self._config = get_config(project_root)
        self._index_manager = IndexManager(self._config)

        # ============================================================================
        # 보안 수정: 보안 디렉토리 생성 함수 사용(P1 MEDIUM)
        # 원본 코드: self.archive_dir.mkdir(parents=True, exist_ok=True)
        # 취약점: 권한 미설정, OS 기본값 사용(755일 수 있으며, 같은 그룹 사용자의 읽기 허용)
        # ============================================================================
        create_secure_directory(str(self.archive_dir))

        # 아카이브 파일 경로
        self.characters_archive = self.archive_dir / "characters.json"
        self.plot_threads_archive = self.archive_dir / "plot_threads.json"
        self.reviews_archive = self.archive_dir / "reviews.json"

        # 아카이브 규칙 설정
        self.config = {
            "character_inactive_threshold": 50,  # 50챕터 이상 미등장 캐릭터는 비활성으로 간주
            "plot_resolved_threshold": 20,       # 회수된 복선은 20챕터 경과 후 아카이브
            "review_old_threshold": 50,          # 검토 보고서는 50챕터 경과 후 아카이브
            "file_size_trigger_mb": 1.0,         # state.json 1.0MB 초과 시 강제 아카이브 트리거
            "chapter_trigger": 10                # 10챕터마다 검사
        }

    def load_state(self):
        """state.json 로드"""
        if not self.state_file.exists():
            print(f"❌ state.json 존재하지 않음: {self.state_file}")
            sys.exit(1)

        with open(self.state_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_state(self, state):
        """state.json 저장(원자적 쓰기)"""
        # 중앙화된 원자적 쓰기 사용(자동 백업)
        atomic_write_json(self.state_file, state, use_lock=True, backup=True)
        print(f"✅ state.json 원자적으로 업데이트 완료")

    def load_archive(self, archive_file):
        """아카이브 파일 로드"""
        if not archive_file.exists():
            return []

        with open(archive_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_archive(self, archive_file, data):
        """아카이브 파일 저장"""
        with open(archive_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def check_trigger_conditions(self, state):
        """아카이브 트리거 필요 여부 확인"""
        current_chapter = state.get("progress", {}).get("current_chapter", 0)

        # 조건 1: 파일 크기 임계값 초과
        file_size_mb = self.state_file.stat().st_size / (1024 * 1024)
        size_trigger = file_size_mb >= self.config["file_size_trigger_mb"]

        # 조건 2: 챕터 수가 트리거 간격의 배수
        chapter_trigger = (current_chapter % self.config["chapter_trigger"]) == 0 and current_chapter > 0

        return {
            "should_archive": size_trigger or chapter_trigger,
            "file_size_mb": file_size_mb,
            "current_chapter": current_chapter,
            "size_trigger": size_trigger,
            "chapter_trigger": chapter_trigger
        }

    def identify_inactive_characters(self, state):
        """비활성 보조 캐릭터 식별(v5.1 도입, v5.4 유지)"""
        current_chapter = state.get("progress", {}).get("current_chapter", 0)
        threshold = self.config["character_inactive_threshold"]

        # v5.1 도입: SQLite에서 모든 캐릭터 엔티티 조회
        characters = self._index_manager.get_entities_by_type("캐릭터")

        inactive = []
        for char in characters:
            # 보조 캐릭터만 아카이브(tier="장식" 또는 tier="서브")
            tier = str(char.get("tier", "")).strip()
            if tier == "핵심":
                continue

            # 마지막 등장 챕터 확인
            last_appearance = char.get("last_appearance", 0)
            try:
                last_appearance = int(last_appearance)
            except (TypeError, ValueError):
                last_appearance = 0
            if last_appearance <= 0:
                continue

            inactive_chapters = current_chapter - last_appearance

            if inactive_chapters >= threshold:
                char_id = char.get("id", "")
                char_data = {
                    "id": char_id,
                    "name": char.get("canonical_name", char_id),
                    "tier": tier,
                    "last_appearance_chapter": last_appearance
                }
                char_data.update(char)
                inactive.append({
                    "character": char_data,
                    "inactive_chapters": inactive_chapters,
                    "last_appearance": last_appearance
                })

        return inactive

    def identify_resolved_plot_threads(self, state):
        """아카이브 가능한 회수된 복선 식별"""
        current_chapter = state.get("progress", {}).get("current_chapter", 0)
        plot_threads = state.get("plot_threads", {}) or {}
        foreshadowing = plot_threads.get("foreshadowing", []) or []
        resolved_legacy = plot_threads.get("resolved", []) or []
        threshold = self.config["plot_resolved_threshold"]

        archivable = []
        # 새 형식: plot_threads.foreshadowing(status로 회수 여부 식별)
        if isinstance(foreshadowing, list):
            for item in foreshadowing:
                if not isinstance(item, dict):
                    continue
                status = str(item.get("status", "")).strip()
                if status not in ["회수됨", "resolved"]:
                    continue
                try:
                    resolved_chapter = int(item.get("resolved_chapter", 0))
                except (TypeError, ValueError):
                    continue
                chapters_since_resolved = current_chapter - resolved_chapter
                if chapters_since_resolved >= threshold:
                    archivable.append({
                        "thread": item,
                        "chapters_since_resolved": chapters_since_resolved,
                        "resolved_chapter": resolved_chapter
                    })

        # 이전 형식 호환: plot_threads.resolved(회수된 목록 직접 저장)
        if isinstance(resolved_legacy, list):
            for item in resolved_legacy:
                if not isinstance(item, dict):
                    continue
                try:
                    resolved_chapter = int(item.get("resolved_chapter", 0))
                except (TypeError, ValueError):
                    continue
                chapters_since_resolved = current_chapter - resolved_chapter
                if chapters_since_resolved >= threshold:
                    archivable.append({
                        "thread": item,
                        "chapters_since_resolved": chapters_since_resolved,
                        "resolved_chapter": resolved_chapter
                    })

        return archivable

    def identify_old_reviews(self, state):
        """아카이브 가능한 이전 검토 보고서 식별"""
        current_chapter = state.get("progress", {}).get("current_chapter", 0)
        reviews = state.get("review_checkpoints", [])
        threshold = self.config["review_old_threshold"]

        def _parse_end_chapter(review: dict) -> int:
            # 새 형식: {"chapters":"5-6","report":"...","reviewed_at":"..."}
            chapters = review.get("chapters")
            if isinstance(chapters, str):
                parts = [p.strip() for p in chapters.replace("—", "-").split("-") if p.strip()]
                if parts:
                    try:
                        return int(parts[-1])
                    except ValueError:
                        pass

            # 이전 형식: {"chapter_range":[5,6], "date":"..."}
            cr = review.get("chapter_range")
            if isinstance(cr, (list, tuple)) and len(cr) >= 2:
                try:
                    return int(cr[1])
                except (TypeError, ValueError):
                    pass

            # 폴백: report 파일명에서 "Ch5-6" 또는 "第005-006" 추출
            report = review.get("report")
            if isinstance(report, str):
                import re
                m = re.search(r"Ch(\d+)[-–—](\d+)", report)
                if m:
                    try:
                        return int(m.group(2))
                    except ValueError:
                        pass
                m = re.search(r"第(\d+)[-–—](\d+)章", report)
                if m:
                    try:
                        return int(m.group(2))
                    except ValueError:
                        pass

            return 0

        old_reviews = []
        for review in reviews:
            review_chapter = _parse_end_chapter(review)
            chapters_since_review = current_chapter - review_chapter

            if chapters_since_review >= threshold:
                old_reviews.append({
                    "review": review,
                    "chapters_since_review": chapters_since_review,
                    "review_chapter": review_chapter
                })

        return old_reviews

    def archive_characters(self, inactive_list, dry_run=False):
        """비활성 캐릭터 아카이브(v5.1 도입: IndexManager를 사용하여 상태 업데이트)"""
        if not inactive_list:
            return 0

        # 기존 아카이브 로드
        archived = self.load_archive(self.characters_archive)

        # 타임스탬프 추가
        timestamp = datetime.now().isoformat()
        for item in inactive_list:
            item["character"]["archived_at"] = timestamp
            archived.append(item["character"])

            # v5.1 도입: IndexManager를 통한 엔티티 상태 업데이트
            if not dry_run:
                try:
                    entity_id = item["character"].get("id")
                    if entity_id:
                        # 엔티티의 current_json에 archived 마크 추가
                        self._index_manager.update_entity_field(
                            entity_id, "status", "archived"
                        )
                except Exception as e:
                    print(f"⚠️ 엔티티 상태 업데이트 실패(아카이브에 영향 없음): {e}")

        if not dry_run:
            self.save_archive(self.characters_archive, archived)

        return len(inactive_list)

    def archive_plot_threads(self, resolved_list, dry_run=False):
        """회수된 복선 아카이브"""
        if not resolved_list:
            return 0

        # 기존 아카이브 로드
        archived = self.load_archive(self.plot_threads_archive)

        # 타임스탬프 추가
        timestamp = datetime.now().isoformat()
        for item in resolved_list:
            item["thread"]["archived_at"] = timestamp
            archived.append(item["thread"])

        if not dry_run:
            self.save_archive(self.plot_threads_archive, archived)

        return len(resolved_list)

    def archive_reviews(self, old_reviews_list, dry_run=False):
        """이전 검토 보고서 아카이브"""
        if not old_reviews_list:
            return 0

        # 기존 아카이브 로드
        archived = self.load_archive(self.reviews_archive)

        # 타임스탬프 추가
        timestamp = datetime.now().isoformat()
        for item in old_reviews_list:
            item["review"]["archived_at"] = timestamp
            archived.append(item["review"])

        if not dry_run:
            self.save_archive(self.reviews_archive, archived)

        return len(old_reviews_list)

    def remove_from_state(self, state, inactive_chars, resolved_threads, old_reviews):
        """state.json/SQLite에서 아카이브된 데이터 제거(v5.1 도입, v5.4 유지)"""
        # v5.1 도입: 캐릭터 데이터는 SQLite에 있으며, archive_characters에서 이미 상태 업데이트 처리
        # 여기서는 state.json의 복선과 검토 보고서만 처리 필요

        # 아카이브된 복선 제거
        if resolved_threads:
            thread_ids = {
                (item.get("thread", {}) or {}).get("content") or (item.get("thread", {}) or {}).get("description")
                for item in resolved_threads
            }
            thread_ids = {t for t in thread_ids if isinstance(t, str) and t.strip()}

            plot_threads = state.get("plot_threads", {}) or {}
            if isinstance(plot_threads.get("foreshadowing"), list):
                plot_threads["foreshadowing"] = [
                    t for t in plot_threads["foreshadowing"]
                    if not isinstance(t, dict) or (t.get("content") or t.get("description")) not in thread_ids
                ]
            if isinstance(plot_threads.get("resolved"), list):
                plot_threads["resolved"] = [
                    t for t in plot_threads["resolved"]
                    if not isinstance(t, dict) or (t.get("content") or t.get("description")) not in thread_ids
                ]
            state["plot_threads"] = plot_threads

        # 이전 검토 보고서 제거
        if old_reviews:
            review_keys = set()
            for item in old_reviews:
                review = item.get("review", {}) or {}
                key = review.get("report") or review.get("reviewed_at") or review.get("date")
                if isinstance(key, str) and key.strip():
                    review_keys.add(key)

            state["review_checkpoints"] = [
                review for review in state.get("review_checkpoints", [])
                if (review.get("report") or review.get("reviewed_at") or review.get("date")) not in review_keys
            ]

        return state

    def run_auto_check(self, force=False, dry_run=False):
        """자동 아카이브 검사"""
        state = self.load_state()

        # 트리거 조건 확인
        trigger = self.check_trigger_conditions(state)

        if not force and not trigger["should_archive"]:
            print("✅ 아카이브 불필요(트리거 조건 미충족)")
            print(f"   파일 크기: {trigger['file_size_mb']:.2f} MB (임계값: {self.config['file_size_trigger_mb']} MB)")
            print(f"   현재 챕터: {trigger['current_chapter']} (매 {self.config['chapter_trigger']} 챕터마다 트리거)")
            return

        print("🔍 아카이브 검사 시작...")
        print(f"   파일 크기: {trigger['file_size_mb']:.2f} MB")
        print(f"   현재 챕터: {trigger['current_chapter']}")

        # 아카이브 가능 데이터 식별
        inactive_chars = self.identify_inactive_characters(state)
        resolved_threads = self.identify_resolved_plot_threads(state)
        old_reviews = self.identify_old_reviews(state)

        # 통계 출력
        print(f"\n📊 아카이브 통계:")
        print(f"   비활성 캐릭터: {len(inactive_chars)}")
        print(f"   회수된 복선: {len(resolved_threads)}")
        print(f"   이전 검토 보고서: {len(old_reviews)}")

        if not (inactive_chars or resolved_threads or old_reviews):
            print("\n✅ 아카이브 불필요(조건에 맞는 데이터 없음)")
            return

        # Dry-run 모드
        if dry_run:
            print("\n🔍 [Dry-run] 아카이브될 데이터:")
            if inactive_chars:
                print("\n   비활성 캐릭터:")
                for item in inactive_chars[:5]:  # 처음 5개만 표시
                    print(f"   - {item['character']['name']} ({item['inactive_chapters']} 챕터 미등장)")
            if resolved_threads:
                print("\n   회수된 복선:")
                for item in resolved_threads[:5]:
                    desc = item["thread"].get("content") or item["thread"].get("description") or ""
                    print(f"   - {str(desc)[:30]}... (회수 후 {item['chapters_since_resolved']} 챕터)")
            if old_reviews:
                print("\n   이전 검토 보고서:")
                for item in old_reviews[:5]:
                    print(f"   - Ch{item['review_chapter']} ({item['chapters_since_review']} 챕터 전)")
            return

        # 아카이브 실행
        chars_archived = self.archive_characters(inactive_chars, dry_run=dry_run)
        threads_archived = self.archive_plot_threads(resolved_threads, dry_run=dry_run)
        reviews_archived = self.archive_reviews(old_reviews, dry_run=dry_run)

        # state.json에서 제거
        state = self.remove_from_state(state, inactive_chars, resolved_threads, old_reviews)
        self.save_state(state)

        # 최종 통계
        print(f"\n✅ 아카이브 완료:")
        print(f"   캐릭터 아카이브: {chars_archived} → {self.characters_archive.name}")
        print(f"   복선 아카이브: {threads_archived} → {self.plot_threads_archive.name}")
        print(f"   보고서 아카이브: {reviews_archived} → {self.reviews_archive.name}")

        # 아카이브 후 파일 크기 표시
        new_size_mb = self.state_file.stat().st_size / (1024 * 1024)
        saved_mb = trigger["file_size_mb"] - new_size_mb
        print(f"\n💾 파일 크기: {trigger['file_size_mb']:.2f} MB → {new_size_mb:.2f} MB (절감 {saved_mb:.2f} MB)")

    def restore_character(self, name):
        """아카이브된 캐릭터 복구(v5.1 도입: IndexManager를 사용하여 상태 복구)"""
        archived = self.load_archive(self.characters_archive)

        # 캐릭터 검색
        char_to_restore = None
        for char in archived:
            if char["name"] == name:
                char_to_restore = char
                break

        if not char_to_restore:
            print(f"❌ 아카이브에서 캐릭터를 찾을 수 없음: {name}")
            return

        # archived_at 필드 제거
        char_to_restore.pop("archived_at", None)

        # 원자성 수정: 먼저 아카이브에서 제거
        archived = [char for char in archived if char["name"] != name]
        self.save_archive(self.characters_archive, archived)

        # v5.1 도입: SQLite로 복구(IndexManager 통해)
        char_id = char_to_restore.get("id", char_to_restore.get("name", "unknown"))
        try:
            # 엔티티 상태를 active로 업데이트
            self._index_manager.update_entity_field(char_id, "status", "active")
            print(f"✅ 캐릭터 복구 완료: {name}")
        except Exception as e:
            print(f"⚠️ 엔티티 상태 복구 실패: {e}")

    def show_stats(self):
        """아카이브 통계 표시"""
        chars = self.load_archive(self.characters_archive)
        threads = self.load_archive(self.plot_threads_archive)
        reviews = self.load_archive(self.reviews_archive)

        print("📊 아카이브 통계:")
        print(f"   캐릭터 아카이브: {len(chars)}")
        print(f"   복선 아카이브: {len(threads)}")
        print(f"   보고서 아카이브: {len(reviews)}")

        # 아카이브 파일 크기 계산
        total_size = 0
        for archive_file in [self.characters_archive, self.plot_threads_archive, self.reviews_archive]:
            if archive_file.exists():
                total_size += archive_file.stat().st_size

        print(f"   아카이브 크기: {total_size / 1024:.2f} KB")

        # state.json 크기 표시
        state_size_mb = self.state_file.stat().st_size / (1024 * 1024)
        print(f"\n💾 state.json 현재 크기: {state_size_mb:.2f} MB")


def main():
    parser = argparse.ArgumentParser(description="state.json 데이터 아카이브 관리")

    parser.add_argument("--auto-check", action="store_true", help="자동 아카이브 검사")
    parser.add_argument("--force", action="store_true", help="강제 아카이브(트리거 조건 무시)")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run 모드(아카이브될 데이터만 표시)")
    parser.add_argument("--restore-character", metavar="NAME", help="아카이브된 캐릭터 복구")
    parser.add_argument("--stats", action="store_true", help="아카이브 통계 표시")
    parser.add_argument("--project-root", metavar="PATH", help="프로젝트 루트 디렉토리(기본값: 현재 디렉토리)")

    args = parser.parse_args()

    # 프로젝트 루트 디렉토리 분석("워크스페이스 루트 디렉토리" 전달 허용, 실제 book project_root로 통합 분석)
    try:
        project_root = str(resolve_project_root(args.project_root) if args.project_root else resolve_project_root())
    except FileNotFoundError as exc:
        print(f"❌ 프로젝트 루트 디렉토리를 찾을 수 없음(.webnovel/state.json 포함 필요): {exc}", file=sys.stderr)
        sys.exit(1)

    manager = ArchiveManager(project_root=project_root)

    # 작업 실행
    if args.auto_check or args.force:
        manager.run_auto_check(force=args.force, dry_run=args.dry_run)
    elif args.restore_character:
        manager.restore_character(args.restore_character)
    elif args.stats:
        manager.show_stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
