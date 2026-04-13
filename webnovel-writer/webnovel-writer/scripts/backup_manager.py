#!/usr/bin/env python3
"""
Git 통합 백업 관리 시스템 (Backup Manager with Git)

핵심 개념: 200만 자를 쓰다 보면 필연적으로 "폐기 설정"이 생기므로, 임의 시점으로의 롤백을 지원해야 한다.

🔧 주요 업그레이드: Git을 사용한 원자적 버전 관리

Git을 선택한 이유：
1. ✅ 원자적 롤백: state.json + chapters/*.md 동시 롤백, 데이터 100% 일관성
2. ✅ 증분 저장: diff만 저장하여 95% 공간 절약
3. ✅ 성숙하고 안정적: 20년간 검증된 버전 관리 시스템
4. ✅ 브랜치 관리: "평행 세계" 창작을 자연스럽게 지원

기능:
1. 자동 Git 커밋: 매번 /webnovel-write 완료 후 자동 commit
2. 원자적 롤백: git checkout으로 모든 파일 동시 롤백
3. 버전 이력: git log로 전체 이력 조회
4. 차이 비교: git diff로 임의 두 버전 간 차이 조회
5. 브랜치 생성: git branch로 임의 시점에서 브랜치 생성

사용 방법:
  # 45챕터 완료 후 자동 백업 (자동 git commit)
  python backup_manager.py --chapter 45

  # 30챕터 상태로 롤백 (git checkout)
  python backup_manager.py --rollback 30

  # 20챕터와 40챕터의 차이 조회 (git diff)
  python backup_manager.py --diff 20 40

  # 50챕터에서 브랜치 생성 (git branch)
  python backup_manager.py --create-branch 50 --branch-name "alternative-ending"

  # 모든 백업 목록 (git log)
  python backup_manager.py --list

Git 커밋 규범:
  - 커밋 메시지 형식: "Chapter {N}: {챕터 제목}"
  - Tag 형식: "ch{N}" (예: ch0045)
  - 각 챕터는 하나의 commit + 하나의 tag에 대응

데이터 일관성 보장：
  ✅ 롤백 시, state.json과 모든 .md 파일 동기 롤백
  ✅ "상태 기록은 축기기인데, 파일에는 금단기로 되어있는" 데이터 불일치가 발생하지 않음
  ✅ 원자적 작업, 전부 성공하거나 전부 실패
"""

import subprocess
import json
import os
import sys
import shutil
from pathlib import Path

from runtime_compat import enable_windows_utf8_stdio
from datetime import datetime
from typing import Optional, List, Tuple

# ============================================================================
# 보안 수정: 보안 유틸리티 함수 임포트(P1 MEDIUM)
# ============================================================================
from security_utils import sanitize_commit_message, is_git_available, is_git_repo, git_graceful_operation
from project_locator import resolve_project_root

# Windows 인코딩 호환성 수정
if sys.platform == "win32":
    enable_windows_utf8_stdio()

class GitBackupManager:
    """Git 기반 백업 관리자(우아한 폴백 지원)"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.git_dir = self.project_root / ".git"
        self.git_available = is_git_available()

        if not self.git_available:
            print("⚠️  Git 사용 불가, 로컬 백업 모드 사용 예정")
            print("💡 Git 버전 관리를 사용하려면 Git을 설치하세요: https://git-scm.com/")
            return

        # Git 초기화 여부 확인
        if not self.git_dir.exists():
            print("⚠️  Git 초기화되지 않음, /webnovel-init 실행 또는 수동으로 git init 실행 필요")
            print("💡 Git 자동 초기화 중...")
            self._init_git()

    def _init_git(self) -> bool:
        """Git 저장소 초기화"""
        try:
            # git init
            subprocess.run(
                ["git", "init"],
                cwd=self.project_root,
                check=True,
                capture_output=True
            )

            # .gitignore 생성
            gitignore_file = self.project_root / ".gitignore"
            if not gitignore_file.exists():
                with open(gitignore_file, 'w', encoding='utf-8') as f:
                    f.write("""# Python
__pycache__/
*.py[cod]
*.so

# Temporary files
*.tmp
*.bak
.DS_Store

# IDE
.vscode/
.idea/

# Don't ignore .webnovel (we need to track state.json)
# But ignore cache files
.webnovel/context_cache.json
""")

            # 초기 커밋
            subprocess.run(
                ["git", "add", "."],
                cwd=self.project_root,
                check=True,
                capture_output=True
            )

            subprocess.run(
                ["git", "commit", "-m", "Initial commit: Project initialized"],
                cwd=self.project_root,
                check=True,
                capture_output=True
            )

            print("✅ Git 저장소 초기화 완료")
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Git 초기화 실패: {e}")
            return False

    def _run_git_command(self, args: List[str], check: bool = True) -> Tuple[bool, str]:
        """Git 명령 실행(우아한 폴백 지원)"""
        if not self.git_available:
            return False, "Git 사용 불가"

        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.project_root,
                check=check,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=60
            )

            return True, result.stdout

        except subprocess.CalledProcessError as e:
            return False, e.stderr
        except subprocess.TimeoutExpired:
            return False, "Git 명령 시간 초과"
        except OSError as e:
            return False, str(e)

    def _local_backup(self, chapter_num: int) -> bool:
        """로컬 백업(Git 사용 불가 시 폴백 방안)"""
        backup_dir = self.project_root / ".webnovel" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"ch{chapter_num:04d}_{timestamp}"
        backup_path = backup_dir / backup_name

        try:
            # state.json 백업
            state_file = self.project_root / ".webnovel" / "state.json"
            if state_file.exists():
                backup_path.mkdir(parents=True, exist_ok=True)
                shutil.copy2(state_file, backup_path / "state.json")

            print(f"✅ 로컬 백업 완료: {backup_path}")
            return True
        except OSError as e:
            print(f"❌ 로컬 백업 실패: {e}")
            return False

    def backup(self, chapter_num: int, chapter_title: str = "") -> bool:
        """
        현재 상태 백업 (Git commit + tag, 또는 로컬 백업)

        Args:
            chapter_num: 챕터 번호
            chapter_title: 챕터 제목(선택사항)
        """
        print(f"📝 백업 중: chapter {chapter_num}...")

        # Git을 사용할 수 없는 경우, 로컬 백업 사용
        if not self.git_available:
            return self._local_backup(chapter_num)

        # Step 1: git add .
        success, output = self._run_git_command(["add", "."])
        if not success:
            print(f"❌ git add 실패: {output}")
            return False

        # Step 2: git commit
        commit_message = f"Chapter {chapter_num}"
        if chapter_title:
            # ============================================================================
            # 보안 수정: 커밋 메시지 정리, 명령 주입 방지 (CWE-77) - P1 MEDIUM
            # 원본 코드: commit_message += f": {chapter_title}"
            # 취약점: chapter_title에 Git 플래그가 포함될 수 있음 (예: --author, --amend) 명령 주입 초래
            # ============================================================================
            safe_chapter_title = sanitize_commit_message(chapter_title)
            commit_message += f": {safe_chapter_title}"

        success, output = self._run_git_command(
            ["commit", "-m", commit_message],
            check=False  # "변경사항 없음" 상황 허용
        )

        if not success and "nothing to commit" in output:
            print("⚠️  변경사항 없음, 커밋 건너뜀")
            return True
        elif not success:
            print(f"❌ git commit 실패: {output}")
            return False

        print(f"✅ Git 커밋 완료: {commit_message}")

        # Step 3: git tag
        tag_name = f"ch{chapter_num:04d}"

        # 이전 tag 삭제(존재하는 경우)
        self._run_git_command(["tag", "-d", tag_name], check=False)

        success, output = self._run_git_command(["tag", tag_name])
        if not success:
            print(f"⚠️  tag 생성 실패(치명적이지 않음): {output}")
        else:
            print(f"✅ Git tag 생성 완료: {tag_name}")

        return True

    def rollback(self, chapter_num: int) -> bool:
        """
        지정된 챕터로 롤백 (Git checkout)

        ⚠️ 경고: 모든 미커밋 변경사항이 폐기됩니다!
        """

        tag_name = f"ch{chapter_num:04d}"

        print(f"🔄 롤백 중: chapter {chapter_num}...")
        print(f"⚠️  경고: 모든 미커밋 변경사항이 폐기됩니다!")

        # 미커밋 변경사항 확인
        success, status_output = self._run_git_command(["status", "--porcelain"])

        if status_output.strip():
            print("\n⚠️  미커밋 변경사항 감지:")
            print(status_output)

            # 백업 커밋 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_branch = f"backup_before_rollback_{timestamp}"

            print(f"\n💾 백업 브랜치 생성 중: {backup_branch}")

            success, _ = self._run_git_command(["checkout", "-b", backup_branch])
            if not success:
                print("❌ 백업 브랜치 생성 실패")
                return False

            success, _ = self._run_git_command(["add", "."])
            success, _ = self._run_git_command(
                ["commit", "-m", f"Backup before rollback to chapter {chapter_num}"]
            )

            print(f"✅ 백업 브랜치 생성 완료: {backup_branch}")

            # master로 전환
            success, _ = self._run_git_command(["checkout", "master"])

        # 롤백 실행
        success, output = self._run_git_command(["checkout", tag_name])

        if not success:
            print(f"❌ 롤백 실패: {output}")
            print(f"💡 팁: tag 확인 '{tag_name}' 존재(--list 실행으로 모든 백업 조회)")
            return False

        print(f"✅ 롤백 완료: chapter {chapter_num}!")
        print(f"\n💡 팁:")
        print(f"  - 모든 파일(state.json + chapters/*.md) 동기 롤백 완료")
        print(f"  - 복구하려면 실행: git checkout master")

        return True

    def diff(self, chapter_a: int, chapter_b: int):
        """두 버전 간 차이 비교 (Git diff)"""

        tag_a = f"ch{chapter_a:04d}"
        tag_b = f"ch{chapter_b:04d}"

        print(f"📊 비교: 제 {chapter_a} 챕터와 제 {chapter_b} 챕터의 차이...\n")

        success, output = self._run_git_command(["diff", tag_a, tag_b, "--stat"])

        if not success:
            print(f"❌ 비교 실패: {output}")
            return

        print("📈 파일 변경 통계:")
        print(output)

        # state.json 상세 차이 표시
        print("\n📝 state.json 상세 차이:")
        success, state_diff = self._run_git_command(
            ["diff", tag_a, tag_b, "--", ".webnovel/state.json"]
        )

        if success and state_diff:
            print(state_diff[:2000])  # 출력 길이 제한
            if len(state_diff) > 2000:
                print("\n...(출력이 너무 길어 잘림)")
        else:
            print("(변경사항 없음)")

    def list_backups(self):
        """모든 백업 목록 (Git log + tags)"""

        print("\n📚 백업 목록 (Git tags):\n")

        # 모든 tags 조회
        success, tags_output = self._run_git_command(["tag", "-l", "ch*"])

        if not success or not tags_output:
            print("⚠️  백업 없음")
            return

        tags = sorted(tags_output.strip().split('\n'))

        for tag in tags:
            # 챕터 번호 추출
            chapter_num = int(tag[2:])

            # 해당 tag의 커밋 정보 조회
            success, commit_info = self._run_git_command(
                ["log", tag, "-1", "--format=%h %ci %s"]
            )

            if success:
                print(f"📖 {tag} | {commit_info.strip()}")

        print(f"\n합계: {len(tags)} 개 백업")

        # 최근 5개 커밋 표시
        print("\n📜 최근 커밋 이력:\n")
        success, log_output = self._run_git_command(
            ["log", "--oneline", "-5"]
        )

        if success:
            print(log_output)

    def create_branch(self, chapter_num: int, branch_name: str) -> bool:
        """지정된 챕터에서 브랜치 생성 (Git branch)"""

        tag_name = f"ch{chapter_num:04d}"

        print(f"🌿 제 {chapter_num} 챕터에서 브랜치 생성: {branch_name}")

        # tag 존재 여부 확인
        success, _ = self._run_git_command(["rev-parse", tag_name], check=False)

        if not success:
            print(f"❌ Tag '{tag_name}' 존재하지 않음")
            return False

        # 브랜치 생성
        success, output = self._run_git_command(["branch", branch_name, tag_name])

        if not success:
            print(f"❌ 브랜치 생성 실패: {output}")
            return False

        print(f"✅ 브랜치 생성 완료: {branch_name}")
        print(f"\n💡 브랜치로 전환:")
        print(f"  git checkout {branch_name}")

        return True

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Git 통합 백업 관리 시스템",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 45챕터 완료 후 자동 백업
  python backup_manager.py --chapter 45

  # 30챕터로 롤백(원자적: state.json + 모든 .md 파일)
  python backup_manager.py --rollback 30

  # 20챕터와 40챕터의 차이 조회
  python backup_manager.py --diff 20 40

  # 50챕터에서 브랜치 생성
  python backup_manager.py --create-branch 50 --branch-name "alternative-ending"

  # 모든 백업 목록
  python backup_manager.py --list
        """
    )

    parser.add_argument('--chapter', type=int, help='백업 챕터 번호')
    parser.add_argument('--chapter-title', help='챕터 제목(선택사항)')
    parser.add_argument('--rollback', type=int, metavar='CHAPTER', help='지정된 챕터로 롤백')
    parser.add_argument('--diff', nargs=2, type=int, metavar=('A', 'B'), help='두 버전 비교')
    parser.add_argument('--create-branch', type=int, metavar='CHAPTER', help='지정된 챕터에서 브랜치 생성')
    parser.add_argument('--branch-name', help='브랜치 이름')
    parser.add_argument('--list', action='store_true', help='모든 백업 목록')
    parser.add_argument('--project-root', default='.', help='프로젝트 루트 디렉토리')

    args = parser.parse_args()

    # 프로젝트 루트 디렉토리 분석 (“워크스페이스 루트 디렉토리” 전달 허용, 실제 book project_root로 통합 분석)
    try:
        project_root = str(resolve_project_root(args.project_root))
    except FileNotFoundError as exc:
        print(f"❌ 프로젝트 루트 디렉토리를 찾을 수 없음(.webnovel/state.json 포함 필요): {exc}", file=sys.stderr)
        sys.exit(1)

    # 관리자 생성
    manager = GitBackupManager(project_root)

    # 작업 실행
    if args.chapter:
        manager.backup(args.chapter, args.chapter_title or "")

    elif args.rollback:
        manager.rollback(args.rollback)

    elif args.diff:
        manager.diff(args.diff[0], args.diff[1])

    elif args.create_branch:
        if not args.branch_name:
            print("❌ 브랜치 생성에 --branch-name 매개변수 필요")
            sys.exit(1)
        manager.create_branch(args.create_branch, args.branch_name)

    elif args.list:
        manager.list_backups()

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
