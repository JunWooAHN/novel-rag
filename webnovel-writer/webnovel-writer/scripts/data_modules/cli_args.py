#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI 매개변수 호환 도구.

배경：
- data_modules 하위 CLI는 일반적으로 argparse + subparsers 사용.
- argparse의 전역 매개변수(예: --project-root)는 서브 커맨드 앞에 위치해야 함:
    python -m data_modules.index_manager --project-root X get-core-entities
  하지만 실제 작성 워크플로우(skills/agents 문서, 도구 호출)에서는 --project-root를 서브 커맨드 뒤에 놓는 경우가 잦음：
    python -m data_modules.index_manager get-core-entities --project-root X
  이것은 바로 "unrecognized arguments" 오류를 발생（issues7 로그 참조）.

여기서 경량 argv 전처리를 제공: --project-root를 임의 위치에서 추출하여 앞으로 이동，
기존 argparse 정의를 크게 변경하지 않고 두 가지 작성 방식 모두 호환 가능.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from typing import List, Optional, Tuple


def _extract_flag_value(argv: List[str], flag: str) -> Tuple[Optional[str], List[str]]:
    """
    Extract a flag value from argv.

    Supports:
    - --flag VALUE
    - --flag=VALUE

    Returns:
    - (value, remaining_argv)
    - value uses the *last* occurrence when repeated.
    - if a dangling `--flag` has no value, it is kept in remaining_argv for argparse to raise.
    """
    value: Optional[str] = None
    rest: List[str] = []
    i = 0
    while i < len(argv):
        token = argv[i]
        if token == flag:
            if i + 1 < len(argv):
                value = argv[i + 1]
                i += 2
                continue
            # Dangling flag; keep it so argparse can error out properly.
            rest.append(token)
            i += 1
            continue
        if token.startswith(flag + "="):
            value = token.split("=", 1)[1]
            i += 1
            continue
        rest.append(token)
        i += 1
    return value, rest


def normalize_global_project_root(argv: List[str], *, flag: str = "--project-root") -> List[str]:
    """
    Normalize argv so a global `--project-root` (when present) is moved before subcommands.

    This makes argparse+subparsers accept both:
    - `... --project-root X cmd ...`
    - `... cmd ... --project-root X`
    """
    value, rest = _extract_flag_value(argv, flag)
    if value is None:
        return argv
    return [flag, value] + rest


def load_json_arg(raw: str) -> Any:
    """
    CLI에서 전달된 JSON 매개변수 파싱, 두 가지 형식 지원：
    - 직접 JSON 문자열：'{"a":1}'
    - @ 파일 경로：'@data.json'（파일에서 JSON 읽기, shell 따옴표 지옥 방지）
      - 특수 경우: '@-'는 stdin에서 읽기를 의미
    """
    if raw is None:
        raise ValueError("missing json arg")
    text = str(raw).strip()
    if text.startswith("@"):
        target = text[1:].strip()
        if not target:
            raise ValueError("invalid json arg: '@' without path")
        if target == "-":
            content = sys.stdin.read()
        else:
            content = Path(target).read_text(encoding="utf-8")
        return json.loads(content)
    return json.loads(text)
