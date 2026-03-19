# 프로젝트 구조와 운영

## 디렉토리 계층（실제 운영）

Claude Code + Marketplace 설치 환경에서 최소 4개의 개념 계층이 있습니다：

1. `WORKSPACE_ROOT`（Claude 워크스페이스 루트, 일반적으로 `${CLAUDE_PROJECT_DIR}`）
2. `WORKSPACE_ROOT/.claude/`（워크스페이스 레벨 포인터 및 설정）
3. `PROJECT_ROOT`（실제 소설 프로젝트 루트, `/webnovel-init`이 책 제목으로 생성）
4. `CLAUDE_PLUGIN_ROOT`（플러그인 캐시 디렉토리, 프로젝트 내부에 위치하지 않음）

### A) Workspace 디렉토리（`.claude` 포함）

```text
workspace-root/
├── .claude/
│   ├── .webnovel-current-project   # 현재 소설 프로젝트 루트를 가리킴
│   └── settings.json
├── 소설A/
├── 소설B/
└── ...
```

### B) 소설 프로젝트 디렉토리（`PROJECT_ROOT`）

```text
project-root/
├── .webnovel/            # 런타임 데이터（state/index/vectors/summaries）
├── 본문/                  # 본문 챕터
├── 개요/                  # 총강 및 권별 개요
└── 설정집/                # 세계관, 캐릭터, 능력 체계
```

## 플러그인 디렉토리（Marketplace 설치）

플러그인은 소설 프로젝트 디렉토리 내에 있지 않으며, Claude 플러그인 캐시 디렉토리에 있습니다. 런타임에서 `CLAUDE_PLUGIN_ROOT`로 통일하여 참조합니다：

```text
${CLAUDE_PLUGIN_ROOT}/
├── skills/
├── agents/
├── scripts/
└── references/
```

### C) 사용자 레벨 전역 매핑（폴백）

워크스페이스에 사용 가능한 포인터가 없을 때, 사용자 레벨 registry를 사용하여 `workspace -> current_project_root` 매핑을 수행합니다：

```text
${CLAUDE_HOME:-~/.claude}/webnovel-writer/workspaces.json
```

## 시뮬레이션 디렉토리 실측（2026-03-03）

`D:\wk\novel skill\plugin-sim-20260303-012048` 기반 실제 결과：

- `WORKSPACE_ROOT`：`D:\wk\novel skill\plugin-sim-20260303-012048`
- 포인터 파일：`D:\wk\novel skill\plugin-sim-20260303-012048\.claude\.webnovel-current-project`
- 포인터 내용：`D:\wk\novel skill\plugin-sim-20260303-012048\범인자본론-2차테스트`
- 생성된 프로젝트 예시：`범인자본론/`、`범인자본론-2차테스트/`

## 자주 사용하는 운영 명령어

통합 전처리（수동 CLI 시나리오）：

```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
export SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT}/scripts"
export PROJECT_ROOT="$(python "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" where)"
```

### 인덱스 재구축

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index process-chapter --chapter 1
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index stats
```

### 상태 리포트

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" status -- --focus all
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" status -- --focus urgency
```

### 벡터 재구축

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" rag index-chapter --chapter 1
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" rag stats
```

### 테스트 진입점

```bash
pwsh "${CLAUDE_PLUGIN_ROOT}/scripts/run_tests.ps1" -Mode smoke
pwsh "${CLAUDE_PLUGIN_ROOT}/scripts/run_tests.ps1" -Mode full
```
