---
category_id: research
lineage_id: lin-16d1e284-4d59-41b3-8d06-310f74670154
document_id: doc-e349a5a8-6df4-43f6-9d1e-26672d84fc91
parent_lineage_id: null
abstract: YAGO 4.6 다섯 대상의 첫 PostgreSQL 현실 전표 릴리스와 1450 조회, 출처·시간·불변성 검증 및 사용 범위의 한계를 기록한다.
version: 0.0.1
created_at: '2026-09-28T21:21:27Z'
updated_at: '2026-09-28T21:22:52Z'
tags:
- YAGO
- 역사온톨로지
- PostgreSQL
- 현실전표
canon: false
---
# YAGO 다섯 대상 현실 전표 SoT 첫 릴리스 검증

2026-09-29 기준, 기존 H200 영속 Storage의 PostgreSQL 16에 다섯 대상의 **범위 한정 현실 전표 릴리스**를 실제 발행하고, 새 프로세스에서 1450년 상태와 출처를 조회했다. 현재 사용판은 `reality:yago46:five:640261c0eea9d3b0:r2`이고, 최초판 `reality:yago46:five:640261c0eea9d3b0`도 같은 DB에서 바이트가 변하지 않은 채 조회된다. 이 결과는 YAGO 출처에 결박된 작은 제품 절편의 작동 검증이다. YAGO 주장의 역사적 진실, 세계사 전체 포괄, 특정 작품의 `ReviewScope` 완료나 작가 승인 역사표를 뜻하지 않는다.

## 실제로 조회하는 방법

기존 kt cloud AI Nexus H200 세션의 `/home/work/novel-toy-tune/reality-sot-pilot-20260929`에서 다음처럼 실행한다. PostgreSQL은 같은 Storage의 기존 클러스터를 쓰되 DB는 `reality_sot_pilot_20260929`로 분리했다. DSN에는 비밀값이 없다.

```sh
cd /home/work/novel-toy-tune/reality-sot-pilot-20260929
export PYTHONPATH=src
export SOT_DSN='host=/tmp/novel-ontology-pg-1100 port=55432 dbname=reality_sot_pilot_20260929'
PY=/home/work/novel-toy-tune/venv-gemma4/bin/python
$PY -m novel_factory.reality.sot_cli --dsn "$SOT_DSN" release
$PY -m novel_factory.reality.sot_cli --dsn "$SOT_DSN" query --entity trial:yago46:Munjong_of_Joseon --as-of 1450
$PY -m novel_factory.reality.sot_cli --dsn "$SOT_DSN" query --entity trial:yago46:Danjong_of_Joseon --as-of 1450-12-31
$PY -m novel_factory.reality.sot_cli --dsn "$SOT_DSN" source --statement-id facts:28729034
```

`1450`은 `[1450-01-01, 1450-12-31]`인 **연도 구간**이며 1월 1일로 바꾸지 않는다. 한 연도 안에 직위가 바뀌면 `possible_nominal`로, 명시한 하루의 시작·끝 경계에서는 `possible_boundary`로 표시한다. `supported_nominal`은 보존된 YAGO 날짜 문자열을 같은 명목 달력에서 비교한 결과이지 원사료 달력이나 역사적 진실의 확정이 아니다. 결과마다 릴리스·claim·policy decision·YAGO 파일/hash/줄·원 triple이 있고, 해당하는 경우 연결 Meta ID와 원 시간값이 따라오며, 없거나 불명확하면 미상으로 남는다. 미래 상태, 미래 사건, 과거, 시간 미상, 지식·분류는 현재 상태와 다른 lane에 남는다.

## 원천과 변환 범위

입력은 앞 시험의 고정 [foundation SQLite](../../data/analysis/private/yago-foundation-100-20260928/foundation.sqlite3) SHA-256 `640261c0eea9d3b064aba865f78c6d3c905098d63635fb8ea3deebfc0d551b14`다. 원본 78GB를 다시 훑거나 재해시하지 않았다. [YAGO 원본 manifest](../../data/research/yago-storage-20260928/manifest-final.json)의 파일 hash/좌표를 보존한 다섯 대상 캡처에 한한다. 입력은 5개 entity, YAGO 진술 152개(매핑 130: alias 70·외부 ID 10·구조 50, 제외 22), Meta 40개(부모 연결 24·outgoing orphan 5·incoming observation 11)다. [Luna 입력 무결성 점검](../../data/analysis/private/yago-sot-pilot-20260929/mechanical-review/input-inventory.json)은 고정 입력 세 hash·고정 캡처의 152개 statement ID/line 일치·분모를 대조했다.

구조 매핑 50개를 전부 역사 전표로 세지 않는다. `yago5-deterministic-v2` 정책에서 Meta의 자체 시작/끝을 모두 가진 왕·태자 유형 또는 배우자 관계만 `H_state` 12개로, 생몰일 6개는 지속 상태가 아닌 `H_event`로 분리했다. 한글·Bloomery의 지식 속성/분류 9개는 `knowledge_or_taxonomy`이고, 나머지 23개 관계·속성은 `temporal_unknown`이다. 한글 `facts:46623039`의 `"1443"^^xsd:gYear`는 r2의 K 기원 **후보** `time.origin`에 raw·year 정밀도·원 달력 `unknown`으로 표현한다. 특정 사람의 한글 인지, 실제 1450 사용·보급, 창제 정확일 또는 B bridge를 만들지 않았다. 일치·경합은 원 Wikidata 전체 statement, rank, reference, 반복 재위 기간을 확인하지 못한 상태이며, YAGO와 그 바탕의 Wikidata를 독립 증언 두 건으로 가산하지 않는다. 이전 모델의 `same` 제안은 수락 0건이므로 위키 잔여 후보를 자동 삭제·병합하지 않았다.

50개 구조 claim은 모두 `source_grounded_pilot_include`라는 **정책 결정**과 source ID에 연결되어 릴리스마다 정확히 50 claim·50 decision·50 member다. 날짜 없는 가족·장소·성별은 원천 주장으로 보존하지만 당시 지속 상태라고 단정하지 않는다. 출생/사망 장소를 생몰일과 추론 병합하지 않았으므로 미래 사망 장소도 1450 현재 사건으로 새지 않는다. 출처 claim 정책 수락과 사람의 역사적 진실 검토, 작품 사용 적격은 분리한다.

## 1450 질의의 양성과 경계

실제 PostgreSQL에서 새 프로세스별로 저장한 [r2 다섯 질의](../../data/analysis/private/yago-sot-pilot-20260929/v2/)는 각 대상의 출처와 정책 결정을 포함한다. 문종 왕 `facts:28729034`와 태자 `facts:28729033`는 1450년 내부 전환 때문에 둘 다 `possible_nominal`이며, `1450-03-03` 정확일은 양쪽 `possible_boundary`다. 단종 태자 `facts:47318069`는 연도 안에 시작하므로 `possible_nominal`, `1450-12-31` 명목 날짜에는 원천 구간 내 `supported_nominal`이다. 단종 왕 `facts:47318070`과 세조 왕 `facts:9920154`는 1450에는 `future`다. 문종·단종·세조 사망은 `future_events`, 단종 1454년 시작 배우자 둘은 `future`에 있다. 세조의 1428년 시작 배우자 상태 같은 양성 결과도 원천 Meta와 함께 보이며, 세조 왕 재위를 앞당기지 않는다. Bloomery는 분류 두 개만 있고 1450의 실제 제철 공정 사용·생산은 0건이다. 같은 주체/관계의 여러 값은 검토용 `potential_competition`일 뿐 배타성이 증명된 역사 충돌로 판정하지 않는다.

## PostgreSQL, 불변성, 검토 근거

운영 DB는 `reality_sot_pilot_20260929`, 영속 PGDATA는 `/home/work/novel-toy-tune/ontology-multilingual-trial/pgdata`다. 실제 DB 전역 행은 entity 5/source 152/Meta 40/claim 51/decision 51/member 100/release 2/scope 2로, v1·r2가 한 개 수정 claim/decision만 별도 revision ID로 유지해 전역 claim이 51개다. r2는 `supersedes_release_id`·`policy_delta`로 v1과 한글 K 시간 표현의 정정 이유를 명시한다. 개별 claim/decision에는 별도 `supersedes_*` 필드가 없어 소비자는 릴리스 간 멤버 차이와 같은 source ID를 따라야 한다. 출처 152개와 Meta 40개는 두 판에서 동일하다.

[PG 검증 영수증](../../data/analysis/private/yago-sot-pilot-20260929/pg-verification.json)에서 같은 입력 재발행 `created=false`, 같은 릴리스 ID의 변경·변조 입력 SHA 거부, 운영 entity/source/Meta/claim/decision/member/release/scope의 수정·삭제 거부(`P0001`) 및 전후 readback 동일을 확인했다. 별도 **합성 시험 DB**에서 v1·가상 정정 v2를 같은 DB에 발행하고 구판 hash 불변·발행판 member 추가 거부를 확인했다. 실제 r2의 [발행 후 검증](../../data/analysis/private/yago-sot-pilot-20260929/v2/postpublication-verification.json)도 두 판 멱등 재실행·같은 ID 변경 거부·v1/r2 멤버십 및 r2 claim/decision 변조 거부를 확인한다. [r2 전체 PG readback](../../data/analysis/private/yago-sot-pilot-20260929/v2/pg-readback.json) 파일 SHA-256은 `b144299f23f93a0b0b4a34829ab897f2a74098b25a12af48927d551f8eab275a`다. PG 검증 JSON의 `readback_sha256`은 정렬한 compact **payload** hash이므로 이 파일 바이트 hash와 값이 다르다.

v1 readback은 r2 발행 전후 파일 바이트 SHA `6f067950355c7203af5a79ec86b19c8dad10ca048348c8683daa824df7f1954b`로 동일하다. [델타 대조](../../data/analysis/private/yago-sot-pilot-20260929/v2/delta-verification.json)는 공통 49 claim/decision과 source/entity/Meta 전건 동치, H 세 인물·Bloomery 질의 내용의 릴리스 ID 외 동치를 확인한다. 기존 `ontology_expanded`의 page 255/unit 1,256/attempt 1,097/candidate 6,224는 이전 [PG 기록](../../data/analysis/private/yago-foundation-100-20260928/final-process-pg-mount.json)과 같았다. [기계·출처 목록](../../data/analysis/private/yago-sot-pilot-20260929/transfer-inventory.json)은 전송 경로/hash와 `.env`·키·소설 코퍼스 제외를 보존한다.

`pg_dump -Fc` SHA-256 `5f615dfd5db2dac9694ff3b703d2439a79147af6bd7a6adf20fa89890b629277`를 같은 Storage에 두고 별도 `reality_sot_pilot_20260929_restore` DB에 복원했다. 복원 DB에서 새 프로세스로 조회한 두 릴리스 JSON은 운영판과 각각 파일 바이트 hash가 일치한다([복원 영수증](../../data/analysis/private/yago-sot-pilot-20260929/v2/restore-receipt.json)). 이는 같은 Storage에서의 논리 백업·복원 검사이며 NFS 서버 측 내구성이나 A40 독립 백업 완료는 아니다.

제품 구현은 [결정적 매핑](../../src/novel_factory/reality/sot.py) SHA `f9abb69b26114242d7d9e5a9939cd9fa123374b7f17a1ae1a2e96f40d43de720`, [PostgreSQL 어댑터](../../src/novel_factory/reality/adapters/sot_postgres.py) SHA `8ccccd4216177ca404c5a12d7e2af585f5c55174d72e05559ff31ffb91686a4e`, [CLI](../../src/novel_factory/reality/sot_cli.py) SHA `f0c9704cf4f85a84a558b73143809d07162d4a405e871dc7caf21d46f97ada99` 판이다. `PYTHONPATH=src python3 -m pytest -q tests/novel_factory/test_reality_sot.py`는 7/7 통과했고 [독립 Sol 실행 검토](../../data/analysis/private/yago-sot-pilot-20260929/independent-review/runtime-review.md)가 고정 원천·50 claim·v1/r2 질의를 대조했다. 최종 코드·결과·문서의 수락은 별도 검토 기록에서 확인한다. 이번 파일럿은 선택 범위를 넘는 원 Wikidata 전체 statement/위키 본문 검토, 원 달력·반복 기간 복원, 역사적 참 검증, 작품별 `ReviewScope` 심사·역사표 잠금은 완료하지 않았다.
