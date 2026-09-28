---
category_id: plans-index
lineage_id: legacy-e4c4ac45-4277-5022-8ce0-5c8205c86e6f
document_id: doc-80bc9998-8a02-437f-b30b-57a166a5bd1e
parent_lineage_id: null
abstract: 통합 구현 순서와 주제별 계획의 진입점을 찾을 때 읽는다.
version: 0.1.2
created_at: '2026-09-25T11:55:10.000000Z'
updated_at: '2026-09-27T07:03:17Z'
tags:
- 계획
- 색인
canon: false
---
# 현재 실행 계획 안내

핵심 규칙은 [시스템 README](../systems/README.md)를 따른다. 실제 구현의 첫 묶음과 의존 순서는 [통합 시스템 구현 플랜](20260918-current-system-execution-plan-v0-1.md)에서 확인한다. 기존 경로를 유지한 같은 계획의 개정안이며 코드·운영 DB·학습 완료 기록은 아니다.

주제별 배경과 실행 상태는 [글공장 문서 위키](../wiki/index.md)에서 찾는다. 이 계획의 원문과 완료 근거는 위키의 요약보다 우선한다.

2026-09-27 구현 준비: 세 업무축의 공개 계약을 필요한 범위만 정하고, **코퍼스 SQLite의 고정 원문 조회·분석 결과/검토/재개 상태 정본화**를 첫 구현 묶음으로 둔다. 이후 문체 학습과 현실 역사 릴리스의 좁은 경로를 독립적으로 연결하고 작품 잠금·정사까지 한 건 검증한다. 앞서 완료한 선호 작가의 구조 지도·대표 장면 [표본 분석](../research/author-study/README.md)은 보존하되 새 화별 분석이나 실제 학습 완료와 구별한다.

| 문서 | 사용 목적 | 현재 읽는 방법 |
|---|---|---|
| [위키백과 덤프 → 현실 역사 온톨로지 변환기 PRD](../prd/wikipedia-history-ontology.md) | 덤프에서 역사·지식·연결·근거 구조체를 만드는 제품의 요구·조회 계약·수락검사 | 별도 구성요소 PRD 초안. 구축·검증 실행은 미수행 |
| [위키백과 다국어 순회·입력 보수 플랜](20260927-wikipedia-multilingual-remediation-plan.md) | 전체 사이트 인벤토리·전언어 본문 순회와 H200 DB 조회→온톨로지 후보→한국어 근거 검색 첫 절편 | 구현 전 계획. 기존 영문 시험을 보존하며 DB·다국어 추출·A40 백업 실행은 후속 작업 |
| [대체역사 생성용 현실 역사·지식 구축 대상 목록](wikipedia-reality-sot-build-plan.md) | A40 서버 구축을 전제로 1950년 이전 역사·지식·연결·근거의 34개 데이터 집합과 제외 경계 정의 | 이번 범위의 목록·우선순위 초안. 구축·검증 실행은 미수행 |
| [위키백과 역사 SoT·온톨로지 상세 매핑](wikipedia-history-sot-mapping.md) | CIDOC CRM 기반 입력·의미 영역·원자 관계의 상세 후보 사전 | 앞의 구축 대상에 해당하는 부분을 적용. 실제 덤프 검증은 미수행 |
| [통합 시스템 구현 플랜](20260918-current-system-execution-plan-v0-1.md) | 현재 코드·자료의 재사용/이관, 첫 구현 묶음, 세 모듈의 단계별 수락검사 | 구현 배정의 시작점. 계획·검토 상태이며 실행 미완료 |
| [toy-tune 계획](20260914-toy-tune-architecture-and-backendai-bootstrap-plan-v0-1.md) | 데이터 준비·H200·학습·이동성 | 학습 절차를 참고. SQLite 우선 F/G 순서는 현행 PostgreSQL 기준으로 대체 |
| [지식 구축 계획](20260914-enwiki-granite-knowledge-ingestion-plan-v0-1.md) | 영어 자료·기간 범위·Granite 검색 검증 | K 단계 참고. 운영 저장소는 PostgreSQL + pgvector |
| [역사 SoT·온톨로지 조사 계획](20260924-history-sot-ontology-research-plan.md) | 보유 위키 덤프에서 원역사 릴리스와 검색 방식 결정을 위한 R0–R5 조사 | [계획 독립 검토 수락](../research/20260924-history-sot-ontology-plan-review.md). 조사·실험 미실행; 다운로드 완료와 무결성 검증 구분 |
| [문체 임베딩 계획](20260914-munche-style-embedding-integration-plan-v0-1.md) | Munche 비교·문체 평가·예문 검색 | S0/S1은 파일 실험, 운영 S2는 PostgreSQL. SQLite 운영 bank 전제는 대체 |
| [9월 11일 토이 학습 계획](20260911-gemma4-toy-finetuning-practice-plan-v0-1.md), [9월 8일 학습 계획](20260908-gemma4-finetuning-plan-v0-1.md) | 초기 실험 의도·조사 경위 | 후속 계획과 충돌하는 선택·순서는 적용하지 않음 |

[상세 아키텍처 v5](../20260914-novel-factory-architecture-v5.md)는 의미 계약을 참고한다. 남아 있는 SQLite 우선·작품별 운영 파일·PostgreSQL 후순위 표현은 핵심 설계로 대체한다. 세부 문서 전체의 재작성을 첫 실험의 선행 작업으로 만들지 않고, 해당 구현 작업에 쓰는 절을 함께 갱신한다.

`plan/`과 `docs/legacy/`는 과거 자료, `docs/reports/`는 조사·실행 근거다. 실행 완료는 실제 명령·결과·산출물에 근거해 해당 계획과 보고서에 기록한다.
