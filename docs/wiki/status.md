# 현재 상태와 미결정

기준일: 2026-09-24. 아래의 `확인`은 연결된 검증·검토 기록의 범위 안에서만 유효하다.

| 상태 | 사실과 한계 | 근거 |
|---|---|---|
| **확인: 원문 보존** | 7편, 현재 분할판 3,292구간, raw byte 합계 61,533,769. SQLite 본문 재조합 hash와 로컬 manifest·사본 일치. 원격 Drive 객체와 독립적인 바이트 동일성까지 증명한 것은 아님. | [코퍼스 안내](../research/chapter-ingestion/README.md), [독립 검토](../research/chapter-ingestion/review.md) |
| **확인: 첫 50 번호** | 249/350 확정. 고종·고려 각 50은 공식 회차 대응 미확정, 콧수염 41편은 중복 충돌 1. 미매핑도 본문은 저장됨. | [경계 표](../research/chapter-ingestion/README.md), [검토](../research/chapter-ingestion/review.md#경계-위험의-별도-대조) |
| **확인: 선행 표본 분석** | 7편의 구조 지도·대표 장면, 작가별 4개 검토 완료. 작가 비교·입력 계약 교차 검토와 개발 파일럿 1건 수락. | [작가 연구](../research/author-study/README.md), [집필 명세 연구](../research/writing-spec-v0-1/README.md) |
| **미실행** | 첫 50화의 의미 분석 카드 350건, 실제 Gemma 학습, 운영 PostgreSQL·pgvector, 실제 역사 설계·잠금·공개 경로. | [코퍼스 안내](../research/chapter-ingestion/README.md), [실행계획 §1](../plans/20260918-current-system-execution-plan-v0-1.md#1-출발점) |

다음 검토는 두 갈래다. 첫 50화 분석은 [실행 전 방법안](../plans/20260924-first-50-episode-analysis-method.md)의 경계·카드·t시점 원장·Sol 검수 조건을 참고한다. 원문 적재는 이미 끝났지만 350화 의미 분석과 후속 분석 테이블은 미실행이다. 작품별 공식 번호 불명은 보류 상태로 남긴다. 작가 비교에서는 사용자가 아직 선택하지 않은 취향과 학습 원문·구간을 확정한 뒤 split을 고정한다. [집필 기준 초안](../research/writing-spec-v0-1/writing-criteria-draft.md#먼저-읽을-1쪽-결정할-것), [현행 실행계획 §5](../plans/20260918-current-system-execution-plan-v0-1.md#5-바로-시작할-첫-작업)

**B1 설계 미결정:** 부족·충돌·미확인 사항의 승인 조건, 부분 잠금과 선행 조건, 서술되지 않은 사건의 확정, 외부 게시 중 계획 변경의 복구. [실행계획 §4](../plans/20260918-current-system-execution-plan-v0-1.md#4-b1에서-결정할-네-가지-규칙). 첫 50 분석용 SQLite의 분석 스키마·백업·revision 등도 계획상의 미결정이며, 현재 원문 코퍼스 스키마와 동일하다고 가정하지 않는다. [분석 적재 계획](../plans/20260924-first-50-sqlite-storage.md)

**옛 설계 충돌:** [상세 아키텍처 v5](../20260914-novel-factory-architecture-v5.md)의 SQLite 우선·작품별 운영 파일·PostgreSQL 후순위 표현은 [핵심 설계 머리말과 §6](../systems/README.md#6-교체-가능한-기술-변하지-않는-계약)로 대체한다. 과거 계획의 ‘10–20편’ 수량 우선, HelixDB, 인과 수치 점수, 중간 사건 권고 취급도 [현행 실행계획 §2–3](../plans/20260918-current-system-execution-plan-v0-1.md#2-과거-플랜에서-현재-작업으로-바꾸는-기준)과 다르다. 상세 문서를 수정할 때 이 대체 관계를 먼저 확인한다.

**역사 지식 조사 — 계획 검토 수락:** `wiki-dump/`의 텍스트 XML bzip2 19개 다운로드는 사용자 확인 및 로컬 목록·총량 대조가 있다. 공식 배포 manifest·checksum·압축/파싱 무결성은 아직 검증하지 않았다. [역사 SoT·온톨로지 조사 계획](../plans/20260924-history-sot-ontology-research-plan.md)은 [독립 검토 수락](../research/20260924-history-sot-ontology-plan-review.md)을 받았으나 R0–R5 조사 결론·실험·PostgreSQL 구축은 미실행이다. [사전 출처 지도](../research/20260924-history-sot-ontology-source-map.md)

**앵커 이음새 설계 — 문서 완료·독립 검토 수락:** 사용자 합의와 미채택 제안을 [정본·개변 역사 온톨로지 문서](../systems/20260924-history-ontology-and-anchor-bridges.md)에 정리했다. 다른 Sol이 수정본을 수락했으며 검토 범위는 [현재 체크포인트](../harness/current-checkpoint.md)에 있다. 온톨로지 적재, 작품 개변 DB, 인과 계산기, 앵커 연결 생성, 실제 역사 복원 평가는 미실행이다.

**최신 통합판 — 독립 검토 수락:** 사용자 확정인 재미 우선·역사 전문가도 납득할 개연성, SOTA 역사 경로/Backfilling과 Gemma 문체 집필의 역할을 [핵심 설계](../systems/README.md)와 [이음새 문서](../systems/20260924-history-ontology-and-anchor-bridges.md)에 반영했다. 질문 기반 온톨로지 항목 도출과 세부 평가 방법은 제안으로 남겼다. 다른 Sol이 이번 갱신의 확정/제안 경계와 보완 루프를 검토·수락했다. 구축·학습·복원 평가는 미실행이다. [현재 체크포인트](../harness/current-checkpoint.md)
