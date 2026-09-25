# Original RDB 스키마 설계서 v1

**작성일**: 2026-04-17
**상위 문서**: alt_history_factory_index_v3.md (프로젝트 인덱스)
**상태**: 스키마 뼈대 확정. 인포박스 정규화 펼침 대상 및 시대 프로파일은 파일럿 후 확정.

---

## 0. 이 문서의 위치

Original PostgreSQL의 `original` 스키마에 대한 설계서. 4개 언어 위키피디아 역사 카테고리 덤프를 정규화·추출한 정사(正史) 저장소.

작품별 `novel_XXX` 스키마 및 `meta` 스키마는 본 문서 범위 밖.

---

## 1. 설계 원칙

- **직접 얻을 수 있는 것과 가공이 필요한 것을 분리**. 덤프 파싱 단계(S1~S3)와 LLM 판정 단계(S4~S7)의 산출물을 스키마 레벨에서 구분.
- **NULL 허용을 통한 지연 평가**. 판정 필드는 전부 NULL 허용. 초벌 판정 전·후의 레코드가 공존 가능.
- **온톨로지 고정**. entity_type, event_type, relation_type은 모두 CHECK 제약으로 값 집합 고정.
- **2단계 판정 운영**. Qwen-35B 초벌 → 시대 단위 Claude 재판정 → 수동 큐레이션. 우선순위 curated > claude_refined > qwen_35b_initial.
- **교차 언어 병합 없음**. Wikidata Q-ID는 참조 필드로만 보관. 언어별 레코드 각각 보관.

---

## 2. 파이프라인 단계

스키마의 어느 컬럼이 어느 단계에서 채워지는지 명시.

| 단계 | 내용 | 채워지는 컬럼 |
|---|---|---|
| S1 덤프 파싱 | XML → 문서·섹션·인포박스 분해 | documents(식별·제목·원본), sections 전체 |
| S2 구조화 정규화 | 인포박스·카테고리에서 파생 필드 추출 | documents의 period_*, date_precision, primary_region, era_tags, domain_tags, infobox_type |
| S3 위키링크 추출 | 본문 위키링크를 엔티티 후보로 | entities 뼈대 (canonical 미확정) |
| S4 NER·관계 추출 | 본문에서 엔티티·관계 정제 | entities 보강, relationships (extraction_source='llm_ner') |
| S5 사건 추출 | 본문에서 사건 레코드 생성 | events 뼈대 |
| S6 초벌 판정 | Qwen-35B로 파급력·범위 부여 | entities·events의 impact_level, scope_domains, propagation_speed, judgment_* |
| S7 임베딩 | 섹션별 Qwen3-Embedding | section_embeddings |

S6 이후 언제든 별도 트리거로 **S6b: 시대 단위 Claude 재판정**이 실행될 수 있다. 이는 상위 문서에서 "모드 0b"로 분류.

---

## 3. 테이블 전체 DDL

### 3.1 documents

문서 = 위키 아티클 하나. 언어별 독립 레코드.

```sql
CREATE TABLE original.documents (
  id                 BIGSERIAL PRIMARY KEY,
  lang               CHAR(2) NOT NULL,
  wiki_page_id       BIGINT NOT NULL,
  wikidata_qid       TEXT NULL,
  title              TEXT NOT NULL,
  title_normalized   TEXT NOT NULL,
  url                TEXT,
  redirect_to_id     BIGINT NULL REFERENCES original.documents(id),
  dump_revision_id   BIGINT,
  dump_timestamp     TIMESTAMPTZ,
  categories         TEXT[],
  infobox_type       TEXT,
  infobox_raw        JSONB,
  -- 정규화 펼침 (파일럿 후 10~20개 확정)
  period_start       DATE NULL,
  period_end         DATE NULL,
  date_precision     TEXT NULL CHECK (date_precision IN
                       ('day','month','year','decade','century')),
  primary_region     TEXT NULL,
  era_tags           TEXT[],
  domain_tags        TEXT[],
  -- 충실성 평가 (canonical_name 승격 근거)
  fidelity_score     SMALLINT NULL CHECK (fidelity_score BETWEEN 1 AND 100),
  fidelity_rank      SMALLINT NULL,
  is_canonical       BOOLEAN NOT NULL DEFAULT FALSE,
  UNIQUE(lang, wiki_page_id)
);

CREATE INDEX idx_doc_qid ON original.documents(wikidata_qid);
CREATE INDEX idx_doc_lang_infobox ON original.documents(lang, infobox_type);
CREATE INDEX idx_doc_era_tags ON original.documents USING GIN(era_tags);
CREATE INDEX idx_doc_domain_tags ON original.documents USING GIN(domain_tags);
CREATE INDEX idx_doc_categories ON original.documents USING GIN(categories);
```

**컬럼 해설**

- `wikidata_qid`: 교차 언어 조인용 키. 병합 파이프라인은 없음. 같은 Q-ID를 가진 4개 언어 레코드가 공존할 수 있다.
- `infobox_raw`: 인포박스 전체를 jsonb로 보존. 정규화 펼침 컬럼에 없는 필드도 나중에 쿼리 가능.
- `period_start/end`: 문서 대상의 시기. 인물은 활동 기간, 사건은 진행 기간, 조직은 존속 기간.
- `era_tags`: 시대 프로파일 매칭 키. 예: `{'joseon_early','imjin_war'}`.
- `domain_tags`: political/military/scientific/economic/cultural/religious 중 복수 선택.
- `fidelity_score`: 청킹 시 AI가 부여하는 문서 충실성 점수(1–100).
- `fidelity_rank`: 동일 Q-ID 묶음 내 순위(1=최고).
- `is_canonical`: 묶음 내 canonical 승격 여부. entities.canonical_name의 출처가 된다.

### 3.2 sections

섹션 = 청크. 임베딩 단위.

```sql
CREATE TABLE original.sections (
  id                 BIGSERIAL PRIMARY KEY,
  document_id        BIGINT NOT NULL REFERENCES original.documents(id),
  section_path       TEXT NOT NULL,
  section_level      SMALLINT,
  order_in_document  INTEGER,
  title              TEXT,
  body_text          TEXT NOT NULL,
  char_count         INTEGER,
  is_lead            BOOLEAN DEFAULT FALSE,
  merged_from        TEXT[],
  split_index        INTEGER NULL,
  era_span_start     DATE NULL,
  era_span_end       DATE NULL
);

CREATE INDEX idx_sec_doc_order ON original.sections(document_id, order_in_document);
```

**컬럼 해설**

- `section_path`: 상위 제목 경로. 예: `"역사 > 초기 역사 > 건국"`.
- `merged_from`: 300자 미만 섹션 병합 시 원본 섹션 제목들.
- `split_index`: 8000자 초과로 분할된 경우 분할 순번(0, 1, 2, ...).
- `era_span_*`: 섹션이 특정 시기를 다루는 경우의 시간 범위. 섹션 제목에 연도 포함 시 규칙 기반 추출.

### 3.3 entities

인물·장소·조직·인공물·기술·개념.

```sql
CREATE TABLE original.entities (
  id                    BIGSERIAL PRIMARY KEY,
  wikidata_qid          TEXT NULL,
  canonical_name        TEXT NOT NULL,
  canonical_lang        CHAR(2) NOT NULL,
  entity_type           TEXT NOT NULL CHECK (entity_type IN
                          ('person','place','organization','artifact','technology','concept')),
  entity_subtype        TEXT NULL,
  primary_document_id   BIGINT NULL REFERENCES original.documents(id),
  aliases               TEXT[],
  active_period_start   DATE NULL,
  active_period_end     DATE NULL,
  birth_date            DATE NULL,
  death_date            DATE NULL,
  date_precision        TEXT NULL CHECK (date_precision IN
                          ('day','month','year','decade','century')),
  primary_region        TEXT NULL,
  short_description     TEXT,
  -- 판정 필드
  impact_level          SMALLINT NULL CHECK (impact_level IN (1,2,3)),
  scope_domains         TEXT[] NULL,
  judgment_source       TEXT NOT NULL DEFAULT 'qwen_35b_initial'
                          CHECK (judgment_source IN
                          ('qwen_35b_initial','claude_refined','curated')),
  judgment_at           TIMESTAMPTZ,
  judgment_refined      BOOLEAN NOT NULL DEFAULT FALSE,
  judgment_era_tags     TEXT[] NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_ent_qid ON original.entities(wikidata_qid);
CREATE INDEX idx_ent_type ON original.entities(entity_type, entity_subtype);
CREATE INDEX idx_ent_region ON original.entities(primary_region);
CREATE INDEX idx_ent_aliases ON original.entities USING GIN(aliases);
CREATE INDEX idx_ent_era_judged ON original.entities USING GIN(judgment_era_tags);
CREATE INDEX idx_ent_refine_queue ON original.entities(judgment_refined)
  WHERE judgment_refined = FALSE;
```

**엔티티 서브타입 예시**

- person: ruler / general / scholar / scientist / artisan / priest / merchant / ...
- place: capital / province / fortress / port / route / ...
- organization: dynasty / government / army / guild / religious_order / ...
- artifact: weapon / ship / coin / book / tool / monument / ...
- technology: military / naval / agricultural / medical / printing / navigation / ...
- concept: ideology / law / custom / religion_doctrine / ...

서브타입은 CHECK 제약을 걸지 않는다. 자유 문자열. 사용 분포가 안정되면 나중에 문서화.

**impact_level 기준**

- 1: Local — 특정 지역·집단에 영향
- 2: Regional — 한 왕조·문명권 규모 영향
- 3: Epochal — 시대 전환을 야기하는 규모

### 3.4 events

사건. 미세 입도로 추출.

```sql
CREATE TABLE original.events (
  id                    BIGSERIAL PRIMARY KEY,
  wikidata_qid          TEXT NULL,
  canonical_name        TEXT NOT NULL,
  canonical_lang        CHAR(2) NOT NULL,
  event_type            TEXT NOT NULL CHECK (event_type IN (
                          'battle','war','uprising',
                          'coronation','succession','coup','revolution','abdication',
                          'treaty','alliance','diplomatic_mission',
                          'invention','discovery','publication',
                          'founding','reform',
                          'assassination','execution','trial',
                          'plague','famine','natural_disaster',
                          'migration','exile',
                          'religious_event','cultural_event',
                          'other')),
  event_subtype         TEXT NULL,
  primary_document_id   BIGINT NULL REFERENCES original.documents(id),
  date_start            DATE NULL,
  date_end              DATE NULL,
  date_precision        TEXT NULL CHECK (date_precision IN
                          ('day','month','year','decade','century')),
  primary_location      TEXT NULL,
  region_scope          TEXT NULL CHECK (region_scope IN
                          ('local','regional','transregional','global')),
  description           TEXT,
  source_section_ids    BIGINT[],
  -- 판정 필드
  impact_level          SMALLINT NULL CHECK (impact_level IN (1,2,3)),
  scope_domains         TEXT[] NULL,
  propagation_speed     TEXT NULL CHECK (propagation_speed IN
                          ('fast','medium','slow')),
  judgment_source       TEXT NOT NULL DEFAULT 'qwen_35b_initial'
                          CHECK (judgment_source IN
                          ('qwen_35b_initial','claude_refined','curated')),
  judgment_at           TIMESTAMPTZ,
  judgment_refined      BOOLEAN NOT NULL DEFAULT FALSE,
  judgment_era_tags     TEXT[] NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_evt_type ON original.events(event_type);
CREATE INDEX idx_evt_start ON original.events(date_start);
CREATE INDEX idx_evt_end ON original.events(date_end);
CREATE INDEX idx_evt_location ON original.events(primary_location);
CREATE INDEX idx_evt_scope_impact ON original.events(region_scope, impact_level);
CREATE INDEX idx_evt_era_judged ON original.events USING GIN(judgment_era_tags);
CREATE INDEX idx_evt_refine_queue ON original.events(judgment_refined)
  WHERE judgment_refined = FALSE;
```

**이벤트 입도 원칙**

- 위키 문서 하나에서 개별 전투·조약·발명 단위까지 추출.
- 예: "임진왜란" 문서 → 전쟁 이벤트 1건 + 부산진 전투, 한산도 대첩, 명량 해전, 노량 해전 등 개별 전투 이벤트들.
- 상위-하위 사건은 `relationships.part_of` 엣지로 연결.

**propagation_speed 기준**

- fast: 수개월 내 파급
- medium: 수년 내 파급
- slow: 수십 년 이상 파급

### 3.5 relationships

엔티티·사건 간 엣지. 23개 관계 타입.

```sql
CREATE TABLE original.relationships (
  id                    BIGSERIAL PRIMARY KEY,
  source_id             BIGINT NOT NULL,
  source_kind           TEXT NOT NULL CHECK (source_kind IN ('entity','event')),
  target_id             BIGINT NOT NULL,
  target_kind           TEXT NOT NULL CHECK (target_kind IN ('entity','event')),
  relation_type         TEXT NOT NULL CHECK (relation_type IN (
                          'commanded','participated_in','fought_against','allied_with',
                          'caused','enabled','prevented',
                          'invented','discovered','founded',
                          'used',
                          'succeeded','appointed','overthrew',
                          'killed','captured',
                          'negotiated','ceded',
                          'member_of','part_of','located_in',
                          'married','parent_of')),
  evidence_section_ids  BIGINT[],
  confidence            REAL NULL,
  extraction_source     TEXT NOT NULL CHECK (extraction_source IN
                          ('wikilink','infobox','llm_ner','curated'))
);

CREATE INDEX idx_rel_source ON original.relationships(source_id, source_kind, relation_type);
CREATE INDEX idx_rel_target ON original.relationships(target_id, target_kind, relation_type);
CREATE INDEX idx_rel_type ON original.relationships(relation_type);
```

**중요 제약**

- source_id, target_id의 FK는 걸지 않음. source_kind·target_kind 분기 때문. 참조 무결성은 애플리케이션 레이어에서 검증.
- 시간 필드(date_start/end)는 **없음**. 관계의 시간 정보는 source·target 양단의 events.date_* 또는 entities.active_period_*를 조인으로 얻는다.

### 3.6 section_embeddings

```sql
CREATE TABLE original.section_embeddings (
  section_id         BIGINT NOT NULL REFERENCES original.sections(id),
  embedding_model    TEXT NOT NULL,
  embedding          VECTOR(1024),
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (section_id, embedding_model)
);
```

**설계 메모**

- embedding_model을 PK 일부로 둔 이유: 임베딩 모델 교체 시 기존 벡터 보존하면서 신규 모델 결과를 추가 가능.
- VECTOR(1024)는 Qwen3-Embedding + MRL 1024D 잠정. 파일럿 결과에 따라 2560 또는 4096으로 변경 가능.

### 3.7 judgment_history

2단계 판정의 이력 박제.

```sql
CREATE TABLE original.judgment_history (
  id                    BIGSERIAL PRIMARY KEY,
  target_id             BIGINT NOT NULL,
  target_kind           TEXT NOT NULL CHECK (target_kind IN ('entity','event')),
  judgment_source       TEXT NOT NULL,
  judgment_at           TIMESTAMPTZ NOT NULL,
  impact_level          SMALLINT,
  scope_domains         TEXT[],
  propagation_speed     TEXT,
  era_context           TEXT,
  reasoning_snapshot    TEXT
);

CREATE INDEX idx_jhist_target ON original.judgment_history(target_id, target_kind);
CREATE INDEX idx_jhist_at ON original.judgment_history(judgment_at);
```

**박제 시점**

- Claude 재판정 시 기존 Qwen 판정 값을 이 테이블로 복제.
- 수동 큐레이션 시 기존 값을 복제.
- 박제 후 본 레코드(events·entities)의 판정 필드를 덮어쓴다.

---

## 4. 온톨로지 집합

### 4.1 entity_type (6종)

```
person, place, organization, artifact, technology, concept
```

### 4.2 event_type (27종)

| 분류 | 타입 | 의미 |
|---|---|---|
| 군사 | battle | 개별 전투·교전 |
| 군사 | war | 전쟁·원정·장기 충돌 |
| 군사 | uprising | 반란·봉기·민중 봉기 |
| 정치변동 | coronation | 즉위·대관 |
| 정치변동 | succession | 평화적 계승 전환 |
| 정치변동 | coup | 정변·쿠데타 |
| 정치변동 | revolution | 혁명·체제 전환 |
| 정치변동 | abdication | 폐위·양위·퇴위 |
| 외교 | treaty | 조약·협정·강화 |
| 외교 | alliance | 동맹 형성 |
| 외교 | diplomatic_mission | 사절·외교 임무 |
| 지식 | invention | 발명 |
| 지식 | discovery | 발견 |
| 지식 | publication | 저술·저작 공표 |
| 제도 | founding | 설립·창건 |
| 제도 | reform | 제도 개혁·개편 |
| 위해 | assassination | 암살 |
| 위해 | execution | 처형 |
| 위해 | trial | 재판·탄핵·숙청 |
| 재난 | plague | 역병·전염병 |
| 재난 | famine | 기근 |
| 재난 | natural_disaster | 자연재해 |
| 이동 | migration | 집단 이주·정착 |
| 이동 | exile | 망명·유배 |
| 종교문화 | religious_event | 종교적 사건 |
| 종교문화 | cultural_event | 문화적 사건 |
| 폴백 | other | 기타 |

### 4.3 relation_type (23종)

| 분류 | 타입 | 의미 | 전형적 source → target |
|---|---|---|---|
| 군사 | commanded | 지휘 | person → event/organization |
| 군사 | participated_in | 참여 | person/organization → event |
| 군사 | fought_against | 교전·적대 | entity → entity |
| 군사 | allied_with | 동맹 | entity → entity |
| 인과 | caused | 유발 (도화선·구조적 원인 모두 포함) | event → event |
| 인과 | enabled | 가능하게 함 (필요조건) | entity/event → event |
| 인과 | prevented | 저지·무산 | entity/event → event |
| 창제 | invented | 발명 | person → artifact/technology |
| 창제 | discovered | 발견 | person → place/concept |
| 창제 | founded | 설립·창건 | person → organization/place |
| 사용 | used | 사용 | entity → artifact/technology |
| 권력 | succeeded | 계승 | person → person |
| 권력 | appointed | 임명 | person → person |
| 권력 | overthrew | 전복·축출 | person/organization → person |
| 위해 | killed | 살해 | person → person |
| 위해 | captured | 포획·점령 | entity → entity |
| 협상 | negotiated | 협상·체결 | person/organization → event |
| 협상 | ceded | 할양 | organization → organization |
| 소속 | member_of | 소속 | person → organization |
| 소속 | part_of | 부분·포함 | entity/event → entity/event |
| 소속 | located_in | 지리적 포함 | entity/event → place |
| 친족 | married | 혼인 | person → person |
| 친족 | parent_of | 부모·자식 | person → person |

triggered는 caused에 통합. influenced는 제외.

### 4.4 기타 제약된 값

- `date_precision`: day / month / year / decade / century
- `region_scope`: local / regional / transregional / global
- `propagation_speed`: fast / medium / slow
- `impact_level`: 1 / 2 / 3
- `judgment_source`: qwen_35b_initial / claude_refined / curated
- `extraction_source`: wikilink / infobox / llm_ner / curated
- `source_kind`, `target_kind`: entity / event

---

## 5. 2단계 판정 파이프라인

### 5.1 초벌: Qwen-35B (모드 0)

대상: 모든 entities·events.

실행:
- `judgment_source = 'qwen_35b_initial'`
- `judgment_at = now()`
- `judgment_refined = FALSE`
- `judgment_era_tags = '{}'`

### 5.2 재판정: Claude (작품 기획 단계 = 모드 0b)

대상 추출 쿼리:

```sql
SELECT * FROM original.events
WHERE judgment_refined = FALSE
  AND judgment_source != 'curated'
  AND era_tags_match(judgment_era_tags, :target_era_tags)
  -- era_tags_match는 애플리케이션 함수 또는 SQL 함수로 정의
  -- 간단한 경우: NOT (:target_era = ANY(judgment_era_tags))
```

실행 순서 (레코드당 트랜잭션):

1. 기존 판정 값을 `judgment_history`에 INSERT (reasoning_snapshot 포함).
2. 본 레코드 UPDATE:
   - `judgment_source = 'claude_refined'`
   - `judgment_refined = TRUE`
   - `judgment_era_tags = judgment_era_tags || ARRAY[:target_era]`
   - `judgment_at = now()`
   - `impact_level`, `scope_domains`, `propagation_speed` 갱신.

### 5.3 큐레이션: 수동

- 언제든 실행 가능.
- `judgment_source = 'curated'`.
- 이후 모든 자동 파이프라인에서 제외. 부분 인덱스의 조건에 포함되지 않음.

### 5.4 우선순위

```
curated > claude_refined > qwen_35b_initial
```

상위 판정은 하위 판정으로 덮이지 않는다. 파이프라인 코드가 강제.

---

## 6. 인덱스 전략

### 6.1 공통 원칙

- 단순 컬럼 인덱스는 CHECK 제약 값이 있는 컬럼부터 (cardinality 예측 가능).
- GIN은 배열·jsonb 컬럼에만.
- 부분 인덱스는 `judgment_refined = FALSE`처럼 파이프라인 큐 패턴에 사용.

### 6.2 관계 그래프 탐색 고려

`relationships` 테이블은 그래프 탐색의 출발점이다. 탐색 패턴은 주로:

- 특정 source에서 나가는 엣지: `idx_rel_source`
- 특정 target으로 들어오는 엣지: `idx_rel_target`
- 특정 관계 타입 전체: `idx_rel_type` (예: 모든 caused 엣지)

3홉 이상 탐색은 PostgreSQL 재귀 CTE로 감당 가능하나, 대규모 원본에서는 시대별 HelixDB로 위임하는 것이 본래 설계. RDB는 시대별 HelixDB 구축의 소스 역할.

### 6.3 재판정 대기 큐 인덱스

```sql
CREATE INDEX idx_evt_refine_queue ON original.events(judgment_refined)
  WHERE judgment_refined = FALSE;
```

`judgment_refined = TRUE` 상태로 전환된 레코드는 이 인덱스에서 제거되므로 큐가 자동으로 비워진다.

---

## 7. 크기 추정

### 7.1 행 수 추정

- documents: 170만 ~ 265만 (4개 언어, 역사 카테고리 필터 후)
- sections: 680만 ~ 1060만
- entities: 수백만 (문서당 복수 엔티티)
- events: 수백만 ~ 천만 (미세 입도)
- relationships: 수천만 (엔티티·이벤트당 평균 수 개의 엣지)
- section_embeddings: sections와 1:1 (임베딩 모델 1종 기준)

### 7.2 디스크 추정

- 본문 + 인포박스: 수십 GB
- 임베딩 (1024D float16): 680만 × 2KB ≈ 13.6GB, Int8 SQ 시 6.8GB
- 인덱스: 전체 테이블의 20~40%
- **총 60~100GB** 레인지

v2.1에서 Original RDB 디스크 예상 60~80GB로 기재된 것에 정합. 상한은 relationships와 인덱스 부풀림 여부에 달림.

### 7.3 판정 파이프라인 LLM 호출량

- Qwen-35B 초벌 (S4~S6 합산): 청크당 2~3회 호출 기준 1400만~3200만 회. 수 주~수 개월 소요.
- Claude 재판정: 시대 프로파일당 대상 레코드 수에 따라 수천~수만 회. 작품 기획 때마다 발생.

---

## 8. 미결 사항

### 8.1 파일럿 후 결정

- **인포박스 정규화 펼침 대상 상위 10~20 필드**. 실제 덤프의 인포박스 분포를 본 뒤 빈도·유용성 기준 선별.
- **embedding VECTOR 차원 최종값**. Qwen3-Embedding MRL 1024 vs 2560 품질 차이 실측 후.
- **fidelity_score 부여 기준**. Qwen-35B가 문서 품질을 평가하는 프롬프트·기준의 명세. 재현성 확보 필요.

### 8.2 구축 전 결정

- **시대 프로파일 초기 목록**. era_tags의 실제 값 집합. 별도 문서에서 다룰 항목.
- **entity_subtype 표준 어휘**. 제약 없이 시작 가능하나, 질의 일관성을 위해 주요 서브타입 사전 정의 권장.
- **역사 카테고리 필터의 언어별 매핑**. 4개 언어 각각에서 "역사 카테고리"의 실제 카테고리 목록.

### 8.3 운영 규약 결정

- **era_tags_match 함수의 구현**. 태그 정확 일치 / 부분 일치 / 상위-하위 관계 허용 중 어느 방식인지.
- **reasoning_snapshot 템플릿**. Claude 재판정 시 근거 서술의 구조(자유 서술 / 구조화 JSON / 하이브리드).
- **큐레이션 UI**. 수동 수정을 어떻게 입력받을지. 본 문서 범위 밖.

---

## 9. 변경 이력

- **v1 (이 문서)**: 초기 스키마 확정. 7개 테이블, 온톨로지 3종(entity 6 / event 27 / relation 23), 2단계 판정 파이프라인, judgment_history 도입.
