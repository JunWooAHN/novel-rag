---
category_id: document-harness
lineage_id: legacy-57c7707a-eb5d-527c-96db-4544f7c1311b
document_id: doc-61e62788-fec3-42d0-bcbf-4e26164f5ee7
parent_lineage_id: null
abstract: DB 고정 분석 입력·제출·독립 검토·재개 작업 카드를 작성할 때 쓰는 양식.
version: 0.0.1
created_at: '2026-09-27T02:29:48.000000Z'
updated_at: '2026-09-27T02:29:48Z'
tags:
- 작업양식
- 작품분석
canon: false
---
# 작업 카드 양식

카드를 복사해 작업별 파일 또는 배정 메시지에 채운다. 사용자에게 계획만 허용된 일은 상태를 `계획`으로 두고 실행 배정하지 않는다.

| 항목 | 기록 |
|---|---|
| ID·상태 | `계획 / 배정 / 진행 / 보류 / 검토 / 완료` 중 하나와 시점 |
| 요청·권한 | 원문 요청, 승인된 범위, 필요한 사용자 결정 |
| 담당·모델 | Astra 배정자, Sol/Luna 수행자, 독립 검토자(필요 시) |
| 범위 | 작품·작가·화/파일/DB 범위와 제외 범위 |
| 입력 | 읽을 경로, revision/hash, 선행 산출물과 허용 문맥 |
| 코퍼스 입력 판·작업 ID | `work_id`, `source_revision_id`/원본 SHA-256, `segmentation_id`, 확정 `chapter` 번호 또는 승인 `window` ID·근거, `workflow_kind`/role/split, `task_id`와 반환 본문 span/hash |
| 산출물·소유 파일 | 쓸 경로와 단일 writer, 다른 카드와의 충돌 여부 |
| 제출·독립 검토·재개 | 제출 ID·정확한 SHA-256, 독립 검토 전 `view-result`/`export-result`의 DB 제출판 재조회, 다른 검토자의 review ID·판정/보류 이유, `resume`의 다음 미완료 항목·체크포인트. 학습 투입/작품 정사 승인은 별도 기록 |
| 완료 조건 | 검증 방법, 근거 위치, 검토 수락 조건 |
| 중단점 | 마지막 완료 범위, 다음 행동, 보류 사유 |

소설 t화 분석 카드는 새 문맥인지, t화 이하의 **DB 고정판 입력**만 전달됐는지, 해당 번호 경계가 확정됐는지, 3~5화 체크포인트가 어디 있는지를 반드시 적는다. 승인 `window`는 공식 `chapter` 완료로 세지 않는다. 원문 좌표·hash와 명령 경로는 [코퍼스 안내](../research/chapter-ingestion/README.md) 및 [첫 분석 절편 사용법](../../src/novel_factory/README.md)에 맞춘다. 실패한 DB 조회를 원본 TXT로 자동 대체하지 않는다.
