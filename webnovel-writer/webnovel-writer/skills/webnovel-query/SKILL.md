---
name: webnovel-query
description: Queries project settings for characters, powers, factions, items, and foreshadowing. Supports urgency analysis and golden finger status. Activates when user asks about story elements or /webnovel-query.
allowed-tools: Read Grep Bash AskUserQuestion
---

# Information Query Skill

## Project Root Guard (반드시 먼저 확인)

- Claude Code의 "작업 영역 루트 디렉토리"가 반드시 "책 프로젝트 루트 디렉토리"와 같지는 않습니다. 일반적인 구조: 작업 영역이 `D:\wk\xiaoshuo`이고, 책 프로젝트가 `D:\wk\xiaoshuo\凡人资本论`인 경우.
- 반드시 실제 책 프로젝트 루트(반드시 `.webnovel/state.json` 포함)를 먼저 해석한 후, 이후 모든 읽기/쓰기 경로를 해당 디렉토리 기준으로 합니다.
- 플러그인 디렉토리 `${CLAUDE_PLUGIN_ROOT}/` 하위에서 프로젝트 파일을 읽거나 쓰는 것을 **금지**합니다.

환경 설정 (bash 명령 실행 전):
```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

if [ -z "${CLAUDE_PLUGIN_ROOT}" ] || [ ! -d "${CLAUDE_PLUGIN_ROOT}/skills/webnovel-query" ]; then
  echo "ERROR: CLAUDE_PLUGIN_ROOT가 설정되지 않았거나 디렉토리가 없습니다: ${CLAUDE_PLUGIN_ROOT}/skills/webnovel-query" >&2
  exit 1
fi
export SKILL_ROOT="${CLAUDE_PLUGIN_ROOT}/skills/webnovel-query"

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
정보 조회 진행:
- [ ] Step 1: 조회 유형 식별
- [ ] Step 2: 대응 참조 파일 로딩
- [ ] Step 3: 프로젝트 데이터 로딩 (state.json)
- [ ] Step 4: 컨텍스트 충분 여부 확인
- [ ] Step 5: 조회 실행
- [ ] Step 6: 출력 포맷 정리
```

---

## Reference Loading Levels (strict, lazy)

- L0: 먼저 조회 유형을 식별하고, 모든 참조를 사전 로딩하지 않습니다.
- L1: 모든 조회에서 기본 데이터 흐름 규범만 로딩합니다.
- L2: 조회 유형에 따라 대응하는 전문 참조만 로딩합니다.

### L1 (minimum)
- [system-data-flow.md](references/system-data-flow.md)

### L2 (conditional by query type)
- 복선 조회: [foreshadowing.md](references/advanced/foreshadowing.md)
- 리듬 조회: [strand-weave-pattern.md](../../references/shared/strand-weave-pattern.md)
- 태그 형식 조회: [tag-specification.md](references/tag-specification.md)

Do not load two or more L2 files unless the user request clearly spans multiple query types.

## Step 1: 조회 유형 식별

| 키워드 | 조회 유형 | 로딩 필요 |
|--------|---------|--------|
| 캐릭터/주인공/조연 | 표준 조회 | system-data-flow.md |
| 경계/축기/금단 | 표준 조회 | system-data-flow.md |
| 복선/긴급 복선 | 복선 분석 | foreshadowing.md |
| 골든핑거/시스템 | 골든핑거 상태 | system-data-flow.md |
| 리듬/Strand | 리듬 분석 | strand-weave-pattern.md |
| 태그/엔티티 형식 | 형식 조회 | tag-specification.md |

## Step 2: 대응 참조 파일 로딩

**모든 조회에서 반드시 실행**:
```bash
cat "${SKILL_ROOT}/references/system-data-flow.md"
```

**복선 조회 시 추가 실행**:
```bash
cat "${SKILL_ROOT}/references/advanced/foreshadowing.md"
```

**리듬 조회 시 추가 실행**:
```bash
cat "${SKILL_ROOT}/../../references/shared/strand-weave-pattern.md"
```

**태그 형식 조회 시 추가 실행**:
```bash
cat "${SKILL_ROOT}/references/tag-specification.md"
```

## Step 3: 프로젝트 데이터 로딩

```bash
cat "$PROJECT_ROOT/.webnovel/state.json"
```

## Step 4: 컨텍스트 충분 여부 확인

**체크리스트**:
- [ ] 조회 유형 식별 완료
- [ ] 대응 참조 파일 로딩 완료
- [ ] state.json 로딩 완료
- [ ] 답변을 어디서 찾아야 하는지 파악

**누락이 있으면 → 해당 Step으로 복귀**

## Step 5: 조회 실행

### 표준 조회

| 키워드 | 검색 대상 |
|--------|---------|
| 캐릭터/주인공/조연 | 主角卡.md, 角色库/ |
| 경계/실력 | 力量体系.md |
| 종문/세력 | 世界观.md |
| 아이템/보물 | 物品库/ |
| 장소/비경 | 世界观.md |

### 복선 긴급도 분석

**3계층 분류** (foreshadowing.md 출처):
- **핵심 복선**: 메인 라인 줄거리 - 가중치 3.0x
- **서브 복선**: 조연/서브 라인 - 가중치 2.0x
- **장식 복선**: 분위기/디테일 - 가중치 1.0x

**긴급도 공식**:
```
긴급도 = (경과 장수 / 목표 장수) x 계층 가중치
```

**상태 판정**:
- 🔴 Critical: 목표 초과 OR 핵심 >20장
- 🟡 Warning: >80% 목표 OR 서브 >30장
- 🟢 Normal: 계획 범위 내

**빠른 분석**:
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" status -- --focus urgency
```

### 골든핑거 상태

출력 포함:
- 기본 정보 (이름/유형/활성화 장)
- 현재 등급과 진행도
- 해금된 스킬 및 쿨다운
- 미해금 스킬 미리보기
- 업그레이드 조건
- 발전 제안

### Strand 리듬 분석

**빠른 분석**:
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" status -- --focus strand
```

**경고 확인**:
- Quest >5 연속 장
- Fire >10장 미등장
- Constellation >15장 미등장

## Step 6: 출력 포맷 정리

```markdown
# 조회 결과: {키워드}

## 📊 개요
- **매칭 유형**: {type}
- **데이터 소스**: state.json + 설정집 + 개요
- **매칭 수량**: X건

## 🔍 상세 정보

### 1. Runtime State (state.json)
{구조화된 데이터}
**Source**: `.webnovel/state.json` (lines XX-XX)

### 2. 설정집 매칭 결과
{매칭 내용, 파일 경로와 행 번호 포함}

## ⚠️ 데이터 일관성 검사
{state.json과 정적 파일 간의 차이}
```
