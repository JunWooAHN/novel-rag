#!/usr/bin/env python3
"""
Project location helpers for webnovel-writer scripts.

Problem this solves:
- Many scripts assumed CWD is the project root and used relative paths like `.webnovel/state.json`.
- In this repo, commands/scripts are often invoked from the repo root, while the actual project lives
  in a subdirectory (default: `webnovel-project/`).

These helpers provide a single, consistent way to locate the active project root.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from runtime_compat import normalize_windows_path


DEFAULT_PROJECT_DIR_NAMES: tuple[str, ...] = ("webnovel-project",)
CURRENT_PROJECT_POINTER_REL: Path = Path(".claude") / ".webnovel-current-project"

# 사용자 수준 글로벌 매핑（skills/agents가 ~/.claude에 설치될 때, 프로젝트 디렉토리는 임의 드라이브에 위치 가능）
# 이 파일은 “빈 컨텍스트 + CWD가 프로젝트 내에 없는” 상황에서도 올바른 project_root를 찾기 위해 사용.
GLOBAL_REGISTRY_REL: Path = Path("webnovel-writer") / "workspaces.json"

# Claude Code 일반적인 환경 변수（존재 시 우선 “워크스페이스 루트 디렉토리” 힌트로 사용）
ENV_CLAUDE_PROJECT_DIR = "CLAUDE_PROJECT_DIR"
ENV_CLAUDE_HOME = "CLAUDE_HOME"
ENV_WEBNOVEL_CLAUDE_HOME = "WEBNOVEL_CLAUDE_HOME"


def _find_git_root(cwd: Path) -> Optional[Path]:
    """Return nearest git root for cwd, if any."""
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _normcase_path_key(p: Path) -> str:
    """
    안정적인 경로 key 생성（Windows에서 대소문자/구분자 무관）.

    주의: key는 매핑 테이블 인덱스에만 사용되며, 실제 경로는 여전히 원본 절대 경로 문자열로 저장.
    """
    try:
        resolved = p.expanduser().resolve()
    except Exception:
        resolved = p.expanduser()
    return os.path.normcase(str(resolved))


def _get_user_claude_root() -> Path:
    raw = os.environ.get(ENV_WEBNOVEL_CLAUDE_HOME) or os.environ.get(ENV_CLAUDE_HOME)
    if raw:
        try:
            return normalize_windows_path(raw).expanduser().resolve()
        except Exception:
            return normalize_windows_path(raw).expanduser()
    return (Path.home() / ".claude").resolve()


def _global_registry_path() -> Path:
    return _get_user_claude_root() / GLOBAL_REGISTRY_REL


def _default_registry() -> dict:
    return {
        "schema_version": 1,
        "workspaces": {},
        "last_used_project_root": "",
        "updated_at": _now_iso(),
    }


def _load_global_registry(path: Path) -> dict:
    if not path.is_file():
        return _default_registry()
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
    except Exception:
        return _default_registry()
    if not isinstance(data, dict):
        return _default_registry()

    if data.get("schema_version") != 1:
        data["schema_version"] = 1
    if not isinstance(data.get("workspaces"), dict):
        data["workspaces"] = {}
    if not isinstance(data.get("last_used_project_root"), str):
        data["last_used_project_root"] = ""
    if not isinstance(data.get("updated_at"), str):
        data["updated_at"] = _now_iso()
    return data


def _save_global_registry(path: Path, data: dict) -> None:
    # 쓰기는 best-effort：사용자 디렉토리 권한/읽기 전용 드라이브 등의 상황이 메인 프로세스를 차단해서는 안 됨.
    try:
        from security_utils import atomic_write_json

        data["updated_at"] = _now_iso()
        atomic_write_json(path, data, backup=False)
    except Exception:
        # 비차단
        return


def _resolve_project_root_from_global_registry(
    base: Path,
    *,
    workspace_hint: Optional[Path] = None,
    allow_last_used_fallback: bool = False,
) -> Optional[Path]:
    """
    사용자 수준 registry에서 project_root를 분석.

    보안 정책：
    - workspace_hint 우선 사용 / CLAUDE_PROJECT_DIR 힌트로 매칭.
    - 기본적으로 last_used 폴백 미사용, “완전히 빈 컨텍스트”에서 잘못된 프로젝트에 매칭되는 것을 방지.
    """
    reg_path = _global_registry_path()
    reg = _load_global_registry(reg_path)
    workspaces = reg.get("workspaces") or {}
    if not isinstance(workspaces, dict) or not workspaces:
        return None

    hints: list[Path] = []
    env_ws = os.environ.get(ENV_CLAUDE_PROJECT_DIR)
    if env_ws:
        hints.append(normalize_windows_path(env_ws).expanduser())
    if workspace_hint is not None:
        hints.append(workspace_hint)
    hints.append(base)

    # 1) 정확한 매칭
    for hint in hints:
        key = _normcase_path_key(hint)
        entry = workspaces.get(key)
        if isinstance(entry, dict):
            raw = entry.get("current_project_root")
            if isinstance(raw, str) and raw.strip():
                target = normalize_windows_path(raw).expanduser()
                if not target.is_absolute():
                    continue
                if _is_project_root(target):
                    return target.resolve()

    # 2) 접두사 매칭(workspace 하위 디렉토리에서 실행 시)
    for hint in hints:
        hint_key = _normcase_path_key(hint)
        best_key: Optional[str] = None
        best_len = -1
        for ws_key in workspaces.keys():
            if not isinstance(ws_key, str) or not ws_key:
                continue
            ws_key_norm = os.path.normcase(ws_key)
            if hint_key == ws_key_norm or hint_key.startswith(ws_key_norm.rstrip("\\") + "\\"):
                if len(ws_key_norm) > best_len:
                    best_key = ws_key
                    best_len = len(ws_key_norm)
        if best_key:
            entry = workspaces.get(best_key)
            if isinstance(entry, dict):
                raw = entry.get("current_project_root")
                if isinstance(raw, str) and raw.strip():
                    target = normalize_windows_path(raw).expanduser()
                    if target.is_absolute() and _is_project_root(target):
                        return target.resolve()

    # 3) last_used（선택사항, 기본 비활성）
    if allow_last_used_fallback:
        raw = reg.get("last_used_project_root")
        if isinstance(raw, str) and raw.strip():
            target = normalize_windows_path(raw).expanduser()
            if target.is_absolute() and _is_project_root(target):
                return target.resolve()

    return None


def update_global_registry_current_project(
    *,
    workspace_root: Optional[Path],
    project_root: Path,
) -> Optional[Path]:
    """
    사용자 수준 registry 업데이트：workspace -> current_project_root 매핑。

    반환: registry 파일 경로(쓰기 실패 시 None 반환).
    """
    root = normalize_windows_path(project_root).expanduser()
    try:
        root = root.resolve()
    except Exception:
        root = root
    if not _is_project_root(root):
        raise FileNotFoundError(f"Not a webnovel project root (missing .webnovel/state.json): {root}")

    ws = workspace_root
    if ws is None:
        env_ws = os.environ.get(ENV_CLAUDE_PROJECT_DIR)
        if env_ws:
            ws = normalize_windows_path(env_ws).expanduser()
    if ws is None:
        return None

    try:
        ws = ws.expanduser().resolve()
    except Exception:
        ws = ws.expanduser()

    reg_path = _global_registry_path()
    reg = _load_global_registry(reg_path)
    workspaces = reg.get("workspaces")
    if not isinstance(workspaces, dict):
        workspaces = {}
        reg["workspaces"] = workspaces

    workspaces[_normcase_path_key(ws)] = {
        "workspace_root": str(ws),
        "current_project_root": str(root),
        "updated_at": _now_iso(),
    }
    reg["last_used_project_root"] = str(root)
    _save_global_registry(reg_path, reg)
    return reg_path


def _candidate_roots(cwd: Path, *, stop_at: Optional[Path] = None) -> Iterable[Path]:
    yield cwd
    for name in DEFAULT_PROJECT_DIR_NAMES:
        yield cwd / name

    for parent in cwd.parents:
        yield parent
        for name in DEFAULT_PROJECT_DIR_NAMES:
            yield parent / name
        if stop_at is not None and parent == stop_at:
            break


def _is_project_root(path: Path) -> bool:
    return (path / ".webnovel" / "state.json").is_file()


def _pointer_candidates(cwd: Path, *, stop_at: Optional[Path] = None) -> Iterable[Path]:
    """Yield candidate pointer files from cwd up to parents (bounded by stop_at when provided)."""
    for candidate in (cwd, *cwd.parents):
        yield candidate / CURRENT_PROJECT_POINTER_REL
        if stop_at is not None and candidate == stop_at:
            break


def _resolve_project_root_from_pointer(cwd: Path, *, stop_at: Optional[Path] = None) -> Optional[Path]:
    """
    Resolve project root from workspace pointer file.

    Pointer file format:
    - plain text absolute path, one line.
    - relative path is also supported (resolved relative to pointer's `.claude/` dir).
    """
    for pointer_file in _pointer_candidates(cwd, stop_at=stop_at):
        if not pointer_file.is_file():
            continue
        raw = pointer_file.read_text(encoding="utf-8").strip()
        if not raw:
            continue
        target = normalize_windows_path(raw).expanduser()
        if not target.is_absolute():
            target = (pointer_file.parent / target).resolve()
        if _is_project_root(target):
            return target.resolve()
    return None


def _find_workspace_root_with_claude(start: Path) -> Optional[Path]:
    """Find nearest ancestor containing `.claude/`."""
    for candidate in (start, *start.parents):
        if (candidate / ".claude").is_dir():
            return candidate
    return None


def write_current_project_pointer(project_root: Path, *, workspace_root: Optional[Path] = None) -> Optional[Path]:
    """
    Write workspace-level current project pointer and return pointer file path.

    If no workspace root with `.claude/` can be found, returns None (non-fatal).
    """
    root = normalize_windows_path(project_root).expanduser().resolve()
    if not _is_project_root(root):
        raise FileNotFoundError(f"Not a webnovel project root (missing .webnovel/state.json): {root}")

    ws_root = Path(workspace_root).expanduser().resolve() if workspace_root else _find_workspace_root_with_claude(root)
    if ws_root is None:
        ws_root = _find_workspace_root_with_claude(Path.cwd().resolve())
    if ws_root is None:
        # 폴백: `.claude/`를 찾을 수 없는 경우, 프로젝트 부모 디렉토리를 “워크스페이스” 후보로 간주,
        # 사용자 수준 registry 쓰기 전용(`.claude/` 디렉토리 생성하지 않음, pointer 파일 미기록).
        ws_root = root.parent if root.parent != root else None
    # 주의: ws_root가 None일 수 있음（예: 전역 설치된 skills/agents, 워크스페이스 내에 `.claude/`）。
    # 이런 경우에도 사용자 수준 registry에 기록 필요, 이후 “빈 컨텍스트”에서의 위치 찾기 지원.

    pointer_file: Optional[Path] = None
    if ws_root is not None:
        # 워크스페이스 내에 이미 `.claude/`가 존재하는 경우에만 포인터 기록, 임의 디렉토리에 `.claude/`를 무단 생성하는 것 방지.
        if (ws_root / ".claude").is_dir():
            try:
                pointer_file = ws_root / CURRENT_PROJECT_POINTER_REL
                pointer_file.write_text(str(root), encoding="utf-8")
            except Exception:
                pointer_file = None

    # best-effort 사용자 수준 registry 업데이트(비차단)
    try:
        update_global_registry_current_project(workspace_root=ws_root, project_root=root)
    except Exception:
        pass

    return pointer_file


def resolve_project_root(explicit_project_root: Optional[str] = None, *, cwd: Optional[Path] = None) -> Path:
    """
    Resolve the webnovel project root directory (the directory containing `.webnovel/state.json`).

    Resolution order:
    1) explicit_project_root (if provided)
    2) env var WEBNOVEL_PROJECT_ROOT (if set)
    3) Search from cwd and parents, including common subdir `webnovel-project/`

    Search safety:
    - If current location is inside a Git repo, parent search stops at the repo root.
      This avoids accidentally binding to unrelated parent directories.

    Raises:
        FileNotFoundError: if no valid project root can be found.
    """
    if explicit_project_root:
        root = normalize_windows_path(explicit_project_root).expanduser().resolve()
        if _is_project_root(root):
            return root

        # 호환: 명시적으로 “워크스페이스 루트 디렉토리” 전달（`.claude/.webnovel-current-project` 포인터 포함）
        # 예: D:\wk\xiaoshuo는 프로젝트 루트가 아니지만, 그 포인터가 D:\wk\xiaoshuo\<책이름>을 가리킴
        pointer_root = _resolve_project_root_from_pointer(root, stop_at=_find_git_root(root))
        if pointer_root is not None:
            return pointer_root

        # 호환: 명시적으로 “워크스페이스 루트 디렉토리” 전달하지만 그 `.claude/`가 사용자 디렉토리(전역 설치) 내에 있을 때,
        # workspace 내부에 포인터 파일이 없을 수 있음. 이 경우 사용자 수준 registry에서 검색.
        reg_root = _resolve_project_root_from_global_registry(
            root,
            workspace_hint=root,
            allow_last_used_fallback=False,
        )
        if reg_root is not None:
            return reg_root

        raise FileNotFoundError(f"Not a webnovel project root (missing .webnovel/state.json): {root}")

    env_root = os.environ.get("WEBNOVEL_PROJECT_ROOT")
    if env_root:
        root = normalize_windows_path(env_root).expanduser().resolve()
        if _is_project_root(root):
            return root
        raise FileNotFoundError(f"WEBNOVEL_PROJECT_ROOT is set but invalid (missing .webnovel/state.json): {root}")

    base = (cwd or Path.cwd()).resolve()
    git_root = _find_git_root(base)

    # Workspace pointer fallback (for layouts where `.claude` is in workspace root and projects are subdirs).
    pointer_root = _resolve_project_root_from_pointer(base, stop_at=git_root)
    if pointer_root is not None:
        return pointer_root

    # 사용자 수준 registry 폴백（”컨텍스트 힌트가 있을 때”만 활성화, 잘못된 매칭 방지）
    # - CLAUDE_PROJECT_DIR가 존재하면: Claude Code가 워크스페이스 컨텍스트를 제공한 것으로 간주
    # - 그렇지 않으면 base가 이미 기록된 workspace 내에 있을 때만 활성화(접두사 매칭)
    allow_last_used = bool(os.environ.get(ENV_CLAUDE_PROJECT_DIR))
    reg_root = _resolve_project_root_from_global_registry(
        base,
        workspace_hint=None,
        allow_last_used_fallback=allow_last_used,
    )
    if reg_root is not None:
        return reg_root

    for candidate in _candidate_roots(base, stop_at=git_root):
        if _is_project_root(candidate):
            return candidate.resolve()

    raise FileNotFoundError(
        "Unable to locate webnovel project root. Expected `.webnovel/state.json` under the current directory, "
        "a parent directory, or `webnovel-project/`. Run /webnovel-init first or pass --project-root / set "
        "WEBNOVEL_PROJECT_ROOT."
    )


def resolve_state_file(
    explicit_state_file: Optional[str] = None,
    *,
    explicit_project_root: Optional[str] = None,
    cwd: Optional[Path] = None,
) -> Path:
    """
    Resolve `.webnovel/state.json` path.

    If explicit_state_file is provided, returns it as-is (resolved to absolute if relative).
    Otherwise derives it from resolve_project_root().
    """
    base = (cwd or Path.cwd()).resolve()
    if explicit_state_file:
        p = Path(explicit_state_file).expanduser()
        return (base / p).resolve() if not p.is_absolute() else p.resolve()

    root = resolve_project_root(explicit_project_root, cwd=base)
    return root / ".webnovel" / "state.json"

