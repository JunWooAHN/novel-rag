# Claude Code 호출 매트릭스 (명령 귀속 및 트리거 시점)

> 목적: "누가 호출하는지, 언제 호출하는지, 어떤 스크립트를 호출하는지"를 명확히 하여, Claude Code 내부 프로세스를 수동 명령으로 오인하는 것을 방지합니다.

## 규칙

- 본 프로젝트의 스크립트는 기본적으로 **Claude Code Skill/Agent**가 프로세스 노드에서 트리거합니다.
- 문서에서 명시적으로 설명하지 않는 한, 스크립트를 "사용자 수동 일상 명령"으로 간주하지 않습니다.
- 새 스크립트 또는 새 명령 트리거 포인트를 추가할 때, 반드시 본 파일을 동기 업데이트해야 합니다.

## 명령 수준 매트릭스 (진입점 -> 호출자 -> 트리거 시점)

| 진입 명령 | 호출자 | 트리거 시점 | 핵심 스크립트/동작 |
|---|---|---|---|
| `/webnovel-init` | `webnovel-init` Skill | 새 프로젝트 생성, 심층 초기화 단계 | `scripts/init_project.py` + `idea_bank.json` 생성 |
| `/webnovel-plan` | `webnovel-plan` Skill | 권 대강/챕터 대강 생성 완료 후 상태 기록 시 | `scripts/update_state.py --volume-planned ...` |
| `/webnovel-write` | `webnovel-write` Skill | 작성 프로세스 Step 5 데이터 체인 업데이트 시 | Task가 `data-agent` 호출(내부에서 state/index 기록) |
| `/webnovel-query` | `webnovel-query` Skill | "복선 긴급도/Strand 리듬" 등 분석 요청 시 | `scripts/status_reporter.py --focus urgency/strand` |
| `/webnovel-resume` | `webnovel-resume` Skill | 중단 복구 감지, 정리, 중단점 복구 시 | `scripts/workflow_manager.py detect/cleanup/clear` |

## 스크립트 수준 매트릭스 (스크립트 -> 트리거 주체 -> 시점)

| 스크립트 | 주요 트리거 주체 | 트리거 노드 | 비고 |
|---|---|---|---|
| `${CLAUDE_PLUGIN_ROOT}/scripts/webnovel.py` | 모든 Skills / Agents | CLI 호출이 필요한 모든 노드 | **통합 진입점**: 실제 book project_root를 파싱하고, `data_modules/*` 또는 `scripts/*.py`로 전달하여, `PYTHONPATH/cd/매개변수 순서`로 인한 암묵적 실패를 방지 |
| `${CLAUDE_PLUGIN_ROOT}/scripts/update_state.py` | `webnovel-plan` Skill | 챕터 대강/권 계획 저장 후 `state.json` 업데이트 | 자동화 스크립트에서도 호출 가능; 기본적으로 수동 일상 진입점이 아님 |
| `${CLAUDE_PLUGIN_ROOT}/scripts/status_reporter.py` | `webnovel-query` Skill / `pacing-checker` Agent(선택) | 쿼리 분석 또는 리듬 검토 시 | 건강 보고서 및 긴급도 분석 출력 |
| `${CLAUDE_PLUGIN_ROOT}/scripts/workflow_manager.py` | `webnovel-resume` Skill | 복구 프로세스 detect/cleanup/clear | 복구 시나리오에서만 트리거 |
| `${CLAUDE_PLUGIN_ROOT}/scripts/init_project.py` | `webnovel-init` Skill | 프로젝트 초기화 단계 | 프로젝트 스캐폴딩 및 기본 상태 파일 담당 |

## 내부 라이브러리 호출 (독립 명령이 아님)

| 내부 모듈 | 호출자 | 트리거 시점 |
|---|---|---|
| `${CLAUDE_PLUGIN_ROOT}/scripts/data_modules/state_validator.py` | `update_state.py`, `status_reporter.py` | `state.json` 읽기/쓰기 시 자동 정규화 및 검증 |

## 변경 제약 (향후 개발 시 반드시 준수)

1. "Skill/Agent가 트리거할 수 있는" 새 스크립트를 추가하면, 반드시 본 매트릭스에 보충해야 합니다.
2. 스크립트 트리거 시점이 변경되면(예: plan 단계에서 write 단계로 변경), 반드시 본 매트릭스를 동기 업데이트해야 합니다.
3. PR/커밋 설명에 "호출자 + 트리거 노드 + 수동 호출 허용 여부"를 명시해야 합니다.
