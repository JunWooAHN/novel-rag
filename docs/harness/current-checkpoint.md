---
category_id: document-harness
lineage_id: legacy-40925fad-cbff-589b-9799-6cc13abe142b
document_id: doc-18b24822-1b5b-41e6-a540-bf54c6623625
parent_lineage_id: null
abstract: 중단된 작업의 산출물과 다음 행동을 확인할 때 읽는다.
version: 0.0.5
created_at: null
updated_at: '2026-09-25T01:13:36Z'
tags:
- 하네스
---
# 현재 체크포인트

기준일: 2026-09-25. 현재 작업은 아래 **문서 생애주기 하네스 구현**이다. 역사 온톨로지 문서 정리와 이전 작업 카드는 아래에 보존한다. 이 문서는 재개 인덱스이며 소설 분석·학습·작품 캐논 실행 승인이 아니다.

## 현재 작업 카드 — `DOC-HARNESS-IMPLEMENT-20260925`

| 항목 | 실제 기록 |
|---|---|
| 요청·권한 | 사용자가 문서 생애주기 계획 구현을 요청. 전용 CLI·SQLite·의미 검증·초기 비파괴 적재까지 허용하며 소설 원문 DB, 전체 문서 일괄 개정, Git commit은 범위 밖. |
| 담당·소유 | Astra 루트 조율, Sol 단일 구현·DB writer. Luna는 [초기 manifest](../../data/document_harness/initial-import-manifest.json)와 DB 읽기 점검, 다른 Sol은 독립 코드 검토. |
| 산출 | [CLI와 사용법](../../tools/document_harness/README.md), [설계·상태](document-lifecycle.md), `data/document_harness/documents.sqlite3`와 초기 manifest. 2026-09-25 초기 `docs/`·`plan/` Markdown 99개·1,178,728 bytes를 원본 불변의 legacy·`canon=false`로 적재. 이후 하네스 관리판 5개를 명시 채택했고 현재 DB는 총 108판이다. 기존 인벤토리 대비 소스 해시 변경 0건. |
| 검증 | Python 단위 테스트 7개 통과. 초기 DB `integrity_check=ok`, 문서판 99, `canon=1` 0, FTS 99. Luna가 manifest 99개 경로·크기·SHA-256과 DB 본문 재해시 99/99를 읽기 전용 확인. 하네스 문서 4개와 도구 안내를 같은 계통의 관리판으로 전환·명시 채택했다. 임시 목적지에 실제 SQLite backup→restore→verify를 실행해 복원본 108판·canon 5·무결성 ok를 확인했다. 다른 Sol의 독립 코드 검토는 `harness.py` SHA-256 `1748d50fd17c16640901f7410c0344997338b08b10dce630247652d99245dc35`, 테스트 SHA-256 `54af3db45663f2e52d49a4bfd39c364928b9ec1d8d81982ff1d8f0d3dced824d`를 기준으로 필수 미해결 없이 수락했다. |
| 다음 행동 | 최종 관리판과 [전용 DB 백업](../../data/document_harness/documents-20260925-final.sqlite3)의 복원 검증을 완료했다. 다음은 Astra의 읽기 전용 최종 스냅샷 대조·보고다. 후속 문서 선택은 사용자의 명시적 선택과 공용 `finalize` 경로를 따르며 미분류 legacy 문서는 임의 채택하지 않는다. `canon=false`인 기존 문서 99개의 적용 여부는 자동 결정하지 않는다. |

## 현재 작업 카드 — `HISTORY-ONTOLOGY-FUN-FIRST-DOC-20260924`

| 항목 | 실제 기록 |
|---|---|
| 요청·권한 | 사용자가 “재미가 먼저, 역사 전문가도 납득할 만하면 충분”하다는 품질 기준을 확정하고 기존 문답의 문서화를 요청. 이번 범위는 문서 통합·링크 갱신뿐이며 역사자료 처리·계산기·모델·평가 실행은 아님. |
| 담당·소유 | Astra 루트 조율. Sol이 [정본·개변 역사와 앵커 이음새](../systems/20260924-history-ontology-and-anchor-bridges.md), [핵심 설계](../systems/README.md)의 해당 원칙, 허용된 위키·세션·체크포인트만 편집. Luna는 의도/과설계 읽기 전용 감사, 다른 Sol은 독립 검토. |
| 입력·출처 | 최신 사용자 품질·역할 결정, 기존 작은 앵커·정본/개변 역사 문답, [핵심 설계](../systems/README.md), [조사 계획](../plans/20260924-history-sot-ontology-research-plan.md), 사전 확인한 온톨로지·인과 원자료. 덤프·소설 원문 본문은 이번 작업에서 읽지 않음. |
| 산출·검증 | 통합판에 재미 우선 선택 기준, SOTA 역설계→Backfilling→정방향 검토→작가 잠금→Gemma 본문 흐름, 질문 기반 최소 온톨로지 항목 제안을 반영. 다른 Sol이 사용자 확정/제안, 부족·충돌 보완 루프, 미실행 경계를 읽기 전용 검토하고 **수락**했다(별도 리뷰 파일 없이 메시지 보고). 수정 문서 11개의 URL 디코딩한 상대링크 존재·후행 공백 0과 새 온톨로지 항목 heading/fragment 대응을 확인. 구현·실험·성능 수치 없음. |
| 미결정·다음 행동 | 객체 구조, 구간 간격, 정성 판단 단위, 평가 가림·기준, 실제 구현 방법은 미결정. Astra가 문서 갱신과 미실행 경계를 보고한다. |

## 이전 작업 카드 — `HISTORY-ONTOLOGY-BRIDGES-DOC-20260924`

| 항목 | 실제 기록 |
|---|---|
| 요청·권한 | 사용자가 지금까지의 문답을 문서로 정리하도록 요청. 새 실행 계획·스키마 확정·덤프 처리·구현·실험은 요청 범위 밖. |
| 담당·소유 | Astra 루트 조율, Sol이 [문답 정리](../systems/20260924-history-ontology-and-anchor-bridges.md) 및 허용된 systems 링크·위키·세션 결정·체크포인트 작성. Luna는 사용자 결정/제안 구분을 읽기 전용 점검, 다른 Sol은 독립 검토. |
| 입력·출처 | 최신 사용자 문답의 촘촘한 앵커·정본/개변 상호분석·시계열 전제, [핵심 설계](../systems/README.md), [조사 계획](../plans/20260924-history-sot-ontology-research-plan.md), CIDOC CRM·SEM·OWL-Time·Event Calculus·Halpern/Pearl 원문. 이번에는 사전 문헌을 확인했으나 dump 본문·source hash는 읽거나 계산하지 않음. |
| 산출·검증 | 설계 대화 정리와 재발견 링크 작성. 다른 Sol이 사용자 합의/제안·조약 포함관계·후보/승인 상태를 검토하고 수정본을 **수락**했다(별도 리뷰 파일 없이 메시지 보고). 수정 문서의 URL 디코딩한 상대링크는 모두 존재하고 후행 공백은 0. 실제 전표 추출, DB/코드 변경, 인과 계산·검색/복원 benchmark는 없음. |
| 미결정·다음 행동 | 앵커 한 쌍에서 고정할 사실과 허용 상태 변경을 사용자와 문답으로 좁히고, 입력/출력·객체·평가 세부는 제안으로 유지. Astra가 문서 정리 결과와 미실행 경계를 보고한다. |

## 이전 작업 카드 — `HISTORY-SOT-RESEARCH-PLAN-20260924`

| 항목 | 실제 기록 |
|---|---|
| 요청·권한 | 보유 위키 덤프를 원역사 SoT로 사용하고 온톨로지·벡터 검색의 순서와 필요성을 조사할 **계획 작성**. 덤프 처리·실험·DB 구축 권한은 이번 요청 범위 밖. |
| 담당·소유 | Astra 루트가 배정·취합, Sol이 [조사 계획](../plans/20260924-history-sot-ontology-research-plan.md) 및 관련 색인·체크포인트 작성, Luna가 [공식 출처 지도와 로컬 목록 점검](../research/20260924-history-sot-ontology-source-map.md), 별도 Sol이 독립 검토. 동일 파일 동시 편집 없음. |
| 입력·snapshot | 사용자 확인: `wiki-dump/`의 텍스트 XML bzip2 19개 다운로드 완료. Luna의 읽기 전용 목록 대조는 19개, 46,445,603,916 bytes(43.26 GiB). 파일별 source hash·공식 배포 manifest 대조·압축/파싱 검증은 아직 수행하지 않음. [사전 출처 지도](../research/20260924-history-sot-ontology-source-map.md)와 [기존 K 계획](../plans/20260914-enwiki-granite-knowledge-ingestion-plan-v0-1.md) 참고. |
| 산출·상태 | [R0–R5 조사 계획](../plans/20260924-history-sot-ontology-research-plan.md) 작성 및 [다른 Sol의 독립 검토 수락](../research/20260924-history-sot-ontology-plan-review.md). 조사 결론/ADR·gold set·검색 benchmark·PostgreSQL + pgvector 구축은 없음. |
| 미결정·다음 행동 | Astra가 계획과 미실행 경계를 보고한다. 후속 연구 요청이 오면 R0의 공식 manifest·checksum·파싱 표본 검증 방법부터 별도 작업으로 배정한다. |

## 이전 작업 카드 — `HARNESS-BOOTSTRAP-20260924`

| 항목 | 실제 기록 |
|---|---|
| 요청·권한 | 현재 대화를 Astra 오케스트레이션 프로젝트 하네스로 만들라는 요청. 하네스 구성까지만 해당하며 회차 분석·학습 시작 권한은 아님. |
| 담당·소유 | Astra 루트가 배정·취합. Sol 구현 담당은 `AGENTS.md`, `.codex/config.toml`, `.codex/agents/{sol,luna}.toml`, `docs/harness/{README,task-template,current-checkpoint}.md`, `docs/{README,wiki/index,wiki/sources,wiki/log}.md`를 소유. 별도 Luna가 `docs/harness/session-decisions.md`, 다른 Sol이 `docs/harness/review.md`를 소유한다. |
| 입력 | 사용자 최신 요청·세션 결정, [핵심 설계](../systems/README.md), [위키 규칙](../wiki/rules.md), 공식 OpenAI Docs의 [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)·[Configuration Reference](https://learn.chatgpt.com/docs/config-file/config-reference). |
| 산출·검증 | 프로젝트 설정과 문서 작성. Python `tomllib` 파싱 성공, `git diff --check` 통과. CLI 0.144.4에서 최신 `agents.max_concurrent_threads_per_session`은 로더 오류여서 공식 문서상 legacy alias `agents.max_threads`로 교체했다. `codex debug prompt-input`은 승격된 읽기 전용 실행에서 exit 0이고 프로젝트 `AGENTS.md`가 프롬프트에 포함됐다. 이 결과는 실제 모델 접근권이나 역할 spawn 성공까지 증명하지 않는다. |
| 검토·미결정 | 다른 Sol의 [독립 검토](review.md)는 문서·정적 설정을 수락했다. `--strict-config`는 이 CLI의 `debug`/`features` 명령에 지원되지 않는다. 역할 선택과 실제 모델 실행은 현재 작업에서 수행하지 않았다. |
| 다음 행동 | 후속 요청은 [양식](task-template.md)으로 별도 배정하고 실행 시 실제 역할 선택·모델 접근을 확인한다. |

| 항목 | 확인된 기록 |
|---|---|
| 결정 | [세션 결정](session-decisions.md)에 Astra 루트, Sol 실무·검토, Luna 작품 분석과 사용자 작업 범위가 있다. |
| 기존 산출물 | [7편 표본·4작가 검토](../research/author-study/README.md), [원문 코퍼스](../research/chapter-ingestion/README.md), [독립 검토](../research/chapter-ingestion/review.md). |
| 원문·좌표 | 원문 7편 61,533,769 bytes와 현재 3,292구간. 작품별 source revision/hash는 [manifest](../references/manifest.json) 및 코퍼스 DB에서 직접 재확인한다. 이 체크포인트에 원문 본문은 복제하지 않는다. |
| 회차 경계 | 첫 350개 대상 중 249 mapped, 100 unmapped, 1 conflict. 미확정 번호를 회차로 추정하지 않는다. |
| 미실행 | 350화 의미 분석·학습·운영 캐논 반영. [후속 분석 계획](../plans/20260924-first-50-analysis-and-ingestion-plan.md) |
| 다음 행동 | 하네스 검증 결과는 위 카드와 [독립 검토](review.md)에 있다. 다음 실행 요청이 오면 새 작업 카드로 범위·소유·검증을 배정한다. |

작업을 시작할 때 이 표의 수치와 hash를 연결된 원자료에서 다시 확인한다. 진행 중 새 산출물이 생기면 경로·source hash·최종 완료 화·미결정·다음 행동을 갱신한다.
