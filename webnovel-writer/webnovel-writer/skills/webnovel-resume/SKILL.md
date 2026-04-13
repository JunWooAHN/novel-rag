---
name: webnovel-resume
description: Recovers interrupted webnovel tasks with precise workflow state tracking. Detects interruption point and provides safe recovery options. Activates when user wants to resume or /webnovel-resume.
allowed-tools: Read Bash AskUserQuestion
---

# Task Resume Skill

## Project Root Guard (반드시 먼저 확인)

- Claude Code의 "작업 영역 루트 디렉토리"가 반드시 "책 프로젝트 루트 디렉토리"와 같지는 않습니다. 일반적인 구조: 작업 영역이 `D:\wk\소설`이고, 책 프로젝트가 `D:\wk\소설\범인자본론`인 경우.
- 반드시 실제 책 프로젝트 루트(반드시 `.webnovel/state.json` 포함)를 먼저 해석한 후, 이후 모든 읽기/쓰기 경로를 해당 디렉토리 기준으로 합니다.

환경 설정 (bash 명령 실행 전):
```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

if [ -z "${CLAUDE_PLUGIN_ROOT}" ] || [ ! -d "${CLAUDE_PLUGIN_ROOT}/skills/webnovel-resume" ]; then
  echo "ERROR: CLAUDE_PLUGIN_ROOT가 설정되지 않았거나 디렉토리가 없습니다: ${CLAUDE_PLUGIN_ROOT}/skills/webnovel-resume" >&2
  exit 1
fi
export SKILL_ROOT="${CLAUDE_PLUGIN_ROOT}/skills/webnovel-resume"

if [ -z "${CLAUDE_PLUGIN_ROOT}" ] || [ ! -d "${CLAUDE_PLUGIN_ROOT}/scripts" ]; then
  echo "ERROR: CLAUDE_PLUGIN_ROOT가 설정되지 않았거나 디렉토리가 없습니다: ${CLAUDE_PLUGIN_ROOT}/scripts" >&2
  exit 1
fi
export SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT}/scripts"

export PROJECT_ROOT="$(python "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" where)"
```

## Workflow Checklist

Copy and track progress:

```
태스크 복구 진행:
- [ ] Step 1: 복구 프로토콜 로딩 (cat "${SKILL_ROOT}/references/workflow-resume.md")
- [ ] Step 2: 데이터 규범 로딩 (cat "${SKILL_ROOT}/references/system-data-flow.md")
- [ ] Step 3: 컨텍스트 충분 여부 확인
- [ ] Step 4: 중단 상태 감지
- [ ] Step 5: 복구 옵션 표시 (AskUserQuestion)
- [ ] Step 6: 복구 실행
- [ ] Step 7: 태스크 계속 (선택)
```

---

## Reference Loading Levels (strict, lazy)

- L0: 중단 복구 필요성이 확인되기 전까지 참조를 로딩하지 않습니다.
- L1: 복구 프로토콜 메인 파일만 로딩합니다.
- L2: 데이터 일관성 검사 시에만 데이터 규범을 로딩합니다.

### L1 (minimum)
- [workflow-resume.md](references/workflow-resume.md)

### L2 (conditional)
- [system-data-flow.md](references/system-data-flow.md) (상태 필드/복구 전략 확인이 필요할 때만)

## Step 1: 복구 프로토콜 로딩 (반드시 실행)

```bash
cat "${SKILL_ROOT}/references/workflow-resume.md"
```

**핵심 원칙** (읽은 후 적용):
- **스마트 이어쓰기 금지**: 컨텍스트 유실 위험 높음
- **반드시 감지 후 복구**: 중단점을 추측하지 않음
- **반드시 사용자 확인**: 자동 복구하지 않음

## Step 2: 데이터 규범 로딩

```bash
cat "${SKILL_ROOT}/references/system-data-flow.md"
```

## Step 3: 컨텍스트 충분 여부 확인

**체크리스트**:
- [ ] 복구 프로토콜 이해 완료
- [ ] Step 난이도 등급 파악
- [ ] 상태 구조 이해 완료
- [ ] "삭제 후 재시작" vs "스마트 이어쓰기" 원칙 명확

**누락이 있으면 → 해당 Step으로 복귀**

## Step 난이도 등급 (workflow-resume.md 출처)

| Step | 난이도 | 복구 전략 |
|------|------|---------|
| Step 1 | ⭐ | 바로 재실행 |
| Step 1.5 | ⭐ | 재설계 |
| Step 2A | ⭐⭐ | 반제품 삭제, 처음부터 다시 시작 |
| Step 2B | ⭐⭐ | 적응 계속 또는 2A로 복귀 |
| Step 3 | ⭐⭐⭐ | 사용자 결정: 재심사 또는 건너뛰기 |
| Step 4 | ⭐⭐ | 윤색 계속 또는 삭제 후 재작성 |
| Step 5 | ⭐⭐ | 재실행 (멱등) |
| Step 6 | ⭐⭐⭐ | 스테이징 영역 확인, 커밋/롤백 결정 |

## Step 4: 중단 상태 감지

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" workflow detect
```

**출력 상황**:
- 중단 없음 → 프로세스 종료, 사용자에게 알림
- 중단 감지 → Step 5 계속

## Step 5: 복구 옵션 표시 (반드시 실행)

**사용자에게 표시**:
- 태스크 명령과 파라미터
- 중단 시간과 경과 시간
- 완료된 단계
- 현재 (중단된) 단계
- 남은 단계
- 복구 옵션 및 위험 등급

**예시 출력**:

```
🔴 중단된 태스크 감지:

태스크: /webnovel-write 7
중단 위치: Step 2 - 장 내용 생성 중

완료됨:
  ✅ Step 1: 컨텍스트 로딩

미완료:
  ⏸️ Step 2: 장 내용 (1500자 작성됨)
  ⏹️ Step 3-7: 미시작

복구 옵션:
A) 반제품 삭제, Step 1부터 다시 시작 (권장)
B) Ch6으로 롤백, Ch7의 모든 진행 포기

선택하세요 (A/B):
```

## Step 6: 복구 실행

**옵션 A - 삭제 후 재시작** (권장):
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" workflow cleanup --chapter {N} --confirm
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" workflow clear
```

**옵션 B - Git 롤백**:
```bash
git -C "$PROJECT_ROOT" reset --hard ch{N-1:04d}
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" workflow clear
```

## Step 7: 태스크 계속 (선택)

사용자가 즉시 계속하기를 선택하면:
```bash
/{original_command} {original_args}
```

---

## 특수 시나리오

### Step 6 중단 (비용 높음)

```
복구 옵션:
A) 쌍장 심사 재실행 (비용: ~$0.15) ⚠️
B) 심사 건너뛰고 다음 장 계속 (나중에 보충 심사 가능)
```

### Step 4 중단 (부분 상태)

```
⚠️ state.json이 부분적으로 업데이트되었을 수 있음

A) state.json 확인 및 수정
B) 이전 장으로 롤백 (안전)
```

### 장시간 중단 (>1시간)

```
⚠️ 중단이 1시간을 초과함

컨텍스트 유실 위험 높음
이어쓰기보다 처음부터 다시 시작하는 것을 권장
```

---

## 금지 사항

- ❌ 반제품 내용 스마트 이어쓰기
- ❌ 자동 복구 전략 선택
- ❌ 중단 감지 건너뛰기
- ❌ 검증 없이 state.json 수정
