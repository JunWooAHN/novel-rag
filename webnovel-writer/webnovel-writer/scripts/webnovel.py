#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
webnovel 통합 진입 스크립트(필요 없음 `cd`）

사용법예시：
  python "<SCRIPTS_DIR>/webnovel.py" preflight
  python "<SCRIPTS_DIR>/webnovel.py" where
  python "<SCRIPTS_DIR>/webnovel.py" index stats

说明：
- 이 스크립트는 `.claude/scripts` sys.path에 추가한 후 전달만 `data_modules.webnovel`。
- skills/agents가 프로젝트 수준 또는 사용자 수준(~/.claude)에 설치될 때의 호출 방식에 적응.
"""

from __future__ import annotations

import sys
from pathlib import Path

from runtime_compat import enable_windows_utf8_stdio


def main() -> None:
    scripts_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(scripts_dir))

    # 지연 임포트, sys.path 미준비 방지
    from data_modules.webnovel import main as _main

    _main()


if __name__ == "__main__":
    enable_windows_utf8_stdio(skip_in_pytest=True)
    main()
