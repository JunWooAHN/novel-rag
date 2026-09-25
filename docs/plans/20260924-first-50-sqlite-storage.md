# 첫 50화 분석 코퍼스의 SQLite 저장 계획

상태: **원문 코퍼스 적재 완료, 350개 회차 의미 분석 저장은 후속 계획**. 사용자의 최신 요청으로 [실제 원문 DB](../../data/analysis/novel-corpus.sqlite3)와 [원문 적재 도구](../../tools/novel_corpus/README.md)가 생성되었다. 이 문서의 아래 `analysis_revisions`·`evidence` 등은 아직 구현하지 않은 후속 분석 설계다. 현재 구현된 물리 스키마는 [schema.sql](../../tools/novel_corpus/schema.sql), 실제 검증·한계는 [적재 검토](../research/chapter-ingestion/review.md)를 따른다.

## 범위와 경계

목표는 선호 작가 4명의 보유 작품 7편을 작품별 1~50화까지 분석해, 총 350개 회차 분석 단위를 검토·조회·이어쓰기 가능한 형태로 보존하는 것이다. 이는 기존의 구조 지도/대표 장면 분석을 전편 정독으로 바꾸어 부르는 작업이 아니라 새로운 회차 단위 분석이다. 7편의 과거 분석·원문 및 이들에서 파생한 결과는 영구 개발 자료이며 최종 미관측 테스트 자료가 아니다. 실제 학습 입력이나 스타일 reference를 만들려면 별도 split/중복 정책을 먼저 승인받아야 한다.

SQLite는 분석 코퍼스 전용 저장소다. 운영 캐논 DB인 PostgreSQL + pgvector를 대체하거나 캐논 상태를 기록하지 않는다. **현재는 7편의 원문 `TEXT`와 경계·원문 revision만 적재했다.** 이번 문서의 350개 분석 레코드·검토 이력은 아직 저장되지 않았고 원문 해석·실제 학습도 수행하지 않았다.

원문은 `docs/references/manifest.json`에 기록된 로컬 사본을 재사용한다. 원격 체크섬이 제공되지 않은 파일은 로컬 해시가 원격 바이트 동일성을 증명한다고 표현하지 않는다. 기준 사본 식별자는 원본 파일 전체의 바이트 SHA-256이며 원문 범위는 UTF-8 디코딩 뒤 선행 BOM(U+FEFF)과 CRLF/LF를 보존한 Python Unicode 코드포인트의 반개구간 `[start,end)`로 기록한다. 원문은 `splitlines()`, `trim()`, 개행 정규화 등으로 바꾸지 않는다. JS UTF-16 인덱스와 바이트 offset을 코드포인트 위치로 취급하지 않는다.

## 권장 배치와 보존

- 현재 활성 원문 파일: `data/analysis/novel-corpus.sqlite3` (저장소 루트 기준). Git에는 포함하지 않는다. 후속 의미 분석을 같은 DB에 확장할지 별도 DB로 둘지는 해당 단계에서 결정한다.
- 현재 추적할 계약 산출물: `tools/novel_corpus/schema.sql`, `corpus.py`, 테스트, `docs/research/chapter-ingestion/*-boundaries.json` 및 이 계획. 아래 후속 분석 테이블·마이그레이션·JSONL 계약은 별도 구현 전 검토한다.
- 지속 보존: 원문 로컬 사본은 읽기 전용 입력으로 유지하고 별도 백업 대상으로 포함한다. DB와 원문 SHA-256 manifest, 적용 schema version, 마지막 성공 export manifest를 하나의 백업 세트로 묶는다. 정기적으로 닫힌 SQLite 파일의 일관된 스냅샷을 생성해 작업 디렉터리 밖의 암호화된 백업 위치에 보관한다. DB 파일을 실행 중 단순 복사해 일관성을 가정하지 않는다. 백업 주기·보존 기간은 실행 전에 정하되 단일 복사본만을 보존으로 보지 않는다.
- **원문 전체는 현재 SQLite `segments.body`의 `TEXT`로 저장한다.** 앞머리·무번호·불명·중복·후기를 포함한 전 구간이 연속·비중첩이며 이를 합쳐 UTF-8 인코딩하면 source revision의 raw byte hash와 일치해야 한다. `docs/references`의 읽기 전용 사본은 독립 대조·복구용으로 보존하고 함께 백업한다. DB의 상대 경로, raw SHA-256, 크기/BOM/개행 메타데이터와 사본을 대조한다. 후속 분석의 근거 좌표는 이 원문 revision에 연결한다.
- 복원: 깨끗한 위치에 백업 세트를 복원하고, 파일 해시·SQLite 무결성 검사·외래키 검사·schema version·원문 hash/범위 재검사를 한 뒤 조회 샘플을 확인한다. 활성 DB를 백업 파일로 덮어쓰기 전에 복원본 검증을 완료한다.
- 이식/장기 읽기: 스키마 버전이 있는 JSONL을 테이블별로 내보내고, manifest에 DB snapshot 식별자, schema/migration 버전, export 시각(UTC), 레코드별 개수, JSONL SHA-256, 참조한 원문 사본의 상대 경로 및 바이트 SHA-256을 기록한다. 복원은 JSONL만으로도 새 DB에 재구성할 수 있도록 내보내기/가져오기를 왕복 검증한다.

## 후속 의미 분석용 제안 스키마

아래 표는 **현재 원문 DB의 테이블 목록이 아니다.** 현재 구현은 [원문 코퍼스 스키마](../../tools/novel_corpus/schema.sql)의 `works`·`source_revisions`·`segmentations`·`segments`와 조회 view를 사용한다. 후속 의미 분석에서는 목록·이력·참조를 안정적으로 조회할 핵심 필드만 정규화하고, 서사 기법의 세부 관찰은 버전이 있는 JSON 컬럼으로 유연하게 두는 방안을 제안한다.

| 테이블 | 주요 필드와 용도 |
|---|---|
| `authors` | `author_id` PK, `name` UNIQUE. 네 작가 메타데이터. |
| `works` | `work_id` PK, `author_id` FK, `title`, `manifest_path`, `current_source_revision_id` nullable FK. 작품별 source 파일 연결 및 회차 범위 계획. 제목은 유일 키로 가정하지 않는다. |
| `chapter_targets` | `work_id` FK, `target_number` (1..50), `mapped_chapter_id` nullable FK, `mapping_status` (`unmapped`, `mapped`, `hold`, `conflict`, `not_present`), `mapping_note`; PK (`work_id`, `target_number`). 작품별 50개 목표 항목을 먼저 등록해 350개 분모 및 미발견/모호/중복 충돌을 구분한다. |
| `source_revisions` | `source_revision_id` PK, `work_id` FK, `relative_path`, `sha256_raw_bytes`, `byte_size`, `encoding`, `has_utf8_bom`, `newline_profile_json`, `ends_with_newline`, `manifest_revision`, `created_at`, `change_note`. 파일 바이트별 불변 이력. SHA가 같으면 같은 원문 revision을 가리킨다. |
| `chapters` | `chapter_id` PK, `work_id` FK, `source_revision_id` FK, `ordinal` (작품 내 정렬), `label_raw`, `number_claimed` nullable, `kind` (`numbered`, `prologue`, `epilogue`, `unresolved` 등), `header_occurrence`, `start_cp`, `end_cp`, `boundary_status`, `boundary_note`. 같은 텍스트에서 중복 표제도 각각 보존한다. |
| `analysis_revisions` | `analysis_id` PK, `chapter_id` FK, `revision_no`, `import_key` NOT NULL UNIQUE, `status` (`draft`, `hold`, `accepted`, `rejected`, `superseded`), `analysis_schema_version`, `prompt_version`, `model_id`, `model_version`, `run_id`, `input_hash`, `analysis_json`, `created_at`, `supersedes_analysis_id` nullable FK, `review_note`. 과거 가정·수정·반려를 행으로 남긴다. accepted도 새 revision에 의해 삭제/덮어쓰기하지 않는다. |
| `evidence` | `evidence_id` PK, `analysis_id` FK, `source_revision_id` FK, `start_cp`, `end_cp`, `evidence_kind`, `claim_id`, `claim_path`, `basis` (`observed`, `inference`, `assumption`), `quote_check_hash`/`quote_check_status`, `note`. 각 분석 주장을 재검증 가능한 범위에 연결한다. `claim_id`는 같은 revision의 JSON `claims[].id`와 일치해야 한다. 원문 인용문 전체는 중복 저장하지 않고 필요 최소 짧은 anchor만 별도 허용한다. |
| `narrative_promises` | `promise_id` PK, `work_id` FK, `introduced_analysis_id` FK, `promise_key`, `description`, `basis`, `status` (`open`, `fulfilled`, `abandoned`, `uncertain`), `created_at`. |
| `promise_events` | `promise_event_id` PK, `promise_id` FK, `analysis_id` FK, `event_type` (`introduced`, `reinforced`, `fulfilled`, `revised`, `abandoned`, `reviewed`), `evidence_id` nullable FK, `note`. 약속의 변경/회수 이력을 연결한다. |
| `reviews` | `review_id` PK, `analysis_id` FK, `reviewer`, `decision` (`accepted`, `hold`, `rejected`, `revision_requested`), `review_note`, `created_at`. 검토 행위의 시간 순서를 보존한다. |

`analysis_json`은 분석 스키마 버전을 가진 JSON object이며 비교 가능한 고정 최상위 키 `events`, `character_state`, `character_desires`, `character_knowledge`, `exposition_methods`, `serial_links`, `technique_key`, `claims`, `uncertainties`를 갖는다. 각 `claims[]` 항목은 안정적인 분석 revision 내부 `id`, `claim_path`, `statement`, `basis`를 갖고 근거 행은 `claim_id`로 정확히 연결한다. 세부 관찰/해석/가설/반례는 이 키들 아래 유연하게 둔다. 상태, 회차 식별, 원문 좌표, 모델·프롬프트 버전, 주장 근거 연결은 조회 필드/관계로 유지한다. Promise는 식별된 장기 약속의 lifecycle만 관계형으로 두고, 일반적인 관찰·작은 모티프는 JSON detail에 남겨 모든 메모가 별도 행/테이블이 되는 것을 피한다.

회차 경계 생성 시 표제 문자열과 자동 추출 번호는 구별한다. `number_claimed`는 파싱에 성공한 숫자만 두되 표제 해석이 모호하면 null과 `unresolved`를 쓴다. `ordinal`은 원문 등장 순서이고 회차 번호를 대신하지 않는다. 프롤로그·에필로그·회차 밖 노트는 `kind`로 분리한다. 동일 번호가 여러 번 등장하거나 중복 헤더가 있으면 고유성 제약으로 숨기거나 병합하지 않고 `header_occurrence`와 경계를 각각 기록해 검토 대상으로 둔다. 경계가 확정되지 않은 경우 `boundary_status=hold`로 남기며 자동으로 1~50 중 하나에 배정하지 않는다.

## 제약, 이어쓰기와 동시성

- 모든 테이블 PK는 안정적인 UUID/ULID형 텍스트 ID를 쓰고, 참조는 명시적 FK와 `ON DELETE RESTRICT`를 기본으로 한다. 이력 데이터의 cascade 삭제는 금지한다.
- `PRAGMA foreign_keys=ON`은 모든 연결에서 설정한다. import는 단일 트랜잭션으로 진행하고 FK·좌표·schema 검증이 하나라도 실패하면 해당 batch를 rollback한다.
- 주요 인덱스: `chapter_targets(mapping_status, work_id)`, `chapters(work_id, ordinal)`, `chapters(work_id, number_claimed, header_occurrence)`, `analysis_revisions(chapter_id, revision_no DESC)`, `analysis_revisions(status, created_at)`, `evidence(analysis_id)`, `evidence(source_revision_id, start_cp, end_cp)`, `narrative_promises(work_id, status)`, `promise_events(promise_id, analysis_id)`. 유일 제약은 `chapter_targets(work_id, target_number)`, `analysis_revisions(chapter_id, revision_no)`, `analysis_revisions(import_key)`, `source_revisions(work_id, sha256_raw_bytes)`에 둔다. 회차 번호에는 UNIQUE를 적용하지 않는다.
- 이어쓰기는 회차마다 `pending → draft → hold/revision_requested → accepted` 같은 상태와 분석 run을 저장해 다음 실행이 마지막 완료·보류 회차를 찾게 한다. 예컨대 350행의 목표 인벤토리를 먼저 만들고(회차 발견/번호 신뢰도 포함), 아직 경계 미확정인 항목도 누락과 구별한다. 중단은 완료된 회차를 남기고 다음 run이 빈 회차부터 시작한다. 배치 안의 실패는 트랜잭션 전체를 되돌리며, 실패 상세는 외부 run 로그와 JSONL 입력 산출물에 보존한다.
- chapter/source/schema/prompt/model/run을 모두 고정 식별자로 남긴다. `input_hash`는 원문 revision hash + chapter 범위 + analysis schema/prompt 버전 + run input 설정의 정규 직렬화 hash다. 출력이 달라진 재분석은 새 analysis revision으로 추가하며 예전 draft/accepted/rejected와 그 reviewer 결정을 보존한다.
- 중복 방지는 두 층으로 한다. `import_key`(작품, source hash, 회차 경계, 분석 schema/prompt, 입력 hash의 결정적 조합)는 동일 산출물 재전송의 idempotent 방지용이다. 의미상 거의 같은 분석은 자동 병합하지 않고, 정규화 텍스트/근거 범위 및 기존 회차를 비교해 `possible_duplicate_of` 검토 표식(분석 JSON 또는 별도 검토 메모)을 남겨 사람이 판정한다. 같다는 판단이 없는 서로 다른 run은 모두 이력으로 남긴다.
- 수락의 원자성: `reviews`가 `decision='accepted'`로 추가되는 같은 단일 writer 트랜잭션 안에서 해당 `analysis_revisions.status`를 `accepted`로 바꾸고, 같은 chapter의 이전 accepted revision은 삭제하지 않은 채 `superseded`로 전이한다. 트랜잭션 끝에 chapter당 accepted revision이 최대 하나이며 accepted 상태마다 대응 review가 존재하는지 검사한다. hold/reject도 review 행과 상태 변경을 한 트랜잭션에서 함께 commit한다. 직접 SQL 수정은 금지하고 이 전이만 수행하는 적재 명령을 사용한다.
- 원문 경로가 가리키는 파일의 현재 raw SHA가 등록된 `source_revision`과 다르면 기존 chapter/evidence 좌표를 재사용해 accepted로 저장하지 않는다. 새 `source_revision`을 등록한 뒤 모든 범위 재검증과 필요한 재경계 작업을 거쳐 새 분석 revision을 만든다. 과거 revision은 삭제하지 않는다.
- 한 명의 coordinator가 파일별 산출물을 모으고, 작품별 JSONL 분석 산출물은 일시적/검토 가능한 교환 형식으로 유지한 후 검증을 통과한 배치만 **단일 writer**가 직렬 적재한다. 여러 Luna가 같은 SQLite 파일에 직접 쓰지 않는다. WAL은 단일 writer를 대체하지 않으며 필수 해법으로 간주하지 않는다. 기본 journal mode는 먼저 단일 writer 동작으로 충분한지 확인하고, 동시에 읽는 작업이 실제 writer를 막는 문제가 측정될 때만 WAL을 고려한다.

## JSONL 산출물과 batch 절차

각 작품 담당은 공유 DB 대신 작품별 JSONL 파일을 작성한다. 각 파일은 manifest row로 `work_id`, `source_revision_id`, 원문 SHA-256, chapter 범위, analysis schema, prompt/model/run 버전, 레코드 수와 파일 SHA-256을 선언한다. 한 회차 JSONL 레코드는 target 매핑 제안, chapter 경계, `import_key`를 포함한 analysis revision 필드, 근거 배열, promise event 제안, review 상태를 각각 명시한다. 리뷰 없는 산출물의 기본 상태는 `draft`이며, 사람이 승인한 결과만 `accepted`로 전이한다. 보류·반려 결정은 별도 review 이력과 분석 revision 상태로 남긴다.

단일 writer batch는 다음 순서로 실행한다.

1. JSONL 문법·스키마 버전·manifest digest·예상 작품/원문 SHA·범위와 사전 등록한 `chapter_targets` 1~50을 검증한다.
2. raw bytes에서 SHA-256, 바이트 크기, BOM, CRLF/LF/단독 CR 개수, 끝 개행을 다시 계산해 등록 source revision과 대조한다. 지정된 사본이 다르면 적재를 중단하고 새 revision 경로로 분기한다.
3. 각 chapter에 대해 `0 <= start_cp < end_cp <= len(decoded_text)` 및 원문에서 직접 자른 경계/짧은 anchor 일치를 확인한다. 표제 일치·경계 정렬·근거 인용 확인을 수행하며 `trim/splitlines/개행 치환`된 텍스트 기준 좌표는 거부한다.
4. 모든 evidence가 같은 `source_revision_id`를 가리키고 chapter 범위 안에 있으며 end-exclusive 경계가 유효한지 확인한다. 주장이 관찰인지 추론/가정인지 basis 필드를 갖는지 확인한다. 근거가 없는 사실 주장은 경고 또는 hold 대상이다.
5. 구조·FK·status transition·run lineage를 검증한 뒤 결정적 import key로 기존 행 존재를 확인한다. 완전히 동일한 키는 no-op 재실행으로 처리하고, 달라진 내용은 이력을 새 revision으로 쓴다.
6. 한 batch 트랜잭션으로 쓰고 import report를 JSONL manifest 옆에 남긴다. 오류 시 rollback하여 일부 chapter만 반영되는 상태를 만들지 않는다. 재실행은 성공한 산출물에 대해 동일 행 수를 유지하며 이미 적재된 건을 중복하지 않아야 한다.

## 승인 후 수락 검사 및 복구 검증 계획

실행 단계에서 각 작품의 `chapter_targets` 1~50을 먼저 50행씩 등록해 정확히 350행 분모를 만들고, 산출물 batch마다 다음을 통과해야 한다.

- source coverage: 일곱 작품 모두 올바른 작가에 연결되고 각 회차 경계가 등록 revision 하나에 연결된다. 번호 불확실성·중복 헤더·프롤로그는 집계에서 별도 상태로 보인다. 목표 1~50 중 미발견/미검토 항목이 완료로 오인되지 않는다.
- evidence integrity: 모든 증거 범위가 원문 SHA가 같은 revision에서 재구성되고, 저장한 짧은 anchor/quote hash 검사가 일치한다. CRLF·BOM 포함 fixture를 대상으로 코드포인트 범위를 다시 적용해 slice가 정확히 복원되는지 확인한다.
- workflow integrity: draft/hold/rejected/accepted가 필터링되고, accepted 분석에도 검토 기록이 이어지며, revision 변경 뒤 예전 가정과 결정이 남는다. 중단 후 이어하기가 이미 끝난 chapter를 건너뛰고 보류 항목을 보류로 보존한다.
- import integrity: 같은 JSONL 두 번 적재한 결과가 행 수·ID·관계가 변하지 않는지 확인한다. 수정된 분석은 새 revision이 되는지, 바뀐 원문 SHA는 새 source revision을 요구하는지, 한 레코드 오류 시 batch가 전부 rollback되는지 확인한다.
- restore/export integrity: DB 백업에서 임시 경로 복원, `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, 핵심 조회, JSONL export/import 왕복의 개수·ID·hash 비교를 완료한다. 중간 실패 시 마지막 유효 backup과 import manifest로 복구 가능한지 확인한다.

## 후속 분석 스키마가 구현된 뒤의 조회 예시

아래 SQL은 후속 분석 스키마 연결을 보여주는 초안이며 **현재 `novel-corpus.sqlite3`에는 실행할 수 없다.** 목표 수는 제안된 `chapter_targets`의 350개 고정 행이 분모다. 현재 원문 DB에서 번호별 경계 상태를 볼 때는 `first_50_status` view나 [CLI](../../tools/novel_corpus/README.md)의 `status`·`chapters`를 사용한다. 표제가 모호하거나 중복되어도 대상 번호는 하나씩 보존한다. 최신 분석 revision은 chapter마다 하나만 고른다.

**1. 350회차의 완료·보류·누락:**

```sql
WITH latest AS (
  SELECT ar.*, ROW_NUMBER() OVER (
    PARTITION BY ar.chapter_id ORDER BY ar.revision_no DESC
  ) AS rn
  FROM analysis_revisions ar
), target_state AS (
  SELECT t.work_id, t.target_number, t.mapping_status, c.chapter_id,
         l.status AS latest_status,
         EXISTS (SELECT 1 FROM reviews r
                 JOIN analysis_revisions ra ON ra.analysis_id = r.analysis_id
                 WHERE ra.chapter_id = c.chapter_id AND r.decision = 'accepted'
                   AND ra.status = 'accepted') AS has_accepted
  FROM chapter_targets t
  LEFT JOIN chapters c ON c.chapter_id = t.mapped_chapter_id
  LEFT JOIN latest l ON l.chapter_id = c.chapter_id AND l.rn = 1
)
SELECT w.title,
       COUNT(*) AS target_total,
       SUM(mapping_status = 'mapped') AS boundary_mapped,
       SUM(mapping_status IN ('hold','conflict')) AS boundary_hold_or_conflict,
       SUM(latest_status = 'draft') AS latest_draft,
       SUM(latest_status = 'hold') AS latest_hold,
       SUM(latest_status = 'rejected') AS latest_rejected,
       SUM(has_accepted) AS accepted,
       SUM(mapping_status IN ('unmapped','not_present')) AS missing_or_unmapped
FROM target_state ts
JOIN works w ON w.work_id = ts.work_id
WHERE w.work_id IN (:seven_work_ids)
GROUP BY w.work_id;
```

`chapter_targets`가 있어 표제 미발견 회차도 집계에서 사라지지 않는다. `mapping_status='conflict'`는 한 target의 복수 후보를 자동 매핑하지 않고 hold로 친다. 별도 이력 질의는 `analysis_revisions`와 `reviews`의 모든 행을 시간순으로 반환한다. 최신 accepted 사례만 필요한 조회는 회차별 최신 accepted revision을 고르는 `latest_accepted` CTE로 제한하고, 과거 revision까지 검토하려는 조회만 전체 revision을 반환한다. 위 집계는 최신 revision 상태와 accepted review 존재를 분리해 센다.

**2. 1~10화의 욕망·약속 변화:** `analysis_json`의 `character_desires`와 `promise_events`의 introduced/reinforced/revised/fulfilled를 chapter 번호와 revision 상태별로 시간 순 정렬.

```sql
WITH latest_accepted AS (
  SELECT ar.*, ROW_NUMBER() OVER (
    PARTITION BY ar.chapter_id ORDER BY ar.revision_no DESC
  ) AS rn
  FROM analysis_revisions ar WHERE ar.status = 'accepted'
)
SELECT t.target_number, ar.status, ar.analysis_json,
       p.promise_key, pe.event_type, pe.note
FROM chapters c
JOIN chapter_targets t ON t.mapped_chapter_id = c.chapter_id
  AND t.mapping_status = 'mapped'
JOIN latest_accepted ar ON ar.chapter_id = c.chapter_id AND ar.rn = 1
LEFT JOIN promise_events pe ON pe.analysis_id = ar.analysis_id
LEFT JOIN narrative_promises p ON p.promise_id = pe.promise_id
WHERE t.work_id = :work_id AND t.target_number BETWEEN 1 AND 10
ORDER BY t.target_number, pe.promise_event_id;
```

**3. 설명과 행동의 연결 근거:** `analysis_json`의 claim path와 JSON detail에서 관계 후보를 고르고, `evidence`를 통해 원문 위치와 판정 basis를 가져온다.

```sql
WITH latest_accepted AS (
  SELECT ar.*, ROW_NUMBER() OVER (
    PARTITION BY ar.chapter_id ORDER BY ar.revision_no DESC
  ) AS rn
  FROM analysis_revisions ar WHERE ar.status = 'accepted'
)
SELECT t.target_number, e.claim_id, e.claim_path, e.basis, e.start_cp, e.end_cp,
       e.quote_check_status, e.note
FROM evidence e
JOIN latest_accepted ar ON ar.analysis_id = e.analysis_id AND ar.rn = 1
JOIN chapters c ON c.chapter_id = ar.chapter_id
JOIN chapter_targets t ON t.mapped_chapter_id = c.chapter_id
  AND t.work_id = :work_id AND t.mapping_status = 'mapped'
WHERE t.work_id = :work_id
  AND e.claim_path IN ('exposition_to_action', 'description_to_choice')
ORDER BY t.target_number, e.start_cp;
```

**4. 미회수 약속과 회수 회차:** 현재 약속 상태 및 이력을 함께 확인해 open/uncertain 약속, fulfill 회차를 찾는다.

```sql
WITH latest_accepted AS (
  SELECT ar.*, ROW_NUMBER() OVER (
    PARTITION BY ar.chapter_id ORDER BY ar.revision_no DESC
  ) AS rn
  FROM analysis_revisions ar WHERE ar.status = 'accepted'
), accepted_events AS (
  SELECT pe.* FROM promise_events pe
  JOIN latest_accepted ea ON ea.analysis_id = pe.analysis_id AND ea.rn = 1
)
SELECT p.promise_key, p.description, p.status AS current_status,
       intro_target.target_number AS introduced_chapter,
       fulfill_target.target_number AS fulfilled_chapter
FROM narrative_promises p
JOIN latest_accepted iar ON iar.analysis_id = p.introduced_analysis_id AND iar.rn = 1
JOIN chapters intro ON intro.chapter_id = iar.chapter_id
JOIN chapter_targets intro_target ON intro_target.mapped_chapter_id = intro.chapter_id
  AND intro_target.mapping_status = 'mapped'
LEFT JOIN accepted_events pe ON pe.promise_id = p.promise_id AND pe.event_type = 'fulfilled'
LEFT JOIN latest_accepted far ON far.analysis_id = pe.analysis_id AND far.rn = 1
LEFT JOIN chapters fulfill ON fulfill.chapter_id = far.chapter_id
LEFT JOIN chapter_targets fulfill_target ON fulfill_target.mapped_chapter_id = fulfill.chapter_id
  AND fulfill_target.mapping_status = 'mapped'
WHERE p.work_id = :work_id
  AND (p.status IN ('open','uncertain') OR fulfill.chapter_id IS NOT NULL)
ORDER BY intro_target.target_number, fulfill_target.target_number;
```

**5. 같은 기법의 작가/작품별 사례:** JSON detail은 탐색 조건으로만 쓰고, 반환 사례를 evidence와 검토 상태로 확인한다. 자주 쓰는 technique key는 analysis schema의 고정 vocabulary로 정한다.

```sql
WITH latest_accepted AS (
  SELECT ar.*, ROW_NUMBER() OVER (
    PARTITION BY ar.chapter_id ORDER BY ar.revision_no DESC
  ) AS rn
  FROM analysis_revisions ar WHERE ar.status = 'accepted'
)
SELECT a.name, w.title, t.target_number, ar.status,
       json_extract(ar.analysis_json, '$.technique_key') AS technique,
       e.start_cp, e.end_cp, e.basis
FROM latest_accepted ar
JOIN chapters c ON c.chapter_id = ar.chapter_id
JOIN works w ON w.work_id = c.work_id
JOIN authors a ON a.author_id = w.author_id
JOIN chapter_targets t ON t.mapped_chapter_id = c.chapter_id
  AND t.work_id = w.work_id AND t.mapping_status = 'mapped'
JOIN evidence e ON e.analysis_id = ar.analysis_id
WHERE json_extract(ar.analysis_json, '$.technique_key') = :technique
  AND ar.rn = 1
ORDER BY a.name, w.title, t.target_number;
```

SQL 초안은 번호 불확실성·최신 revision 선택·JSON 경로 계약을 실제 schema 승인 때 확정해야 한다. 사실 확인이나 모델 학습 출처로 자동 승격하는 질의가 아니다.

## 미결정 사항

검토자가 결정할 항목: 백업 주기/보존 장소, ID 포맷(UUID 또는 ULID), 분석 JSON vocabulary의 최소 필수 키, 350 목표 chapter 인벤토리 생성 정책, 단일 writer를 담당할 batch 운영자/명령, 실제 학습 split 승인 절차. WAL 사용 여부는 동시 reader/writer 측정 뒤 정하며 초기 전제로 두지 않는다.
