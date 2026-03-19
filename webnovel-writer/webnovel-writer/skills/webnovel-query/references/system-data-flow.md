---
name: system-data-flow
purpose: 프로젝트 초기화와 상태 조회 시 로드, 데이터 구조 이해
---

<context>
이 파일은 프로젝트 데이터 구조 참고용입니다. Claude는 일반 파일 구성을 이미 알고 있으며, 여기서는 웹소설 워크플로우에 특화된 디렉터리 규약과 스크립트 역할만 보충합니다.
</context>

<instructions>

## 디렉터리 규약

```
프로젝트 루트/
├── 正文/           # 챕터 파일 (第0001章.md 또는 第1卷/第001章-제목.md)
├── 大纲/           # 권강/장강/장면강
├── 设定集/         # 세계관/파워 시스템/캐릭터 카드/아이템 카드
└── .webnovel/
    ├── state.json          # 간소화 상태 (< 5KB): 진도/주인공/strand_tracker/소거
    ├── index.db            # SQLite 주저장소: 엔티티/별명/관계/상태 변화/챕터/장면
    ├── workflow_state.json # 워크플로우 중단점 (/webnovel-resume용)
    ├── vectors.db          # RAG 벡터 DB
    ├── summaries/          # 챕터 요약 (chNNNN.md)
    └── archive/            # 보관 데이터 (비활성 캐릭터/이미 회수된 복선)
```

## 아키텍처 변경 설명

**핵심 변화**: state.json 팽창 문제 해결 (20장 이후 token 폭발)

| 데이터 유형 | 구버전 저장 위치 | 현재 저장 위치 |
|----------|--------------|--------------|
| entities_v3 | state.json | **index.db** (entities 테이블) |
| alias_index | state.json | **index.db** (aliases 테이블) |
| state_changes | state.json | **index.db** (state_changes 테이블) |
| structured_relationships | state.json | **index.db** (relationships 테이블) |
| progress | state.json | state.json (유지) |
| protagonist_state | state.json | state.json (유지) |
| strand_tracker | state.json | state.json (유지) |
| disambiguation_* | state.json | state.json (유지) |

## 듀얼 Agent 아키텍처

```
집필 전: Context Agent 데이터 읽기 → 컨텍스트 패키지 조립
        ├── state.json에서 간소화 데이터 읽기 (진도/설정)
        └── index.db에서 SQL로 필요에 따라 쿼리 (엔티티/관계)

집필 중: Writer가 컨텍스트 패키지를 사용하여 순수 본문 생성 (XML 태그 없음)

집필 후: Data Agent 본문 처리 → AI 엔티티 추출 → 데이터 체인에 기록
        ├── index.db에 기록 (엔티티/별명/상태 변화/관계)
        ├── state.json 업데이트 (진도/주인공 스냅샷 + chapter_meta)
        └── summaries/chNNNN.md에 기록 (챕터 요약)

Context Agent (읽기) ←→ index.db + state.json ←→ Data Agent (쓰기)
```

## 스크립트/모듈 역할 속찰

### 핵심 스크립트

| 스크립트 | 입력 | 출력 |
|------|------|------|
| `init_project.py` | 프로젝트 정보 | `.webnovel/state.json` 생성 + `index.db` 초기화 |
| `update_state.py` | 매개변수 | `state.json` 필드 원자적 업데이트 (진도/주인공/strand_tracker) |
| `backup_manager.py` | 챕터 번호 | 자동 Git 백업 |
| `status_reporter.py` | 없음 | 건강 보고서/복선 긴급도 생성 |
| `archive_manager.py` | 없음 | 비활성 데이터 보관 |
| `data_modules/migrate_state_to_sqlite.py` | 프로젝트 경로 | 구 state.json을 SQLite로 마이그레이션 |

### data_modules 모듈

| 모듈 | 역할 |
|------|------|
| `state_manager.py` | 엔티티 상태 관리 (간소화 state.json + SQLite 동기) |
| `sql_state_manager.py` | SQLite 상태 관리 (JSON 기록 대체) |
| `index_manager.py` | SQLite 인덱스 관리 (엔티티/별명/관계/상태 변화/챕터/장면) |
| `entity_linker.py` | 별명 등록과 소거 |
| `rag_adapter.py` | 벡터 임베딩과 시맨틱 검색 |
| `style_sampler.py` | 스타일 샘플 추출과 관리 |
| `api_client.py` | LLM API 호출 캡슐화 |
| `config.py` | 설정 관리 |

## 매 챕터 데이터 체인

```
1. Context Agent 창작 과제서 조립
   → state.json 읽기 (간소화 버전: 진도/설정)
   → SQL로 index.db 쿼리 (핵심 엔티티/필요시 엔티티)
   → RAG 검색 (관련 장면)

2. Step 1.5 챕터 설계
   → 오프닝/훅/쾌감 포인트 패턴 선택 (최근 3장과 회피)

3. Writer 챕터 내용 생성
   → 2A 초고 (순수 본문)
   → 2B 스타일 적응 (선택)

4. 심사 (6개 Agent 병렬)
   → 쾌감 포인트/일관성/리듬/OOC/연속성/추독력 검사
   → 심사 보고서 출력

5. 웹소설화 윤색
   → 심사 보고서 기반 문제 수정
   → 구감 규칙 강화

6. Data Agent 데이터 체인 처리
   → AI 엔티티 추출 (XML 태그 파싱 대체)
   → 엔티티 소거 (신뢰도 전략)
   → index.db에 기록 (엔티티/별명/상태 변화/관계)
   → state.json 업데이트 (진도/주인공 스냅샷 + chapter_meta)
   → summaries/chNNNN.md에 기록 (챕터 요약)
   → 벡터 임베딩 (RAG)
   → 스타일 샘플 평가

7. Git 백업 (필수)
```

> `update_state.py`는 수동/스크립트화 업데이트용으로 `progress`/`protagonist_state`/`strand_tracker` 등 필드를 업데이트합니다. 메인 흐름에서는 보통 Data Agent가 데이터 체인 처리 시 동기적으로 진도를 추진합니다.

## state.json 간소화 구조

```json
{
  "project_info": {"title": "", "genre": ""},
  "progress": {"current_chapter": N, "total_words": W, "current_volume": 1},
  "protagonist_state": {
    "name": "",
    "power": {"realm": "", "layer": 1, "bottleneck": ""},
    "location": {"current": "", "last_chapter": 0},
    "golden_finger": {"name": "", "level": 1, "skills": []}
  },
  "strand_tracker": {
    "last_quest_chapter": 0,
    "last_fire_chapter": 0,
    "last_constellation_chapter": 0,
    "current_dominant": "quest",
    "chapters_since_switch": 0,
    "history": []
  },
  "relationships": {},
  "plot_threads": {"active_threads": [], "foreshadowing": []},
  "world_settings": {},
  "disambiguation_warnings": [],
  "disambiguation_pending": [],
  "review_checkpoints": [],
  "chapter_meta": {},
  "_migrated_to_sqlite": true
}
```

> **현재 구조 설명**: entities_v3, alias_index, state_changes, structured_relationships는 index.db로 마이그레이션되었으며, 더 이상 state.json에 저장되지 않습니다.

## index.db 테이블 구조

```sql
-- 엔티티 테이블
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,           -- 캐릭터/장소/아이템/세력/초식
    canonical_name TEXT NOT NULL,
    tier TEXT DEFAULT '장식',     -- 핵심/중요/부차/장식
    desc TEXT,
    current_json TEXT,            -- JSON: {realm, location, ...}
    first_appearance INTEGER,
    last_appearance INTEGER,
    is_protagonist INTEGER DEFAULT 0,
    is_archived INTEGER DEFAULT 0
);

-- 별명 테이블 (일대다)
CREATE TABLE aliases (
    alias TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    PRIMARY KEY (alias, entity_id, entity_type)
);

-- 상태 변화 테이블
CREATE TABLE state_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL,
    field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT,
    chapter INTEGER NOT NULL
);

-- 관계 테이블
CREATE TABLE relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_entity TEXT NOT NULL,
    to_entity TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    chapter INTEGER NOT NULL,
    UNIQUE(from_entity, to_entity, type)
);

-- 기존 테이블 (유지)
CREATE TABLE chapters (...);
CREATE TABLE scenes (...);
CREATE TABLE appearances (...);
```

## Data Agent AI 추출 흐름

현재 메인 흐름에서는 더 이상 XML 태그를 요구하지 않으며, Data Agent가 지능적으로 추출합니다:

1. **엔티티 식별**: 본문 의미에서 캐릭터/장소/아이템/세력 식별
2. **엔티티 매칭**: 기존 엔티티와 우선 매칭 (alias_index를 통해)
3. **소거 처리**:
   - 신뢰도 > 0.8: 자동 채택
   - 신뢰도 0.5-0.8: 채택하되 warning 기록
   - 신뢰도 < 0.5: 수동 확인 대기 표시
4. **상태 변화 식별**: 경지 돌파/위치 이동/관계 변화
5. **저장소 기록**: index.db에 직접 기록 (엔티티/별명/관계/상태 변화)

## 복선 필드 규범

| 필드 | 규범값 | 호환값 (역사) |
|------|--------|---------------|
| status | `미회수` / `회수완료` | 대기회수/진행중/active/pending |

**권장 필드**: content, status, planted_chapter, target_chapter, tier

## alias_index 형식 (일대다)

```json
{
  "임천": [{"type": "캐릭터", "id": "lintian"}],
  "천운종": [
    {"type": "장소", "id": "loc_tianyunzong"},
    {"type": "세력", "id": "faction_tianyunzong"}
  ]
}
```

같은 별명이 여러 엔티티에 매핑될 수 있으며, 소거 시 type 또는 컨텍스트에 따라 판단합니다.

</instructions>

<examples>

<example>
<input>현재 진도 조회</input>
<output>
```bash
cat "$PROJECT_ROOT/.webnovel/state.json" | jq '.progress'
# 출력: { "current_chapter": 45, "total_words": 135000 }
```
</output>
</example>

<example>
<input>엔티티 조회 (SQL)</input>
<output>
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index get-entity --id "xiaoyan"
# 출력: {"id": "xiaoyan", "type": "캐릭터", "canonical_name": "소염", ...}

python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index get-core-entities
# 출력: 모든 핵심 엔티티 (주인공 + tier=핵심/중요)
```
</output>
</example>

<example>
<input>별명으로 엔티티 조회 (일대다)</input>
<output>
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index get-by-alias --alias "천운종"
# 출력: [{"id": "loc_tianyunzong", "type": "장소"}, {"id": "faction_tianyunzong", "type": "세력"}]
```
</output>
</example>

<example>
<input>상태 변화 조회</input>
<output>
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index get-state-changes --entity "xiaoyan" --limit 10
# 출력: [{entity_id, field, old_value, new_value, reason, chapter}, ...]
```
</output>
</example>

<example>
<input>관계 조회</input>
<output>
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index get-relationships --entity "xiaoyan"
# 출력: [{from_entity, to_entity, type, description, chapter}, ...]
```
</output>
</example>

<example>
<input>복선 긴급도 확인</input>
<output>
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" status -- --focus urgency
```
</output>
</example>

<example>
<input>엔티티 출장 기록 조회</input>
<output>
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index entity-appearances --entity "lintian"
```
</output>
</example>

<example>
<input>구 state.json을 SQLite로 마이그레이션</input>
<output>
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" migrate -- --backup
# 자동으로 state.json 백업, 데이터를 index.db로 마이그레이션, state.json 간소화
```
</output>
</example>

</examples>

<errors>
❌ 복선 상태를 "대기회수"로 기입 → ✅ 규범값 "미회수" 사용
❌ 수동 업데이트 시 planted_chapter 추가 누락 → ✅ 스크립트가 자동 보완
❌ 보관 경로 혼동 → ✅ `.webnovel/archive/*.json`으로 고정
❌ alias_index가 단일 객체를 기대 → ✅ 현재 구조는 배열 형식 (일대다)
❌ XML 태그 추출을 기대 → ✅ 현재 메인 흐름은 Data Agent AI 자동 추출
❌ 구버전 data_modules.state_manager schema 사용 → ✅ entities_v3 구조로 통일
❌ 여전히 state.json에서 entities_v3 읽기 → ✅ SQL로 index.db 쿼리로 변경
❌ 여전히 state.json에 대량 데이터 기록 → ✅ SQLite 증분 기록으로 변경
❌ state.json이 계속 팽창하게 둠 → ✅ 마이그레이션 스크립트 실행: `python "${SCRIPTS_DIR}/webnovel.py" migrate`
</errors>
