# 엔티티 관리 규범 (Entity Management Specification)

> **적용 범위**: 모든 엔티티 유형(캐릭터/장소/아이템/세력/기술)
> **핵심 목표**: AI 기반 엔티티 추출, 별칭 관리, 버전 추적

---

## 현재 규범 변경 사항

1. **SQLite 저장**: 엔티티, 별칭, 상태 변화, 관계를 `index.db`로 마이그레이션
2. **state.json 간소화**: 진행 상태, 주인공 상태, 리듬 추적만 보유 (< 5KB)
3. **AI 추출**: Data Agent가 순수 본문에서 의미 기반 엔티티 추출
4. **신뢰도 기반 소거**: >0.8 자동 채택, 0.5-0.8 경고, <0.5 수동 확인
5. **듀얼 Agent 아키텍처**: Context Agent (읽기) + Data Agent (쓰기)

> **참고**: XML 태그는 수동 주석 시나리오에서 여전히 사용 가능하지만, 주요 프로세스에서는 더 이상 요구하지 않습니다.

---

## 1. 저장 아키텍처

### 1.1 데이터 분포

| 데이터 유형 | 저장 위치 | 설명 |
|---------|---------|------|
| 엔티티 (entities) | index.db | SQLite entities 테이블 |
| 별칭 (aliases) | index.db | SQLite aliases 테이블 (일대다) |
| 상태 변화 | index.db | SQLite state_changes 테이블 |
| 관계 | index.db | SQLite relationships 테이블 |
| 챕터 색인 | index.db | SQLite chapters 테이블 |
| 장면 색인 | index.db | SQLite scenes 테이블 |
| 진행/설정 | state.json | 간소화된 JSON (< 5KB) |
| 주인공 상태 | state.json | protagonist_state 스냅샷 |
| 리듬 추적 | state.json | strand_tracker |

### 1.2 index.db Schema

```sql
-- 엔티티 테이블
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,  -- 캐릭터/장소/아이템/세력/기술
    canonical_name TEXT NOT NULL,
    tier TEXT DEFAULT '장식',  -- 핵심/중요/부차/장식
    desc TEXT,
    current_json TEXT,  -- JSON 형식의 현재 상태
    first_appearance INTEGER,
    last_appearance INTEGER,
    is_protagonist INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

-- 별칭 테이블 (일대다)
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
    chapter INTEGER,
    created_at TEXT
);

-- 관계 테이블
CREATE TABLE relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_entity TEXT NOT NULL,
    to_entity TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    chapter INTEGER,
    created_at TEXT,
    UNIQUE(from_entity, to_entity, type)
);
```

### 1.3 각 엔티티 유형 특성

| 엔티티 유형 | 별칭 복잡도 | 속성 변화 | 계층 관계 |
|---------|-----------|---------|---------|
| 캐릭터    | 높음(다양한 호칭)| 높음(경지/위치/관계)| 없음 |
| 장소    | 중간(약칭/전체명)| 낮음(상태 변화)| 있음(도>시>구)|
| 아이템    | 낮음(별칭이 적음)| 중간(업그레이드/이전)| 없음 |
| 세력    | 중간(약칭/별칭)| 중간(등급/영지)| 있음(본부>지부)|
| 기술    | 낮음(별칭이 드묾)| 중간(업그레이드)| 없음 |

---

## 2. 처리 프로세스

### 2.1 Data Agent 자동 추출

```
챕터 본문
    ↓
Data Agent (AI 의미 분석)
    ↓
┌─────────────────────────────────────────────────────────┐
│ 1. 등장 엔티티 식별                                          │
│    - 기존 엔티티 매칭(aliases 테이블 통해)                      │
│    - 새 엔티티 식별, suggested_id 생성                       │
│                                                          │
│ 2. 신뢰도 평가                                            │
│    ├─ > 0.8: 자동 채택                                   │
│    ├─ 0.5-0.8: 채택하되 경고                               │
│    └─ < 0.5: 수동 확인 대기 표시                             │
│                                                          │
│ 3. index.db에 기록                                        │
│    - entities 테이블: 새 엔티티/등장 챕터 업데이트                    │
│    - aliases 테이블: 새 별칭 등록                             │
│    - state_changes 테이블: 속성 변화 기록                     │
│    - relationships 테이블: 새 관계 기록                       │
│                                                          │
│ 4. state.json 업데이트 (간소화)                               │
│    - protagonist_state: 주인공 상태 스냅샷                    │
│    - strand_tracker: 리듬 추적                           │
│    - disambiguation_warnings/pending: 소거 기록          │
└─────────────────────────────────────────────────────────┘
    ↓
index.db 업데이트 완료
```

### 2.2 쿼리 인터페이스

```bash
# 엔티티 쿼리
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index get-entity --id "xiaoyan"

# 핵심 엔티티 쿼리
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index get-core-entities

# 별칭으로 검색
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index get-by-alias --alias "萧炎"

# 상태 변화 이력 쿼리
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index get-state-changes --entity "xiaoyan"

# 관계 쿼리
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index get-relationships --entity "xiaoyan"
```

---

## 3. 태그 체계 (선택사항)

> 현재 주요 프로세스는 Data Agent 자동 추출을 사용합니다. 아래 태그는 **수동 주석 시나리오**에서만 사용됩니다.

### 3.1 새 엔티티 생성 (`<entity>`)

```xml
<entity type="캐릭터" id="lintian" name="린톈" desc="주인공, 탐식 골든핑거 각성" tier="핵심">
  <alias>폐물</alias>
  <alias>그 소년</alias>
</entity>

<entity type="장소" id="tianyunzong" name="천운종" desc="동역 3대 종문 중 하나" tier="핵심">
  <alias>종문</alias>
</entity>
```

### 3.2 별칭 추가 (`<entity-alias>`)

```xml
<entity-alias id="lintian" alias="린종주" context="천운종주가 된 후"/>
<entity-alias ref="린톈" alias="불멸전신" context="전신 칭호 승격 후"/>
```

### 3.3 속성 업데이트 (`<entity-update>`)

```xml
<entity-update id="lintian">
  <set key="realm" value="축기기 1층" reason="혈살 비경 돌파"/>
  <set key="location" value="천운종"/>
</entity-update>
```

**작업 유형**:

| 작업 | 문법 | 설명 |
|------|------|------|
| set | `<set key="k" value="v"/>` | 속성값 설정 |
| unset | `<unset key="k"/>` | 속성 삭제 |
| add | `<add key="k" value="v"/>` | 배열에 요소 추가 |
| remove | `<remove key="k" value="v"/>` | 배열에서 요소 삭제 |
| inc | `<inc key="k" delta="1"/>` | 수치 증가 |

---

## 4. ID 생성 규칙

```python
def generate_entity_id(entity_type: str, name: str, existing_ids: set) -> str:
    """
    고유 엔티티 ID 생성

    규칙:
    1. 병음(공백 제거, 소문자) 우선 사용
    2. 충돌 시 숫자 접미사 추가
    3. 유형 접두사: 아이템→item_, 세력→faction_, 기술→skill_, 장소→loc_
    """
    prefix_map = {
        "아이템": "item_",
        "세력": "faction_",
        "기술": "skill_",
        "장소": "loc_"
        # 캐릭터는 접두사 없음
    }

    pinyin = ''.join(lazy_pinyin(name))
    base_id = prefix_map.get(entity_type, '') + pinyin.lower()

    final_id = base_id
    counter = 1
    while final_id in existing_ids:
        final_id = f"{base_id}_{counter}"
        counter += 1

    return final_id
```

---

## 5. 오류 처리

### 5.1 별칭 충돌

현재 구조는 **aliases 일대다**를 허용합니다: 동일한 별칭이 여러 엔티티를 가리킬 수 있습니다.

`ref="별칭"`이 여러 엔티티에 매칭되고 소거가 불가능한 경우, 오류 보고:

```
⚠️ 별칭 모호: '종주'가 2개 엔티티에 매칭됨, id를 사용하거나 type 속성을 보충하세요

해결 방안:
  1. 안정적인 id 사용: <entity-update id="...">...</entity-update>
  2. type 보충(교차 유형만 소거 가능; 동일 유형 동명은 여전히 id 필요)
```

### 5.2 신뢰도 처리

| 신뢰도 범위 | 처리 방식 |
|-----------|---------|
| > 0.8 | 자동 채택, 확인 불필요 |
| 0.5 - 0.8 | 제안값 채택, warning 기록 |
| < 0.5 | 수동 확인 대기 표시, 자동 기록하지 않음 |

---

## 6. 마이그레이션 설명

기존 버전 구조에서 현재 구조로 마이그레이션:

```bash
# 마이그레이션 스크립트 실행
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" migrate -- --backup

# 마이그레이션 결과 검증
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index stats
```

마이그레이션 후:
- `index.db`가 모든 엔티티, 별칭, 상태 변화, 관계를 포함
- `state.json`은 진행 상태, 주인공 상태, 리듬 추적만 보유
- 기존 `entities_v3`, `alias_index` 필드는 정리됨

---

## 7. 요약

### 7.1 현재 구조의 핵심 개선 사항

1. **SQLite 저장**: state.json 비대화 문제 해결
2. **간소화된 JSON**: state.json을 < 5KB로 유지
3. **일대다 별칭**: 동일한 별칭이 여러 엔티티에 매핑 가능
4. **AI 자동 추출**: Data Agent 의미 분석이 XML 태그를 대체

### 7.2 데이터 흐름

```
챕터 본문 → Data Agent → index.db (엔티티/별칭/관계/상태 변화)
                      → state.json (진행/주인공 상태/리듬)
                      → vectors.db (장면 벡터)
                              ↓
                      Context Agent → 다음 챕터 컨텍스트
```
