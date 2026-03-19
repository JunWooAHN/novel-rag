---
name: webnovel-write
description: Writes webnovel chapters (default 2000-2500 words). Use when the user asks to write a chapter or runs /webnovel-write. Runs context, drafting, review, polish, and data extraction.
allowed-tools: Read Write Edit Grep Bash Task
---

# Chapter Writing (Structured Workflow)

## 목표

- 안정적인 프로세스로 출판 가능한 장을 산출합니다: 우선 `正文/第{NNNN}章-{title_safe}.md` 사용, 제목이 없을 경우 `正文/第{NNNN}章.md`으로 대체합니다.
- 기본 장 자수 목표: 2000-2500 (사용자나 개요에서 명시적으로 덮어쓸 경우 해당 약정을 따름).
- 심사, 윤색, 데이터 역기입의 완전한 폐쇄 루프를 보장하여 "쓰고 나면 바로 컨텍스트가 유실되는" 상황을 방지합니다.
- 후속 장에서 바로 소비할 수 있는 구조화 데이터를 출력합니다: `review_metrics`, `summaries`, `chapter_meta`.

## 실행 원칙

1. 먼저 입력 완전성을 검증한 후 집필 프로세스에 진입합니다. 핵심 입력이 부족하면 즉시 차단합니다.
2. 심사와 데이터 역기입은 하드 스텝이며, `--fast`/`--minimal`은 선택적 단계의 등급 하향만 허용합니다.
3. 참조 자료는 단계별로 필요에 따라 엄격히 로딩하며, 모든 문서를 한 번에 투입하지 않습니다.
4. Step 2B와 Step 4의 직책을 분리합니다: 2B는 스타일 전환만, 4는 문제 수정과 품질 관리만 수행합니다.
5. 어떤 스텝이든 실패하면 최소 롤백을 우선하며, 전체 프로세스를 재실행하지 않습니다.

## 모드 정의

- `/webnovel-write`: Step 1 → 2A → 2B → 3 → 4 → 5 → 6
- `/webnovel-write --fast`: Step 1 → 2A → 3 → 4 → 5 → 6 (2B 건너뜀)
- `/webnovel-write --minimal`: Step 1 → 2A → 3 (기본 심사 3개만) → 4 → 5 → 6

최소 산출물 (모든 모드):
- `正文/第{NNNN}章-{title_safe}.md` 또는 `正文/第{NNNN}章.md`
- `index.db.review_metrics` 새 레코드 (`overall_score` 포함)
- `.webnovel/summaries/ch{NNNN}.md`
- `.webnovel/state.json`의 진행 상황 및 `chapter_meta` 업데이트

### 프로세스 하드 제약 (금지 사항)

- **병합 스텝 금지**: 두 Step을 하나의 동작으로 합쳐 실행하면 안 됩니다 (예: 2A와 3을 동시에).
- **건너뛰기 금지**: 모드 정의에서 건너뛰기 가능으로 표시되지 않은 Step을 건너뛰면 안 됩니다.
- **임의 개명 금지**: Step의 출력 산출물을 비표준 파일명이나 형식으로 바꾸면 안 됩니다.
- **자작 모드 금지**: `--fast` / `--minimal`은 위 정의대로만 단계를 축소할 수 있으며, 혼합 모드, "반단계" 또는 "간소화판"을 자작할 수 없습니다.
- **자체 심사 대체 금지**: Step 3 심사는 반드시 Task 하위 에이전트가 실행해야 하며, 메인 프로세스에서 인라인으로 심사 결론을 위조하면 안 됩니다.
- **소스코드 탐색 금지**: 스크립트 호출 방식은 본 문서와 data-agent 문서의 명령 예시를 기준으로 하며, 명령 실패 시 로그를 확인하여 문제를 진단하고, 소스코드를 뒤져서 호출 방식을 학습하면 안 됩니다.

## 참조 로딩 등급 (strict, lazy)

- L0: 해당 단계에 진입하기 전에는 어떤 참조 파일도 로딩하지 않습니다.
- L1: 각 단계에서 해당 단계의 "필독" 파일만 로딩합니다.
- L2: 트리거 조건이 충족될 때만 "조건부 필독/선택" 파일을 로딩합니다.

경로 규약:
- `references/...` 현재 skill 디렉토리 기준.
- `../../references/...` 전역 공유 참조 지향.

## References (파일별 참조 목록)

### 루트 디렉토리

- `references/step-3-review-gate.md`
  - 용도: Step 3 심사 호출 템플릿, 집계 형식, 데이터베이스 저장 JSON 규범.
  - 트리거: Step 3 필독.
- `references/step-5-debt-switch.md`
  - 용도: Step 5 부채 이자 스위치 규칙 (기본 비활성화).
  - 트리거: Step 5 필독.
- `../../references/shared/core-constraints.md`
  - 용도: Step 2A 집필 하드 제약 (개요가 법률 / 설정이 물리 / 발명은 식별 필요).
  - 트리거: Step 2A 필독.
- `references/polish-guide.md`
  - 용도: Step 4 문제 수정, Anti-AI 및 No-Poison 규칙.
  - 트리거: Step 4 필독.
- `references/writing/typesetting.md`
  - 용도: Step 4 모바일 독서 배치 및 출판 전 속검.
  - 트리거: Step 4 필독.
- `references/style-adapter.md`
  - 용도: Step 2B 스타일 전환 규칙, 줄거리 사실 변경 불가.
  - 트리거: Step 2B 실행 시 필독 (`--fast`/`--minimal` 건너뜀).
- `references/style-variants.md`
  - 용도: Step 1 (내장 Contract) 도입부/훅/리듬 변체 및 반복 위험 제어.
  - 트리거: Step 1에서 차별화 설계가 필요할 때 로딩.
- `../../references/reading-power-taxonomy.md`
  - 용도: Step 1 (내장 Contract) 훅, 카타르시스, 미시적 실현 taxonomy.
  - 트리거: Step 1에서 추독력 설계가 필요할 때 로딩.
- `../../references/genre-profiles.md`
  - 용도: Step 1 (내장 Contract) 장르별 리듬 임계값과 훅 선호도 설정.
  - 트리거: Step 1에서 `state.project.genre`가 확인될 때 로딩.
- `references/writing/genre-hook-payoff-library.md`
  - 용도: e스포츠/방송문/크툴루의 훅과 미시적 실현 빠른 라이브러리.
  - 트리거: Step 1 장르가 `esports/livestream/cosmic-horror`에 해당할 때 필독.

### writing (문제 지향 참조)

- `references/writing/combat-scenes.md`
  - 트리거: 전투 장 또는 심사에서 "전투 가독성/카메라 혼란" 발견.
- `references/writing/dialogue-writing.md`
  - 트리거: 심사에서 OOC, 대화 설명서화, 대사 식별 불가 발견.
- `references/writing/emotion-psychology.md`
  - 트리거: 감정 전환 경직, 동기 단절, 공감 약함.
- `references/writing/scene-description.md`
  - 트리거: 장면 공허, 공간 방위 불명확, 씬 전환 돌연.
- `references/writing/desire-description.md`
  - 트리거: 주인공 목표 약함, 욕망 추진력 부족.

## 도구 전략 (필요 시)

- `Read/Grep`: `state.json`, 개요, 장 본문 및 참조 파일 읽기.
- `Bash`: `extract_chapter_context.py`, `index_manager`, `workflow_manager` 실행.
- `Task`: `context-agent`, 심사 subagent, `data-agent` 호출 및 병렬 실행.

## 상호작용 흐름

### Step 0: 사전 검사 및 컨텍스트 최소 로딩

필수 수행:
- 실제 책 프로젝트 루트 (book project_root) 해석: 반드시 `.webnovel/state.json` 포함.
- 핵심 입력 검증: `大纲/总纲.md`, `${CLAUDE_PLUGIN_ROOT}/scripts/extract_chapter_context.py` 존재.
- 변수 정규화:
  - `WORKSPACE_ROOT`: Claude Code가 연 작업 영역 루트 디렉토리 (책 프로젝트의 상위 디렉토리일 수 있음, 예: `D:\wk\xiaoshuo`)
  - `PROJECT_ROOT`: 실제 책 프로젝트 루트 디렉토리 (반드시 `.webnovel/state.json` 포함, 예: `D:\wk\xiaoshuo\凡人资本论`)
  - `SKILL_ROOT`: skill 위치 디렉토리 (고정 `${CLAUDE_PLUGIN_ROOT}/skills/webnovel-write`)
  - `SCRIPTS_DIR`: 스크립트 디렉토리 (고정 `${CLAUDE_PLUGIN_ROOT}/scripts`)
  - `chapter_num`: 현재 장 번호 (정수)
  - `chapter_padded`: 4자리 장 번호 (예: `0007`)

환경 설정 (bash 명령 실행 전):
```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
export SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT is required}/scripts"
export SKILL_ROOT="${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT is required}/skills/webnovel-write"

python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" preflight
export PROJECT_ROOT="$(python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" where)"
```

**하드 문턱**: `preflight`가 반드시 성공해야 합니다. 이 명령이 `CLAUDE_PLUGIN_ROOT`에서 파생된 `SKILL_ROOT` / `SCRIPTS_DIR`, `webnovel.py`, `extract_chapter_context.py` 및 해석된 `PROJECT_ROOT`를 통합 검증합니다. 하나라도 실패하면 즉시 차단합니다.

출력:
- "준비 완료 입력"과 "누락 입력" 목록; 누락이 있으면 차단하고 먼저 보충을 안내합니다.

### Step 0.5: 워크플로 브레이크포인트 기록 (best-effort, 차단하지 않음)

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow start-task --command webnovel-write --chapter {chapter_num} || true
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow start-step --step-id "Step 1" --step-name "Context Agent" || true
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow complete-step --step-id "Step 1" --artifacts '{"ok":true}' || true
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow complete-task --artifacts '{"ok":true}' || true
```

요구사항:
- `--step-id`는 `Step 1` / `Step 2A` / `Step 2B` / `Step 3` / `Step 4` / `Step 5` / `Step 6`만 허용.
- 어떤 기록 실패든 경고만 기록하고, 집필을 차단하지 않습니다.
- 각 Step 실행 종료 후에도 `complete-step` 필요 (실패 시 차단하지 않음).

### Step 1: Context Agent (내장 Context Contract, 직접 집필 실행 패키지 생성)

Task를 사용하여 `context-agent` 호출, 파라미터:
- `chapter`
- `project_root`
- `storage_path=.webnovel/`
- `state_file=.webnovel/state.json`

하드 요구:
- `state` 또는 개요를 사용할 수 없으면 즉시 차단하고 누락 항목을 반환합니다.
- 출력에 반드시 동시 포함:
  - 7개 섹션 태스크북 (목표/갈등/이어받기/캐릭터/장면 제약/복선/추독력);
  - Context Contract 전체 필드 (목표/저항/대가/이 장의 변화/미해결 문제/도입부 유형/감정 리듬/정보 밀도/과도 장 판정/추독력 설계);
  - Step 2A에서 바로 소비할 수 있는 "집필 실행 패키지" (장별 비트, 불변 사실 목록, 금지 사항, 최종 점검 체크리스트).
- 계약서와 태스크북이 충돌할 경우, "개요와 설정 제약 중 더 엄격한 쪽"을 기준으로 합니다.

출력:
- 단일 "창작 실행 패키지" (태스크북 + Context Contract + 직접 집필 프롬프트), Step 2A에서 바로 소비하며, 독립된 Step 1.5를 더 이상 분리하지 않습니다.

### Step 2A: 본문 초안

실행 전 반드시 로딩:
```bash
cat "${SKILL_ROOT}/../../references/shared/core-constraints.md"
```

하드 요구:
- 순수 본문만 장 파일에 출력합니다. 상세 개요에 장 이름이 있으면 우선 `正文/第{chapter_padded}章-{title_safe}.md` 사용, 없으면 `正文/第{chapter_padded}章.md`으로 대체합니다.
- 기본 2000-2500자 기준으로 실행합니다. 개요에서 핵심 전투 장/클라이맥스 장/권말 장으로 표시되었거나 사용자가 명시적으로 지정한 경우 개요/사용자 우선으로 따릅니다.
- 자리표시자 본문 금지 (예: `[TODO]`, `[보충 필요]`).
- 이어받기 관계 유지: 전장에 명확한 훅이 있으면, 이번 장에서 반드시 응답합니다 (부분 실현 가능).

중국어 사고 집필 제약 (하드 규칙):
- **"영어 먼저 중국어 나중" 금지**: 먼저 영어 공학적 골격 (예: ABCDE 분단, Summary/Conclusion 프레임워크)으로 내용을 구성한 후 중국어로 번역하면 안 됩니다.
- **중국어 서사 단위 우선**: "동작, 반응, 대가, 감정, 장면, 관계 이동"을 기본 서사 단위로 하며, 영어 구조 태그로 본문 생성을 구동하지 않습니다.
- **영어 결론 화법 금지**: 본문, 심사 설명, 윤색 설명, 변경 요약, 최종 보고서에서 Overall / PASS / FAIL / Summary / Conclusion 등 영어 결론 제목이 나오면 안 됩니다.
- **영어는 머신 식별자에만 사용**: CLI flag (`--fast`), checker id (`consistency-checker`), DB 필드명 (`anti_ai_force_check`), JSON 키명 등 변경 불가한 인터페이스명은 영어를 유지하며, 나머지는 일률적으로 간체자 중국어를 사용합니다.

출력:
- 장 초안 (Step 2B 또는 Step 3으로 진입 가능).

### Step 2B: 스타일 어댑테이션 (`--fast` / `--minimal` 건너뜀)

실행 전 로딩:
```bash
cat "${SKILL_ROOT}/references/style-adapter.md"
```

하드 요구:
- 표현 층의 전환만 수행하며, 줄거리 사실, 이벤트 순서, 캐릭터 행동 결과, 설정 규칙은 변경하지 않습니다.
- "템플릿 말투, 설명서 말투, 기계적 말투"에 대해 지향적 개선을 수행하고, Step 4를 위한 문제 수정 여지를 남겨둡니다.

출력:
- 스타일화된 본문 (원본 장 파일을 덮어씀).

### Step 3: 심사 (auto 라우팅, 반드시 Task 하위 에이전트가 실행)

실행 전 로딩:
```bash
cat "${SKILL_ROOT}/references/step-3-review-gate.md"
```

호출 제약:
- 반드시 `Task`로 심사 subagent를 호출해야 하며, 메인 프로세스에서 심사 결론을 위조하면 안 됩니다.
- 심사를 병렬로 시작할 수 있으며, `issues/severity/overall_score`를 통합 집계합니다.
- 기본 `auto` 라우팅 사용: "이 장 실행 계약 + 본문 신호 + 개요 태그"에 따라 동적으로 심사기를 선택합니다.

핵심 심사기 (항상 실행):
- `consistency-checker`
- `continuity-checker`
- `ooc-checker`

조건부 심사기 (`auto` 명중 시 실행):
- `reader-pull-checker`
- `high-point-checker`
- `pacing-checker`

모드 설명:
- 표준/`--fast`: 핵심 3개 + auto 명중된 조건부 심사기
- `--minimal`: 핵심 3개만 (조건부 심사기 무시)

심사 지표 데이터베이스 저장 (필수):
```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index save-review-metrics --data "@${PROJECT_ROOT}/.webnovel/tmp/review_metrics.json"
```

review_metrics 필드 제약 (현재 워크플로 약정은 아래 필드만 전달):
```json
{
  "start_chapter": 100,
  "end_chapter": 100,
  "overall_score": 85.0,
  "dimension_scores": {"카타르시스 밀도": 8.5, "설정 일관성": 8.0, "리듬 제어": 7.8, "인물 조형": 8.2, "연속성": 9.0, "추독력": 8.7},
  "severity_counts": {"critical": 0, "high": 1, "medium": 2, "low": 0},
  "critical_issues": ["문제 설명"],
  "report_file": "审查报告/第100-100章审查报告.md",
  "notes": "단일 문자열; selected_checkers / timeline_gate / anti_ai_force_check 등 확장 정보를 한 줄 텍스트로 압축하여 이 필드에 기입"
}
```
- `notes`는 현재 실행 계약에서 반드시 단일 문자열이어야 하며, 객체나 배열을 전달해서는 안 됩니다.
- 현재 워크플로에서 다른 최상위 필드를 추가로 전달하지 않습니다; 스크립트 측에서 여기서 새로운 하드 검증을 하지 않습니다.

하드 요구:
- `--minimal`에서도 반드시 `overall_score`를 산출해야 합니다.
- `review_metrics`가 데이터베이스에 저장되지 않으면 Step 5에 진입할 수 없습니다.

### Step 4: 윤색 (문제 수정 우선)

실행 전 반드시 로딩:
```bash
cat "${SKILL_ROOT}/references/polish-guide.md"
cat "${SKILL_ROOT}/references/writing/typesetting.md"
```

실행 순서:
1. `critical` 수정 (필수)
2. `high` 수정 (수정 불가 시 deviation 기록)
3. `medium/low` 처리 (수익에 따라 선별)
4. Anti-AI 및 No-Poison 전문 최종 점검 실행 (반드시 `anti_ai_force_check: pass/fail` 출력)

출력:
- 윤색 후 본문 (장 파일 덮어씀)
- 변경 요약 (최소 포함: 수정 항목, 유지 항목, deviation, `anti_ai_force_check`)

### Step 5: Data Agent (상태 및 인덱스 역기입)

Task를 사용하여 `data-agent` 호출, 파라미터:
- `chapter`
- `chapter_file` 반드시 실제 장 파일 경로를 전달; 상세 개요에 장 이름이 있으면 우선 `正文/第{chapter_padded}章-{title_safe}.md` 전달, 없으면 `正文/第{chapter_padded}章.md` 전달
- `review_score=Step 3 overall_score`
- `project_root`
- `storage_path=.webnovel/`
- `state_file=.webnovel/state.json`

Data Agent 기본 하위 단계 (모두 실행):
- A. 컨텍스트 로딩
- B. AI 엔티티 추출
- C. 엔티티 소거
- D. state/index 기입
- E. 장 요약 기입
- F. AI 장면 슬라이싱
- G. RAG 벡터 인덱싱 (`rag index-chapter --scenes ...`)
- H. 스타일 샘플 평가 (`style extract --scenes ...`, `review_score >= 80` 시에만)
- I. 부채 이자 (기본 건너뜀)

`--scenes` 소스 우선순위 (G/H 단계 공유):
1. 우선 `index.db`의 scenes 레코드에서 가져옴 (Step F에서 기입한 결과)
2. 그 다음 `start_line` / `end_line`으로 본문에서 슬라이싱 구성
3. 마지막으로 단일 장면 퇴화 허용 (전체 장을 하나의 scene으로)

Step 5 실패 격리 규칙:
- G/H 실패 원인이 `--scenes` 누락, scene 비어있음, scene JSON 형식 오류인 경우: G/H 하위 단계만 보충 실행하고, Step 1-4를 롤백하거나 재실행하지 않습니다.
- A-E 실패 (state/index/summary 기입 실패): Step 5만 재실행하고, 이미 통과한 Step 1-4를 롤백하지 않습니다.
- RAG/style 하위 단계 실패로 인해 전체 집필 체인을 재실행하는 것을 금지합니다.

실행 후 검사 (최소 화이트리스트):
- `.webnovel/state.json`
- `.webnovel/index.db`
- `.webnovel/summaries/ch{chapter_padded}.md`
- `.webnovel/observability/data_agent_timing.jsonl` (관측 로그)

성능 요구:
- timing 로그의 최신 한 건을 읽습니다;
- `TOTAL > 30000ms` 시, 가장 느린 2-3개 환절과 원인 설명을 출력합니다.

관측 로그 설명:
- `call_trace.jsonl`: 외부 프로세스 호출 체인 (에이전트 시작, 대기열, 환경 탐색 등 시스템 오버헤드).
- `data_agent_timing.jsonl`: Data Agent 내부 각 하위 단계 소요 시간.
- 외부 총 소요 시간이 내부 timing 합계보다 훨씬 클 때, 기본적으로 에이전트 시작 및 환경 탐색 오버헤드로 귀인하며, 본문이나 데이터 처리가 느린 것으로 오판하지 않습니다.

부채 이자:
- 기본 비활성화, 사용자가 명시적으로 요청하거나 추적을 활성화할 때만 실행합니다 (`step-5-debt-switch.md` 참조).

### Step 6: Git 백업 (실패 가능하나 설명 필요)

```bash
git add .
git -c i18n.commitEncoding=UTF-8 commit -m "第{chapter_num}章: {title}"
```

규칙:
- 커밋 시점: 검증, 역기입, 정리 모두 완료 후 마지막에 실행.
- 커밋 메시지는 기본 중국어, 형식: `第{chapter_num}章: {title}`.
- commit 실패 시, 반드시 실패 원인과 미커밋 파일 범위를 제시합니다.

## 충분성 게이트 (반드시 통과)

다음 조건을 충족하기 전에는 프로세스를 종료할 수 없습니다:

1. 장 본문 파일 존재하고 비어있지 않음: `正文/第{chapter_padded}章-{title_safe}.md` 또는 `正文/第{chapter_padded}章.md`
2. Step 3에서 `overall_score`를 산출하고 `review_metrics` 데이터베이스 저장 성공
3. Step 4에서 모든 `critical` 처리 완료, `high` 미수정 항목에 deviation 기록 있음
4. Step 4의 `anti_ai_force_check=pass` (전문 검사 기반; fail 시 Step 5에 진입할 수 없음)
5. Step 5에서 `state.json`, `index.db`, `summaries/ch{chapter_padded}.md` 역기입 완료
6. 성능 관측이 활성화된 경우, 최신 timing 레코드를 읽고 결론 출력 완료

## 검증 및 인도

실행 검사:

```bash
test -f "${PROJECT_ROOT}/.webnovel/state.json"
test -f "${PROJECT_ROOT}/正文/第${chapter_padded}章.md"
test -f "${PROJECT_ROOT}/.webnovel/summaries/ch${chapter_padded}.md"
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index get-recent-review-metrics --limit 1
tail -n 1 "${PROJECT_ROOT}/.webnovel/observability/data_agent_timing.jsonl" || true
```

성공 기준:
- 장 파일, 요약 파일, 상태 파일 모두 갖추고 내용 판독 가능.
- 심사 점수 역추적 가능, `overall_score`가 Step 5 입력과 일치.
- 윤색 후 개요 및 설정 제약을 파괴하지 않음.

## 실패 처리 (최소 롤백)

트리거 조건:
- 장 파일 누락 또는 빈 파일;
- 심사 결과가 데이터베이스에 저장되지 않음;
- Data Agent 핵심 산출물 누락;
- 윤색으로 설정 충돌 유입.

복구 흐름:
1. 실패한 단계만 재실행하며, 이미 통과한 단계를 롤백하지 않습니다.
2. 일반적인 최소 수정:
   - 심사 누락: Step 3만 재실행하고 데이터베이스 저장;
   - 윤색 왜곡: Step 2A 출력 복원 후 Step 4 재수행;
   - 요약/상태 누락: Step 5만 재실행;
3. "검증 및 인도" 전체 검사를 재실행하여, 통과 후 종료합니다.
