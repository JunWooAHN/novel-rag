---
name: webnovel-dashboard
description: 시각화 소설 관리 패널(읽기 전용 Web Dashboard)을 시작하여 프로젝트 상태, 엔티티 그래프 및 챕터 내용을 실시간으로 확인합니다.
allowed-tools: Bash Read
---

# Webnovel Dashboard

## 목표

로컬에서 **읽기 전용** 웹 패널을 시작하여 현재 소설 프로젝트의 다음 항목을 시각화하여 조회합니다:
- 창작 진행 상황 및 Strand 리듬 분포
- 설정 사전 (캐릭터/장소/세력 등 엔티티)
- 관계 그래프
- 챕터 및 개요 내용 탐색
- 추독력 분석 데이터

패널은 `watchdog`를 통해 `.webnovel/` 디렉토리 변경을 감시하며 실시간으로 새로고침하고, 프로젝트에 어떠한 수정도 하지 않습니다.

## 실행 단계

### Step 0: 환경 확인

```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

if [ -z "${CLAUDE_PLUGIN_ROOT}" ] || [ ! -d "${CLAUDE_PLUGIN_ROOT}/dashboard" ]; then
  echo "ERROR: dashboard 모듈을 찾을 수 없습니다: ${CLAUDE_PLUGIN_ROOT}/dashboard" >&2
  exit 1
fi
export DASHBOARD_DIR="${CLAUDE_PLUGIN_ROOT}/dashboard"
```

### Step 1: 의존성 설치 (최초)

```bash
python -m pip install -r "${DASHBOARD_DIR}/requirements.txt" --quiet
```

### Step 2: 프로젝트 루트 디렉토리 해석 및 Python 모듈 경로 준비

```bash
export SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT}/scripts"
export PROJECT_ROOT="$(python "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" where)"
echo "프로젝트 경로: ${PROJECT_ROOT}"

# `python -m dashboard.server`가 어떤 작업 디렉토리에서든 플러그인 모듈을 찾을 수 있도록 보장
if [ -n "${PYTHONPATH:-}" ]; then
  export PYTHONPATH="${CLAUDE_PLUGIN_ROOT}:${PYTHONPATH}"
else
  export PYTHONPATH="${CLAUDE_PLUGIN_ROOT}"
fi

# 프론트엔드 dist는 플러그인과 함께 배포됨; 누락 시 설치 패키지 이상
if [ ! -f "${DASHBOARD_DIR}/frontend/dist/index.html" ]; then
  echo "ERROR: 프론트엔드 빌드 산출물이 없습니다 ${DASHBOARD_DIR}/frontend/dist/index.html" >&2
  echo "플러그인을 재설치하거나 관리자에게 배포 패키지 수정을 요청하세요." >&2
  exit 1
fi
```

### Step 3: Dashboard 시작

```bash
python -m dashboard.server --project-root "${PROJECT_ROOT}"
```

시작 후 자동으로 브라우저에서 `http://127.0.0.1:8765`에 접속합니다.

자동 브라우저 열기가 필요 없으면 다음을 사용합니다:

```bash
python -m dashboard.server --project-root "${PROJECT_ROOT}" --no-browser
```

## 주의사항

- Dashboard는 순수 읽기 전용 패널이며, 모든 API는 GET만 지원하고 어떤 수정 인터페이스도 제공하지 않습니다.
- 파일 읽기는 `PROJECT_ROOT` 범위 내로 엄격히 제한되어 경로 탈출을 방지합니다.
- 사용자 정의 포트가 필요한 경우, `--port 9000` 파라미터를 추가합니다.
