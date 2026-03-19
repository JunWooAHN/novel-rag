---
name: webnovel-review
description: Reviews chapter quality with checker agents and generates reports. Use when the user asks for a chapter review or runs /webnovel-review.
allowed-tools: Read Grep Write Edit Bash Task AskUserQuestion
---

# Quality Review Skill

## Project Root Guard (반드시 먼저 확인)

- Claude Code의 "작업 영역 루트 디렉토리"가 반드시 "책 프로젝트 루트 디렉토리"와 같지는 않습니다. 일반적인 구조: 작업 영역이 `D:\wk\xiaoshuo`이고, 책 프로젝트가 `D:\wk\xiaoshuo\凡人资本论`인 경우.
- 반드시 실제 책 프로젝트 루트(반드시 `.webnovel/state.json` 포함)를 먼저 해석한 후, 이후 모든 읽기/쓰기 경로를 해당 디렉토리 기준으로 합니다.

환경 설정 (bash 명령 실행 전):
```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

if [ -z "${CLAUDE_PLUGIN_ROOT}" ] || [ ! -d "${CLAUDE_PLUGIN_ROOT}/skills/webnovel-review" ]; then
  echo "ERROR: CLAUDE_PLUGIN_ROOT가 설정되지 않았거나 디렉토리가 없습니다: ${CLAUDE_PLUGIN_ROOT}/skills/webnovel-review" >&2
  exit 1
fi
export SKILL_ROOT="${CLAUDE_PLUGIN_ROOT}/skills/webnovel-review"

if [ -z "${CLAUDE_PLUGIN_ROOT}" ] || [ ! -d "${CLAUDE_PLUGIN_ROOT}/scripts" ]; then
  echo "ERROR: CLAUDE_PLUGIN_ROOT가 설정되지 않았거나 디렉토리가 없습니다: ${CLAUDE_PLUGIN_ROOT}/scripts" >&2
  exit 1
fi
export SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT}/scripts"

export PROJECT_ROOT="$(python "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" where)"
```

## 0.5 워크플로 브레이크포인트 (best-effort, 메인 흐름을 차단하지 않음)

> 목표: `/webnovel-resume`이 실제 브레이크포인트를 기반으로 복구할 수 있게 합니다. workflow_manager에 오류가 발생해도 **경고만 기록**하고 심사를 계속합니다.

권장 (bash):
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow start-task --command webnovel-review --chapter {end} || true
```

Step 매핑 (반드시 `workflow_manager.py get_pending_steps("webnovel-review")`와 정렬):
- Step 1: 참조 로딩
- Step 2: 프로젝트 상태 로딩
- Step 3: 병렬 검사원 호출
- Step 4: 심사 보고서 생성
- Step 5: 심사 지표를 index.db에 저장
- Step 6: 심사 기록을 state.json에 기록
- Step 7: 핵심 문제 처리 (AskUserQuestion)
- Step 8: 마무리 (태스크 완료)

Step 기록 템플릿 (bash, 실패 시 차단하지 않음):
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow start-step --step-id "Step 1" --step-name "참조 로딩" || true
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow complete-step --step-id "Step 1" --artifacts '{"ok":true}' || true
```

## Review depth

- **Core (default)**: consistency / continuity / ooc / reader-pull
- **Full (핵심 장/사용자 요청)**: core + high-point + pacing

## Step 1: 참조 로딩 (필요 시)

## References (단계별 내비게이션)

- Step 1 (필독, 하드 제약): [core-constraints.md](../../references/shared/core-constraints.md)
- Step 1 (선택, Full 또는 리듬/카타르시스 관련 문제): [cool-points-guide.md](../../references/shared/cool-points-guide.md)
- Step 1 (선택, Full 또는 리듬/카타르시스 관련 문제): [strand-weave-pattern.md](../../references/shared/strand-weave-pattern.md)
- Step 1 (선택, 재작업 제안이 필요할 때만): [common-mistakes.md](references/common-mistakes.md)
- Step 1 (선택, 재작업 제안이 필요할 때만): [pacing-control.md](references/pacing-control.md)

## Reference Loading Levels (strict, lazy)

- L0: 먼저 심사 깊이 (Core / Full)를 결정한 후 참조를 로딩합니다.
- L1: References 영역의 "필독" 항목만 로딩합니다.
- L2: 문제 진단이 필요할 때만 References 영역의 "선택" 항목을 로딩합니다.

**필독**:
```bash
cat "${SKILL_ROOT}/../../references/shared/core-constraints.md"
```

**권장 (Full 또는 필요 시)**:
```bash
cat "${SKILL_ROOT}/../../references/shared/cool-points-guide.md"
cat "${SKILL_ROOT}/../../references/shared/strand-weave-pattern.md"
```

**선택**:
```bash
cat "${SKILL_ROOT}/references/common-mistakes.md"
cat "${SKILL_ROOT}/references/pacing-control.md"
```

## Step 2: 프로젝트 상태 로딩 (존재 시)

```bash
cat "$PROJECT_ROOT/.webnovel/state.json"
```

## Step 3: 병렬 검사원 호출 (Task)

**호출 제약**:
- 반드시 `Task` 도구를 통해 심사 subagent를 호출해야 하며, 메인 흐름에서 직접 인라인 심사 결론을 내리는 것을 금지합니다.
- 각 subagent 결과가 모두 반환된 후 종합 평가와 우선순위를 생성합니다.

**Core**:
- `consistency-checker`
- `continuity-checker`
- `ooc-checker`
- `reader-pull-checker`

**Full 추가**:
- `high-point-checker`
- `pacing-checker`

## Step 4: 심사 보고서 생성

저장 위치: `审查报告/第{start}-{end}章审查报告.md`

**보고서 구조 (간결판)**:
```markdown
# 제 {start}-{end} 장 품질 심사 보고서

## 종합 평가
- 카타르시스 밀도 / 설정 일관성 / 리듬 제어 / 인물 조형 / 연속성 / 추독력
- 종합 평가 및 등급

## 수정 우선순위
- 🔴 고우선 (반드시 수정)
- 🟠 중우선 (수정 권장)
- 🟡 저우선 (선택적 최적화)

## 개선 제안
- 실행 가능한 수정 제안
```

**심사 지표 JSON (트렌드 통계용)**:
```json
{
  "start_chapter": {start},
  "end_chapter": {end},
  "overall_score": 48,
  "dimension_scores": {
    "카타르시스 밀도": 8,
    "설정 일관성": 7,
    "리듬 제어": 7,
    "인물 조형": 8,
    "연속성": 9,
    "추독력": 9
  },
  "severity_counts": {"critical": 1, "high": 2, "medium": 3, "low": 1},
  "critical_issues": ["설정 자기 모순"],
  "report_file": "审查报告/第{start}-{end}章审查报告.md",
  "notes": ""
}
```

참고: 여기서는 심사 지표 JSON만 생성합니다. 데이터베이스 저장은 Step 5를 참조하세요.

## Step 5: 심사 지표를 index.db에 저장 (필수)

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index save-review-metrics --data '@review_metrics.json'
```

## Step 6: 심사 기록을 state.json에 기록 (필수)

심사 보고서 기록을 `state.json.review_checkpoints`에 기록하여 후속 추적 및 역추적에 사용합니다 (`update_state.py --add-review` 의존):
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" update-state -- --add-review "{start}-{end}" "审查报告/第{start}-{end}章审查报告.md"
```

## Step 7: 핵심 문제 처리

critical 문제가 발견되면 (`severity_counts.critical > 0` 또는 `critical_issues` 비어있지 않음), **반드시 AskUserQuestion을 사용하여** 사용자에게 물어봅니다:
- A) 즉시 수정 (권장)
- B) 보고서만 저장하고, 나중에 처리

사용자가 A를 선택하면:
- "재작업 목록" 출력 (critical 문제별 → 위치 → 최소 수정 동작 → 주의사항)
- 사용자가 명시적으로 본문 파일 직접 수정을 허가하면, `Edit`로 해당 장 파일에 최소 수정을 수행하고, `/webnovel-review` 재실행으로 검증할 것을 권장

사용자가 B를 선택하면:
- 본문 수정 없이, 심사 보고서와 지표 기록만 유지하고 이번 심사를 종료

## Step 8: 마무리 (태스크 완료)

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow start-step --step-id "Step 8" --step-name "마무리" || true
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow complete-step --step-id "Step 8" --artifacts '{"ok":true}' || true
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow complete-task --artifacts '{"ok":true}' || true
```
