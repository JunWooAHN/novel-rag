# 대체역사 웹소설 공장 SQLite 정사 구조 검토 보고서 v0.1

- 작성일: 2026-09-08
- 문서 성격: 아키텍처 논의 결과 및 후속 설계 기준
- 범위: HelixDB 대체, SQLite 벡터 검색, 오리진 역사와 작품 정사의 결합, 화별 집필·공개 흐름, 최신 `webnovel-writer` 비교
- 제외 범위: 구체적인 구현 일정, Gemma/Qwen 파인튜닝 실행 계획

## 1. 결론

현재 목표에는 HelixDB를 계속 유지하는 것보다 SQLite 중심 구조가 현실적이다. 시스템을 다음 두 층으로 단순화한다.

```text
original.sqlite                         작품별 canon.sqlite
불변·공용 현실 역사            +        단일·선형 개변 역사
```

작품의 개변 역사는 여러 영구 세계선으로 분기하지 않는다. 집필 중에는 화별 Git 브랜치나 worktree를 임시로 사용할 수 있지만, 화가 공개되면 해당 변경분은 작품의 단일 정사에 직렬로 합쳐진다. 임시 작업 브랜치와 worktree는 병합 후 제거할 수 있다.

SQLite 파일 자체를 Git으로 병합하지 않는다. 각 집필 worktree는 사람이 읽고 비교할 수 있는 화별 역사전표를 만들고, 공개 게이트가 이를 검증하여 중앙 정사 SQLite에 트랜잭션으로 투영한다.

## 2. 용어 구분

이 설계에서는 다음 세 종류의 "커밋"과 "브랜치"를 구분해야 한다.

| 용어 | 의미 |
|---|---|
| Git commit | 파일 변경 이력 |
| Git branch/worktree | 동시 집필이나 실험을 위한 임시 개발 공간 |
| 역사전표 또는 chapter commit | 한 화가 세계에 만든 사건·상태 변경 기록 |
| 개변 역사 브랜치 | Git 브랜치가 아니라 작품의 유일한 대체역사 세계선 |

화마다 역사전표를 만든다고 해서 Git 브랜치가 화 수만큼 늘어나는 것은 아니다. 작품 정사에는 1,000개의 화별 전표가 선형으로 누적될 수 있지만, 세계선은 하나로 유지된다.

## 3. HelixDB를 SQLite로 대체하는 판단

### 3.1 대체가 타당한 이유

- 사용자 한 명이 운영하는 연구·집필 공장이다.
- 쓰기는 화 공개 시점에 직렬화할 수 있다.
- 주요 질의는 전체 그래프 무제한 탐색보다 인물·사건·시기·지역으로 좁힌 1~3 hop 탐색이다.
- 운영 복잡도와 상시 메모리 비용을 줄이는 편이 그래프 DB의 분산·서버 기능보다 중요하다.
- 기존 예상 데이터 60~100GB는 SQLite의 파일 크기 한도 안에 충분히 들어간다.

### 3.2 온톨로지와 저장소의 역할

온톨로지는 DB 제품의 대체물이 아니라 데이터 의미와 제약의 명세다.

- 엔티티 유형, 사건 유형, 관계 유형을 버전 관리한다.
- 사실과 사건은 정규 SQLite 테이블에 저장한다.
- 출처, 신뢰도, 시공간 범위, 유효 기간을 명시한다.
- 텍스트 검색은 FTS5를 사용한다.
- 의미 검색은 SQLite 벡터 확장을 사용한다.
- 짧은 관계 탐색은 recursive CTE 또는 애플리케이션 계층에서 수행한다.

HelixDB의 시대별 합성 그래프는 별도 DB로 물질화하지 않고, 질의 조건과 임시 결과 집합으로 대체한다.

## 4. `sqlite-vector`와 `sqlite-vec` 판단

### 4.1 `sqlite-vector`

- 일반 SQLite 테이블의 BLOB 벡터를 대상으로 동작한다.
- SIMD 기반 전체 스캔과 양자화된 검색을 제공한다.
- 큰 규모의 읽기 중심 벡터 집합에 적합하다.
- 양자화 인덱스는 데이터 변경 후 다시 생성해야 하므로 빈번한 쓰기에는 불편하다.

### 4.2 `sqlite-vec`

- `vec0` 가상 테이블을 중심으로 사용한다.
- 삽입과 삭제가 단순하고 metadata, auxiliary column, partition key를 지원한다.
- 안정판의 검색은 기본적으로 flat KNN이다.
- 신규 ANN 기능은 아직 안정성 검증이 더 필요하다.

### 4.3 현재 선택

초기 기본 확장은 `sqlite-vector`로 잡는다.

- `original.sqlite`: 크고 거의 불변이므로 양자화 검색이 잘 맞는다.
- 작품별 벡터: 규모가 작으므로 우선 `vector_full_scan`으로 충분하다.
- 작품 벡터가 커지면 `accepted_base + recent_delta`로 나누고 주기적으로 compact한다.
- `sqlite-vec`는 작품별 동적 메모리에서 partition 기반 검색이 실제로 필요해질 때 재검토한다.

벡터는 진실의 원본이 아니다. 구조화된 사실·사건·관계가 원본이며, 벡터는 검색을 위한 파생 데이터다.

참고 자료:

- [sqlite-vector](https://github.com/sqliteai/sqlite-vector)
- [sqlite-vec](https://github.com/asg017/sqlite-vec)
- [SQLite FTS5](https://www.sqlite.org/fts5.html)
- [SQLite recursive CTE](https://sqlite.org/lang_with.html)
- [SQLite WAL](https://www.sqlite.org/wal.html)

## 5. 오리진 역사와 작품별 개변 역사

### 5.1 오리진 역사

`original.sqlite`는 위키백과 덤프와 정제된 역사 자료로 구성하는 공용 기준선이다.

- 가능한 한 불변으로 취급한다.
- 엔티티와 사건에 영속적인 외부 식별자를 부여한다.
- 작품이 오리진 행을 복사하거나 직접 수정하지 않는다.
- 잘못된 원자료 정정은 작품 정사와 분리된 오리진 데이터 릴리스로 처리한다.

### 5.2 작품 정사

작품마다 하나의 `canon.sqlite`를 둔다. 작품에서 새로 발생한 사건, 변경된 사실, 인물별 인지 상태, 오리진 사건에 대한 변경 선언을 저장한다.

핵심 테이블 후보는 다음과 같다.

| 테이블 | 역할 |
|---|---|
| `canon_revision` | 현재 공개 정사 버전과 전표 해시 |
| `published_chapters` | 공개 화와 반영된 정사 리비전 연결 |
| `events` | 작품 세계에서 실제로 발생한 사건 |
| `fact_ledger` | 상태 변경 전표와 선행 사실 대체 관계 |
| `original_overrides` | 원역사 사건의 취소·변형·지연·대체 선언 |
| `knowledge_ledger` | 각 인물이 무엇을 언제 알게 되었는지 기록 |
| `memory_vectors` | 검색용 서술 기억과 임베딩 |

SQLite DB 사이에는 강제 가능한 cross-database foreign key가 없으므로, 오리진 참조는 문자열 기반의 안정 식별자를 사용하고 애플리케이션에서 검증한다.

예시:

```text
orig:event:ko:wikidata:Q...
novel:cheolgap:event:ch040:001
```

### 5.3 오리진 사건의 상태

개변점 이후의 모든 원역사를 일괄 삭제하지 않는다. 오리진 사실과 사건을 다음처럼 구분한다.

- `active`: 여전히 유효한 기준 역사
- `contested`: 개변의 영향을 받을 가능성이 있어 그대로 확정할 수 없음
- `overridden`: 작품 정사에서 명시적으로 취소·대체됨

현재 작품 세계는 개념적으로 다음과 같이 계산한다.

```text
유효한 오리진 기준선
+ 공개된 작품 사건
+ 활성 fact ledger
- 명시적으로 override된 오리진 사건
- 현재 질의에서 확정 사실로 사용할 수 없는 contested 사건
```

`original_overrides.effect` 후보는 `prevented`, `modified`, `delayed`, `advanced`, `replaced`, `contested`이다. 적용 시점, 지역, 분야, 종료 조건도 함께 기록해야 한다.

## 6. 역사전표와 시간 모델

각 전표에는 적어도 다음 시간이 필요하다.

- `story_time`: 작품 세계에서 사건이 발생한 시점
- `chapter_time`: 어느 화에서 서술·확정되었는지
- `published_at`: 독자에게 공개되어 정사가 된 시점
- `known_at`: 특정 인물이 그 사실을 알게 된 시점

화별 역사전표 예시는 다음과 같다.

```json
{
  "chapter": 40,
  "base_canon_revision": 39,
  "status": "provisional",
  "events": [
    {
      "operation": "create",
      "event_id": "novel:cheolgap:event:ch040:001",
      "occurred_at": "1453-10-12",
      "summary": "문종이 예정된 사망을 피했다"
    }
  ],
  "original_overrides": [
    {
      "original_event_id": "orig:event:ko:wikidata:Q...",
      "effect": "prevented",
      "replacement_event_id": "novel:cheolgap:event:ch040:001"
    }
  ]
}
```

역사전표는 append-only를 기본으로 한다. 정정이 필요하면 기존 전표를 덮어쓰지 않고 `supersedes` 또는 명시적인 정정 전표로 연결한다.

## 7. 집필 worktree와 공개 게이트

### 7.1 집필 중

각 worktree는 현재 공개 정사 리비전을 기준으로 화를 집필한다. 중앙 `canon.sqlite`를 직접 수정하지 않고 다음 결과를 만든다.

- 본문 초안
- 검수 결과
- 사실·사건 추출 결과
- `history-delta.json`
- 검색용 기억 후보

이 단계의 결과는 `draft`, `reviewed`, `scheduled` 중 하나이며 아직 정사가 아니다.

### 7.2 공개 시

공개 작업은 다음 순서로 직렬화한다.

1. 전표의 `base_canon_revision`과 현재 리비전을 비교한다.
2. 다른 화가 먼저 합쳐졌다면 최신 정사를 기준으로 모순을 재검사한다.
3. 사람의 공개 승인을 확인한다.
4. 하나의 SQLite 트랜잭션으로 사건, 사실, override, 지식, 기억을 반영한다.
5. 본문과 역사전표를 동일한 Git 주계보에 커밋한다.
6. 임시 작업 브랜치와 worktree를 정리한다.

한 화의 정사 반영에서 일부 테이블만 갱신되는 상태를 허용하지 않는다. 실패하면 전체 트랜잭션을 rollback한다.

### 7.3 병렬 집필 제약

40화와 41화를 동시에 집필할 수는 있지만, 41화의 전표는 40화가 공개 정사에 합쳐진 후 다시 검증해야 한다. 병렬 생성은 허용하되 정사 반영은 공개 순서대로 직렬화한다.

## 8. 최신 `lingfengQAQ/webnovel-writer`와의 비교

2026-09-08 기준 upstream 안내상 `master`의 v6가 유지보수 중인 최신 배포 계열이고, v7은 동결된 미출시 기록이며, v8은 개발 중인 차세대다. 따라서 실제 비교 대상은 최신 배포판 v6.2.1이다.

`webnovel-writer`의 `CHAPTER_COMMIT`은 Git commit이나 Git branch가 아니다. 한 화에서 확정된 사건과 상태 변경을 기록하는 애플리케이션 수준의 commit artifact다.

최신 v6 흐름은 다음과 같다.

```text
본문 작성
-> 검수
-> 사실 추출
-> accepted CHAPTER_COMMIT
-> state.json / index.db / vectors.db / summary / memory 투영
```

### 8.1 공통점

- 화별 불변 변경 기록을 만든다.
- 승인된 기록만 정사에 넣는다.
- 정사 기록에서 검색 인덱스와 요약을 투영한다.
- 투영 실패 시 원본 commit에서 재실행할 수 있다.
- 작성 전·commit 전·commit 후 검증 게이트를 둔다.
- AI가 사실을 추출하되 프로그램이 형식과 무결성을 검증한다.

### 8.2 차이점

| 구분 | 최신 `webnovel-writer` v6.2.1 | 본 프로젝트 |
|---|---|---|
| 세계의 출발점 | 작품별 설정집 | 위키백과 기반 공용 오리진 역사 |
| 정사 구조 | 작품 사실의 단일 commit 연쇄 | 오리진 기준선과 단일 개변 정사의 overlay |
| 승인 기준 | 작성·검수 후 accepted | 실제 공개 후 published |
| 역사 의미 | 일반 사건·인물·관계·상태 | 원역사 사건의 취소·지연·대체와 파급 범위 |
| 병렬 집필 | 단일 집필 파이프라인 중심 | 임시 Git worktree와 공개 시 직렬 병합 |
| SQLite | 파생 read model | 역사 온톨로지 질의와 합성의 핵심 read model |
| 벡터 | 작품 내부 기억 검색 | 대규모 오리진 역사와 소규모 작품 기억을 분리 검색 |

본 프로젝트는 `webnovel-writer`와 완전히 다른 생성기를 만드는 것이 아니라, 검증된 commit/projection 패턴을 가져오고 그 위에 대체역사 특화 데이터 모델을 추가하는 방향에 가깝다.

참고 자료:

- [webnovel-writer upstream README](https://github.com/lingfengQAQ/webnovel-writer)
- [webnovel-writer v6 아키텍처](https://github.com/lingfengQAQ/webnovel-writer/blob/master/docs/architecture/overview.md)
- [webnovel-writer v6.2.1 릴리스](https://github.com/lingfengQAQ/webnovel-writer/releases/tag/v6.2.1)

## 9. 저장소와 운영상 주의사항

- SQLite WAL은 네트워크 파일시스템에서 안전하게 사용할 수 없으므로 실제 Backend.AI 마운트 특성을 확인한다.
- 가능하면 활성 DB는 로컬 NVMe에서 사용하고, 공개 commit 또는 checkpoint 단위로 영속 데이터 폴더에 안전하게 백업한다.
- 세션 삭제 시 마운트 밖의 데이터가 사라질 수 있으므로 학습 데이터, 모델, 체크포인트와 정사 원장은 반드시 영속 폴더에 보관한다.
- DB 백업은 파일 복사 시점의 일관성을 보장하기 위해 SQLite Backup API 또는 `VACUUM INTO` 같은 일관된 스냅샷 방법을 사용한다.
- 작품 정사 SQLite와 벡터 인덱스는 재생성 가능하게 유지하고, 공개된 역사전표와 본문을 장기 원본으로 보존한다.

## 10. 현재 결정과 미결정 사항

### 결정

- HelixDB 의존을 제거하는 방향으로 간다.
- 공용 오리진 역사는 SQLite로 구축한다.
- 작품별 영구 개변 세계선은 하나만 둔다.
- 집필 중 임시 worktree는 허용한다.
- 공개된 화만 단일 개변 정사에 직렬 반영한다.
- SQLite 바이너리를 Git merge하지 않고 화별 전표를 병합한다.
- `sqlite-vector`를 초기 기본 후보로 삼는다.
- 구조화된 전표를 진실의 원본, 벡터를 파생 검색 데이터로 취급한다.

### 추가 검증 필요

- 한국어 역사 질의에서 512차원과 1024차원 임베딩의 실제 품질·속도 비교
- 위키백과 덤프에서 사건·관계·시간·출처를 추출하는 ETL 정확도
- `contested` 오리진 사건을 자동 전파할 범위와 사람 승인 경계
- 여러 worktree의 전표 충돌 탐지와 재검증 규칙
- Backend.AI 데이터 폴더의 실제 파일시스템 특성과 SQLite WAL 적합성
- 공개 취소, 플랫폼 수정, 오탈자 수정이 정사 리비전에 미치는 정책

## 11. 후속 플랜에 반영할 원칙

향후 파인튜닝 및 시스템 구현 플랜은 다음 순서를 전제로 다시 작성해야 한다.

1. 집필 역할과 정사 데이터 계약을 먼저 확정한다.
2. 오리진 역사 ETL과 작품 역사전표의 최소 스키마를 검증한다.
3. `original + canon overlay` 질의가 실제 대체역사 질문에 답하는지 평가한다.
4. 생성 모델의 역할을 작가, 계획자, 사실 추출기, 검수기, 수정기로 분리 평가한다.
5. 베이스 모델과 데이터셋을 선정한 뒤 H200 파인튜닝 방식을 결정한다.

모델 파인튜닝은 이 데이터·운영 계약을 대체하지 않는다. 모델은 역사전표를 제안하고 본문을 생성할 수 있지만, 공개 정사 편입과 무결성 판정은 별도 게이트가 담당한다.
