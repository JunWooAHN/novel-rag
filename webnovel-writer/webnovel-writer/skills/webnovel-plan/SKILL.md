---
name: webnovel-plan
description: Builds volume and chapter outlines from the total outline, inherits creative constraints, and prepares writing-ready chapter plans. Use when the user asks for outlining or runs /webnovel-plan.
---

# Outline Planning

Purpose: 총강을 권별 + 장별 개요로 세분화합니다. 전체 스토리를 재설계하지 않습니다.
설정 정책: 먼저 init에서 산출한 총강+세계관을 기반으로 설정집 기준선을 보충하고, 권별 개요 완성 후 기존 설정집에 증분 보충을 직접 수행합니다.

## Project Root Guard
- Claude Code의 "작업 영역 루트 디렉토리"가 반드시 "책 프로젝트 루트 디렉토리"와 같지는 않습니다. 일반적인 구조: 작업 영역이 `D:\wk\xiaoshuo`이고, 책 프로젝트가 `D:\wk\xiaoshuo\凡人资本论`인 경우.
- 반드시 `PROJECT_ROOT`를 실제 책 프로젝트 루트(반드시 `.webnovel/state.json` 포함)로 해석한 후, 이후 모든 읽기/쓰기 경로를 해당 디렉토리 기준으로 합니다.

환경 설정 (bash 명령 실행 전):
```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

if [ -z "${CLAUDE_PLUGIN_ROOT}" ] || [ ! -d "${CLAUDE_PLUGIN_ROOT}/skills/webnovel-plan" ]; then
  echo "ERROR: CLAUDE_PLUGIN_ROOT가 설정되지 않았거나 디렉토리가 없습니다: ${CLAUDE_PLUGIN_ROOT}/skills/webnovel-plan" >&2
  exit 1
fi
export SKILL_ROOT="${CLAUDE_PLUGIN_ROOT}/skills/webnovel-plan"

if [ -z "${CLAUDE_PLUGIN_ROOT}" ] || [ ! -d "${CLAUDE_PLUGIN_ROOT}/scripts" ]; then
  echo "ERROR: CLAUDE_PLUGIN_ROOT가 설정되지 않았거나 디렉토리가 없습니다: ${CLAUDE_PLUGIN_ROOT}/scripts" >&2
  exit 1
fi
export SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT}/scripts"

export PROJECT_ROOT="$(python "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" where)"
```

## References (단계별 내비게이션)

- Step 3 (필독, 비트시트 템플릿): [大纲-卷节拍表.md](../../templates/output/大纲-卷节拍表.md)
- Step 4.5 (필독, 타임라인 템플릿): [大纲-卷时间线.md](../../templates/output/大纲-卷时间线.md)
- Step 4 (필독, 장르 구성): [genre-profiles.md](../../references/genre-profiles.md)
- Step 4 (필독, Strand 리듬): [strand-weave-pattern.md](../../references/shared/strand-weave-pattern.md)
- Step 4 (선택, 카타르시스 구조 세분화 필요 시): [cool-points-guide.md](../../references/shared/cool-points-guide.md)
- Step 5/6 (선택, 갈등 강도 계층화): [conflict-design.md](references/outlining/conflict-design.md)
- Step 5 (선택, 훅/리듬 세분화 필요 시): [reading-power-taxonomy.md](../../references/reading-power-taxonomy.md)
- Step 6 (선택, 장별 미세 구조 세분화): [chapter-planning.md](references/outlining/chapter-planning.md)
- Step 4/5 (선택, e스포츠/방송문/크툴루): [genre-volume-pacing.md](references/outlining/genre-volume-pacing.md)
- 아카이브 (메인 흐름에 포함되지 않음): `references/outlining/outline-structure.md`, `references/outlining/plot-frameworks.md`

## Reference Loading Levels (strict, lazy)

Use progressive disclosure and load only what current step requires:
- L0: No references before scope/volume is confirmed.
- L1: Before each step, load only the "필독" items in **References (단계별 내비게이션)**.
- L2: Load optional items only when the trigger condition applies.

## Workflow
1. Load project data.
2. Build setting baseline from 총강 + 세계관 (in-place incremental).
3. Select volume and confirm scope.
4. Generate volume beat sheet (비트시트).
4.5. Generate volume timeline (타임라인표).
5. Generate volume skeleton.
6. Generate chapter outlines in batches.
7. Enrich existing setting files from volume outline (in-place incremental).
8. Validate + save + update state.

## 1) Load project data
```bash
cat "$PROJECT_ROOT/.webnovel/state.json"
cat "$PROJECT_ROOT/大纲/总纲.md"
```

Optional (only if they exist):
- `设定集/主角组.md`
- `设定集/女主卡.md`
- `设定集/反派设计.md`
- `设定集/世界观.md`
- `设定集/力量体系.md`
- `设定集/主角卡.md`
- `.webnovel/idea_bank.json` (inherit constraints)

If 총강.md lacks volume ranges / core conflict / climax, ask the user to fill those before proceeding.

## 2) Build setting baseline from 총강 + 세계관
목표: 기존 내용을 뒤엎지 않는 전제 하에, 설정집을 "골격 템플릿"에서 "기획 및 집필 가능한" 기준선 상태로 진입시킵니다.

입력 소스:
- `大纲/总纲.md`
- `设定集/世界观.md`
- `设定集/力量体系.md`
- `设定集/主角卡.md`
- `设定集/反派设计.md`

실행 규칙 (필수):
- 증분 보충만 수행하며, 비우거나 파일 전체를 재작성하지 않습니다.
- "실행 가능한 필드"를 우선 보충: 캐릭터 포지셔닝, 세력 관계, 능력 경계, 대가 규칙, 악역 계층 매핑.
- 총강과 기존 설정이 충돌하면, 먼저 충돌을 나열하고 차단하여 사용자 결정을 기다린 후 수정합니다.

기준선 보충 최소 요구:
- `设定集/世界观.md`: 세계 규칙 경계, 사회 구조, 핵심 장소 용도.
- `设定集/力量体系.md`: 경계 체인/능력 제한/대가와 쿨다운.
- `设定集/主角卡.md`: 욕망, 결함, 초기 자원과 제한.
- `设定集/反派设计.md`: 소/중/대 악역 계층과 주인공 미러 관계.

## 3) Select volume
- Offer choices from 총강.md (권명 + 장 범위).
- Confirm any special requirement (tone, POV emphasis, romance, etc.).
총강에 권명/장 범위/핵심 갈등/권말 클라이맥스가 없으면, 먼저 보충 질문하고 총강을 업데이트한 후 계속합니다.

## 4) Generate volume beat sheet (비트시트)
목표: 먼저 이 권의 "약속→위기 상승→중반 반전→최저점→대실현+새 훅"을 확정하여, 권 중반의 표류를 방지합니다.

Load template:
```bash
cat "${SKILL_ROOT}/../../templates/output/大纲-卷节拍表.md"
```

Must satisfy (hard requirements):
- **중반 반전 (필수)**: 비워둘 수 없음; 없으면 `없음(사유: ...)`으로 작성
- **위기 체인**: 최소 3회 상승 (표의 1-3행 비울 수 없음)
- **권말 새 훅**: 반드시 "마지막 장의 장말 미해결 문제"로 이어져야 함

Write output:
```bash
@'
{beat_sheet_content}
'@ | Set-Content -Encoding UTF8 "$PROJECT_ROOT/大纲/第{volume_id}卷-节拍表.md"
```

Completion criteria:
- `大纲/第{volume_id}卷-节拍表.md` 존재하고 비어있지 않음
- Step 4/5에서 Catalyst / 중반 반전 / 최저점 / 대실현 / 새 훅을 직접 참조하여 리듬을 앵커링할 수 있음

## 4.5) Generate volume timeline (타임라인표)

목표: 이 권의 시간축 기준을 수립하여, 장 간 시간 추진 논리의 자체 일관성을 보장하고, "1장에서 재앙이 발생하고 2장에서 전투"와 같은 시간 점프 문제를 방지합니다.

Load template:
```bash
cat "${SKILL_ROOT}/../../templates/output/大纲-卷时间线.md"
```

Must satisfy (hard requirements):
- **시간 기준 (필수)**: 이 권에서 사용하는 시간 체계를 명확히 함 (포스트아포칼립스 X일차/선력 연월/현대 날짜)
- **이 권의 시간 범위 (필수)**: 이 권이 커버하는 시간 범위
- **핵심 카운트다운 이벤트**: 시한성 이벤트가 있으면 (물자 고갈/대회 시작/마감일 등), 반드시 나열하고 D-N으로 표기

Write output:
```bash
@'
{timeline_content}
'@ | Set-Content -Encoding UTF8 "$PROJECT_ROOT/大纲/第{volume_id}卷-时间线.md"
```

Completion criteria:
- `大纲/第{volume_id}卷-时间线.md` 존재하고 비어있지 않음
- 시간 기준과 이 권의 범위가 명확히 됨
- 카운트다운 이벤트가 있으면 표에 기재됨

## 5) Generate volume skeleton
Load genre profile and apply standards:
```bash
cat "${SKILL_ROOT}/../../references/genre-profiles.md"
cat "${SKILL_ROOT}/../../references/shared/strand-weave-pattern.md"
```

Optional (카타르시스 구조 세분화가 필요할 때만):
```bash
cat "${SKILL_ROOT}/../../references/shared/cool-points-guide.md"
```

Optional (권급 갈등 체인과 강도 계층화 보강이 필요할 때만):
```bash
cat "${SKILL_ROOT}/references/outlining/conflict-design.md"
```

Load beat sheet (must exist):
```bash
cat "$PROJECT_ROOT/大纲/第{volume_id}卷-节拍表.md"
```

Extract for current genre:
- Strand 비율 (Quest/Fire/Constellation)
- 카타르시스 밀도 기준 (장당 최소/권장)
- 훅 유형 선호

### Strand Weave 기획 전략
Based on genre profile, distribute chapters:
- **Quest Strand** (메인 라인 추진): 55-65% 장
  - 목표 명확, 진전 가시적, 단계적 성과 있음
  - 예: 경계 돌파, 임무 완수, 보물 획득
- **Fire Strand** (감정/관계): 20-30% 장
  - 인물 관계 변화, 감정 갈등, 팀 다이내믹스
  - 예: 여주와 교류, 사제 갈등, 형제 배신
- **Constellation Strand** (세계관/미스터리): 10-20% 장
  - 세계관 공개, 복선 매설, 미스터리 추진
  - 예: 고대 비밀 발견, 악역 음모 폭로, 세계 진상

**Weaving pattern** (recommended):
- 매 3-5장마다 주도 Strand 전환
- 클라이맥스 장은 다중 Strand 교직 가능
- 권말 3-5장은 Quest Strand 집중

For e스포츠/방송문/크툴루, apply dedicated volume pacing template:
```bash
cat "${SKILL_ROOT}/references/outlining/genre-volume-pacing.md"
```

### 카타르시스 밀도 기획 전략
Based on genre profile:
- **일반 장**: 1-2개 소카타르시스 (강도 2-3)
- **핵심 장**: 2-3개 카타르시스, 최소 1개 중카타르시스 (강도 4-5)
- **클라이맥스 장**: 3-4개 카타르시스, 최소 1개 대카타르시스 (강도 6-7)

**Distribution rule**:
- 매 5-8장마다 최소 1개 핵심 장
- 매 권 최소 1개 클라이맥스 장 (보통 권말)

### 제약 트리거 기획 전략
If idea_bank.json exists:
```bash
cat "$PROJECT_ROOT/.webnovel/idea_bank.json"
```

Calculate trigger frequency:
- **반클리셰 규칙**: 매 N장마다 1회 트리거
  - N = max(5, 총 장수 / 10)
  - 예: 50장 권 → 매 5장마다 트리거
  - 예: 100장 권 → 매 10장마다 트리거
- **하드 제약**: 전 권에 걸쳐, 장별 목표/카타르시스 설계에 반영
- **주인공 결함**: 매 권 최소 2회 갈등 원인이 됨
- **악역 미러**: 악역 등장 장에서 반드시 미러 대비 체현

Use this template and fill from 총강 + idea_bank:

```markdown
# 제 {volume_id} 권: {권명}

> 장 범위: 제 {start} - {end} 장
> 핵심 갈등: {conflict}
> 권말 클라이맥스: {climax}

## 권 요약
{2-3 단락 개요}

## 핵심 인물과 악역
- 주요 등장 캐릭터:
- 악역 계층:

## Strand Weave 기획
| 장 범위 | 주도 Strand | 내용 개요 |
|---------|------------|---------|

## 카타르시스 밀도 기획
| 장 | 카타르시스 유형 | 구체 내용 | 강도 |
|------|---------|---------|------|

## 복선 기획
| 장 | 작업 | 복선 내용 |
|------|------|---------|

## 제약 트리거 기획 (해당 시)
- 반클리셰 규칙: 매 N장마다 1회 트리거
- 하드 제약: 전 권 관통
```

## 6) Generate chapter outlines (batched)
Batching rule:
- 20장 이하: 1 배치
- 21-40장: 2 배치
- 41-60장: 3 배치
- 60장 초과: 4+ 배치

Optional (훅/리듬 세분화가 필요할 때만):
```bash
cat "${SKILL_ROOT}/../../references/reading-power-taxonomy.md"
```

Optional (장별 미세 구조/제목 전략 세분화가 필요할 때만):
```bash
cat "${SKILL_ROOT}/references/outlining/chapter-planning.md"
```

### Chapter generation strategy
For each chapter, determine:

**1. Strand assignment** (follow volume skeleton distribution)
- Quest: 메인 라인 임무 추진, 목표 달성, 능력 향상
- Fire: 인물 관계, 감정 갈등, 팀 다이내믹스
- Constellation: 세계관 공개, 복선 매설, 미스터리 추진

**2. 카타르시스 설계** (based on Strand and position)
- Quest Strand → 성취 카타르시스 (페이스슬랩, 역전, 돌파)
- Fire Strand → 감정 카타르시스 (인정, 보호, 고백)
- Constellation Strand → 인지 카타르시스 (진실, 예언, 정체)

**3. 훅 설계** (based on next chapter's Strand)
- 서스펜스 훅: 질문 제기, 위기 조성
- 약속 훅: 보상 예고, 반전 암시
- 감정 훅: 관계 변화, 캐릭터 위기

**4. 악역 계층** (based on volume skeleton)
- 없음: 일상 장, 수련 장, 관계 장
- 소: 소갈등, 소악역, 국지적 대항
- 중: 중악역 등장, 중요 갈등, 단계적 대항
- 대: 대악역 등장, 핵심 갈등, 권급 클라이맥스

**5. 핵심 엔티티** (new or important)
- 새 캐릭터: 이름 + 한 줄 포지셔닝
- 새 장소: 이름 + 한 줄 설명
- 새 아이템: 이름 + 기능
- 새 세력: 이름 + 입장

**6. 제약 검사** (if idea_bank exists)
- 반클리셰 규칙 트리거 여부?
- 하드 제약 체현 여부?
- 주인공 결함 표현 여부?
- 악역 미러 체현 여부?

Chapter format (include 악역 계층 for context-agent):

```markdown
### 제 {N} 장: {제목}
- 목표: {20자 이내}
- 저항: {20자 이내}
- 대가: {20자 이내}
- 시간 앵커: {포스트아포칼립스 X일차 시간대/선력X년X월X일/구체 날짜+시간대}
- 장내 시간 범위: {예: 3시간/반나절/1일}
- 전장과의 시간차: {예: 바로 이어짐/6시간/1일/밤 넘김}
- 카운트다운 상태: {이벤트A D-3 -> D-2 / 없음}
- 카타르시스: {유형} - {30자 이내}
- Strand: {Quest|Fire|Constellation}
- 악역 계층: {없음/소/중/대}
- 시점/주인공: {주인공A/주인공B/여주/군상}
- 핵심 엔티티: {신규 또는 중요 등장}
- 이 장의 변화: {30자 이내, 정량화 가능한 변화 우선}
- 장말 미해결 문제: {30자 이내}
- 훅: {유형} - {30자 이내}
```

**시간 필드 설명**:
- **시간 앵커**: 이 장이 발생하는 구체적 시간점, 반드시 타임라인표와 일치해야 함
- **장내 시간 범위**: 이 장 내용이 커버하는 시간 길이
- **전장과의 시간차**: 이전 장 종료 시간과의 간격
  - 바로 이어짐: 시간 간격 없이 직접 이어짐
  - 밤 넘김: 밤을 넘기지만 12시간을 초과하지 않음
  - 구체 시간: 예컨대 6시간, 1일, 3일
- **카운트다운 상태**: 카운트다운 이벤트가 있으면, 추진 상황 표기 (D-N → D-(N-1))

**필드 설명**:
- **장말 미해결 문제**: 이 장 결말에 반드시 남겨야 하는 "미해결 결정/문제"로, 독자가 다음 장을 클릭하도록 유도.
  - 규칙: 반드시 **훅**의 유형/강도와 일치해야 하며, "훅은 강한데 문제가 허약한" 불일치가 있어서는 안 됨.
- **훅**: 이 장에 설정해야 할 장말 훅 (기획용)
  - 예: 서스펜스 훅 - 미스터리 인물의 정체가 곧 밝혀짐
  - 의미: 이 장 결말에 이 서스펜스 훅을 설정해야 함
  - 다음 장에서 context-agent가 chapter_meta[N].hook(실제 구현된 훅)을 읽어 "전장 이어받기" 가이드 생성
  - 훅 유형 참조: 서스펜스 훅 | 위기 훅 | 약속 훅 | 감정 훅 | 선택 훅 | 갈망 훅

Save after each batch:
```bash
@'
{batch_content}
'@ | Add-Content -Encoding UTF8 "$PROJECT_ROOT/大纲/第{volume_id}卷-详细大纲.md"
```

## 7) Enrich existing setting files from volume outline
목표: 권별 개요 작성 후, 이 권의 새로운 사실을 "기존 설정집 파일"에 기록하여, 후속 집필에서 직접 읽을 수 있도록 보장합니다.

입력 소스:
- `大纲/第{volume_id}卷-节拍表.md`
- `大纲/第{volume_id}卷-详细大纲.md`
- 기존 설정집 파일 (세계관/능력체계/주인공카드/주인공그룹/여주카드/악역설계)

기록 전략 (필수):
- 관련 단락에 대한 증분 보충만 수행하며, 파일 전체를 덮어쓰지 않습니다.
- 새 캐릭터: 해당 캐릭터 카드 또는 캐릭터 그룹 항목에 기록 (첫 등장 장, 관계, 레드라인 포함).
- 새 세력/장소/규칙: 세계관 또는 능력체계 해당 섹션에 기록.
- 새 악역 계층 정보: 악역 설계에 기록하고 소/중/대 계층 일관성 유지.

충돌 처리 (하드 규칙):
- 권별 개요의 새 정보가 총강이나 확인된 설정과 충돌하면, `BLOCKER`로 표시하고 state 업데이트를 중단.
- 충돌 판결이 완료된 후에만 설정 업데이트를 계속하고 저장 단계로 진입 허용.

## 8) Validate + save
### Validation checks (must pass all)

**1. 카타르시스 밀도 검사**
- 장당 1개 이상 소카타르시스 (강도 2-3)
- 매 5-8장마다 최소 1개 핵심 장 (강도 4-5)
- 매 권 최소 1개 클라이맥스 장 (강도 6-7)

**2. Strand 비율 검사**
Count chapters by Strand and compare with genre profile:
- Quest: 55-65% 차지해야 함
- Fire: 20-30% 차지해야 함
- Constellation: 10-20% 차지해야 함

If deviation > 15%, adjust chapter assignments.

**3. 총강 일관성 검사**
- 권 핵심 갈등이 장들에 관통되는가?
- 권말 클라이맥스가 마지막 3-5장에 체현되는가?
- 핵심 인물이 계획대로 등장하는가?

**4. 제약 트리거 빈도 검사** (if idea_bank exists)
- 반클리셰 규칙 트리거 횟수 >= 총 장수 / N (N = max(5, 총 장수/10))
- 하드 제약이 최소 50% 장에서 체현
- 주인공 결함이 최소 2회 갈등 원인
- 악역 미러가 악역 등장 장에서 체현

**5. 완전성 검사**
Every chapter must have:
- 목표 (20자 이내)
- 저항 (20자 이내)
- 대가 (20자 이내)
- 시간 앵커 (필수)
- 장내 시간 범위 (필수)
- 전장과의 시간차 (필수)
- 카운트다운 상태 (카운트다운 이벤트가 있으면 필수)
- 카타르시스 (유형 + 30자 설명)
- Strand (Quest/Fire/Constellation)
- 악역 계층 (없음/소/중/대)
- 시점/주인공
- 핵심 엔티티 (최소 1개)
- 이 장의 변화 (30자 이내)
- 장말 미해결 문제 (30자 이내)
- 훅 (유형 + 30자 설명)

**6. 타임라인 일관성 검사 (신규)**
- 타임라인표 파일 존재: `大纲/第{volume_id}卷-时间线.md`
- 모든 장의 시간 앵커가 기입됨
- 시간이 단조 증가 (역행 불가, 플래시백으로 명시 표기한 경우 제외)
- 카운트다운 추진 정확 (D-5 → D-4 → D-3, 건너뛰기 불가)
- 대폭 시간 점프 (>3일)는 과도 장 설명 또는 명시 표기 필요

**7. 설정 보완 검사**
- 이 권에 관련된 새 캐릭터/세력/규칙이 기존 설정집 파일에 기록됨
- 모든 새 항목이 이 권의 장별 개요 장으로 역추적 가능
- `BLOCKER` 수가 0; 0보다 크면 반드시 먼저 판결해야 하며, state 업데이트에 진입할 수 없음

Update state (include chapters range):
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" update-state -- \
  --volume-planned {volume_id} \
  --chapters-range "{start}-{end}"
```

Final check:
- 비트시트 파일 기록 완료: `大纲/第{volume_id}卷-节拍表.md`
- 타임라인표 파일 기록 완료: `大纲/第{volume_id}卷-时间线.md`
- 장별 개요 파일 기록 완료: `大纲/第{volume_id}卷-详细大纲.md`
- 설정집 기준선 보충 및 이 권 증분 보충 완료 (원 파일에서 확인 가능)
- 각 장에 포함: 목표/저항/대가/시간 앵커/장내 시간 범위/전장과의 시간차/카타르시스/Strand/악역 계층/시점/핵심 엔티티/이 장의 변화/장말 미해결 문제/훅
- 타임라인 단조 증가, 카운트다운 추진 정확
- 총강 갈등/클라이맥스와 일치, 제약 트리거 빈도 합리적 (idea_bank가 있을 때)

### Hard fail conditions (must stop)
- 비트시트 파일 미존재 또는 비어있음
- 비트시트 중반 반전 누락 ("필수/없음(사유)" 규칙 미준수)
- **타임라인표 파일 미존재 또는 비어있음**
- 장별 개요 파일 미존재 또는 비어있음
- 어떤 장이든 누락: 목표/저항/대가/시간 앵커/장내 시간 범위/전장과의 시간차/카타르시스/Strand/악역 계층/시점/핵심 엔티티/이 장의 변화/장말 미해결 문제/훅
- **어떤 장이든 시간 필드(시간 앵커/장내 시간 범위/전장과의 시간차) 누락**
- **시간 역행이며 플래시백으로 표기되지 않음**
- **카운트다운 산술 충돌 (예: D-5에서 바로 D-2로 점프)**
- **중대 이벤트 발생 시간이 전장과의 간격이 불충분하며 합리적 설명 없음 (예: 포스트아포칼립스 1일차에 파벌 건설)**
- 총강 핵심 갈등이나 권말 클라이맥스와 명백히 충돌
- 설정집 기준선이 미보충이거나, 이 권 증분이 기존 설정집에 기록되지 않음
- `BLOCKER` 미판결 존재
- 제약 트리거 빈도 부족 (idea_bank 활성화 시)

### Rollback / recovery
If any hard fail triggers:
1. Stop and list the failing items.
2. Re-generate only the failed batch (do not overwrite the whole file).
3. If the last batch is invalid, remove that batch and rewrite it.
4. Only update state after Final check passes.

다음 단계:
- 다음 권 기획 계속 → /webnovel-plan
- 집필 시작 → /webnovel-write
