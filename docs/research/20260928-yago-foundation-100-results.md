---
category_id: research
lineage_id: lin-7426d74b-59e9-4e13-b438-e7603f49db7e
document_id: doc-b7b31cd8-dfc7-4663-b69f-87f8d4b51506
parent_lineage_id: null
abstract: YAGO 4.6 기초 원장과 Gemma 원문 잔여 추출을 같은 고정 100구간에서 별도 검증한 결과를 읽는다.
version: 0.0.4
created_at: '2026-09-28T15:06:37.000000Z'
updated_at: '2026-09-28T16:59:58Z'
tags: []
canon: false
---
# YAGO 기초 원장·Gemma 잔여 추출 고정 100구간 검증

**판정:** 출처 원장을 분리한 YAGO 구조 기초를 적재하고 원문 후보를 별도 보존하는 경로는 이 5대상 시험에서 구현·검증됐다. 그러나 모델이 제안한 동일성 연결은 검토자가 한 건도 수락하지 않았고, 부당한 동일시와 원문 주장 생략이 남았다. 이번 잔여 추출 방식을 그대로 운영 병합·자동 억제에 채택할 수 없다. 이는 YAGO 기초 KG 자체의 기각이나 역사 사실 판정이 아니다.

## 고정 입력과 기초 원장

[선정표](../../data/analysis/private/ontology-benchmark-100-20260928/selection.json) SHA-256 45f58bccc92f7b0455bd3c7902da200c24b579d3b706a495721132eeb9b856f0와 [원문 영수증](../../data/analysis/private/ontology-benchmark-100-20260928/remote-receipts/source-100.json) SHA-256 e2a3a74f0e4863859d7ae6a86dd09924230dab9539557b4328d27c649119aefc를 고정했다. 5대상×20구간, 23언어의 동일 unit_id·위키 revision·원문 byte/hash·순서다. 외부 KG는 [H200 원본 보관](20260928-yago-h200-original-setup.md)의 YAGO 4.6 manifest SHA-256 da0d761331e3ccb070bfebbc5ecf4ad5db4165eac0ef5bc619444d95f78a70bb와 [기존 KG 캡처](../../data/analysis/private/yago-benchmark-100-20260928/kg-only-context.json) SHA-256 b8984492124dcb8d767fd7f58d0cc4e8125064017019854bc51b2d204be26349에 제한된다.

[매핑 정책](../../data/analysis/private/yago-foundation-100-20260928/mapping-policy.json) SHA-256 17c06d60d3948b06b012c112d210f5d2b3f892d2b09455cc37260e95688e0b07를 모델 출력 전에 고정했다. [적재 영수증](../../data/analysis/private/yago-foundation-100-20260928/foundation-load.json) SHA-256 4058a2ce39c0ac2413e5f8460654420481b0ac48459469dc97ac7e619db2f626와 [분리된 SQLite 기초 원장](../../data/analysis/private/yago-foundation-100-20260928/foundation.sqlite3) SHA-256 640261c0eea9d3b064aba865f78c6d3c905098d63635fb8ea3deebfc0d551b14는 원 YAGO의 정확 주어 152진술을 130 mapped·22 excluded·0 unmapped로 회계한다. mapped에는 별칭 70·외부 ID 10과 **고유 구조 assertion 50**이 있다. 5개체의 YAGO 파일·행·원술어·객체·해시를 보존했고 위키 출처 span을 만들어 붙이지 않았다. Bloomery는 대상 직접 facts 0, taxonomy/class 정보만 있으며 실제 제련 행위 B의 근거가 아니다.

시간 Meta 관측 40행 중 24행은 부모 진술에 연결됐고, exact-subject outgoing orphan 5행과 incoming 관측 11행은 따로 남겼다. 이 5 orphan의 부모 삼중항이 제한 캡처에 없으므로 Meta 미연결을 시간 부재로 해석할 수 없다. [독립 기계 점검](../../data/analysis/private/yago-foundation-100-20260928/mechanical-review/foundation-check.json) SHA-256 cb3830f3a5ea57ab7a4a6387b6a896caa0d592f075c9d725a4fe447fad5b3789은 원장·출처 좌표·가짜 wiki span 0을 PASS로 대조했다. [다른 Sol의 구조 50건 검토](../../data/analysis/private/yago-foundation-100-20260928/foundation-semantic-review.json) SHA-256 09267c3a032a3fb9ab7e94783207886780ade0e1bf06d3991a3dfdee7a6bc565는 원 YAGO 표현에 대한 매핑 충실도 50/50을 확인했다. 이는 역사적 참·거짓 검증이 아니다.

## 잔여 추출 계약과 실행

[잔여 추출기](../../tools/wiki_ontology_trial/yago_foundation_benchmark/foundation_runner.py)는 기존 위키 원문 span 검증과 H/K/B 기본 정의를 유지하면서, 표시된 KG statement와 원문 claim의 same·extends·conflicts **모델 제안**을 claim/span·statement ID·후보 ordinal에 결속해 따로 감사한다. 프롬프트는 모델이 같다고 판단한 주장의 후보 생략과 same 링크를 요청한다. 후처리는 생성된 후보를 추가 삭제하거나 링크를 자동 병합·수락하지 않는다. 모델 단계에서 빠진 주장은 원문·원시응답·링크가 남아 있어 부당 생략을 검토할 수 있지만, 생성 후보가 보존됐다는 뜻은 아니다. 기계적으로 유효한 연결도 의미상 동일성 승인이 아니다.

[CPU 사전검사](../../data/analysis/private/yago-foundation-100-20260928/preflight.json) SHA-256 4fae0bec190a574377992bc02112cfe9bf44f2b0612b5b6c1f8b037979d3689b는 100 원문/hash·BF16/FP8 no-thinking 템플릿과 token ID 동치를 확인했다. 입력 최대 11,976+출력 상한 2,600≤문맥 14,592로 원문 입력을 자르지 않았다. 실제 raw의 finish_reason=stop은 [독립 최종 기계점검](../../data/analysis/private/yago-foundation-100-20260928/mechanical-review/foundation-results-final-check.json) SHA-256 7f474d4799eae4effdf0741e742502a2ea5d8ec397df7bae9c8aa1a485251d5c가 양 arm 각100건 대조했다. 99구간은 residual mode, 입력이 긴 62위 1구간은 원래 프롬프트·KG 표시0으로 fallback했으며 budget_omitted라 잔여 방식 적용 성공으로 세지 않는다. 표시된 statement는 100구간 합계 870회 반복이지만 고유 표시 ID는 44개이고, 기초 구조 50개 중 6개는 표시되지 않았다.

각 arm은 [원문 baseline](20260928-h200-ontology-benchmark-results.md)과 [단순 YAGO 문맥 시험](20260928-yago-100-benchmark-results.md)의 해당 모델/리비전과 no-thinking·greedy, 최대 출력 2,600, 문맥 14,592, 총 동시 요청 6, B2 두 엔진 50:50을 유지했다. BF16·FP8 가중치의 동일 base 계보는 확인하지 않아 arm 차이를 순수 양자화 효과로 돌리지 않는다. 각 arm은 원문 100개를 **100회 호출**했다. 모델 로딩 관측은 자체 PID 기록→health A 93초, B2 첫 PID→두 엔진 health 168초이며 아래 runner wall과 분리한다. 초기 전체 YAGO TTL 스캔 시간과 GPU peak VRAM은 not_measured; CPU 원문 DB 대조 0.137초·프롬프트 준비 20.909초·사전검사 전체 21.047초는 별도 계측이다.

## 결과: 기초 원장, 원문 후보, 연결은 다른 분모

[최종 결과 SQLite](../../data/analysis/private/yago-foundation-100-20260928/foundation-results-final.sqlite3) SHA-256 6625d081ff4439ab7f0413a66997127a03b3d9d14fb9c3e7984c6d05bc88f2d7에는 200 raw 응답을 보존했다. A는100 validated, B2는99 validated·61위1 failed이다. B2 61위 raw의 후보 배열은 실제 11개라 상한10 검증에 실패했으며 raw11은 아래 공식 후보 540건에 넣지 않았다. raw 실패는 정당한 0후보와 다르다. [고정 최종 패킷](../../data/analysis/private/yago-foundation-100-20260928/quality-packets-final/manifest.json) SHA-256 4c653f9128b09f27b5102459600c56d4daa14b1a98a57fd09bb785715ddf66f5의 arms.A/B2는 baseline, YAGO-A/B2는 단순 문맥, FOUNDATION-A/B2가 이번 시험이다.

| 같은 100구간·각 arm 1회 | 기존 A | 문맥 A | 기초+잔여 A | 기존 B2 | 문맥 B2 | 기초+잔여 B2 |
|---|---:|---:|---:|---:|---:|---:|
| 검증 후보 | 583 | 620 | 542 | 541 | 569 | 540 |
| 원문 지지 | 446 | 473 | 411 | 437 | 438 | 425 |
| 중대 추출 오류 | 111 | 133 | 119 | 80 | 110 | 99 |
| 근거 부족 | 26 | 14 | 12 | 24 | 21 | 16 |
| 검토자가 지적한 중요 누락 항목 / 구간 | 24/24 | 34/34 | 89/88 | 30/30 | 43/43 | 86/86 |
| runner wall, 초 | 488.175 | 512.731 | 611.132 | 625.787 | 656.158 | 781.008 |

새 판정은 [1–50 합본](../../data/analysis/private/yago-foundation-100-20260928/quality-review/semantic-001-050.json) SHA-256 de2d3eeb9a2f37aa94b515ebce8d9d73c06d52da36ee6f56de1344da9d27cef7와 [51–100 검토](../../data/analysis/private/yago-foundation-100-20260928/quality-review/semantic-051-100.json) SHA-256 49b78de13963b5d499a913a0bc39ddabe0f8ad9f4503f3a64ccaff2a1a218052를 합친 [좌표·분모 집계](../../data/analysis/private/yago-foundation-100-20260928/semantic-aggregate-final.json) SHA-256 53d10da7778d3d439c5c72c17f8fdcc939ae443a177d2eecc28669280e58b305다. 1–50의 B2 26–50은 제3 Sol이 별도 검토했고, 합본 작성자는 중간판을 대체하며 동일 출력 4건의 판정차를 조정해 통합했다. 이 보조 검토는 중복 집계하지 않았다. supported는 해당 위키 원문에 대한 후보 지지이며 공개·캐논 수락이나 역사 truth가 아니다. extraction_error는 사실값만이 아니라 관계 방향·명령/실행 혼동·H/K/B 층위·적용범위 오류도 포함한다. 중요 누락은 검토자가 지적한 항목이며 완전 정답셋이 없으므로 recall이 아니다. 이번 검토는 KG로 덮였다는 주장과 링크도 따로 감사하므로 과거 두 검토의 누락 건수와 엄격한 동등 지표로 뺄 수 없다.

새 A/B2의 실제 후보0 구간은 각각 11개이며 그중 10개씩은 정당, 58위는 양쪽 모두 생몰년 분류가 있는데 후보0이라 부당했다. B2 32위는 **후보 1개가 나온** 구간을 검토자가 오히려 0이 적절하다고 본 사례로, 관측 0에 섞지 않았다. B2 실패 61위도 별도다. 새 arm 짝 비교는 A 선호 30·B2 선호 27·동률 43구간이고, 이 선호는 양쪽 후보의 절대적 안전성을 뜻하지 않는다.

모델의 기초 연결 제안은 A 105건(기계 valid44·invalid61), B2 96건(valid25·invalid71)이었다. **의미 검토에서 정당한 same은 0건**이다. A의 unsafe_same 54건·그 외 same invalid10건, B2 unsafe_same 48건·그 외 same invalid26건이 남았다. 특히 same을 제안하며 후보 ordinal을 비운 링크 A5·B2 3건은 모두 부당 동일시로 검토됐다. 이는 생성단계 생략 위험이고 확정된 중복 절감은 0건이다. extends 제안은 A20·B2 12, 차이·충돌 검토 대상 conflicts는 A21건만 정당한 관계 표현으로 판정됐지만 어느 쪽이 역사적 진실인지는 확정하지 않는다. 아랍어 문종 9위의 위키 계승상자 1550–1552와 KG 왕 기간, 연도 분류와 정확 일자 사이의 차이는 same으로 지울 수 없다는 사례다.

따라서 기초 50개를 후보 542/540과 합쳐 볼 때 이는 **서로 다른 출처의 행 수**일 뿐 전역 고유 주장 수가 아니다. 고유 기초50을 위키 100구간마다 다시 가산하지 않고, same+후보 없음에서 이미 생략된 후보를 다시 차감하지 않는다. 실제 후보 간 중복 제거도 사람 검토로 동일성이 수락된 범위만 가능하다. 다국어 residual↔residual 전체 의미 병합은 수행하지 않았다. 기존 YAGO가 같은 원천 Wikidata에서 파생한 진술을 독립 증언 둘로 중복 가산하지 않는다.

## 비용, 보존 상태, 적용 판단

새 runner wall은 기존 대비 A +25.2%·B2 +24.8%, 단순 문맥 시험 대비 +19.2%·+19.0%였다. 이는 각 조건 **한 번씩 실행한 개발 표본**이며 KG 적재·사전검사·모델 로딩과 추론 wall을 섞지 않은 값이다. 프롬프트·출력 계약도 달라 비용 증가를 YAGO 자료 단독의 인과 효과로 계산할 수 없다. 100호출을 유지했으므로 호출 절감은 없다.

[최종 기계점검](../../data/analysis/private/yago-foundation-100-20260928/mechanical-review/foundation-results-final-check.json)은 raw200·고정 원문과 prompt·후보542/540·B2 실패 raw11·엔진 분할·원본 불변을 PASS로 확인했다. [실행 영수증](../../data/analysis/private/yago-foundation-100-20260928/execution-receipts.json) SHA-256 2ee1d2daa1192534d6bfb32daa36f411475208a45c6454e35e8465cde943b883과 [재접속·프로세스·PG 확인](../../data/analysis/private/yago-foundation-100-20260928/final-process-pg-mount.json) SHA-256 604cb610c78ddc66662924e231bff80fa507e15656176782580ef2d15eff1bce에서 소유 모델 PID 종료·GPU0MiB·NFS RW·운영 PG page255/source unit1,256/candidate6,224 불변을 확인했다. [51–100 의미검토 기계 대조](../../data/analysis/private/yago-foundation-100-20260928/mechanical-review/semantic-integrity-051-100-check.json) SHA-256 3d9e02d5435b02330164d040fdc4e6d4a4bee9fe5d082a0389c89dbe337764a2는 해당 절반을 PASS로 확인했다. [최종 1–50 기계 대조](../../data/analysis/private/yago-foundation-100-20260928/mechanical-review/semantic-integrity-final-check.json) SHA-256 39802cd18bd47bf8527e2e5553b8dfdd57fa48917d270b7b467af489daf1d8ba는 100 arm행·615후보·162링크의 실제 좌표 불일치 0으로 PASS_SCOPED_WITH_LIMITATIONS이며, A 검토의 problems 필드 306개는 기록되지 않아 그 필드 비교만 불가했다. 두 최종 의미 원장 전체의 후보·링크·분모는 [다른 Sol의 집계 실행 수락](../../data/analysis/private/yago-foundation-100-20260928/aggregate-code-review.json) SHA-256 fbac8bee906ae2ed3a070512e7f847bba2d955750e2bdbd7d47c4566284a987c 및 합본 작성자의 원문 검토에 근거한다. 이 기계 대조는 검토자의 의미 판단을 대신하지 않는다. 이 시험은 후보를 운영 DB, 현실 역사 릴리스 또는 작품 역사표에 채택하지 않았다.

이 시험은 **5대상·23언어 고정100구간의 기초 KG+잔여 추출 원형**이다. 출처 분리·정밀도/Meta 고아행 보존·감사 가능성은 확인했지만, Wikidata 원 statement/reference 전체 보완이나 안전한 합병·시간/충돌 해소까지 검증한 것은 아니다. 후보의 원문 지지 판정과 YAGO 구조 매핑 검토는 역사적 정확도 평가가 아니다. 다음 구현 판단은 시간·역할·부정·출처를 갖춘 same 제안의 안전성, 생략 원문 주장의 복구, 중대 추출 오류와 중요 누락을 별도 고정 확인셋에서 다시 보는 데 달려 있다.
