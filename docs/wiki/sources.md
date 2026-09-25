# 문서 출처 색인

이 색인은 문서의 출처·상태·권위를 구분해 위키 작성 시 원자료를 다시 찾도록 돕는다. 최초 범위는 `docs/**/*.md`, `plan/**/*.md`, 그리고 `tools/novel_corpus/README.md`, `toy-tune/README.md`, `webnovel-writer/{README.md,docs/README.md}`였고 당시 **83개 Markdown 원자료**를 제목·경로·상태 표기를 중심으로 분류했다. 이후 추가된 하네스 문서는 아래 별도 절에 등록한다. 새로 작성되는 `docs/wiki/**`와 탐색 진입점인 `docs/README.md`는 원자료 인벤토리에서 제외한다. 아래 목적 요약과 상태는 색인 작업에서 확인한 범위만 기술하며, 문서 전문을 모두 정독했다는 뜻은 아니다. 개별 항목은 제목·경로·메타데이터 기준으로 포함한 것도 있다.

## 읽기 우선순위와 권위

1. 현재 규칙·기술 기준은 [핵심 시스템 설계](../systems/README.md)가 기본 기준이며, 문서 자체도 상세 문서와의 충돌 시 우선한다고 명시한다. 다만 사용자의 최신 명시 결정은 해당 README와 이 색인보다 우선한다. 목표 설계와 구현 상태를 구별한다.
2. 지금의 작업 순서·완료 현황은 [계획 안내](../plans/README.md)와 연결된 통합 실행계획을 읽는다. 실행계획은 제안 및 보고된 상태이며, 실제 구현 근거와 혼동하지 않는다. 2026-09-24 첫 50화 관련 문서도 서로 구분한다: 통합 계획과 SQLite 계획은 **원문 코퍼스 적재 완료를 반영한 후속 350화 의미 분석 계획**이며, 의미 분석 레코드는 미실행이다. 분석 방법 문서는 계속 실행 전 계획이다.
3. 완료·검증 여부는 해당 실행·검토 결과와 도구 README에서 확인한다. 계획의 완료 조건, 오래된 파일의 “완료” 표기, 날짜만으로 현행 결정이나 구현을 승격하지 않는다.
4. 분석 문서는 표본·검토 범위를 보존하는 연구 결과다. 사용자 승인 전 초안은 기준으로 확정하지 않는다. 레거시·과거 계획은 당시 의도에 대한 참고다.
5. Webnovel Writer는 별도 참고 작품/도구 자료다. 그 설계·장르 지침은 이 프로젝트의 기준이나 현재 구현으로 간주하지 않는다.

**독해 상태:** 표의 83개 항목은 모두 목록화했지만 전부 정독한 것은 아니다. 이번 인벤토리에서 본문을 직접 확인한 범위는 `docs/systems/README.md`의 권위·저장·위키 규칙, `docs/plans/README.md`, `plan/README.md`, 현행 통합 실행계획의 상태·순서 절, `docs/research/chapter-ingestion/README.md`, 원문 보관 README, 코퍼스 README, `toy-tune/README.md`의 안내·상태다. 그 밖의 항목은 제목·경로와 폴더/상태 메타데이터를 기준으로 등록했으며, 주제 위키에 반영할 때 원문을 열어 주장별 근거와 상태를 확인해야 한다.

**확인된 충돌:** 현행 저장 기준은 중앙 PostgreSQL + pgvector이며 SQLite는 토이 실험·오프라인 반출·아카이브 후보, HelixDB는 운영하지 않는 것으로 [핵심 시스템 설계](../systems/README.md) §6에 명시돼 있다. `docs/plans/README.md`와 [현행 통합 실행계획](../plans/20260918-current-system-execution-plan-v0-1.md)도 9월 초기 계획, 과거 HelixDB/SQLite 운영 전제를 이 기준으로 대체한다고 안내한다. 그러므로 [4월 통합 설계](../260417%20%E1%84%90%E1%85%A9%E1%86%BC%E1%84%92%E1%85%A1%E1%86%B8%20%E1%84%8B%E1%85%A1%E1%84%8F%E1%85%B5%E1%84%90%E1%85%A6%E1%86%A8%E1%84%8E%E1%85%A5%20%E1%84%89%E1%85%A5%E1%86%AF%E1%84%80%E1%85%A8%E1%84%89%E1%85%A5.md), [legacy DB 설계](../legacy/Local%20PostgreSQL%20SOT%20DB%20%EC%84%A4%EA%B3%84%EC%84%9C.md), [과거 플랜 저장 안내](../../plan/README.md)의 당시 기술·완료 표기는 역사적 맥락으로만 읽는다. 날짜만으로 현행 상태를 추론하지 않는다.

## 문서 목록

### Codex 프로젝트 하네스 — 2026-09-24 추가

이 문서는 작업을 배정하고 재개하는 운영 지침이다. 시스템 설계·실행 검토·사용자 승인 원장을 대체하지 않는다. 역할 파일은 [하네스 안내](../harness/README.md#codex-설정의-범위)에 연결한다.

| 문서 | 목적·출처 상태 |
|---|---|
| [README.md](../harness/README.md) — Astra 오케스트레이션 하네스 | 역할·작업 분류·시작/완료/재개 절차. 현재 운영 지침. |
| [session-decisions.md](../harness/session-decisions.md) — 세션 하네스 결정 | 최신 대화에서 지속할 사용자 결정과 확인 상태. 승인 원장 아님. |
| [task-template.md](../harness/task-template.md) — 작업 카드 양식 | 새 배정의 범위·소유권·검증·문맥을 적는 양식. |
| [current-checkpoint.md](../harness/current-checkpoint.md) — 현재 체크포인트 | 현행 재개 지점과 미실행 상태. 실행 결과는 연결된 기록에서 확인. |
| [review.md](../harness/review.md) — Codex 프로젝트 하네스 독립 검토 | 별도 Sol의 문서·정적 설정 검토 수락. 실제 역할 선택·모델 실행 수락 아님. |

### 핵심 설계와 현행 기준

2026-09-24 추가: [정본·개변 역사 온톨로지와 앵커 이음새](../systems/20260924-history-ontology-and-anchor-bridges.md)는 최신 사용자 문답의 목표·작동 전제와 아직 채택되지 않은 구간·평가 보완안을 구분한 설계 정리다. [핵심 시스템 설계](../systems/README.md)의 승인·저장 규범이나 실제 구현 상태를 대체하지 않는다. 문서 완료·독립 검토 수락 상태([체크포인트](../harness/current-checkpoint.md))이며 온톨로지·계산기·복원 평가 실행 기록은 아니다.

같은 문서는 이후 사용자 확정인 **재미 우선·전문가도 납득할 개연성**, SOTA의 역사 경로·Backfilling과 Gemma의 본문 집필 역할, 질문 기반 항목 도출 제안을 통합하도록 갱신했다. 이번 갱신도 다른 Sol이 [독립 검토 수락](../harness/current-checkpoint.md)했다. 이는 온톨로지 구축·복원 성능의 수락이 아니다.

현재 규칙의 최우선 원천은 systems/README.md. 나머지는 상세 의미 계약·환경 인벤토리 또는 명시적으로 과거 인덱스/스키마다.

| 문서 | 목적·출처 상태 |
|---|---|
| [20260914-novel-factory-architecture-v5.md](../20260914-novel-factory-architecture-v5.md) — 대체역사 설계·집필 공장 통합 아키텍처 v5 | 제목·경로 기준 참고; 적용 상태는 문서 안의 명시 상태 확인. |
| [alt_history_factory_index_v3.md](../alt_history_factory_index_v3.md) — 대체역사 AI 팩토리 프로젝트 인덱스 v3 | 과거 설계 인덱스; 본문에 현행 기준이 v5라고 명시. |
| [original_rdb_schema_v1.md](../original_rdb_schema_v1.md) — Original RDB 스키마 설계서 v1 | 제목·경로 기준 참고; 적용 상태는 문서 안의 명시 상태 확인. |
| [README.md](../systems/README.md) — 대체역사 AI 공장 — 핵심 시스템 설계 | 핵심 규칙·기술 선택. 최상위 설계 기준; 최우선으로 읽음. |
| [system-setup.md](../systems/system-setup.md) — 🖥️ 서버 관리 인벤토리 (2026-04-16 기준) | 제목·경로 기준 참고; 적용 상태는 문서 안의 명시 상태 확인. |

### 현재 실행 순서·계획

2026-09-24 추가: [역사 SoT·온톨로지 조사 계획](../plans/20260924-history-sot-ontology-research-plan.md)은 기존 영어 위키백과·Granite 계획의 조사 단계 보완이다. [독립 검토 수락](../research/20260924-history-sot-ontology-plan-review.md) 상태이며 조사 실행/실험 결과가 아니다. [사전 공식 출처 지도](../research/20260924-history-sot-ontology-source-map.md)는 19개 로컬 XML 메타데이터와 기술 문서의 좁은 사전 조사로, checksum·본문 검증이나 채택 결론이 아니다.

현재 실행계획은 순서 제안과 명시된 상태 기록. 2026-09-24 첫 50 분석 관련 자료는 계획이며 실행 결과가 아니다. 9/8·9/11 초기 계획은 역사적 의도다.

| 문서 | 목적·출처 상태 |
|---|---|
| [20260908-gemma4-finetuning-plan-v0-1.md](../plans/20260908-gemma4-finetuning-plan-v0-1.md) — Gemma 4 Fine-tuning Plan v0.1 | 제목·경로 기준 참고; 적용 상태는 문서 안의 명시 상태 확인. |
| [20260911-gemma4-toy-finetuning-practice-plan-v0-1.md](../plans/20260911-gemma4-toy-finetuning-practice-plan-v0-1.md) — Gemma 4 토이 파인튜닝 연습 액션플랜 v0.1 | 제목·경로 기준 참고; 적용 상태는 문서 안의 명시 상태 확인. |
| [20260914-enwiki-granite-knowledge-ingestion-plan-v0-1.md](../plans/20260914-enwiki-granite-knowledge-ingestion-plan-v0-1.md) — 영어 위키백과·Granite 지식 구축 계획 v0.1 | 제목·경로 기준 참고; 적용 상태는 문서 안의 명시 상태 확인. |
| [20260914-munche-style-embedding-integration-plan-v0-1.md](../plans/20260914-munche-style-embedding-integration-plan-v0-1.md) — Munche 문체 임베딩 통합 계획 v0.1 | 제목·경로 기준 참고; 적용 상태는 문서 안의 명시 상태 확인. |
| [20260914-toy-tune-architecture-and-backendai-bootstrap-plan-v0-1.md](../plans/20260914-toy-tune-architecture-and-backendai-bootstrap-plan-v0-1.md) — toy-tune 클린 아키텍처 및 실행 환경 구축 계획 v0.1 | 제목·경로 기준 참고; 적용 상태는 문서 안의 명시 상태 확인. |
| [20260918-current-system-execution-plan-v0-1.md](../plans/20260918-current-system-execution-plan-v0-1.md) — 현행 시스템 통합 실행계획 v0.1 | 현행 설계의 실행 순서·상태 보고. 제안과 실제 구현을 구별. |
| [20260924-first-50-analysis-and-ingestion-plan.md](../plans/20260924-first-50-analysis-and-ingestion-plan.md) — 보유 7편 1–50화 회차별 분석·SQLite 적재 통합 계획 | 원문 코퍼스 적재 완료 상태를 반영한 후속 350화 의미 분석·저장 계획; 의미 분석은 미실행. |
| [20260924-first-50-episode-analysis-method.md](../plans/20260924-first-50-episode-analysis-method.md) — 보유 7편의 1–50화 전수 분석·SQLite 적재 방법 — 실행 전 계획 | 의미 분석·저장 방법의 실행 전 계획; 원문 코퍼스 적재 완료와 구별하며 의미 분석은 미실행. |
| [20260924-first-50-sqlite-storage.md](../plans/20260924-first-50-sqlite-storage.md) — 첫 50화 분석 코퍼스의 SQLite 저장 계획 | 원문 코퍼스 적재 완료 상태를 반영한 후속 350화 의미 분석·저장 계획; 의미 분석은 미실행. |
| [README.md](../plans/README.md) — 현재 실행 계획 안내 | 현행 실행계획 네비게이션; 통합 실행 순서로 연결. |

### 실행·조사 보고서와 기술 검토

조사 근거·판단을 보관한다. 조사 시점의 추천·모델·버전 정보는 현행 규칙보다 우선하지 않는다.

| 문서 | 목적·출처 상태 |
|---|---|
| [20260908-alternate-history-sqlite-canon-report-v0-1.md](../reports/20260908-alternate-history-sqlite-canon-report-v0-1.md) — 대체역사 웹소설 공장 SQLite 정사 구조 검토 보고서 v0.1 | 조사/검토 보고서; 명시된 조사 결과·조건의 근거. |
| [20260908-gemma4-31b-heretic-style-finetuning-deep-research-v0-2.md](../reports/20260908-gemma4-31b-heretic-style-finetuning-deep-research-v0-2.md) — Gemma 4 31B Heretic 웹소설 문체 파인튜닝 심층 조사 v0.2 | 조사/검토 보고서; 명시된 조사 결과·조건의 근거. |
| [20260908-qwen38-27b-h200-finetuning-feasibility-report-v0-1.md](../reports/20260908-qwen38-27b-h200-finetuning-feasibility-report-v0-1.md) — Qwen3.8-27B Uncensored GGUF H200 파인튜닝 타당성 검토 v0.1 | 조사/검토 보고서; 명시된 조사 결과·조건의 근거. |

### 실제 원문에 대한 분석·경계 기록·집필 기준 연구

표본 분석·독립 검토·경계 판정·프로토콜 및 초안. 표본을 전편 독해로 일반화하지 않고, 초안/보류/충돌 상태는 각 문서의 명시 상태를 따른다.

| 문서 | 목적·출처 상태 |
|---|---|
| [20260924-bestseller-selection.md](../research/20260924-bestseller-selection.md) — 보유 소설 중 베스트셀러·흥행작 분석 후보 | 제목·경로 기준 참고; 적용 상태는 문서 안의 명시 상태 확인. |
| [20260924-owned-novels-catalog.md](../research/20260924-owned-novels-catalog.md) — 보유 소설 목록 | 제목·경로 기준 참고; 적용 상태는 문서 안의 명시 상태 확인. |
| [README.md](../research/author-study/README.md) — 선호 작가별 소설 분석 | 선호 작가 4명·보유 7편 분석의 범위와 진행 현황. |
| [analysis-contract.md](../research/author-study/analysis-contract.md) — 작품 분석과 작가 검토 작업 지침 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [author-profile.md](../research/author-study/ganda-left/author-profile.md) — 간다왼쪽: 보유작 한 편에서 얻은 집필 기법 후보 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [preflight.md](../research/author-study/ganda-left/preflight.md) — 간다왼쪽 작가 분석 사전 점검 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [review.md](../research/author-study/ganda-left/review.md) — 간다왼쪽 작품 검토 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [1588.md](../research/author-study/ganda-left/works/1588.md) — 《1588 샤인머스캣으로 귀농 왔더니 신대륙》 작품 분석 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [author-profile.md](../research/author-study/garlic-snack/author-profile.md) — 마늘맛스낵 — 보유 2편의 표본 기반 작법 프로필 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [preflight.md](../research/author-study/garlic-snack/preflight.md) — 마늘맛스낵 작가 분석 사전 점검 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [review.md](../research/author-study/garlic-snack/review.md) — 마늘맛스낵 작품별 Sol 검토 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [goryeo.md](../research/author-study/garlic-snack/works/goryeo.md) — 《고려, 신대륙에 떨어지다》 — 마늘맛스낵 작품 분석 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [poland.md](../research/author-study/garlic-snack/works/poland.md) — 《폴란드 여왕 키우기》 표본 기반 분석 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [author-profile.md](../research/author-study/myeongwon/author-profile.md) — 명원: 보유작 한 편에서 관찰한 기법 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [preflight.md](../research/author-study/myeongwon/preflight.md) — 명원 작가 분석 사전 점검 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [review.md](../research/author-study/myeongwon/review.md) — 명원 작품 분석 검토 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [fair-trade.md](../research/author-study/myeongwon/works/fair-trade.md) — 명원 작품 분석: 《대영제국 선비의 공정무역》 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [author-profile.md](../research/author-study/richerlen/author-profile.md) — 리첼렌: 세 보유작의 표본에서 본 작법 프로필 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [preflight.md](../research/author-study/richerlen/preflight.md) — 리첼렌 작가 연구 사전 점검 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [review.md](../research/author-study/richerlen/review.md) — 리첼렌 작품 분석 검토 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [source-offset-notes.md](../research/author-study/richerlen/source-offset-notes.md) — 원문 복사와 표본 위치 확인 메모 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [gogjong.md](../research/author-study/richerlen/works/gogjong.md) — 리첼렌 작품 연구: 《폭군 고종대왕 일대기》 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [mustache.md](../research/author-study/richerlen/works/mustache.md) — 《초대 콧수염 대마왕이 되었다》 — 리첼렌 작가 연구 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [sunjong.md](../research/author-study/richerlen/works/sunjong.md) — 리첼렌, 《성군 순종대왕 일대기》 표본 분석 | 표본 기반 작품/작가 분석 또는 검토 기록; 분석 범위 한정. |
| [1588-boundaries.md](../research/chapter-ingestion/1588-boundaries.md) — 1588 원문 경계 검수 | 작품별 원문 경계 조사·검수 결과; 공식 번호 미확정은 보류로 유지. |
| [README.md](../research/chapter-ingestion/README.md) — 보유 소설 7편의 원문·경계 SQLite | 실제 원문 적재 및 경계 현황 요약; 경계 메모/검토 문서가 세부 근거. |
| [fair-trade-boundaries.md](../research/chapter-ingestion/fair-trade-boundaries.md) — 공정무역 원문 경계 검토 | 작품별 원문 경계 조사·검수 결과; 공식 번호 미확정은 보류로 유지. |
| [gogjong-boundaries.md](../research/chapter-ingestion/gogjong-boundaries.md) — 폭군 고종대왕 일대기 원문 경계 메모 | 작품별 원문 경계 조사·검수 결과; 공식 번호 미확정은 보류로 유지. |
| [goryeo-boundaries.md](../research/chapter-ingestion/goryeo-boundaries.md) — 고려, 신대륙에 떨어지다 — 원문 경계 인덱스 | 작품별 원문 경계 조사·검수 결과; 공식 번호 미확정은 보류로 유지. |
| [mustache-boundaries.md](../research/chapter-ingestion/mustache-boundaries.md) — 《초대 콧수염 대마왕이 되었다》 경계 점검 | 작품별 원문 경계 조사·검수 결과; 공식 번호 미확정은 보류로 유지. |
| [poland-boundaries.md](../research/chapter-ingestion/poland-boundaries.md) — 폴란드 여왕 키우기 원문 경계 검토 | 작품별 원문 경계 조사·검수 결과; 공식 번호 미확정은 보류로 유지. |
| [review.md](../research/chapter-ingestion/review.md) — 7편 원문 SQLite 적재 독립 검토 | 작품별 원문 경계 조사·검수 결과; 공식 번호 미확정은 보류로 유지. |
| [sunjong-boundaries.md](../research/chapter-ingestion/sunjong-boundaries.md) — 《성군 순종대왕 일대기》 원문 경계 점검 | 작품별 원문 경계 조사·검수 결과; 공식 번호 미확정은 보류로 유지. |
| [README.md](../research/writing-spec-v0-1/README.md) — 작가 비교에서 집필 기준·입력 역설계로 | 비교·집필 기준·입력 계약의 작성/검토 상태 안내; 사용자 채택 전 초안 포함. |
| [author-comparison.md](../research/writing-spec-v0-1/author-comparison.md) — 네 선호 작가의 표본 기반 작법 비교 — 선택 전 자료 | 작가 비교·초안·입력 역구성 연구/검토; 승인된 기준과 구별. |
| [comparison-review.md](../research/writing-spec-v0-1/comparison-review.md) — 작가 비교·집필 기준 초안 독립 검토 | 작가 비교·초안·입력 역구성 연구/검토; 승인된 기준과 구별. |
| [source-audit.md](../research/writing-spec-v0-1/pilot-1588/source-audit.md) — 1588 파일럿 후보 원문 감사 | 작가 비교·초안·입력 역구성 연구/검토; 승인된 기준과 구별. |
| [reverse-candidate-policy.md](../research/writing-spec-v0-1/reverse-candidate-policy.md) — 역설계 학습 후보 선정 정책 v0.1 | 작가 비교·초안·입력 역구성 연구/검토; 승인된 기준과 구별. |
| [reverse-input-contract.md](../research/writing-spec-v0-1/reverse-input-contract.md) — 기존 원문을 정답으로 삼는 역설계 입력 계약 v0.1 | 작가 비교·초안·입력 역구성 연구/검토; 승인된 기준과 구별. |
| [reverse-review.md](../research/writing-spec-v0-1/reverse-review.md) — 입력 역구성 계약 교차 검토 — 진행 기록 | 작가 비교·초안·입력 역구성 연구/검토; 승인된 기준과 구별. |
| [writing-criteria-draft.md](../research/writing-spec-v0-1/writing-criteria-draft.md) — 집필 기준 초안 v0.1 — 사용자 선택용 | 작가 비교·초안·입력 역구성 연구/검토; 승인된 기준과 구별. |

### 원문 저장·코퍼스 도구 메타데이터와 안내

원문 보존 위치·hash 및 코퍼스 사용·상태를 가리키는 메타데이터. 원문 본문·DB 본문은 이 색인에서 읽거나 복제하지 않는다.

| 문서 | 목적·출처 상태 |
|---|---|
| [README.md](../references/README.md) — 소설 원문 보관 | 원문 사본 7편의 보관 메타데이터와 분석 링크; 본문 열람 대상 아님. |
| [README.md](../../tools/novel_corpus/README.md) — 원문 코퍼스 SQLite | 원문 SQLite 적재/검증 도구 안내와 보존 의미; DB 본문 메타데이터만 참조. |

### 과거 계획 보관

plan/README.md에서 현행 기준으로 쓰지 말라고 한 2026년 3~4월 자료. 구체 요구는 현재 완료 조건과 대조한 뒤에만 재사용한다.

| 문서 | 목적·출처 상태 |
|---|---|
| [260320_webnovel-project-setup.md](../../plan/260320_webnovel-project-setup.md) — 칸글 소설 프로젝트 작업 플랜 | 2026년 3–4월 당시 플랜·검토; 현행 기준 아님. |
| [260413 개발 플랜 및 데이터 명세서.md](../../plan/260413%20%E1%84%80%E1%85%A2%E1%84%87%E1%85%A1%E1%86%AF%20%E1%84%91%E1%85%B3%E1%86%AF%E1%84%85%E1%85%A2%E1%86%AB%20%E1%84%86%E1%85%B5%E1%86%BE%20%E1%84%83%E1%85%A6%E1%84%8B%E1%85%B5%E1%84%90%E1%85%A5%20%E1%84%86%E1%85%A7%E1%86%BC%E1%84%89%E1%85%A6%E1%84%89%E1%85%A5.md) — **자동 집필 RAG 시스템 개발 플랜 및 데이터 명세서** | 2026년 3–4월 당시 플랜·검토; 현행 기준 아님. |
| [260413_v2.1_재구축_플랜순서 .md](../../plan/260413_v2.1_%EC%9E%AC%EA%B5%AC%EC%B6%95_%ED%94%8C%EB%9E%9C%EC%88%9C%EC%84%9C%20.md) — 재구축 플랜 순서 (Greenfield Master Index) | 2026년 3–4월 당시 플랜·검토; 현행 기준 아님. |
| [260413_v2_클린코드_피드백_검토.md](../../plan/260413_v2_%ED%81%B4%EB%A6%B0%EC%BD%94%EB%93%9C_%ED%94%BC%EB%93%9C%EB%B0%B1_%EA%B2%80%ED%86%A0.md) — v2 플랜에 대한 클린코드 피드백 — 검토 및 반영안 | 2026년 3–4월 당시 플랜·검토; 현행 기준 아님. |
| [260413_개발플랜_냉정한_피드백.md](../../plan/260413_%EA%B0%9C%EB%B0%9C%ED%94%8C%EB%9E%9C_%EB%83%89%EC%A0%95%ED%95%9C_%ED%94%BC%EB%93%9C%EB%B0%B1.md) — 개발 플랜 냉정한 피드백: 대체역사 웹소설 RAG AI | 2026년 3–4월 당시 플랜·검토; 현행 기준 아님. |
| [260413_리팩토링_플랜순서.md](../../plan/260413_%EB%A6%AC%ED%8C%A9%ED%86%A0%EB%A7%81_%ED%94%8C%EB%9E%9C%EC%88%9C%EC%84%9C.md) — 리팩토링 플랜 순서 (Master Index) | 2026년 3–4월 당시 플랜·검토; 현행 기준 아님. |
| [260414_v1_v2_기능비교.md](../../plan/260414_v1_v2_%EA%B8%B0%EB%8A%A5%EB%B9%84%EA%B5%90.md) — v1 ↔ v2 기능 변화 비교 | 2026년 3–4월 당시 플랜·검토; 현행 기준 아님. |
| [260418_strategy_layer_작성플랜.md](../../plan/260418_strategy_layer_%EC%9E%91%EC%84%B1%ED%94%8C%EB%9E%9C.md) — 03_strategy_layer_260418.md 작성 플랜 | 2026년 3–4월 당시 플랜·검토; 현행 기준 아님. |
| [260418_통합설계서_v3_v4.1_정리플랜.md](../../plan/260418_%ED%86%B5%ED%95%A9%EC%84%A4%EA%B3%84%EC%84%9C_v3_v4.1_%EC%A0%95%EB%A6%AC%ED%94%8C%EB%9E%9C.md) — v3 인덱스 vs v4.1 통합 설계서 불일치 정리 플랜 | 2026년 3–4월 당시 플랜·검토; 현행 기준 아님. |
| [README.md](../../plan/README.md) — 과거 플랜 보관 | 과거 플랜 보관 정책·현행 참조 링크. |
| [260413_v2_재구축_플랜순서.md](../../plan/legacy/260413_v2_%EC%9E%AC%EA%B5%AC%EC%B6%95_%ED%94%8C%EB%9E%9C%EC%88%9C%EC%84%9C.md) — 재구축 플랜 순서 (Greenfield Master Index) | 2026년 3–4월 당시 플랜·검토; 현행 기준 아님. |

### 별도 Webnovel Writer 참고자료

별도 프로젝트 README와 문서 네비게이션. 해당 도구의 기능·설계 참고이지 이 프로젝트의 권위 문서가 아니다.

| 문서 | 목적·출처 상태 |
|---|---|
| [README.md](../../webnovel-writer/README.md) — Webnovel Writer | 별도 저장소 프로젝트 개요 및 사용법. |
| [README.md](../../webnovel-writer/docs/README.md) — 문서 센터 | 별도 저장소 프로젝트 개요 및 사용법. |

### 과거 설계 문서

legacy/는 과거 보관 자료. 4월 설계 문서는 현행 아키텍처 v5와 systems/README에 종속되며, 번역 플랜은 별도 제안이다.

| 문서 | 목적·출처 상태 |
|---|---|
| [260417 역설계 아키텍처 설계서.md](../260417%20%E1%84%8B%E1%85%A7%E1%86%A8%E1%84%89%E1%85%A5%E1%86%AF%E1%84%80%E1%85%A8%20%E1%84%8B%E1%85%A1%E1%84%8F%E1%85%B5%E1%84%90%E1%85%A6%E1%86%A8%E1%84%8E%E1%85%A5%20%E1%84%89%E1%85%A5%E1%86%AF%E1%84%80%E1%85%A8%E1%84%89%E1%85%A5.md) — **아키텍처 핵심: 역방향 인과율 추론 및 역사표 창조 (Backfilling)** | 제목·경로 기준 참고; 적용 상태는 문서 안의 명시 상태 확인. |
| [260417 통합 아키텍처 설계서.md](../260417%20%E1%84%90%E1%85%A9%E1%86%BC%E1%84%92%E1%85%A1%E1%86%B8%20%E1%84%8B%E1%85%A1%E1%84%8F%E1%85%B5%E1%84%90%E1%85%A6%E1%86%A8%E1%84%8E%E1%85%A5%20%E1%84%89%E1%85%A5%E1%86%AF%E1%84%80%E1%85%A8%E1%84%89%E1%85%A5.md) — **대체역사 AI 팩토리 통합 아키텍처 설계서 (v4.1: 로컬 분산 배포형 \- HelixDB SQ 최적화)** | 제목·경로 기준 참고; 적용 상태는 문서 안의 명시 상태 확인. |
| [260504_웹소설 자동 집필 시스템 아키텍처 연구.md](../260504_%E1%84%8B%E1%85%B0%E1%86%B8%E1%84%89%E1%85%A9%E1%84%89%E1%85%A5%E1%86%AF%20%E1%84%8C%E1%85%A1%E1%84%83%E1%85%A9%E1%86%BC%20%E1%84%8C%E1%85%B5%E1%86%B8%E1%84%91%E1%85%B5%E1%86%AF%20%E1%84%89%E1%85%B5%E1%84%89%E1%85%B3%E1%84%90%E1%85%A6%E1%86%B7%20%E1%84%8B%E1%85%A1%E1%84%8F%E1%85%B5%E1%84%90%E1%85%A6%E1%86%A8%E1%84%8E%E1%85%A5%20%E1%84%8B%E1%85%A7%E1%86%AB%E1%84%80%E1%85%AE.md) — **대체역사 웹소설 자동 집필을 위한 AI 팩토리 통합 아키텍처 및 최신 설계 방향성 검증 보고서** | 제목·경로 기준 참고; 적용 상태는 문서 안의 명시 상태 확인. |
| [chinese-to-korean-translation-plan.md](../chinese-to-korean-translation-plan.md) — webnovel-writer 중국어→영어/한국어 번역 플랜 | 제목·경로 기준 참고; 적용 상태는 문서 안의 명시 상태 확인. |
| [Local PostgreSQL SOT DB 설계서.md](../legacy/Local%20PostgreSQL%20SOT%20DB%20%EC%84%A4%EA%B3%84%EC%84%9C.md) — **Phase 1: 로컬 PostgreSQL 기반 SOT 아키텍처 및 스키마 (Dual-DB 적용)** | 구버전 설계/파이프라인; 현재 설계보다 낮은 권위. |
| [Training Data Pipeline.md](../legacy/Training%20Data%20Pipeline.md) — **대체역사물 파인튜닝을 위한 데이터 역산(Reverse Engineering) 파이프라인** | 구버전 설계/파이프라인; 현재 설계보다 낮은 권위. |
| [역설계 아키텍처 설계서.md](../legacy/%EC%97%AD%EC%84%A4%EA%B3%84%20%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98%20%EC%84%A4%EA%B3%84%EC%84%9C.md) — **아키텍처 핵심: 역방향 인과율 추론 및 역사표 창조 (Backfilling)** | 구버전 설계/파이프라인; 현재 설계보다 낮은 권위. |
| [통합 아키텍처 설계서.md](../legacy/%ED%86%B5%ED%95%A9%20%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98%20%EC%84%A4%EA%B3%84%EC%84%9C.md) — **대체역사 AI 팩토리 통합 아키텍처 설계서 (v4.1: 로컬 분산 배포형 \- HelixDB SQ 최적화)** | 구버전 설계/파이프라인; 현재 설계보다 낮은 권위. |

### 시스템 인벤토리 및 기타 참고

독립적으로 확인할 운영 메모·기타 문서. 목적과 적용 범위는 각 문서 본문에서 확인한다.

| 문서 | 목적·출처 상태 |
|---|---|
| [README.md](../../toy-tune/README.md) — toy-tune | 현재 코드 범위와 미구현 경계 요약; 학습 완료로 오독 금지. |

## 확인된 상태와 미확인 사항

- 원문 사본 메타데이터는 [보관 목록](../references/README.md)과 [manifest](../references/manifest.json)에 있다. 안내 문서가 보고한 7편 합계는 61,533,769바이트다. SQLite 경로는 `data/analysis/novel-corpus.sqlite3`; 본문 내용은 색인 작성에서 읽지 않았다.
- [원문·경계 현황](../research/chapter-ingestion/README.md)에 따르면 현재 7편 3,292구간이며 첫 50화 목표 350개 중 번호 경계 249개가 확정됐다. 고종 0/50, 고려 0/50은 공식 번호 미확정이며, 콧수염은 49/50이고 41편 표제 중복 충돌 1건이 남아 있다. 의미 분석 카드 350건 작성·적재는 미실행이다.
- 해당 수치는 chapter-ingestion README와 개별 경계·검토 문서의 상태를 반영한 인벤토리 기록이다. 본문 분석이나 DB 재검증을 이번 색인 작업에서 수행한 것은 아니다.
- `docs/wiki/`의 주제별 종합 문서는 이 출처 목록에서 다루지 않는다. 개별 주장·설계·실험을 종합할 때 위 권위 순서와 원자료 링크를 함께 유지한다.
