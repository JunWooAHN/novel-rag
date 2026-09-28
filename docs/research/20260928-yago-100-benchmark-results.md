---
category_id: research
lineage_id: lin-597f5c3b-f248-4594-a469-48432d01f96a
document_id: doc-1774575e-2ecd-40a5-937a-52fde8ec9cb7
parent_lineage_id: null
abstract: 같은 위키 원문 100구간의 YAGO 문맥 추가 전후 속도·원문 근거 품질을 검토할 때 읽는다
version: 0.0.2
created_at: '2026-09-28T12:41:25.000000Z'
updated_at: '2026-09-28T12:48:24Z'
tags: []
canon: false
---
# YAGO 4.6 문맥을 더한 고정 100구간 추출 회귀시험

같은 위키 원문 100구간에 **YAGO 4.6 진술 문맥과 사용 안내를 함께 추가**한 개발 회귀시험이다. 모델이 만든 H/K/B 후보를 원문에 다시 대조한 결과, A(BF16)에서는 지지 후보가 446→473건이면서 중대 의미 오류도 111→133건, B2(FP8 두 엔진)에서는 지지 후보가 437→438건이면서 오류가 80→110건이었다. 이번 단순 문맥 추가 방식을 그대로 운영 추출에 채택하기는 어렵다. 이는 YAGO를 원본 골격으로 쓰고 부족한 Wikidata 진술·원문 추출을 별도 출처로 합치는 [역사 온톨로지 PRD](../prd/wikipedia-history-ontology.md)의 설계를 기각하는 실험이 아니다.

## 입력과 처리 범위

[선정표](../../data/analysis/private/ontology-benchmark-100-20260928/selection.json) SHA-256 `45f58bccc92f7b0455bd3c7902da200c24b579d3b706a495721132eeb9b856f0`의 5대상×20구간, 23언어, 동일 `unit_id`·위키 revision·원문 byte/hash·순서를 [기존 A/B2 본측정](20260928-h200-ontology-benchmark-results.md)과 맞췄다. 동일 Gemma 4 31B BF16 A와 FP8 B2 모델판, no-thinking·greedy, 총 동시 요청 6, 출력 상한 2,600, 최대 문맥 14,592를 유지했다. 이번에는 원문 프롬프트에 고정 YAGO 진술 문맥과 “원문 span으로만 H/K/B 후보를 지지하고 KG는 문맥으로만 사용”하는 안내를 더했다. YAGO 사실에 가짜 위키 span을 붙이지 않았고 기존 원문 span 구조 검증을 유지했다. 따라서 **YAGO 사실 자체의 효과와 안내문 효과는 분리되지 않는다.**

원본 판은 [H200 Storage 보관 보고](20260928-yago-h200-original-setup.md)의 YAGO 4.6 manifest SHA-256 `da0d761331e3ccb070bfebbc5ecf4ad5db4165eac0ef5bc619444d95f78a70bb`이다. [KG-only 원장](../../data/analysis/private/yago-benchmark-100-20260928/kg-only-context.json) SHA-256 `b8984492124dcb8d767fd7f58d0cc4e8125064017019854bc51b2d204be26349`은 YAGO 파일·행·진술 ID·시간 Meta를 위키 출처와 구별해 보존한다. 직접 facts는 문종 36·단종 30·세조 27·한글 23건이고 Bloomery는 직접 facts 0, taxonomy class 진술 36건 중 프롬프트에 적합한 2건뿐이다. Bloomery의 class 정보를 실제 제련 행위 B의 증거로 승격할 수 없다. 이는 **5개 대상의 자료 범위**이며 100개 독립 KG 대상을 발견한 수치가 아니다.

[CPU 사전 검사](../../data/analysis/private/yago-benchmark-100-20260928/preflight.json) SHA-256 `ca0d184cd955649c5f75b64c17d874f14627f177d28f27c21322ec261ee026aa`에서 원문 100/100 byte/hash와 A/B2 토크나이저·템플릿의 입력 token ID 100/100 동치를 확인했다. 같은 unit에는 같은 완결 KG 진술 ID·순서·렌더링 bytes를 넣었다. 80구간에는 직접 사실, Bloomery 20구간에는 분류 문맥이 들어갔고 `budget_omitted`는 0이다. 단위별 2–15진술, 합계 874회 **반복 주입**이며 서로 다른 874개 사실이 아니다. 최대 입력 11,977+출력 상한 2,600=14,577토큰으로 문맥 14,592 이내였다. 원문·후보·KG 진술을 잘라 맞추지 않았다.

## 처리시간과 기계적 결과

| 관측값 | 기존 A | YAGO A | 기존 B2 | YAGO B2 |
|---|---:|---:|---:|---:|
| 100요청의 구조 검사 성공 / 실패 | 95 / 5 | 100 / 0 | 96 / 4 | 99 / 1 |
| runner wall, 모델 로딩 제외 | 488.175초 | 512.731초 | 625.787초 | 656.158초 |
| 검증 후보 전체 / 검증 뒤 0후보 구간 | 583 / 9 | 620 / 10 | 541 / 11 | 569 / 11 |
| 원시 응답 본문 무출력 / `finish_reason=stop` | 0 / 100 | 0 / 100 | 0 / 100 | 0 / 100 |

YAGO A의 wall은 기존보다 24.556초(약 5.0%), YAGO B2는 30.371초(약 4.9%) 길었다. 각각 한 번의 개발 실행이며 입력 프롬프트도 달라 반복 오차나 YAGO 단독 비용을 추정하지 않는다. [사전 검사](../../data/analysis/private/yago-benchmark-100-20260928/preflight.json)의 원문 DB 대조 0.382초와 모델 processor 로드·문맥 선별을 포함한 프롬프트 준비 66.129초는 위 추론 runner wall과 별개다. **초기 YAGO TTL 스캔 시간과 A peak VRAM은 `not_measured`**이며 사후 추정하지 않았다. B2의 57위는 후보 10개 상한 위반으로 raw를 보존한 구조 실패이고 재시도하지 않았다. `raw-empty=0`은 “후보 0개=0” 또는 “모두 원문 지지”라는 뜻이 아니다.

## 원문 근거 전수 검토

두 Sol이 [최종 10개 검토 패킷](../../data/analysis/private/yago-benchmark-100-20260928/quality-packets-final/manifest.json) SHA-256 `fb190384224eda3bc7abf9ae952f15b5177fbc4bf51dbe867cef1cfc17736b86`을 1–50·51–100으로 나눠 새 A/B2의 **검증 후보 전부**를 같은 원문과 기존 판정에 대조했다. [1–50 최종 검토](../../data/analysis/private/yago-benchmark-100-20260928/quality-review/semantic-001-050.json) SHA-256 `a7c63db087d616c29b5ffeb907f5c6683cf977dea76eeb5b2fd04326108291e5`, [51–100 검토](../../data/analysis/private/yago-benchmark-100-20260928/quality-review/semantic-051-100.json) SHA-256 `33a46ff1b81fc58424f84aa8153d49cb00866151182973014e43b56e79f0f89c`. [집계 대조](../../data/analysis/private/yago-benchmark-100-20260928/semantic-aggregate-final.json) SHA-256 `e12c608b37d3d78524904cea7164b5e14e3635ba98e95b26d1ff37946895c6a4`는 각 후보 ordinal·H/K/B층·DB 상태·위키 근거 좌표·원문 인용과 판정을 패킷에 맞췄다. 중간 집계 뒤 1–50 검토자의 동일 후보 상충 판정 3건을 정정한 **최종판** 수치다.

| 원문 대조 판정 | 기존 A | YAGO A | 기존 B2 | YAGO B2 |
|---|---:|---:|---:|---:|
| 검증 후보 분모 | 583 | 620 | 541 | 569 |
| 원문 지지 | 446 | 473 | 437 | 438 |
| 중대 의미 오류 | 111 | 133 | 80 | 110 |
| 문맥 부족·판정 유보 | 26 | 14 | 24 | 21 |
| 검토자가 지적한 중요 누락 항목 / 해당 구간 | 24 / 24 | 34 / 34 | 30 / 30 | 43 / 43 |

새 A의 133오류 중 검토 전(`candidate_unreviewed`) 후보에 47건, 새 B2의 110오류 중 58건이 있었다. 이 DB 상태는 의미 수락이 아니다. 여기서 `material_error`는 사실 오류만이 아니라 관계 방향·명령/실행 혼동·H/K/B 층위·프로젝트 적용 범위 위반도 포함한 후보 판정이며, 위키 사실 자체의 오류율이 아니다. `issue_types`는 한 후보에 복수 표지가 가능하고 두 검토자의 명명이 완전히 같지 않아 합산 유형별 비율은 산출하지 않았다. 반복 확인된 오류는 **내용이 비어 있는 K**, 일반 제련 공정·정적 지식을 실제 역사 B로 올린 관계, 행위자·시점·부정의 오독이다. 세조 영어 55위에서는 양쪽이 자살 **명령**을 사망 **완료**로 과장했다. Bloomery 영어 82위와 독일어 95위에서도 일반 공정이 실제 역사 B로 남았다. 반면 Bloomery 스페인어 100위의 서지 목록을 실제 제련으로 만들지 않은 양쪽 0후보는 정당하다. 지적된 중요 누락 수는 검토자가 표시한 항목이며 사전 정의된 완전 정답셋의 재현율이 아니다. YAGO A/B2 짝 비교는 A 선호 30·B2 선호 24·동률 46구간이었다. 상대 선호는 둘 다 원문에 맞는다는 뜻이 아니다.

## 검증, 보존, 결론의 한계

[최종 SQLite](../../data/analysis/private/yago-benchmark-100-20260928/yago-benchmark-100.sqlite3) SHA-256 `406c71eae9a39da438fc49d432d8ed6c8b4e63f6f549d7867298db656b9fa298`는 원본 PostgreSQL과 기존 100회 SQLite와 분리했다. [독립 기계 점검](../../data/analysis/private/yago-benchmark-100-20260928/mechanical-review/final-results-check.json) SHA-256 `2740a6a4a3201528cee1eac0b543fb1ed972703869e208d6503d61aa8978795e`는 고정 입력·200 raw byte/hash·KG 선택/순서·최종 패킷·B2 50:50·원본 SQLite 불변을 **PASS**로 확인했다. 별도 [의미 검토 연결 점검](../../data/analysis/private/yago-benchmark-100-20260928/mechanical-review/semantic-integrity-check.json) SHA-256 `9d2993f98bc5fa99744268110ea93254247284da2e9281ce7d8beeb14999b087`은 100구간·1,189후보의 연결과 전수 판정, 인용 좌표를 기계 대조해 **PASS**했다. 이는 검토자의 의미 판단을 독립 재판정한 것은 아니다. [종료 영수증](../../data/analysis/private/yago-benchmark-100-20260928/final-process-pg-mount.json) SHA-256 `bc0742fe0393d7964744dd32093721d77ec26c440e5610c5e2ddccce62dd27a9`에서 소유 모델 PID가 없고 GPU 사용량 0MiB이며 NFS Storage가 마운트되어 있다. 운영 PG의 페이지 255·구간 1,256·기존 후보 6,224 등 건수는 선행 영수증과 같다. 기존 결과 SQLite SHA-256 `9493c6ab3ab3cb9ed4d4435a9645d0d2b6a17187d2653af142242ebd608ab961`도 유지됐다. 실행 runner [benchmark_100.py](../../tools/wiki_ontology_trial/multilingual/benchmark_100.py) SHA-256 `8b6bf0878f7608dfa8037920a4409af54ab9088e378de011aaf5eb50443d8d07` 판이다.

오프라인 경계 테스트는 [최종 로그](../../data/analysis/private/yago-benchmark-100-20260928/unit-tests-final.log) SHA-256 `a45288ad0174212c3ea4a3661068454f6e9b82aa46aa1922c4b01425068439bc`의 9/9 통과다. 위 `supported`는 **위키 원문에 대한 출처 정합성**이지 역사 진실, YAGO 사실 정확도, 작품 역사표 수락, 전체 위키 성능을 뜻하지 않는다. 5개 주제·23언어 고정 개발 표본이며 YAGO-only 관계 커버리지, 위키 span 기반 추출 지지, 중요 누락은 각각 다른 분모다. 이 실험은 PRD의 “YAGO 기본 구조 → 원 Wikidata statement·qualifier·reference 보완 → H200 근거 span 후보 추출 → 시간·출처·충돌 검증 → 승인 경계” 전체 흐름을 실행한 것이 아니다. 이번 단순 문맥 추가에서 오류·누락 증가를 먼저 해소하고, KG-only 사실 원장을 별도로 검증한 뒤 새 고정 확인셋에서 재평가해야 한다. 후보를 운영 DB나 현실 역사 릴리스에 자동 반영하지 않았다.
