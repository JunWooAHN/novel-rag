"""
경로 탈출 방지 도구 (Path Traversal Guard)

모든 파일 읽기 API는 디스크 접근 전에 **반드시** 이 모듈을 통한 검증을 거쳐야 합니다.
"""

from pathlib import Path
from fastapi import HTTPException


def safe_resolve(project_root: Path, relative: str) -> Path:
    """상대 경로를 절대 경로로 해석하고, project_root 내부에 있는지 확인합니다.

    Raises:
        HTTPException 403 해석된 경로가 project_root 밖으로 탈출한 경우.
    """
    try:
        resolved = (project_root / relative).resolve()
    except (OSError, ValueError):
        raise HTTPException(status_code=403, detail="잘못된 경로입니다")

    # 대상 경로가 project_root의 "하위 경로 또는 자기 자신"인지 엄격하게 확인
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="경로 이탈: PROJECT_ROOT 외부의 파일에 접근할 수 없습니다")

    return resolved
