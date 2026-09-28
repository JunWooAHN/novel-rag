---
category_id: research
lineage_id: lin-ff072fc5-1a5b-4053-8354-44f73473cfe4
document_id: doc-14367867-484b-4d0b-b44a-7dfcad370f0e
parent_lineage_id: null
abstract: 다섯 대상 YAGO 현실 릴리스 r3의 시간 미상 주장 23건에 출처 결박 시대 검색 범위를 더해 실제 PostgreSQL에서 전표·질의를 검증한다.
version: 0.0.1
created_at: '2026-09-28T21:57:49Z'
updated_at: '2026-09-28T21:59:13Z'
tags:
- YAGO
- 역사온톨로지
- PostgreSQL
- 현실전표
canon: false
---
# YAGO 시간 미상 주장의 시대 검색 전표 r3

기존 다섯 대상 YAGO [첫 현실 전표 릴리스](20260929-yago-history-sot-pilot.md)에 시간 미상 주장 23건의 **대략적인 시대 검색 범위**를 추가한 r3를 실제 H200 영속 Storage의 전용 PostgreSQL DB `reality_sot_pilot_20260929`에 발행했다. 현재 릴리스 ID는 `reality:yago46:five:640261c0eea9d3b0:r3`이다. [23건 인간 가독 전표](../../data/analysis/private/yago-sot-temporal-20260929/ledgers.md)와 [기계 판독 전표](../../data/analysis/private/yago-sot-temporal-20260929/ledgers.json)는 모두 발행 후 새 프로세스가 운영 DB를 읽어 만든 것이다. 각각 파일 SHA-256은 `9ede339fb3857061c974f3355df19052cd1ce69abe187c5d698b9ed2200fbd06`, `7d4a967cfc0340016d224ef20114c8e1feeda40780fe97f22150703a0882c279`이다.

기존 23개 주장의 원래 유효 시간 `time={}`는 그대로 **미상**이다. 문종 9건에는 별도 출생·사망 근거의 `[1414,1453)`년, 단종 7건에는 `[1441,1458)`년, 세조 7건에는 `[1417,1469)`년을 `context_range`로 붙였다. 이는 인물 생애를 이용한 **시대 탐색 힌트**이며 각 부모·성별·국적·언어·직업 주장이 생애 내내 유효했다는 판정이 아니다. 출생지·사망지 여섯 건에는 같은 인물의 별도 출생일·사망일 주장을 의미상 연결한 더 좁은 `inferred_event_bound`를 두었다. 예를 들어 단종 출생지 `facts:47318064`는 출생일 `facts:47318066`에 결박한 1441년 사건 후보, 사망지 `facts:47318075`는 사망일 `facts:47318067`에 결박한 1457년 사건 후보로 찾는다. 장소·날짜의 결합 자체는 원 YAGO 한 문장에 명시되지 않았으므로 파생 후보이지 독립 확인된 사건이 아니다. 검색 범위는 숫자 연도 버킷이고 원 `xsd:date`의 어휘상 day 정밀도·raw 값·원 달력 미상은 근거 패킷에 따로 보존했다.

다음 명령은 **기존 승인 H200 세션**의 `/home/work/novel-toy-tune/reality-sot-pilot-20260929`에서 실행한다. 접속은 비밀번호 없는 기존 로컬 Unix socket DSN을 쓴다.

```sh
cd /home/work/novel-toy-tune/reality-sot-pilot-20260929
export PYTHONPATH=src
export SOT_DSN='host=/tmp/novel-ontology-pg-1100 port=55432 dbname=reality_sot_pilot_20260929'
PY=/home/work/novel-toy-tune/venv-gemma4/bin/python
$PY -m novel_factory.reality.sot_cli --dsn "$SOT_DSN" era --release-id reality:yago46:five:640261c0eea9d3b0:r3 --period 1400..1499
$PY -m novel_factory.reality.sot_cli --dsn "$SOT_DSN" era --release-id reality:yago46:five:640261c0eea9d3b0:r3 --period 1450
$PY -m novel_factory.reality.sot_cli --dsn "$SOT_DSN" era --release-id reality:yago46:five:640261c0eea9d3b0:r3 --period 1200
$PY -m novel_factory.reality.sot_cli --dsn "$SOT_DSN" ledgers --release-id reality:yago46:five:640261c0eea9d3b0:r3 --format markdown
$PY -m novel_factory.reality.sot_cli --dsn "$SOT_DSN" query --release-id reality:yago46:five:640261c0eea9d3b0:r3 --entity trial:yago46:Danjong_of_Joseon --as-of 1450
```

이전 r2를 재조회할 때는 `--release-id reality:yago46:five:640261c0eea9d3b0:r2`, v1은 `--release-id reality:yago46:five:640261c0eea9d3b0`로 명시한다.

실제 [1400–1499 시대 질의](../../data/analysis/private/yago-sot-temporal-20260929/era-1400-1499.json)는 장소 사건 후보 6건과 일반 관계의 문맥 후보 17건을 **별도 lane**에서 찾는다. [1450 시대 질의](../../data/analysis/private/yago-sot-temporal-20260929/era-1450.json)는 장소 사건 후보 0건·문맥 후보 17건이다. [1200](../../data/analysis/private/yago-sot-temporal-20260929/era-1200.json)과 [1890](../../data/analysis/private/yago-sot-temporal-20260929/era-1890.json)은 이 23건에서 각각 0건이다. 장소 주장은 더 좁은 사건 범위를 우선 적용해 넓은 생애 문맥으로 중복 계수하지 않는다. K/분류 9건은 시대 사건 매치에서 제외하며 수만 별도 표시한다. [1450 단종 현재 상태 패킷](../../data/analysis/private/yago-sot-temporal-20260929/query-danjong-1450.json)에서는 사망지가 `temporal_unknown`에 남고 파생 발생 시점이 `future`로 표시된다. 당시 현재 상태로 승격되지 않는다.

[운영 PG r3 새 프로세스 readback](../../data/analysis/private/yago-sot-temporal-20260929/pg-readback.json) 파일 SHA-256은 `71161cba74d438dc7f0bef10875ba4f8022048fd9cb7316e0b43e649f7d60ed2`이며 로컬 결정적 준비판 전체 payload와 일치했다. r1·r2의 발행 후 readback 파일은 이전 바이트 SHA-256 `6f067950355c7203af5a79ec86b19c8dad10ca048348c8683daa824df7f1954b`, `b144299f23f93a0b0b4a34829ab897f2a74098b25a12af48927d551f8eab275a`와 각각 동일하다. r3는 23개 claim/decision만 새 `:r3` revision으로 추가했고 나머지 27쌍은 r2와 동일하다. DB 전체는 entity 5/source 152/Meta 40/claim 74/decision 74/member 150/release 3/scope 3이며, 릴리스마다 claim·decision·member 각 50건이다. [운영 검증 영수증](../../data/analysis/private/yago-sot-temporal-20260929/pg-verification.json)은 동일 입력 재발행 `created=false`, 같은 ID의 다른 payload 거부, 발행 후 수정·삭제·멤버 추가·공유 원천 수정의 SQLSTATE `P0001`과 세 릴리스 readback hash 불변을 기록한다. 영수증의 readback hash는 압축 canonical JSON payload digest로, 위 내보낸 파일 바이트 SHA와 구별한다.

이 작업은 고정 공개 YAGO 5대상 원천 152개·Meta 40개를 재사용했다. YAGO 원본 78GB 재처리, 새 GPU 추론, 위키 원문·원 Wikidata 전체 statement 검토는 하지 않았다. 생몰과 장소가 같은 YAGO 원천 계열에서 파생했으므로 독립 증언 두 건으로 세지 않는다. 숫자 범위는 후보를 찾는 데 유용하지만 원 달력, 정확한 역사 사실, 사후 칭호의 당시 사용, 인물 인지, 작품별 `ReviewScope` 적격이나 작가 역사표 잠금을 증명하지 않는다. 생몰 근거가 없거나 무효인 경우 범위를 채우지 않고 미상과 사유만 남기도록 별도 합성 격리 테스트에서 확인했다. 제품 코드 SHA는 [매핑·조회](../../src/novel_factory/reality/sot.py) `b79712136558042e815fa4b99eb2920e17d19e356f1ecad5d0286c52fcf40bed`, [CLI](../../src/novel_factory/reality/sot_cli.py) `7e6dce062ec383f0a640511f6d49cdd9bed7e43e6c98a0c9b8d2839305910ad6`이며 관련 단위 테스트는 10/10 통과했다. 이 보고서는 실제 파일럿 검증 기록으로 `canon=false` 유지한다.
