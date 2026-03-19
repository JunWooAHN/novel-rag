#!/usr/bin/env python3
"""
보안 유틸리티 함수 라이브러리
webnovel-writer 시스템용 범용 보안 함수

생성 시간: 2026-01-02
생성 이유: 보안 감사에서 경로 탐색 및 명령 주입 취약점 발견
수정 방안: 모든 보안 관련 입력 정리 함수 중앙 관리
"""

import json
import os
import re
import sys
import tempfile
from pathlib import Path

from runtime_compat import enable_windows_utf8_stdio
from typing import Any, Dict, Optional, Union

# filelock 임포트 시도(선택적 의존성)
try:
    from filelock import FileLock
    HAS_FILELOCK = True
except ImportError:
    HAS_FILELOCK = False


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """
    파일명 정리, 경로 탐색 공격 방지 (CWE-22)

    보안 핵심 함수 - extract_entities.py 경로 탐색 취약점 수정

    Args:
        name: 원본 파일명(경로 탐색 문자 포함 가능)
        max_length: 파일명 최대 길이（기본 100자）

    Returns:
        안전한 파일명(기본 파일명만 포함, 모든 경로 정보 제거)

    예시:
        >>> sanitize_filename("../../../etc/passwd")
        'passwd'
        >>> sanitize_filename("C:\\Windows\\System32")
        'System32'
        >>> sanitize_filename("일반 캐릭터 이름")
        '일반 캐릭터 이름'

    보안 검증:
        - ✅ 디렉토리 탐색 방지（../、..\\）
        - ✅ 절대 경로 방지（/、C:\\）
        - ✅ 특수 문자 제거
        - ✅ 길이 제한
    """
    # Step 1: 기본 파일명만 유지(모든 경로 제거)
    safe_name = os.path.basename(name)

    # Step 2: 경로 구분자 제거(이중 안전)
    safe_name = safe_name.replace('/', '_').replace('\\', '_')

    # Step 3: 안전한 문자만 유지
    # 允许：中文(\u4e00-\u9fff)、자母(a-zA-Z)、数자(0-9)、下划线(_)、连자符(-)
    safe_name = re.sub(r'[^\w\u4e00-\u9fff-]', '_', safe_name)

    # Step 4: 연속 밑줄 제거(미화)
    safe_name = re.sub(r'_+', '_', safe_name)

    # Step 5: 길이 제한
    if len(safe_name) > max_length:
        safe_name = safe_name[:max_length]

    # Step 6: 앞뒤 밑줄 제거
    safe_name = safe_name.strip('_')

    # Step 7: 비어있지 않도록 보장(방어적 프로그래밍)
    if not safe_name:
        safe_name = "unnamed_entity"

    return safe_name


def sanitize_commit_message(message: str, max_length: int = 200) -> str:
    """
    Git 커밋 메시지 정리, 명령 주입 방지 (CWE-77)

    보안 핵심 함수 - backup_manager.py 명령 주입 취약점 수정

    Args:
        message: 원본 커밋 메시지(Git 플래그 포함 가능)
        max_length: 메시지 최대 길이（기본 200자）

    Returns:
        안전한 커밋 메시지(Git 특수 플래그 및 위험 문자 제거)

    예시:
        >>> sanitize_commit_message("Test\\n--author='Attacker'")
        'Test  author Attacker'
        >>> sanitize_commit_message("--amend Chapter 1")
        'amend Chapter 1'

    보안 검증:
        - ✅ 다중 행 주입 방지(개행 문자)
        - ✅ Git 플래그 주입 방지（--xxx）
        - ✅ 매개변수 구분자 혼동 방지(따옴표)
        - ✅ 단일 문자 플래그 방지（-x）
    """
    # Step 1: 개행 문자 제거(다중 행 매개변수 주입 방지)
    safe_msg = message.replace('\n', ' ').replace('\r', ' ')

    # Step 2: Git 특수 플래그 제거(--로 시작하는 매개변수)
    safe_msg = re.sub(r'--[\w-]+', '', safe_msg)

    # Step 3: 따옴표 제거(매개변수 구분자 혼동 방지)
    safe_msg = safe_msg.replace("'", "").replace('"', '')

    # Step 4: 앞의 - 제거(단일 문자 플래그 방지, 예: -m)
    safe_msg = safe_msg.lstrip('-')

    # Step 5: 연속 공백 제거(미화)
    safe_msg = re.sub(r'\s+', ' ', safe_msg)

    # Step 6: 길이 제한
    if len(safe_msg) > max_length:
        safe_msg = safe_msg[:max_length]

    # Step 7: 앞뒤 공백 제거
    safe_msg = safe_msg.strip()

    # Step 8: 비어있지 않도록 보장
    if not safe_msg:
        safe_msg = "Untitled commit"

    return safe_msg


def create_secure_directory(path: str, mode: int = 0o700) -> Path:
    """
    안전한 디렉토리 생성(소유자만 접근 가능)

    보안 핵심 함수 - 파일 권한 설정 누락 취약점 수정

    Args:
        path: 디렉토리 경로
        mode: 권한 모드（기본값0o700，소유자만 읽기/쓰기/실행 가능）

    Returns:
        Path对象

    예시:
        >>> create_secure_directory('.webnovel')
        PosixPath('.webnovel')  # drwx------ (700)

    보안 검증:
        - ✅ 소유자만 접근 가능（0o700）
        - ✅ 같은 그룹 사용자의 읽기 방지
        - ✅ 크로스 플랫폼 호환（Windows/Linux/macOS）
    """
    path_obj = Path(path)

    # Windows mode를 전달하면 예상치 못한 ACL 동작을 트리거（실제 테스트에서 디렉토리 생성 후 즉시 접근 불가）。
    # 따라서 Windows에서는 mode를 전달하지 않고, 기본 상속 권한 유지；Unix 계열 시스템에서만 mode 사용。
    if os.name == 'nt':
        os.makedirs(path, exist_ok=True)
    else:
        os.makedirs(path, mode=mode, exist_ok=True)

    # 이중 안전: 권한 명시적 설정(일부 시스템에서 makedirs의 mode 매개변수 무시 가능)
    if os.name != 'nt':  # Unix系统（Linux/macOS）
        os.chmod(path, mode)

    return path_obj


def create_secure_file(file_path: str, content: str, mode: int = 0o600) -> None:
    """
    안전한 파일 생성(소유자만 읽기/쓰기 가능)

    Args:
        file_path: 파일 경로
        content: 파일 내용
        mode: 권한 모드（기본값0o600，소유자만 읽기/쓰기 가능）

    보안 검증:
        - ✅ 소유자만 읽기/쓰기 가능（0o600）
        - ✅ 다른 사용자 접근 방지
    """
    # 파일 생성
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # 권한 설정(Unix 시스템만)
    if os.name != 'nt':
        os.chmod(file_path, mode)


def validate_integer_input(value: str, field_name: str) -> int:
    """
    정수 입력 검증 및 변환(엄격 모드)

    보안 핵심 함수 - update_state.py 약한 검증 취약점 수정

    Args:
        value: 입력값(문자열)
        field_name: 필드 이름(오류 메시지용)

    Returns:
        변환된 정수

    Raises:
        ValueError: 입력이 유효한 정수가 아님

    예시:
        >>> validate_integer_input("123", "chapter_num")
        123
        >>> validate_integer_input("abc", "level")
        ValueError: ❌ 오류:level 정수여야 함, 수신:: abc
    """
    try:
        return int(value)
    except ValueError:
        print(f"❌ 오류:{field_name} 정수여야 함, 수신:: {value}", file=sys.stderr)
        raise ValueError(f"Invalid integer input for {field_name}: {value}")


# ============================================================================
# Git 环境检测（优雅降级지원）
# ============================================================================

# Git 가용성 감지 결과 캐시
_git_available: Optional[bool] = None


def is_git_available() -> bool:
    """
    Git 사용 가능 여부 감지

    Returns:
        bool: Git 是否可用

    说明：
        - 감지 결과가 캐시되어 중복 감지 방지
        - Git 없는 환경에서의 우아한 폴백 지원에 사용
    """
    global _git_available

    if _git_available is not None:
        return _git_available

    import subprocess

    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        _git_available = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        _git_available = False

    return _git_available


def is_git_repo(path: Union[str, Path]) -> bool:
    """
    지정된 디렉토리가 Git 저장소인지 감지

    Args:
        path: 디렉토리 경로

    Returns:
        bool: Git 저장소 여부
    """
    if not is_git_available():
        return False

    path = Path(path)
    git_dir = path / ".git"
    return git_dir.exists() and git_dir.is_dir()


def git_graceful_operation(
    args: list,
    cwd: Union[str, Path],
    *,
    fallback_msg: str = "Git 사용 불가，跳过版本控制操作"
) -> tuple:
    """
    우아한 Git 작업 실행(Git 사용 불가 시 조용히 폴백)

    Args:
        args: Git 명령 매개변수('git' 미포함)
        cwd: 작업 디렉토리
        fallback_msg: 폴백 시 알림 메시지

    Returns:
        (success: bool, output: str, was_skipped: bool)
        - success: 작업 성공 여부
        - output: 출력 내용
        - was_skipped: Git 사용 불가로 인한 건너뜀 여부

    예시:
        >>> success, output, skipped = git_graceful_operation(
        ...     ["add", "."], cwd="/path/to/project"
        ... )
        >>> if skipped:
        ...     print("Git not available, using fallback")
    """
    if not is_git_available():
        print(f"⚠️  {fallback_msg}", file=sys.stderr)
        return False, "", True

    import subprocess

    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=60
        )
        return result.returncode == 0, result.stdout, False
    except subprocess.TimeoutExpired:
        print(f"⚠️  Git 작업 시간 초과: git {' '.join(args)}", file=sys.stderr)
        return False, "", False
    except OSError as e:
        print(f"⚠️  Git 작업 실패: {e}", file=sys.stderr)
        return False, "", False


# ============================================================================
# 원자적 파일 쓰기(동시성 충돌 및 데이터 손상 방지)
# ============================================================================


class AtomicWriteError(Exception):
    """원자적 쓰기 실패 예외"""
    pass


def atomic_write_json(
    file_path: Union[str, Path],
    data: Dict[str, Any],
    *,
    use_lock: bool = True,
    backup: bool = True,
    indent: int = 2
) -> None:
    """
    JSON 파일 원자적 쓰기, 동시성 충돌 및 데이터 손상 방지 (CWE-362, CWE-367)

    보안 핵심 함수 - state.json 동시 쓰기 위험 수정

    구현 전략:
    1. 임시 파일에 쓰기(같은 디렉토리, 같은 파일 시스템 보장)
    2. 선택: filelock으로 배타적 잠금 획득
    3. 선택: 원본 파일 백업
    4. 원자적 이름 변경（os.replace 在 POSIX 上是原子的）

    Args:
        file_path: 대상 파일 경로
        data: 쓰기할 딕셔너리 데이터
        use_lock: 파일 잠금 사용 여부(filelock 라이브러리 필요)
        backup: 쓰기 전 원본 파일 백업 여부
        indent: JSON 들여쓰기（기본값 2）

    Raises:
        AtomicWriteError: 쓰기 실패 시 throw

    예시:
        >>> atomic_write_json('.webnovel/state.json', {'progress': {'chapter': 10}})

    보안 검증:
        - ✅ 쓰기 중단으로 인한 데이터 손상 방지(임시 파일에 먼저 쓰기)
        - ✅ 동시 쓰기 충돌 방지(filelock)
        - ✅ 롤백 지원(백업 메커니즘)
        - ✅ 크로스 플랫폼 호환
    """
    file_path = Path(file_path)
    parent_dir = file_path.parent
    parent_dir.mkdir(parents=True, exist_ok=True)

    # JSON 내용 준비
    try:
        json_content = json.dumps(data, ensure_ascii=False, indent=indent)
    except (TypeError, ValueError) as e:
        raise AtomicWriteError(f"JSON 직렬화 실패: {e}")

    # 잠금 파일 경로
    lock_path = file_path.with_suffix(file_path.suffix + '.lock')
    backup_path = file_path.with_suffix(file_path.suffix + '.bak')

    # 임시 파일 생성(같은 디렉토리로 같은 파일 시스템 보장, os.replace의 원자적 작업 가능)
    fd, temp_path = tempfile.mkstemp(
        suffix='.tmp',
        prefix=file_path.stem + '_',
        dir=parent_dir
    )

    try:
        # Step 1: 임시 파일에 쓰기
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(json_content)
            f.flush()
            os.fsync(f.fileno())  # 디스크 쓰기 보장

        # Step 2: 잠금 획득(사용 가능하고 활성화된 경우)
        lock = None
        if use_lock and HAS_FILELOCK:
            lock = FileLock(str(lock_path), timeout=10)
            lock.acquire()

        try:
            # Step 3: 원본 파일 백업(존재하고 백업 활성화된 경우)
            if backup and file_path.exists():
                try:
                    import shutil
                    shutil.copy2(file_path, backup_path)
                except OSError:
                    pass  # 백업 실패가 쓰기를 차단하지 않음

            # Step 4: 원자적 이름 변경
            os.replace(temp_path, file_path)
            temp_path = None  # 성공 표시, 정리 불필요

        finally:
            if lock is not None:
                lock.release()

    except Exception as e:
        raise AtomicWriteError(f"원자적 쓰기 실패: {e}")

    finally:
        # 정리: 임시 파일 삭제(여전히 존재하면 쓰기 실패를 의미)
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def read_json_safe(
    file_path: Union[str, Path],
    default: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    JSON 파일 안전 읽기(기본값 및 오류 처리 포함)

    Args:
        file_path: 파일 경로
        default: 파일 미존재 또는 파싱 실패 시 기본값

    Returns:
        파싱된 딕셔너리, 또는 기본값

    예시:
        >>> state = read_json_safe('.webnovel/state.json', {})
    """
    file_path = Path(file_path)
    if default is None:
        default = {}

    if not file_path.exists():
        return default

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠️ JSON 읽기 실패 ({file_path}): {e}", file=sys.stderr)
        return default


def restore_from_backup(file_path: Union[str, Path]) -> bool:
    """
    백업에서 파일 복구

    Args:
        file_path: 원본 파일 경로

    Returns:
        복구 성공 여부

    예시:
        >>> restore_from_backup('.webnovel/state.json')
        True
    """
    file_path = Path(file_path)
    backup_path = file_path.with_suffix(file_path.suffix + '.bak')

    if not backup_path.exists():
        print(f"⚠️ 백업 파일 미존재: {backup_path}", file=sys.stderr)
        return False

    try:
        import shutil
        shutil.copy2(backup_path, file_path)
        print(f"✅ 백업에서 복구 완료: {file_path}")
        return True
    except OSError as e:
        print(f"❌ 복구 실패: {e}", file=sys.stderr)
        return False


# ============================================================================
# 단위 테스트(내장 자체 검사)
# ============================================================================

def _run_self_tests():
    """내장 보안 테스트 실행"""
    print("🔍 보안 유틸리티 함수 자체 검사 실행...")

    # Test 1: sanitize_filename
    assert sanitize_filename("../../../etc/passwd") == "passwd", "경로 탐색 테스트 실패"
    assert sanitize_filename("C:\\Windows\\System32") == "System32", "Windows경로 테스트 실패"
    assert sanitize_filename("일반 캐릭터 이름") == "일반 캐릭터 이름", "중국어 테스트 실패"
    assert sanitize_filename("/tmp/../../../../../etc/hosts") == "hosts", "복잡한 경로 탐색 테스트 실패"
    assert sanitize_filename("test///file...name") == "file_name", "특수 문자 테스트 실패"  # . 会被替换
    print("  ✅ sanitize_filename: 모든 테스트 통과")

    # Test 2: sanitize_commit_message
    result = sanitize_commit_message("Test\n--author='Attacker'")
    assert "\n" not in result, "개행 문자 미제거"
    assert "--author" not in result, "Git플래그 미제거"
    assert "Attacker" in result, "내용이 잘못 제거됨"

    assert sanitize_commit_message("--amend Chapter 1") == "Chapter 1", "Git플래그 테스트 실패"  # --amend被完全移除
    assert "'" not in sanitize_commit_message("Test'message"), "따옴표 테스트 실패"
    assert sanitize_commit_message("-m Test") == "m Test", "단일 문자 플래그 테스트 실패"  # -m被移除后是"m Test"
    print("  ✅ sanitize_commit_message: 모든 테스트 통과")

    # Test 3: validate_integer_input
    assert validate_integer_input("123", "test") == 123, "정수 검증 테스트 실패"
    try:
        validate_integer_input("abc", "test")
        assert False, "ValueError를 throw해야 함"
    except ValueError:
        pass
    print("  ✅ validate_integer_input: 모든 테스트 통과")

    # Test 4: atomic_write_json
    import tempfile as tf
    test_dir = Path(tf.mkdtemp())
    test_file = test_dir / "test_state.json"

    # 写入测试
    test_data = {"chapter": 10, "중국어 키": "중국어 값"}
    atomic_write_json(test_file, test_data, use_lock=False, backup=False)
    assert test_file.exists(), "원자적 쓰기가 파일을 생성하지 않음"

    # 读取검증
    with open(test_file, 'r', encoding='utf-8') as f:
        loaded = json.load(f)
    assert loaded == test_data, "원자적 쓰기 데이터 불일치"

    # 备份测试
    atomic_write_json(test_file, {"updated": True}, use_lock=False, backup=True)
    backup_file = test_file.with_suffix('.json.bak')
    assert backup_file.exists(), "백업 미생성"

    # 恢复测试
    restore_from_backup(test_file)
    with open(test_file, 'r', encoding='utf-8') as f:
        restored = json.load(f)
    assert restored == test_data, "복구 데이터 불일치"

    # 정리
    import shutil
    shutil.rmtree(test_dir)
    print("  ✅ atomic_write_json: 모든 테스트 통과")
    if HAS_FILELOCK:
        print("  ℹ️  filelock 사용 가능, 파일 잠금 지원 활성화됨")
    else:
        print("  ⚠️  filelock 미설치, 파일 잠금 기능 사용 불가")

    print("\n✅ 모든 보안 유틸리티 함수 테스트 통과!")


if __name__ == "__main__":
    # Windows UTF-8 인코딩 수정（必须在打印前执行）
    if sys.platform == "win32":
        enable_windows_utf8_stdio()

    # 자체 검사 테스트 실행
    _run_self_tests()
