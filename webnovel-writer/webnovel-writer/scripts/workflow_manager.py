#!/usr/bin/env python3
"""
Workflow state manager
- Track write/review task execution status
- Detect interruption points
- Provide recovery options
- Emit call traces for observability
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from chapter_paths import default_chapter_draft_path, find_chapter_file
from project_locator import resolve_project_root
from runtime_compat import enable_windows_utf8_stdio, normalize_windows_path
from security_utils import atomic_write_json, create_secure_directory


logger = logging.getLogger(__name__)


# UTF-8 output for Windows console (CLI run only, avoid pytest capture issues)
if sys.platform == "win32" and __name__ == "__main__" and not os.environ.get("PYTEST_CURRENT_TEST"):
    enable_windows_utf8_stdio(skip_in_pytest=True)


TASK_STATUS_RUNNING = "running"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"

STEP_STATUS_STARTED = "started"
STEP_STATUS_RUNNING = "running"
STEP_STATUS_COMPLETED = "completed"
STEP_STATUS_FAILED = "failed"


def now_iso() -> str:
    return datetime.now().isoformat()


def find_project_root(override: Optional[Path] = None) -> Path:
    """Resolve project root (containing .webnovel/state.json).

    Args:
        override: If provided, use this path directly instead of auto-detecting.
    """
    if override is not None:
        # 允许传入“工作区根目录”，统一解析到真正的 book project_root（必须포함 .webnovel/state.json）
        return resolve_project_root(str(override))
    return resolve_project_root()


# Global variable to hold CLI-provided project root
_cli_project_root: Optional[Path] = None


def _get_active_project_root() -> Path:
    """Resolve workflow paths while兼容测试中없음参 monkeypatch。"""
    if _cli_project_root is not None:
        return find_project_root(_cli_project_root)
    return find_project_root()


def get_workflow_state_path() -> Path:
    """Absolute path to workflow_state.json."""
    project_root = _get_active_project_root()
    return project_root / ".webnovel" / "workflow_state.json"


def get_call_trace_path() -> Path:
    project_root = _get_active_project_root()
    return project_root / ".webnovel" / "observability" / "call_trace.jsonl"


def append_call_trace(event: str, payload: Optional[Dict[str, Any]] = None):
    """Append workflow call trace event (best effort)."""
    payload = payload or {}
    trace_path = get_call_trace_path()
    create_secure_directory(str(trace_path.parent))
    row = {
        "timestamp": now_iso(),
        "event": event,
        "payload": payload,
    }
    with open(trace_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def safe_append_call_trace(event: str, payload: Optional[Dict[str, Any]] = None):
    try:
        append_call_trace(event, payload)
    except Exception as exc:
        logger.warning("failed to append call trace for event '%s': %s", event, exc)


def expected_step_owner(command: str, step_id: str) -> str:
    """Resolve expected caller owner by command + step id.

    Returns concise owner tags to align with
    `.claude/references/claude-code-call-matrix.md`.
    """
    if command == "webnovel-write":
        mapping = {
            "Step 1": "context-agent",
            "Step 1.5": "webnovel-write-skill",
            "Step 2A": "writer-draft",
            "Step 2B": "style-adapter",
            "Step 3": "review-agents",
            "Step 4": "polish-agent",
            "Step 5": "data-agent",
            "Step 6": "backup-agent",
        }
        return mapping.get(step_id, "webnovel-write-skill")

    if command == "webnovel-review":
        return "webnovel-review-skill"

    return "unknown"


def step_allowed_before(command: str, step_id: str, completed_steps: list[Dict[str, Any]]) -> bool:
    """Check simple ordering constraints by pending sequence."""
    sequence = get_pending_steps(command)
    if step_id not in sequence:
        return True

    expected_index = sequence.index(step_id)
    completed_ids = [str(item.get("id")) for item in completed_steps]
    required_before = sequence[:expected_index]
    return all(prev in completed_ids for prev in required_before)


def _new_task(command: str, args: Dict[str, Any]) -> Dict[str, Any]:
    started_at = now_iso()
    return {
        "command": command,
        "args": args,
        "started_at": started_at,
        "last_heartbeat": started_at,
        "status": TASK_STATUS_RUNNING,
        "current_step": None,
        "completed_steps": [],
        "failed_steps": [],
        "pending_steps": get_pending_steps(command),
        "retry_count": 0,
        "artifacts": {
            "chapter_file": {},
            "git_status": {},
            "state_json_modified": False,
            "entities_appeared": False,
            "review_completed": False,
        },
    }


def _finalize_current_step_as_failed(task: Dict[str, Any], reason: str):
    current_step = task.get("current_step")
    if not current_step:
        return
    if current_step.get("status") in {STEP_STATUS_COMPLETED, STEP_STATUS_FAILED}:
        return

    current_step = dict(current_step)
    current_step["status"] = STEP_STATUS_FAILED
    current_step["failed_at"] = now_iso()
    current_step["failure_reason"] = reason
    task.setdefault("failed_steps", []).append(current_step)
    task["current_step"] = None


def _mark_task_failed(state: Dict[str, Any], reason: str):
    task = state.get("current_task")
    if not task:
        return

    _finalize_current_step_as_failed(task, reason=reason)
    task["status"] = TASK_STATUS_FAILED
    task["failed_at"] = now_iso()
    task["failure_reason"] = reason


def start_task(command, args):
    """Start a new task."""
    state = load_state()
    current = state.get("current_task")

    if current and current.get("status") == TASK_STATUS_RUNNING:
        current["retry_count"] = int(current.get("retry_count", 0)) + 1
        current["last_heartbeat"] = now_iso()
        state["current_task"] = current
        save_state(state)
        safe_append_call_trace(
            "task_reentered",
            {
                "command": current.get("command"),
                "chapter": current.get("args", {}).get("chapter_num"),
                "retry_count": current["retry_count"],
            },
        )
        print(f"ℹ️ 작업이 이미 실행 중, 재진입 표시 수행: {current.get('command')}")
        return

    state["current_task"] = _new_task(command, args)
    save_state(state)
    safe_append_call_trace("task_started", {"command": command, "args": args})
    print(f"✅ 작업 시작됨: {command} {json.dumps(args, ensure_ascii=False)}")


def start_step(step_id, step_name, progress_note=None):
    """Mark step started."""
    state = load_state()
    task = state.get("current_task")
    if not task:
        print("⚠️ 활성 작업 없음, start-task를 먼저 사용하세요")
        return

    command = str(task.get("command") or "")
    if not step_allowed_before(command, step_id, task.get("completed_steps", [])):
        safe_append_call_trace(
            "step_order_violation",
            {
                "step_id": step_id,
                "command": command,
                "completed_steps": [row.get("id") for row in task.get("completed_steps", [])],
            },
        )

    owner = expected_step_owner(command, step_id)

    _finalize_current_step_as_failed(task, reason="step_replaced_before_completion")

    started_at = now_iso()
    task["current_step"] = {
        "id": step_id,
        "name": step_name,
        "status": STEP_STATUS_STARTED,
        "started_at": started_at,
        "running_at": started_at,
        "attempt": int(task.get("retry_count", 0)) + 1,
        "progress_note": progress_note,
    }
    task["current_step"]["status"] = STEP_STATUS_RUNNING
    task["status"] = TASK_STATUS_RUNNING
    task["last_heartbeat"] = now_iso()

    save_state(state)
    safe_append_call_trace(
        "step_started",
        {
            "step_id": step_id,
            "step_name": step_name,
            "command": task.get("command"),
            "chapter": task.get("args", {}).get("chapter_num"),
            "progress_note": progress_note,
            "expected_owner": owner,
        },
    )
    print(f"▶️ {step_id} 시작: {step_name}")


def complete_step(step_id, artifacts_json=None):
    """Mark step completed."""
    state = load_state()
    task = state.get("current_task")
    if not task or not task.get("current_step"):
        print("⚠️ 활성 Step 없음")
        return

    current_step = task["current_step"]
    if current_step.get("id") != step_id:
        print(f"⚠️ 현재 Step은 {current_step.get('id')}，와 {step_id} 불일치, 완료 거부")
        safe_append_call_trace(
            "step_complete_rejected",
            {
                "requested_step_id": step_id,
                "active_step_id": current_step.get("id"),
                "command": task.get("command"),
            },
        )
        return

    current_step["status"] = STEP_STATUS_COMPLETED
    current_step["completed_at"] = now_iso()

    if artifacts_json:
        try:
            artifacts = json.loads(artifacts_json)
            current_step["artifacts"] = artifacts
            task["artifacts"].update(artifacts)
        except json.JSONDecodeError as exc:
            print(f"⚠️ Artifacts JSON 파싱 실패: {exc}")

    task["completed_steps"].append(current_step)
    task["current_step"] = None
    task["last_heartbeat"] = now_iso()

    save_state(state)
    safe_append_call_trace(
        "step_completed",
        {
            "step_id": step_id,
            "command": task.get("command"),
            "chapter": task.get("args", {}).get("chapter_num"),
        },
    )
    print(f"✅ {step_id} 완료")


def complete_task(final_artifacts_json=None):
    """Mark task completed."""
    state = load_state()
    task = state.get("current_task")
    if not task:
        print("⚠️ 활성 작업 없음")
        return

    _finalize_current_step_as_failed(task, reason="task_completed_with_active_step")

    task["status"] = TASK_STATUS_COMPLETED
    task["completed_at"] = now_iso()

    if final_artifacts_json:
        try:
            final_artifacts = json.loads(final_artifacts_json)
            task["artifacts"].update(final_artifacts)
        except json.JSONDecodeError as exc:
            print(f"⚠️ Final artifacts JSON 파싱 실패: {exc}")

    state["last_stable_state"] = extract_stable_state(task)
    if "history" not in state:
        state["history"] = []
    state["history"].append(
        {
            "task_id": f"task_{len(state['history']) + 1:03d}",
            "command": task["command"],
            "chapter": task["args"].get("chapter_num"),
            "status": TASK_STATUS_COMPLETED,
            "completed_at": task["completed_at"],
        }
    )

    state["current_task"] = None
    save_state(state)
    safe_append_call_trace(
        "task_completed",
        {
            "command": task.get("command"),
            "chapter": task.get("args", {}).get("chapter_num"),
            "completed_steps": len(task.get("completed_steps", [])),
            "failed_steps": len(task.get("failed_steps", [])),
        },
    )
    print("🎀 작업 완료")


def detect_interruption():
    """Detect interruption state."""
    state = load_state()
    if not state or "current_task" not in state or state["current_task"] is None:
        return None

    task = state["current_task"]
    if task.get("status") == TASK_STATUS_COMPLETED:
        return None

    last_heartbeat = datetime.fromisoformat(task["last_heartbeat"])
    elapsed = (datetime.now() - last_heartbeat).total_seconds()

    interrupt_info = {
        "command": task["command"],
        "args": task["args"],
        "task_status": task.get("status"),
        "current_step": task.get("current_step"),
        "completed_steps": task.get("completed_steps", []),
        "failed_steps": task.get("failed_steps", []),
        "elapsed_seconds": elapsed,
        "artifacts": task.get("artifacts", {}),
        "started_at": task.get("started_at"),
        "retry_count": int(task.get("retry_count", 0)),
    }

    safe_append_call_trace(
        "interruption_detected",
        {
            "command": task.get("command"),
            "chapter": task.get("args", {}).get("chapter_num"),
            "task_status": task.get("status"),
            "current_step": (task.get("current_step") or {}).get("id"),
            "elapsed_seconds": elapsed,
        },
    )
    return interrupt_info


def analyze_recovery_options(interrupt_info):
    """Analyze recovery options based on interruption point."""
    current_step = interrupt_info["current_step"]
    command = interrupt_info["command"]
    chapter_num = interrupt_info["args"].get("chapter_num", "?")

    if not current_step:
        return [
            {
                "option": "A",
                "label": "처음부터 시작",
                "risk": "low",
                "description": "전체 프로세스 재실행",
                "actions": [
                    "workflow_state.json 현재 작업 삭제",
                    f"执行 /{command} {chapter_num}",
                ],
            }
        ]

    step_id = current_step["id"]

    if step_id in {"Step 1", "Step 1.5"}:
        return [
            {
                "option": "A",
                "label": "Step 1부터 다시 시작",
                "risk": "low",
                "description": "컨텍스트 다시 로드",
                "actions": [
                    "중단 상태 정리",
                    f"执行 /{command} {chapter_num}",
                ],
            }
        ]

    if step_id in {"Step 2", "Step 2A", "Step 2B"}:
        project_root = find_project_root()
        existing_chapter = find_chapter_file(project_root, chapter_num)
        draft_path = None
        if existing_chapter:
            chapter_path = str(existing_chapter.relative_to(project_root))
        else:
            draft_path = default_chapter_draft_path(project_root, chapter_num)
            chapter_path = str(draft_path.relative_to(project_root))

        options = [
            {
                "option": "A",
                "label": "미완성품 삭제, Step 1에서 재시작",
                "risk": "low",
                "description": f"정리 {chapter_path}，챕터 재생성",
                "actions": [
                    f"삭제 {chapter_path}（존재하는 경우）",
                    "Git 스테이징 영역 정리",
                    "중단 상태 정리",
                    f"执行 /{command} {chapter_num}",
                ],
            }
        ]

        candidate = existing_chapter or draft_path
        if candidate and candidate.exists():
            options.append(
                {
                    "option": "B",
                    "label": "이전 챕터로 롤백",
                    "risk": "medium",
                    "description": "현재 챕터 진행 폐기",
                    "actions": [
                        f"git reset --hard ch{(chapter_num - 1):04d}",
                        "중단 상태 정리",
                        f"계속 여부 재결정 Ch{chapter_num}",
                    ],
                }
            )
        return options

    if step_id == "Step 3":
        return [
            {
                "option": "A",
                "label": "검토 재실행",
                "risk": "medium",
                "description": "검토원 재호출 및 보고서 생성",
                "actions": ["검토 재실행", "검토 보고서 생성", "Step 4 윤색 계속"],
            },
            {
                "option": "B",
                "label": "검토 건너뛰고 직접 윤색",
                "risk": "low",
                "description": "이후 /webnovel-review로 보충 검토 가능",
                "actions": ["검토 건너뜀 표시", "Step 4 윤색 계속"],
            },
        ]

    if step_id == "Step 4":
        project_root = find_project_root()
        existing_chapter = find_chapter_file(project_root, chapter_num)
        draft_path = None
        if existing_chapter:
            chapter_path = str(existing_chapter.relative_to(project_root))
        else:
            draft_path = default_chapter_draft_path(project_root, chapter_num)
            chapter_path = str(draft_path.relative_to(project_root))

        return [
            {
                "option": "A",
                "label": "윤색 계속",
                "risk": "low",
                "description": f"윤색 계속 {chapter_path}，완료 후 Step 5 진입",
                "actions": [f"열기 및 윤색 계속 {chapter_path}", "파일 저장", "Step 5 계속（Data Agent）"],
            },
            {
                "option": "B",
                "label": "윤색 원고 삭제, Step 2A에서 다시 작성",
                "risk": "medium",
                "description": f"삭제 {chapter_path} 그리고 챕터 내용 재생성",
                "actions": [f"삭제 {chapter_path}", "Git 스테이징 영역 정리", "중단 상태 정리", f"执行 /{command} {chapter_num}"],
            },
        ]

    if step_id == "Step 5":
        return [
            {
                "option": "A",
                "label": "Step 5부터 다시 시작",
                "risk": "low",
                "description": "Data Agent 재실행(멱등)",
                "actions": ["重新调用 Data Agent", "Step 6 계속（Git 备份）"],
            }
        ]

    if step_id == "Step 6":
        return [
            {
                "option": "A",
                "label": "Git 커밋 계속",
                "risk": "low",
                "description": "미완료된 Git commit + tag 완료",
                "actions": ["Git 스테이징 영역 확인", "backup_manager.py 재실행", "complete-task 계속"],
            },
            {
                "option": "B",
                "label": "Git 변경사항 롤백",
                "risk": "medium",
                "description": "스테이징 영역의 모든 변경사항 폐기",
                "actions": ["git reset HEAD .", f"제{chapter_num}챕터 파일 삭제", "중단 상태 정리"],
            },
        ]

    return [
        {
            "option": "A",
            "label": "처음부터 시작",
            "risk": "low",
            "description": "전체 프로세스 재실행",
            "actions": ["모든 중단 artifacts 정리", f"执行 /{command} {chapter_num}"],
        }
    ]


def _backup_chapter_for_cleanup(project_root: Path, chapter_num: int, chapter_path: Path) -> Path:
    """Backup chapter file before destructive cleanup."""
    backup_dir = project_root / ".webnovel" / "recovery_backups"
    create_secure_directory(str(backup_dir))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"ch{chapter_num:04d}-{chapter_path.name}.{timestamp}.bak"
    backup_path = backup_dir / backup_name
    shutil.copy2(chapter_path, backup_path)
    return backup_path


def cleanup_artifacts(chapter_num, *, confirm: bool = False):
    """Cleanup partial artifacts."""
    artifacts_cleaned = []
    planned_actions = []

    project_root = find_project_root()

    chapter_path = find_chapter_file(project_root, chapter_num)
    if chapter_path is None:
        draft_path = default_chapter_draft_path(project_root, chapter_num)
        if draft_path.exists():
            chapter_path = draft_path

    if chapter_path and chapter_path.exists():
        planned_actions.append(f"챕터 파일 삭제: {chapter_path.relative_to(project_root)}")

    planned_actions.append("Git 스테이징 영역 재설정: git reset HEAD .")

    if not confirm:
        preview_items = [f"[预览] {action}" for action in planned_actions]
        safe_append_call_trace(
            "artifacts_cleanup_preview",
            {
                "chapter": chapter_num,
                "planned_actions": planned_actions,
                "confirmed": False,
            },
        )
        print("⚠️ 고위험 정리 작업 감지됨, 현재 미리보기만. 실행 확인 시 --confirm을 추가하세요.")
        return preview_items or ["[预览] 정리할 항목 없음"]

    if chapter_path and chapter_path.exists():
        try:
            backup_path = _backup_chapter_for_cleanup(project_root, chapter_num, chapter_path)
        except OSError as exc:
            error_msg = f"❌ 챕터 백업 실패, 삭제 취소됨: {exc}"
            safe_append_call_trace(
                "artifacts_cleanup_backup_failed",
                {
                    "chapter": chapter_num,
                    "chapter_file": str(chapter_path),
                    "error": str(exc),
                },
            )
            return [error_msg]

        chapter_path.unlink()
        artifacts_cleaned.append(str(chapter_path.relative_to(project_root)))
        artifacts_cleaned.append(f"챕터 백업 저장됨: {backup_path.relative_to(project_root)}")

    result = subprocess.run(["git", "reset", "HEAD", "."], cwd=project_root, capture_output=True, text=True)
    if result.returncode == 0:
        artifacts_cleaned.append("Git 스테이징 영역 정리됨(project)")
    else:
        git_error = (result.stderr or "").strip() or "unknown error"
        artifacts_cleaned.append(f"⚠️ Git 스테이징 영역 정리 실패: {git_error}")

    safe_append_call_trace(
        "artifacts_cleaned",
        {
            "chapter": chapter_num,
            "items": artifacts_cleaned,
            "planned_actions": planned_actions,
            "confirmed": True,
            "git_reset_ok": result.returncode == 0,
        },
    )
    return artifacts_cleaned or ["정리할 항목 없음"]


def clear_current_task():
    """Clear interrupted current task."""
    state = load_state()
    task = state.get("current_task")
    if task:
        safe_append_call_trace(
            "task_cleared",
            {
                "command": task.get("command"),
                "chapter": task.get("args", {}).get("chapter_num"),
                "status": task.get("status"),
            },
        )
        state["current_task"] = None
        save_state(state)
        print("✅ 중단된 작업 제거됨")
    else:
        print("⚠️ 중단된 작업 없음")


def fail_current_task(reason: str = "manual_fail"):
    """Mark current task as failed and keep state for diagnostics."""
    state = load_state()
    task = state.get("current_task")
    if not task:
        print("⚠️ 활성 작업 없음")
        return

    _mark_task_failed(state, reason=reason)
    save_state(state)
    safe_append_call_trace(
        "task_failed",
        {
            "command": task.get("command"),
            "chapter": task.get("args", {}).get("chapter_num"),
            "reason": reason,
        },
    )
    print(f"⚠️ 작업 실패 표시됨: {reason}")


def load_state():
    """Load workflow state."""
    state_file = get_workflow_state_path()
    if not state_file.exists():
        return {"current_task": None, "last_stable_state": None, "history": []}
    with open(state_file, "r", encoding="utf-8") as f:
        state = json.load(f)

    state.setdefault("current_task", None)
    state.setdefault("last_stable_state", None)
    state.setdefault("history", [])
    if state.get("current_task"):
        state["current_task"].setdefault("failed_steps", [])
        state["current_task"].setdefault("retry_count", 0)
    return state


def save_state(state):
    """Save workflow state atomically."""
    state_file = get_workflow_state_path()
    create_secure_directory(str(state_file.parent))
    atomic_write_json(state_file, state, use_lock=True, backup=False)


def get_pending_steps(command):
    """Get command pending step list."""
    if command == "webnovel-write":
        # v2: Step 1 内置 Contract v2，不再单独记录 Step 1.5，避免产生 step_order_violation 噪声。
        return ["Step 1", "Step 2A", "Step 2B", "Step 3", "Step 4", "Step 5", "Step 6"]
    if command == "webnovel-review":
        return ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5", "Step 6", "Step 7", "Step 8"]
    return []


def extract_stable_state(task):
    """Extract stable state snapshot."""
    return {
        "command": task["command"],
        "chapter_num": task["args"].get("chapter_num"),
        "completed_at": task.get("completed_at"),
        "artifacts": task.get("artifacts", {}),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="워크플로우 상태 관리")
    parser.add_argument(
        "--project-root",
        dest="global_project_root",
        help="프로젝트 루트 디렉토리(선택사항, 기본 자동 탐지)",
    )
    subparsers = parser.add_subparsers(dest="action", help="작업 유형")

    def add_project_root_arg(subparser):
        """Allow --project-root after subcommand for compatibility."""
        subparser.add_argument("--project-root", help="프로젝트 루트 디렉토리(선택사항, 기본 자동 탐지)")

    p_start_task = subparsers.add_parser("start-task", help="새 작업 시작")
    add_project_root_arg(p_start_task)
    p_start_task.add_argument("--command", required=True, help="명령 이름")
    p_start_task.add_argument("--chapter", type=int, help="챕터 번호")

    p_start_step = subparsers.add_parser("start-step", help="Step 시작")
    add_project_root_arg(p_start_step)
    p_start_step.add_argument("--step-id", required=True, help="Step ID")
    p_start_step.add_argument("--step-name", required=True, help="Step 이름")
    p_start_step.add_argument("--note", help="진행 메모")

    p_complete_step = subparsers.add_parser("complete-step", help="Step 완료")
    add_project_root_arg(p_complete_step)
    p_complete_step.add_argument("--step-id", required=True, help="Step ID")
    p_complete_step.add_argument("--artifacts", help="Artifacts JSON")

    p_complete_task = subparsers.add_parser("complete-task", help="작업 완료")
    add_project_root_arg(p_complete_task)
    p_complete_task.add_argument("--artifacts", help="Final artifacts JSON")

    p_fail_task = subparsers.add_parser("fail-task", help="작업 실패 표시")
    add_project_root_arg(p_fail_task)
    p_fail_task.add_argument("--reason", default="manual_fail", help="실패 이유")

    p_detect = subparsers.add_parser("detect", help="중단 탐지")
    add_project_root_arg(p_detect)

    p_cleanup = subparsers.add_parser("cleanup", help="artifacts 정리")
    add_project_root_arg(p_cleanup)
    p_cleanup.add_argument("--chapter", type=int, required=True, help="챕터 번호")
    p_cleanup.add_argument("--confirm", action="store_true", help="삭제 및 Git 초기화 실행 확인(고위험)")

    p_clear = subparsers.add_parser("clear", help="중단된 작업 제거")
    add_project_root_arg(p_clear)

    args = parser.parse_args()

    # Set global project root if provided (support both before/after subcommand).
    project_root_arg = getattr(args, "project_root", None) or getattr(args, "global_project_root", None)
    if project_root_arg:
        _cli_project_root = normalize_windows_path(project_root_arg)

    if args.action == "start-task":
        start_task(args.command, {"chapter_num": args.chapter})
    elif args.action == "start-step":
        start_step(args.step_id, args.step_name, args.note)
    elif args.action == "complete-step":
        complete_step(args.step_id, args.artifacts)
    elif args.action == "complete-task":
        complete_task(args.artifacts)
    elif args.action == "fail-task":
        fail_current_task(args.reason)
    elif args.action == "detect":
        interrupt = detect_interruption()
        if interrupt:
            print("\n🔶 중단된 작업 탐지됨:")
            print(json.dumps(interrupt, ensure_ascii=False, indent=2))
            print("\n📕 복구 옵션:")
            options = analyze_recovery_options(interrupt)
            print(json.dumps(options, ensure_ascii=False, indent=2))
        else:
            print("✅ 중단된 작업 없음")
    elif args.action == "cleanup":
        cleaned = cleanup_artifacts(args.chapter, confirm=args.confirm)
        if args.confirm:
            print(f"✅ 정리 완료: {', '.join(cleaned)}")
        else:
            for item in cleaned:
                print(item)
            print("⚠️ 이상은 미리보기이며, 실제 정리는 실행되지 않았습니다.")
    elif args.action == "clear":
        clear_current_task()
    else:
        parser.print_help()
