# Step 3 Review Gate

## 호출 제약 (경성 규칙)

- 반드시 `Task`로 검토 subagent를 호출해야 하며, 주 프로세스에서 직접 인라인 "자체 검토 결론"을 내리는 것은 금지.
- 검토 태스크는 병렬 발행 가능하나, 반드시 전부 반환된 후 통합 집계해야 함.
- `overall_score`는 반드시 집계 결과에서 산출해야 하며, 주관적 추정 점수 불가.
- 단일 챕터 집필 시나리오에서, 통일적으로 전달: `{chapter, chapter_file, project_root}`.

## 검토 라우팅 모드

- 표준/`--fast`: `auto` 라우팅 (핵심 3개 + 조건 적중).
- `--minimal`: 고정 핵심 3개 (조건 검토기 미활성).

핵심 검토기 (항상 실행):
- `consistency-checker`
- `continuity-checker`
- `ooc-checker`

조건 검토기 (`auto` 적중 시에만 실행):
- `reader-pull-checker`
- `high-point-checker`
- `pacing-checker`

## Auto 라우팅 판정 신호

입력 신호 출처:
1. Step 1.5 계약서 (과도 챕터 여부, 추독력 설계, 핵심 충돌).
2. 본 챕터 본문 (전투/반전/하이라이트/챕터 말 미종결 문제 등 신호).
3. outline 태그 (핵심 챕터/클라이맥스 챕터/권말 챕터/전환 챕터).
4. 최근 챕터 리듬 (연속 주선, 감정선 단절, 세계관선 단절).

라우팅 규칙:
- `reader-pull-checker`: 다음 조건 중 하나라도 충족 시 활성화
  - 비과도 챕터;
  - 명확한 미종결 문제/기대 앵커 포인트 존재;
  - 사용자가 명시적으로 "추독력 검토" 요청.
- `high-point-checker`: 다음 조건 중 하나라도 충족 시 활성화
  - 핵심 챕터/클라이맥스 챕터/권말 챕터;
  - 본문에 전투, 역전, 체면 깎기, 정체 폭로, 대반전 등 하이라이트 신호 출현.
- `pacing-checker`: 다음 조건 중 하나라도 충족 시 활성화
  - 화 번호 >= 10;
  - 최근 챕터에 명확한 리듬 불균형 위험 존재;
  - 사용자가 명시적으로 "리듬 검토" 요청.

## Task 호출 템플릿 (예시)

```text
selected = ["consistency-checker", "continuity-checker", "ooc-checker"]

if mode != "minimal":
  if trigger_reader_pull: selected.append("reader-pull-checker")
  if trigger_high_point: selected.append("high-point-checker")
  if trigger_pacing: selected.append("pacing-checker")

parallel Task(agent, {chapter, chapter_file, project_root}) for agent in selected
```

## 출력 계약 (통일)

각 checker 반환값은 반드시 `${CLAUDE_PLUGIN_ROOT}/references/checker-output-schema.md`를 준수:
- 필수 포함: `agent`, `chapter`, `overall_score`, `pass`, `issues`, `metrics`, `summary`
- 확장 필드 허용 (예: `hard_violations`, `soft_suggestions`), 단 필수 필드를 대체해서는 안 됨

집계 출력 최소 필드:
- `chapter` (단일 챕터)
- `start_chapter`, `end_chapter` (단일 챕터 시 둘 다 `chapter`와 동일)
- `selected_checkers`
- `overall_score`
- `severity_counts`
- `critical_issues`
- `issues` (플랫화 집계)
- `dimension_scores` (활성화된 checker 기준 계산)

## 요약 출력 템플릿

```text
검토 요약 - 제 {chapter_num} 화
- 활성화된 검토기: {list}
- 심각한 문제: {N} 개
- 높은 우선순위 문제: {N} 개
- 종합 평점: {score}
- 윤색 진입 가능: {예/아니오}
```

## 검토 지표 저장 (필수)

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index save-review-metrics --data "@${PROJECT_ROOT}/.webnovel/tmp/review_metrics.json"
```

review_metrics 파일 필드 제약 (현재 워크플로우 약정에서 아래 필드만 전달):
- `start_chapter` (int), `end_chapter` (int): 단일 챕터 시 둘 다 동일
- `overall_score` (float): 필수
- `dimension_scores` (Dict[str, float]): 활성화된 checker 기준 계산
- `severity_counts` (Dict[str, int]): 키는 critical / high / medium / low
- `critical_issues` (List[str])
- `report_file` (str)
- `notes` (str): 현재 실행 계약에서 반드시 단일 문자열이어야 함; `selected_checkers`, `timeline_gate`, `anti_ai_force_check` 등 확장 정보는 통합하여 한 줄 텍스트로 이 필드에 기록하며, 독립 최상위 키로 전달 금지
- 현재 워크플로우에서 다른 최상위 필드는 추가 전달하지 않음; 스크립트 측에서 여기에 신규 경성 검증을 추가하지 않음

## Step 4 진입 전 게이트

- `overall_score` 생성 완료.
- `save-review-metrics` 성공 완료.
- 검토 보고서의 `issues`, `severity_counts`를 Step 4에서 직접 소비 가능.
- **타임라인 게이트 (신규)**: `TIMELINE_ISSUE`가 존재하고 `severity >= high`이면, Step 4/5 진입 금지, 반드시 먼저 수정 필요.

### 타임라인 게이트 규칙

**Hard Block (수정 후에야 계속 가능)**:
- `TIMELINE_ISSUE` + `severity = critical` (카운트다운 산술 오류)
- `TIMELINE_ISSUE` + `severity = high` (사건 전후 모순/나이 충돌/시간 역행/대폭 시간 도약 무과도)

**Soft Warning (수정 권장이나 계속 가능)**:
- `TIMELINE_ISSUE` + `severity = medium` (시간 앵커 포인트 누락)
- `TIMELINE_ISSUE` + `severity = low` (경미한 시간 모호)

**게이트 판정 로직**:
```text
timeline_issues = filter(issues, type="TIMELINE_ISSUE")
critical_timeline = filter(timeline_issues, severity in ["critical", "high"])

if len(critical_timeline) > 0:
    BLOCK: "{len(critical_timeline)}개의 심각한 타임라인 문제가 존재하며, 수정 후에야 윤색 단계에 진입 가능"
    for issue in critical_timeline:
        print(f"- 제{issue.chapter}화: {issue.description}")
    return BLOCKED
else:
    통과: "타임라인 검사 통과"
```

**수정 안내**:
- 카운트다운 오류 → 카운트다운 진행 수정, D-N → D-(N-1) 연속성 확보
- 시간 역행 → 플래시백 표시 추가, 또는 시간 앵커 포인트 조정
- 대폭 시간 도약 무과도 → 시간 과도 문구/단락 추가, 또는 과도 챕터 삽입
- 사건 전후 모순 → 사건 발생 순서 조정 또는 시간 도약 설명 추가
