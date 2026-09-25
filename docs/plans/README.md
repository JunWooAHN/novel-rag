# 현재 실행 계획 안내

핵심 규칙은 [시스템 README](../systems/README.md)를 따른다. 지금 할 작업과 의존 순서는 [2026-09-18 통합 실행계획](20260918-current-system-execution-plan-v0-1.md)에서 확인한다. 통합 실행계획은 현행 설계를 구현 작업으로 나눈 제안이며, 구현 완료 기록과 구분한다.

주제별 배경과 실행 상태는 [글공장 문서 위키](../wiki/index.md)에서 찾는다. 이 계획의 원문과 완료 근거는 위키의 요약보다 우선한다.

2026-09-24 반영: 사용자가 지정한 리첼렌·간다왼쪽·명원·마늘맛스낵 작가의 보유작을 대상으로 분석(R)을 먼저 수행한다. 작품별 Luna가 구조 지도와 초·중·후반 대표 장면을 분석하고 작가별 Sol이 검토한다. [배정 현황](../research/author-study/README.md)에 따라 루트는 오케스트레이션만 맡는다. 결과로 장면 명세·학습·평가 기준을 정한 뒤 Gemma 학습(A)과 역사 시스템(B)을 진행한다. 로컬 환경 준비는 병행할 수 있다.

| 문서 | 사용 목적 | 현재 읽는 방법 |
|---|---|---|
| [통합 실행계획](20260918-current-system-execution-plan-v0-1.md) | 현재 상태, 첫 작업, 단계별 산출물·완료 조건 | 실행 순서의 시작점 |
| [toy-tune 계획](20260914-toy-tune-architecture-and-backendai-bootstrap-plan-v0-1.md) | 데이터 준비·H200·학습·이동성 | 학습 절차를 참고. SQLite 우선 F/G 순서는 현행 PostgreSQL 기준으로 대체 |
| [지식 구축 계획](20260914-enwiki-granite-knowledge-ingestion-plan-v0-1.md) | 영어 자료·기간 범위·Granite 검색 검증 | K 단계 참고. 운영 저장소는 PostgreSQL + pgvector |
| [역사 SoT·온톨로지 조사 계획](20260924-history-sot-ontology-research-plan.md) | 보유 위키 덤프에서 원역사 릴리스와 검색 방식 결정을 위한 R0–R5 조사 | [계획 독립 검토 수락](../research/20260924-history-sot-ontology-plan-review.md). 조사·실험 미실행; 다운로드 완료와 무결성 검증 구분 |
| [문체 임베딩 계획](20260914-munche-style-embedding-integration-plan-v0-1.md) | Munche 비교·문체 평가·예문 검색 | S0/S1은 파일 실험, 운영 S2는 PostgreSQL. SQLite 운영 bank 전제는 대체 |
| [9월 11일 토이 학습 계획](20260911-gemma4-toy-finetuning-practice-plan-v0-1.md), [9월 8일 학습 계획](20260908-gemma4-finetuning-plan-v0-1.md) | 초기 실험 의도·조사 경위 | 후속 계획과 충돌하는 선택·순서는 적용하지 않음 |

[상세 아키텍처 v5](../20260914-novel-factory-architecture-v5.md)는 의미 계약을 참고한다. 남아 있는 SQLite 우선·작품별 운영 파일·PostgreSQL 후순위 표현은 핵심 설계로 대체한다. 세부 문서 전체의 재작성을 첫 실험의 선행 작업으로 만들지 않고, 해당 구현 작업에 쓰는 절을 함께 갱신한다.

`plan/`과 `docs/legacy/`는 과거 자료, `docs/reports/`는 조사·실행 근거다. 실행 완료는 실제 명령·결과·산출물에 근거해 해당 계획과 보고서에 기록한다.
