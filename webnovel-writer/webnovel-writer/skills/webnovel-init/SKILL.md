---
name: webnovel-init
description: 웹소설 프로젝트를 심층 초기화합니다. 단계적 상호작용을 통해 완전한 창작 정보를 수집하고, 기획 및 집필에 바로 진입할 수 있는 프로젝트 골격과 제약 파일을 생성합니다.
allowed-tools: Read Write Edit Grep Bash Task AskUserQuestion WebSearch WebFetch
---

# Project Initialization (Deep Mode)

## 목표

- 구조화된 상호작용을 통해 충분한 정보를 수집하여 "먼저 생성하고 나중에 재작업"하는 상황을 방지합니다.
- 실행 가능한 프로젝트 골격을 산출합니다: `.webnovel/state.json`, `settings/*`, `outline/master.md`, `.webnovel/idea_bank.json`.
- 이후 `/webnovel-plan` 과 `/webnovel-write` 가 바로 실행될 수 있도록 보장합니다.

## 실행 원칙

1. 먼저 수집하고, 나중에 생성합니다. 충분성 게이트를 통과하지 못하면 `init_project.py`를 실행하지 않습니다.
2. 단계별로 질문하며, 매 라운드마다 "현재 누락되어 다음 단계를 차단하는" 정보만 물어봅니다.
3. `Read/Grep/Bash/Task/AskUserQuestion/WebSearch/WebFetch` 호출을 통해 수집을 보조할 수 있습니다.
4. 사용자가 이미 명확히 한 정보는 다시 물어보지 않습니다. 충돌하는 정보는 사용자에게 우선 결정을 요청합니다.
5. Deep 모드는 완전성을 우선하여 조금 느리더라도 핵심 필드 누락을 금지합니다.

## 참조 로딩 등급 (strict, lazy)

단계적 로딩을 채택하여 모든 자료를 한 번에 투입하는 것을 방지합니다:

- L0: 태스크 확인 전에는 참조를 사전 로딩하지 않습니다.
- L1: 각 단계에서 해당 단계의 "필독" 파일만 로딩합니다.
- L2: 장르, 골든핑거, 창작 제약 조건이 충족될 때만 확장 참조를 로딩합니다.
- L3: 시장 트렌드류, 시의성 있는 자료는 사용자가 명시적으로 요청할 때만 로딩합니다.

경로 규약:
- `references/...` 현재 skill 디렉토리 기준 (`${CLAUDE_PLUGIN_ROOT}/skills/webnovel-init/references/...`).
- `templates/...` 플러그인 루트 디렉토리 기준 (`${CLAUDE_PLUGIN_ROOT}/templates/...`).

기본 로딩 목록:
- L1 (시작 전): `references/genre-tropes.md`
- L2 (필요 시):
  - 장르 템플릿: `templates/genres/{genre}.md`
  - 골든핑거: `../../templates/golden-finger-templates.md`
  - 세계관: `references/worldbuilding/faction-systems.md`
  - 창작 제약: 아래 "파일별 참조 목록"에 따라 트리거 시 로딩
- L3 (명시적 요청):
  - `references/creativity/market-trends-2026.md`

## References (파일별 참조 목록)

### 루트 디렉토리

- `references/genre-tropes.md`
  - 용도: Step 1 장르 정규화, 장르 특성 안내.
  - 트리거: 모든 프로젝트 필독.
- `references/system-data-flow.md`
  - 용도: 초기화 산출물과 후속 `/plan`, `/write`의 데이터 흐름 일관성 검사.
  - 트리거: Step 0 사전 검사 필독.

### worldbuilding

- `references/worldbuilding/character-design.md`
  - 용도: Step 2 캐릭터 차원 보충 질문 (목표, 결함, 동기, 반전).
  - 트리거: 사용자 인물 정보가 추상적이거나 평면적일 때 로딩.
- `references/worldbuilding/faction-systems.md`
  - 용도: Step 4 세력 구도와 조직 계층 설계.
  - 트리거: Step 4 기본 로딩.
- `references/worldbuilding/power-systems.md`
  - 용도: Step 4 능력 체계 유형과 경계 정의.
  - 트리거: 수선/현판타지/고무/이능 관련 시 로딩.
- `references/worldbuilding/setting-consistency.md`
  - 용도: Step 6 일관성 복기 전 설정 충돌 검사.
  - 트리거: Step 6 기본 로딩.
- `references/worldbuilding/world-rules.md`
  - 용도: Step 4 세계 규칙과 금기 사항 수렴.
  - 트리거: Step 4 기본 로딩.

### creativity

- `references/creativity/creativity-constraints.md`
  - 용도: Step 5 창작 제약 패키지 메인 스키마.
  - 트리거: Step 5 필독.
- `references/creativity/category-constraint-packs.md`
  - 용도: Step 5 플랫폼/장르별 제약 패키지 템플릿 선택.
  - 트리거: Step 5 필독.
- `references/creativity/creative-combination.md`
  - 용도: 복합 장르 (A+B) 융합 규칙.
  - 트리거: 사용자가 복합 장르를 선택할 때 로딩.
- `references/creativity/inspiration-collection.md`
  - 용도: 사용자가 막혔을 때 셀링포인트/훅 후보 제공.
  - 트리거: Step 1 또는 Step 5에서 막힐 때 로딩.
- `references/creativity/selling-points.md`
  - 용도: Step 5 셀링포인트 생성과 선별.
  - 트리거: Step 5 필독.
- `references/creativity/market-positioning.md`
  - 용도: 타깃 독자/플랫폼 포지셔닝과 상업화 의미 통일.
  - 트리거: Step 1에서 사용자가 플랫폼이나 상업 목표를 언급할 때 로딩.
- `references/creativity/market-trends-2026.md`
  - 용도: 시간에 민감한 시장 트렌드 참조.
  - 트리거: 사용자가 명시적으로 "현재 트렌드 참조"를 요청할 때만 로딩.
- `references/creativity/anti-trope-xianxia.md`
  - 용도: 반클리셰 라이브러리 (수선/현판타지/고무/서판타지).
  - 트리거: 장르가 해당 매핑에 맞을 때 로딩.
- `references/creativity/anti-trope-urban.md`
  - 용도: 반클리셰 라이브러리 (도시/역사).
  - 트리거: 장르가 해당 매핑에 맞을 때 로딩.
- `references/creativity/anti-trope-game.md`
  - 용도: 반클리셰 라이브러리 (게임/SF/포스트아포칼립스).
  - 트리거: 장르가 해당 매핑에 맞을 때 로딩.
- `references/creativity/anti-trope-rules-mystery.md`
  - 용도: 반클리셰 라이브러리 (규칙 괴담/서스펜스/심령/크툴루).
  - 트리거: 장르가 해당 매핑에 맞을 때 로딩.

## 도구 전략 (필요 시)

- `Read/Grep`: 프로젝트 컨텍스트와 참조 파일 읽기 (`README.md`, `CLAUDE.md`, `templates/genres/*`, `references/*`).
- `Bash`: `init_project.py` 실행, 파일 존재 여부 확인, 최소 검증 명령.
- `Task`: 병렬 하위 작업 분할 (장르 매핑, 제약 패키지 후보 생성, 파일 검증 등).
- `AskUserQuestion`: 핵심 분기 결정, 후보 방안 선택, 최종 확인용.
- `WebSearch`: 최신 시장 트렌드, 플랫폼 동향, 장르 데이터 검색 (도메인 필터 가능).
- `WebFetch`: 확인된 소스 페이지 내용을 크롤링하여 사실 검증.
- 외부 검색 트리거 조건:
  - 사용자가 명시적으로 시장 트렌드나 플랫폼 동향 참조를 요청;
  - 창작 제약에 "시간 민감 근거"가 필요;
  - 장르 정보에 명확한 불확실성이 있음.

## 상호작용 흐름 (Deep)

### Step 0: 사전 검사 및 컨텍스트 로딩

환경 설정 (bash 명령 실행 전):
```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

if [ -z "${CLAUDE_PLUGIN_ROOT}" ] || [ ! -d "${CLAUDE_PLUGIN_ROOT}/scripts" ]; then
  echo "ERROR: CLAUDE_PLUGIN_ROOT가 설정되지 않았거나 디렉토리가 없습니다: ${CLAUDE_PLUGIN_ROOT}/scripts" >&2
  exit 1
fi
export SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT}/scripts"
```

필수 수행:
- 현재 디렉토리가 쓰기 가능한지 확인.
- 스크립트 디렉토리를 해석하고 진입점 존재를 확인 (플러그인 디렉토리만 지원):
  - 고정 경로: `${CLAUDE_PLUGIN_ROOT}/scripts`
  - 진입 스크립트: `${SCRIPTS_DIR}/webnovel.py`
- 해석 결과를 먼저 출력하여 잘못된 디렉토리에 쓰는 것을 방지하는 것을 권장:
  - `python "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" where`
- 최소 참조 로딩:
  - `references/system-data-flow.md` (init 산출물과 plan/write 입력 체인 검증용)
  - `references/genre-tropes.md`
  - `templates/genres/` (사용자가 장르를 선정한 후 필요 시 읽기)

출력:
- Deep 수집 진입 전 "파악된 정보 목록"과 "수집 대기 목록".

### Step 1: 스토리 핵심 및 상업 포지셔닝

수집 항목 (필수):
- 책 제목 (임시 제목 가능)
- 장르 (A+B 복합 장르 지원)
- 목표 규모 (총 자수 또는 총 장수)
- 한 줄 스토리
- 핵심 갈등
- 타깃 독자/플랫폼

장르 집합 (정규화 및 매핑용):
- 현판타지/수선류: 수선 | 시스템류 | 고무 | 서판타지 | 무한류 | 포스트아포칼립스 | SF
- 도시/현대류: 도시이능 | 도시일상 | 도시기발 | 현실소재 | 다크소재 | e스포츠 | 방송문
- 로맨스류: 고대로맨스 | 궁중쟁투 | 청춘달콤 | 재벌총재 | 직장연애 | 민국로맨스 | 환상로맨스 | 현대기발 | 여성향서스펜스 | 막장로맨스 | 대역문 | 다자다복 | 경작 | 시대물
- 특수소재: 규칙괴담 | 서스펜스기발 | 서스펜스심령 | 역사고대 | 역사기발 | 게임스포츠 | 항일첩보 | 지후단편 | 크툴루

상호작용 방식:
- 사용자가 자유롭게 설명하도록 한 뒤, 구조화하여 이차 확인.
- 사용자가 막힐 경우, 2-4개 후보 방향을 제공하여 선택하도록 함.

### Step 2: 캐릭터 골격 및 관계 갈등

수집 항목 (필수):
- 주인공 이름
- 주인공 욕망 (무엇을 원하는가)
- 주인공 결함 (대가를 치르게 할 결함)
- 주인공 구조 (단일 주인공/다중 주인공)
- 감정선 구성 (없음/단일 여주/다수 여주)
- 악역 계층 (소/중/대) 및 미러 대립 한 줄 요약

수집 항목 (선택):
- 주인공 원형 태그 (성장형/복수형/천재류 등)
- 다중 주인공 분담

### Step 3: 골든핑거 및 실현 메커니즘

수집 항목 (필수):
- 골든핑거 유형 ("골든핑거 없음"도 가능)
- 이름/시스템명 (없으면 비워둠)
- 스타일 (하드코어/유머/다크/절제 등)
- 가시성 (누가 알고 있는가)
- 불가역적 대가 (반드시 대가가 있거나 "없음+이유"를 명시)
- 성장 리듬 (느린/중간/빠른)

수집 항목 (조건부 필수):
- 시스템류인 경우: 시스템 성격, 업그레이드 리듬
- 환생인 경우: 환생 시점, 기억 완전성
- 계승/기령인 경우: 보조 범위와 출전 제한

### Step 4: 세계관 및 능력 규칙

수집 항목 (필수):
- 세계 규모 (단일 도시/다중 지역/대륙/다중 세계)
- 능력 체계 유형
- 세력 구도
- 사회 계층 및 자원 분배

수집 항목 (장르 관련):
- 화폐 체계 및 교환 규칙
- 종문/조직 계층
- 경계 체인 및 소경계

### Step 5: 창작 제약 패키지 (차별화 핵심)

프로세스:
1. 장르 매핑에 기반하여 반클리셰 라이브러리 로딩 (최대 2개 주요 관련 라이브러리).
2. 2-3세트 창작 패키지 생성, 각 세트 포함:
   - 한 줄 셀링포인트
   - 반클리셰 규칙 1개
   - 하드 제약 2-3개
   - 주인공 결함 구동 한 줄 요약
   - 악역 미러 한 줄 요약
   - 오프닝 훅
3. 3개 질문 선별:
   - 왜 이 장르는 반드시 이렇게 써야 하는가?
   - 일반적인 주인공으로 바꾸면 무너지는가?
   - 셀링포인트를 한 줄로 명확히 설명할 수 있고 템플릿과 겹치지 않는가?
4. 5차원 평가 점수 표시 (`references/creativity/creativity-constraints.md`의 `8.1 5차원 평가` 참조), 사용자 의사 결정 보조.
5. 사용자가 최종 방안을 선택하거나, 거부하며 사유를 제시.

비고:
- 사용자가 "현재 시장에 맞추라"고 요구하면, 외부 검색을 트리거하고 타임스탬프를 표기할 수 있음.

### Step 6: 일관성 복기 및 최종 확인

"초기화 요약 초안"을 반드시 출력하고 사용자 확인을 받아야 합니다:
- 스토리 핵심 (장르/한 줄 스토리/핵심 갈등)
- 주인공 핵심 (욕망/결함)
- 골든핑거 핵심 (능력과 대가)
- 세계 핵심 (규모/능력/세력)
- 창작 제약 핵심 (반클리셰 + 하드 제약)

확인 규칙:
- 사용자가 명시적으로 확인하지 않으면 생성을 실행하지 않습니다.
- 사용자가 일부만 수정하는 경우, 해당 Step으로 돌아가 최소 재수집.

## 내부 데이터 모델 (초기화 수집 객체)

```json
{
  "project": {
    "title": "",
    "genre": "",
    "target_words": 0,
    "target_chapters": 0,
    "one_liner": "",
    "core_conflict": "",
    "target_reader": "",
    "platform": ""
  },
  "protagonist": {
    "name": "",
    "desire": "",
    "flaw": "",
    "archetype": "",
    "structure": "단일 주인공"
  },
  "relationship": {
    "heroine_config": "",
    "heroine_names": [],
    "heroine_role": "",
    "co_protagonists": [],
    "co_protagonist_roles": [],
    "antagonist_tiers": {},
    "antagonist_level": "",
    "antagonist_mirror": ""
  },
  "golden_finger": {
    "type": "",
    "name": "",
    "style": "",
    "visibility": "",
    "irreversible_cost": "",
    "growth_rhythm": ""
  },
  "world": {
    "scale": "",
    "factions": "",
    "power_system_type": "",
    "social_class": "",
    "resource_distribution": "",
    "currency_system": "",
    "currency_exchange": "",
    "sect_hierarchy": "",
    "cultivation_chain": "",
    "cultivation_subtiers": ""
  },
  "constraints": {
    "anti_trope": "",
    "hard_constraints": [],
    "core_selling_points": [],
    "opening_hook": ""
  }
}
```

## 충분성 게이트 (반드시 통과)

다음 조건을 충족하기 전에는 `init_project.py` 실행을 금지합니다:

1. 책 제목, 장르(복합 가능)가 확정됨.
2. 목표 규모 계산 가능 (자수 또는 장수 중 최소 하나).
3. 주인공 이름 + 욕망 + 결함 완비.
4. 세계 규모 + 능력 체계 유형 완비.
5. 골든핑거 유형 확정 ("골든핑거 없음" 허용).
6. 창작 제약 확정:
   - 반클리셰 규칙 1개
   - 하드 제약 최소 2개
   - 또는 사용자가 명시적으로 거부하고 사유 기록.

## 프로젝트 디렉토리 보안 규칙 (필수)

- `project_root`는 책 제목을 안전하게 변환하여 생성 (불법 문자 제거, 공백을 `-`로 변환).
- 안전화 결과가 비어있거나 `.`으로 시작하면, 자동으로 `proj-` 접두사 추가.
- 플러그인 디렉토리 하위에 프로젝트 파일 생성 금지 (`${CLAUDE_PLUGIN_ROOT}`).

## 실행 생성

### 1) 초기화 스크립트 실행

```bash
python "${SCRIPTS_DIR}/webnovel.py" init \
  "{project_root}" \
  "{title}" \
  "{genre}" \
  --protagonist-name "{protagonist_name}" \
  --target-words {target_words} \
  --target-chapters {target_chapters} \
  --golden-finger-name "{gf_name}" \
  --golden-finger-type "{gf_type}" \
  --golden-finger-style "{gf_style}" \
  --core-selling-points "{core_points}" \
  --protagonist-structure "{protagonist_structure}" \
  --heroine-config "{heroine_config}" \
  --heroine-names "{heroine_names}" \
  --heroine-role "{heroine_role}" \
  --co-protagonists "{co_protagonists}" \
  --co-protagonist-roles "{co_protagonist_roles}" \
  --antagonist-tiers "{antagonist_tiers}" \
  --world-scale "{world_scale}" \
  --factions "{factions}" \
  --power-system-type "{power_system_type}" \
  --social-class "{social_class}" \
  --resource-distribution "{resource_distribution}" \
  --gf-visibility "{gf_visibility}" \
  --gf-irreversible-cost "{gf_irreversible_cost}" \
  --currency-system "{currency_system}" \
  --currency-exchange "{currency_exchange}" \
  --sect-hierarchy "{sect_hierarchy}" \
  --cultivation-chain "{cultivation_chain}" \
  --cultivation-subtiers "{cultivation_subtiers}" \
  --protagonist-desire "{protagonist_desire}" \
  --protagonist-flaw "{protagonist_flaw}" \
  --protagonist-archetype "{protagonist_archetype}" \
  --antagonist-level "{antagonist_level}" \
  --target-reader "{target_reader}" \
  --platform "{platform}"
```

### 2) `idea_bank.json` 작성

`.webnovel/idea_bank.json`에 작성:

```json
{
  "selected_idea": {
    "title": "",
    "one_liner": "",
    "anti_trope": "",
    "hard_constraints": []
  },
  "constraints_inherited": {
    "anti_trope": "",
    "hard_constraints": [],
    "protagonist_flaw": "",
    "antagonist_mirror": "",
    "opening_hook": ""
  }
}
```

### 3) 총강 패치

반드시 보충 완료:
- 한 줄 스토리
- 핵심 메인 라인 / 핵심 히든 라인
- 창작 제약 (반클리셰, 하드 제약, 주인공 결함, 악역 미러)
- 악역 계층
- 핵심 카타르시스 이정표 (2-3개)

## 검증 및 인도

실행 검사:

```bash
test -f "{project_root}/.webnovel/state.json"
find "{project_root}/settings" -maxdepth 1 -type f -name "*.md"
test -f "{project_root}/outline/master.md"
test -f "{project_root}/.webnovel/idea_bank.json"
```

성공 기준:
- `state.json` 존재하고 핵심 필드가 비어있지 않음 (title/genre/target_words/target_chapters).
- 설정집 핵심 파일 존재: `worldview.md`, `power-system.md`, `protagonist.md`, `golden-finger.md`.
- `master.md`에 핵심 메인 라인과 제약 필드가 기입됨.
- `idea_bank.json`이 작성되어 있고 최종 선정 방안과 일치.

## 실패 처리 (최소 롤백)

트리거 조건:
- 핵심 파일 누락;
- 총강 핵심 필드 누락;
- 제약이 활성화되었지만 `idea_bank.json`이 누락되었거나 내용 불일치.

복구 흐름:
1. 누락된 필드만 보충하며, 전량 재질문하지 않습니다.
2. 최소 단계만 재실행:
   - 파일 누락 -> `init_project.py` 재실행;
   - 총강 필드 누락 -> 총강만 패치;
   - idea_bank 불일치 -> 해당 파일만 재작성.
3. 재검증하여 모두 통과 후 종료.
