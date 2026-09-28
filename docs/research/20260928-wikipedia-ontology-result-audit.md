---
category_id: research
lineage_id: lin-b5dce89d-d1be-4f0b-9d50-21923ef14468
document_id: doc-f9d6b5a0-95c7-4976-a6ce-a45e04c8157b
parent_lineage_id: lin-1a78dc59-6af9-4445-88e4-858f5327a856
abstract: 다섯 대상 다국어 위키 원문 처리의 진행 상태와 고정 후보·원문 우선 품질 검토를 확인할 때 읽는다.
version: 0.0.2
created_at: '2026-09-27T23:30:23.000000Z'
updated_at: '2026-09-27T23:31:54Z'
tags:
- 위키백과
- 다국어
- 온톨로지
- 실행검증
canon: false
---
# 다섯 대상 다국어 위키 온톨로지 결과 감사

판정: **원문 저장·고정 구간·근거 좌표를 거쳐 후보를 만드는 파이프라인은 실제 작동하지만, 전체 추출과 후속 색인은 아직 끝나지 않았다.** 더 중요한 품질 경계는 DB의 `candidate_unreviewed`도 사람 검토 전 형식 상태라는 점이다. 고정 의미 표본에서 사건 시점·지식 분류·역사적 지식 연결의 중대 오류가 나왔다. 현 후보를 현실 역사 SoT, 시점별 사실, 집필용 역사표에 자동 채택할 수 없다. 이 문서는 2026-09-28 진행 중 실행을 읽기 전용으로 감사한 비캐논 기록이며, 재실행·후보 상태 변경·릴리스 발행을 수행하지 않았다.

## 관측한 실행 상태

사용자가 승인한 다섯 대상은 문종·단종·세조·한글·Bloomery다. 앞선 적재 검증은 138개 위키의 연결 페이지 255개, 본문 3,303,431 UTF-8 byte와 1,256개 고정 단위의 전체 byte coverage를 확인했다([현재 체크포인트](../harness/current-checkpoint.md)). 이번 원격 `ontology_expanded` DB 읽기에서는 255개 페이지와 1,256개 단위를 재조회했다. `verify`를 실행한 중간 시점에는 페이지·단위·후보의 출처 결박과 전문 coverage 문제 목록이 모두 비었다(당시 attempt 916건). 이는 그 시점의 기계적 무결성이고 역사적 의미 수락이 아니다.

| 2026-09-27 23:28:54 UTC 최종 읽기 스냅샷 | 건수 |
|---|---:|
| 완료 / 실패 / 실행 중 / 미시작 단위 | 934 / 4 / 1 / 317 = 1,256 |
| `candidate_unreviewed` / `held` | 3,111 / 2,302 = 5,413 |
| H 검토 전 / 보류 | 1,943 / 445 |
| K 검토 전 / 보류 | 731 / 673 |
| B 검토 전 / 보류 | 437 / 1,184 |
| 색인 적격 `pre_1950` 근거 span / 실제 span 벡터 / 미색인 | 2,467 / 2 / 2,465 |
| 임베딩 실패 기록 | 0 |

표의 건수는 [마지막 읽기 전용 DB 스냅샷](../../data/analysis/private/ontology-multilingual-expanded/audit-20260928/runtime/db-final-snapshot.json) SHA-256 `6d78919c2ee213d36238ae611a368b21e49878329567443e52e083141e9f4bc0`에 고정했다. 이는 아래 **23:12:06 UTC 의미 표본**을 만든 뒤 진행한 실행의 관측값이며 표본을 다시 뽑은 것이 아니다. 마지막 관측 시점에 H200의 추출 PID `9508`과 종료 후 색인 watcher PID `10349`는 살아 있었고, `remaining-exit-code.txt`, `post-extract-summary.json`, `final-status.json`, `final-verify.json`은 없었다. 따라서 전체 추출의 정상 종료·후속 전량 색인·최종 검증을 완료로 적지 않는다. 기존 2벡터 기능시험은 고정 span 역추적 확인이며 전체 검색 순위나 다국어 검색 품질을 평가할 분모가 아니다. 새 컴퓨트 세션 재시험과 A40 백업도 이번 감사에서 수행하지 않았다.

실패 4단위는 모두 원시 응답을 DB에 보존했지만 완료 후보 행은 만들지 못했다. 네 응답은 각각 후보 11·11·12·11건, 합계 45개의 JSON 후보 항목을 포함하고 정상 파싱된다. validator의 최대 10건 조건을 초과한 것이 확인된 실패 원인이다. 출력이 잘린 JSON으로 분류하지 않는다. 완료됐으나 DB 후보가 0인 단위는 마지막 관측에서 **80개**다. 앞서 79개일 때의 원시 응답 분류에서는 모두 `language_handling=processed`, `candidates=[]`였고 직접 JSON 54개·애플리케이션 `_decode`가 지원하는 포장 JSON 25개였다. 마지막 관측의 추가 한 건도 직접 JSON·`processed`·빈 후보이며, 총 직접 JSON 55개·포장 JSON 25개다. 무후보를 파싱 실패나 언어 처리 불가로 세지 않는다. 이 구분의 [초기 원격 메타](../../data/analysis/private/ontology-multilingual-expanded/audit-20260928/runtime/audit-status.json)와 [79건 응답 분류](../../data/analysis/private/ontology-multilingual-expanded/audit-20260928/runtime/zero-response-summary.json)를 보존했다.

## 고정 후보 의미 검토

[표본 패킷](../../data/analysis/private/ontology-multilingual-expanded/audit-20260928/runtime/semantic-packet.json) SHA-256 `406d348ba34b5377b40ffa381369fce26481ec1d69167f5fc0b5ce99e208647c`은 DB의 2026-09-27 23:12:06 UTC 읽기 스냅샷이다. 다섯 주제마다 H/K/B와 `candidate_unreviewed`/`held` 슬롯을 고정하고, 8개 실제 언어판(en, ko, ja, fr, de, ar, ru, es)의 선호 순서 안에서 후보 ID의 SHA-256 최소값을 택했다. 주표본 45건과 B가 참조하는 K 보조 12건, 총 57건이다. 각 주제는 11~12건이며 후보 전체 필드·보류 사유·원문 인용과 같은 DB 단위의 전후 문맥·위키 revision·UTF-8 span을 담았다. 57건의 저장 근거 좌표는 원문 바이트와 일치한다. 성공 사례만 선별하지 않았으나 층·상태 슬롯을 강제한 **진단 표본**이므로 아래 비율을 전체 후보, 특정 언어 또는 역사적 진실의 정확도로 외삽할 수 없다.

| 주표본 45건 | 원문 주장 지지 | 중대 의미 오류 | 문맥 부족 |
|---|---:|---:|---:|
| 검토 전 25건 | 15 | 10 | 0 |
| 보류 20건 | 2 | 16 | 2 |
| H / K / B 각 15건 | 9 / 7 / 1 | 6 / 6 / 14 | 0 / 2 / 0 |

이는 [독립 의미 검토 요약](../../data/analysis/private/ontology-multilingual-expanded/audit-20260928/semantic/summary.md)과 [후보별 판정](../../data/analysis/private/ontology-multilingual-expanded/audit-20260928/semantic/review.json)에 근거한다. 보조 K 12건의 판정(지지 3·중대 오류 6·문맥 부족 3)은 주표본 집계에 합치지 않았다. 특히 원문이 세조의 State Code 편찬을 지지한 B `e44a08e3…`도 연결 K `7f4779d7…`가 법전 내용판 대신 후대 평가를 담아 **쌍 전체를 정상 브리지로 수락할 수 없다**.

작동한 부분도 있다. 일본어 문종 페이지의 H `d27e1a73…`는 문종의 조선 5대 국왕 재위 1450–1452년을 근거 표에서 적절히 잡았고, 일본어 한글 페이지의 K `56eeac58…`는 평성·상성·거성의 높낮이 대응이라는 지식 내용을 분리했다. 후자는 해당 근거만으로 절대 연대를 확정하지 않았다. 두 사례의 지지는 고정 위키 원문 주장과 후보의 대응에 대한 판정이다.

오류의 실제 양상은 다음과 같다.

- 러시아어 한글 페이지의 검토 전 H `5302ed6c…`는 원문에서 1933년 철자법안 **제안**에 붙은 연도를 학회 **설립**에 잘못 붙였다. [국립한글박물관 연혁](https://www.hangeul.go.kr/webzine/202108/sub1_1.html)과 [한글학회의 통일안 설명](https://hangeul.or.kr/board/normal/article/60713)도 1933년을 맞춤법안 발표 시점으로 설명한다.
- 한국어 세조 페이지의 검토 전 K `c31ce3ed…`는 《효경》 암송 근거에 없는 ‘불교 경전’ 분류를 만들었다. [한국학중앙연구원 효경 항목](https://encykorea.aks.ac.kr/Article/E0073033)은 이를 유교 경전으로 분류한다.
- 아랍어 문종 페이지의 검토 전 B `aad90bcd…`는 측우기 발견 귀속의 출처별 불확실성을 확정하고, 참조 K도 측우기보다 수위 측정 절차로 어긋났다.
- 아랍어 Bloomery 페이지의 검토 전 B `23c8a903…`는 해면철을 모아 단조하는 **일반 공정**을 역사적 지식 도입·채택 사건으로 바꿨다.

H 중에는 원문에 음력 표기가 있는데도 `missing_lunar_basis`로 보류된 2건이 있었다. 이는 보류 상태를 모두 오탐이라고 뜻하지 않으며, 저장 달력 필드와 검토 정책을 함께 확인할 문제다. 23:14:15 UTC 중간 관측의 B 검토 전 434행 모두 활성 K ID를 가진다는 DB 구조 조건도 연결 K의 내용판 적합성이나 브리지의 역사적 의미를 보증하지 않는다.

## 원문 우선 누락 점검

별도 Luna가 고정 원문 9단위를 먼저 읽고 그 사실의 후보를 조회했다([원문 우선 요약](../../data/analysis/private/ontology-multilingual-expanded/audit-20260928/source-first/summary.md) SHA-256 `13ea24a29470f3f490241dfe944e3e25b40f4f2f1b7e424b0ecab4a8bebcd8b9`, [단위별 판정](../../data/analysis/private/ontology-multilingual-expanded/audit-20260928/source-first/review.json) SHA-256 `786139324ff0d5308901b3a7b2574ed210da3cc9efc7da930c2130c7dbe83504`). 문종·단종·세조·한글은 en/ko 각 한 구간, Bloomery는 대응 한국어 페이지가 없어 en 한 구간이다. 9단위 모두 추출 `completed`였다.

문종 사망, 단종 즉위, 세조 왕위 찬탈, 세종의 1443년 훈민정음 창제와 Bloomery의 목탄·광석 장입은 선택 구간이나 인접한 같은 페이지의 후보에서 확인됐다. 이 가운데 문종 사망의 영·한 후보와 영어 한글의 1446년 공식 출판 후보는 `held`였고, 한글 영어 문장의 1443년 말~1444년 초 발표 시점을 창제·궁중 소개와 같은 사건으로 단정할 수 없었다. **후보 존재는 의미 수락이 아니다.** 반대로 Bloomery 영어 완료 페이지에서는 초반 소량 장입 뒤 진행 중 장입량 증가, 석회석 없이 슬래그가 형성되는 자기용융 사실의 대응 후보를 완료된 선택 구간과 관련 같은 페이지 후보 대조에서 찾지 못했다. 이는 국소 누락 의심 사례이며 전체 페이지의 모든 가능한 표현이나 전수 재현율에 대한 결론이 아니다. 선택한 9단위 밖에 있는 같은 페이지의 실패 구간으로 영어 한글 1개와 한국어 세조 1개도 확인했지만 그 내용을 추정하지 않았다.

## 원인 후보와 후속 보수 범위

K/B에 `object`를 요구하는 validator와 모델 프롬프트 사이에는 명시성 차이가 있다. 프롬프트는 K를 독립 지식·개념·내용판이라고 설명하지만 K의 `object` 필수 기입을 별도로 적지 않고 공통 JSON 예시는 `object:null`이다. validator는 K/B의 `object`가 비면 `missing_knowledge_object`로 보류한다. 좁은 raw 대조 시점에 이 사유의 K 630건은 모두 `object` 키가 있으나 비어 있었고 `claim`, `knowledge_object`, `content` 대체 키는 없었다. SHA순으로 고른 raw 응답 3건(ar/ja/en 한글)도 저장 후보와 일치하며 `predicate`가 `is`/`is a`, `object:null`이었다([대조 메타](../../data/analysis/private/ontology-multilingual-expanded/audit-20260928/runtime/k-contract-summary.json)). 마지막 DB 읽기에서는 빈 `object`를 가진 K가 635건으로 늘었다. 이는 프롬프트·검증 계약 불일치와 일치하는 관찰이지, 모델 오류의 유일한 원인을 입증하지 않는다. `held` 사유는 한 후보에 중복될 수 있어 사유별 건수를 더해 보류 총수로 계산하지 않는다.

후속 단계에서는 K 내용 객체의 필수 표현을 프롬프트 예시와 validator에서 일치시키고, 소수의 고정 원문에서 변경 전후를 독립 검토해야 한다. B는 시점 없는 명칭·유형·공정 설명과 **특정 시점에 누가 명칭을 정하거나 지식을 형성·전달·채택했는지**를 구분하고, 연결 K의 내용판까지 함께 검토해야 한다. 실패 raw 4건은 보존한 채 후보 상한 위반 처리 정책을 정하고, 원문 우선 누락 검토와 언어별 상충 주장 비교를 거쳐야 한다. 이번 감사에는 그 수정·재추출·DB 후보 상태 변경·색인·릴리스 발행이 포함되지 않았다. 추출 종료와 watcher 결과 파일이 나온 뒤 별도 최종 확인을 해야 한다.
