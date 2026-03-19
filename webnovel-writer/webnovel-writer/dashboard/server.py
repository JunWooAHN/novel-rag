"""
Dashboard 시작 스크립트

사용법:
    python -m dashboard.server --project-root /path/to/novel-project
    python -m dashboard.server                   # .claude 포인터에서 자동 읽기
"""

import argparse
import os
import sys
import webbrowser
from pathlib import Path


def _resolve_project_root(cli_root: str | None) -> Path:
    """우선순위에 따라 PROJECT_ROOT를 해석합니다: CLI > 환경변수 > .claude 포인터 > CWD."""
    if cli_root:
        return Path(cli_root).resolve()

    env = os.environ.get("WEBNOVEL_PROJECT_ROOT")
    if env:
        return Path(env).resolve()

    # .claude 포인터에서 읽기 시도
    cwd = Path.cwd()
    pointer = cwd / ".claude" / ".webnovel-current-project"
    if pointer.is_file():
        target = pointer.read_text(encoding="utf-8").strip()
        if target:
            p = Path(target)
            if p.is_dir() and (p / ".webnovel" / "state.json").is_file():
                return p.resolve()

    # 최종 폴백: 현재 디렉토리
    if (cwd / ".webnovel" / "state.json").is_file():
        return cwd.resolve()

    print("ERROR: PROJECT_ROOT를 찾을 수 없습니다 (.webnovel/state.json이 포함된 디렉토리가 필요합니다)", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Webnovel Dashboard Server")
    parser.add_argument("--project-root", type=str, default=None, help="소설 프로젝트 루트 디렉토리")
    parser.add_argument("--host", default="127.0.0.1", help="수신 주소")
    parser.add_argument("--port", type=int, default=8765, help="수신 포트")
    parser.add_argument("--no-browser", action="store_true", help="브라우저 자동 열기 비활성화")
    args = parser.parse_args()

    project_root = _resolve_project_root(args.project_root)
    print(f"프로젝트 경로: {project_root}")

    # 경로 처리 후 지연 임포트
    import uvicorn
    from .app import create_app

    app = create_app(project_root)

    url = f"http://{args.host}:{args.port}"
    print(f"Dashboard 시작: {url}")
    print(f"API 문서: {url}/docs")

    if not args.no_browser:
        webbrowser.open(url)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
