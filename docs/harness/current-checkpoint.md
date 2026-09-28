---
category_id: document-harness
lineage_id: legacy-40925fad-cbff-589b-9799-6cc13abe142b
document_id: doc-b61838df-c43b-4522-a443-8dd62817daf1
parent_lineage_id: null
abstract: 중단된 작업의 산출물과 다음 행동을 확인할 때 읽는다.
version: 0.0.35
created_at: '2026-09-25T01:10:18.000000Z'
updated_at: '2026-09-28T23:41:21Z'
tags:
- 하네스
canon: true
---
# 현재 체크포인트

기준일: 2026-09-29. 맨 위 카드는 YAGO 4.6의 1899년 이하 세계사 시간 근거 **전역 스캔 진행 중**, 그다음은 Wikidata 원본 다운로드 **진행 중** 상태다. 기존 YAGO 다섯 대상의 범위 한정 PostgreSQL 현실 릴리스 r3·v1·r2는 보존된다. 위키백과 연결 언어판 255개 본문은 기존 `ontology_expanded`에 보존하며 단위 추출은 사용자 승인 아래 중단된 상태다. 이 문서는 재개 인덱스이며 파일럿 릴리스를 세계사 전체의 역사적 진실, 작품 `ReviewScope` 완료·역사표 잠금 또는 분석 결과의 학습 투입으로 확대하지 않는다.

## 진행 작업 카드 — `YAGO-SOT-THROUGH-1800-20260929`

| 항목 | 확인된 결과와 재개 경계 |
|---|---|
| 범위·원본 | 사용자가 “1800년도까지”를 **1899년 이하, 1800년대 전체 포함**으로 확인했다. 기존 [원본 manifest](../../data/research/yago-storage-20260928/manifest-final.json) SHA `da0d761331e3ccb070bfebbc5ecf4ad5db4165eac0ef5bc619444d95f78a70bb`, H200 해제 원본 12개 78,426,497,491B. 앞의 다섯 대상 파일럿과 다른 세계사 전역 기초 범위이며 YAGO 근거를 역사적 참·작품 정사로 자동 승인하지 않는다. [running 비캐논 보고](../research/20260929-yago-history-sot-through-1899.md) `doc-d21a5daa-765c-4e03-885d-932a92c7c615`. |
| 실제 입력·실패·재개 | 첫 실행 코드 SHA `e46070d3...`는 Meta **6,221,779행/720,870,838B** 전량 원본 SHA 대조를 마친 뒤 facts 시작의 `time` 이름 충돌로 exit 1. [첫 실행 원본 코드·receipt·로그](../../data/research/yago-sot-through-1800-20260929/run-evidence/first-attempt/)를 보존했다. 수정 코드 SHA `ad4f94668b380e4344c391deaaecc8b2ec104291100b0b4544879063a8534932`는 Meta stage/ledger SHA·SQLite 행수와 bloom 재생성 대조를 통과했다([재개 영수증](../../data/research/yago-sot-through-1800-20260929/run-evidence/first-attempt/meta-bloom-verification.json)). [완료된 facts receipt](../../data/research/yago-sot-through-1800-20260929/run-evidence/facts.receipt.json) SHA `a1a20000092e3a49e859d813475d44547e0683d3eaaa84a2894e2c66453d9f81`: 원본 74,497,030행·5,087,821,943B/SHA `17da906c...` manifest 일치; mapped 918,825 + excluded 4,170,181 + unknown 69,408,024 + failed 0 = 74,497,030, PG facts claim 918,825와 일치. **2026-09-29 08:37 KST 무렵** PID 39714의 다음 `beyond-wikipedia` 중간 관찰은 33,000,000행·2,157,461,609B/단계 532.1초·RSS95MiB였다. 이 파일과 후속 단계 완료 receipt는 없다. 원격 `/home/work/novel-toy-tune/reality-yago46-through-1899-20260929/scan-v2.log`, `scan-v2.exit`과 단계 receipt·PG를 다시 확인한다. |
| DB·검증·다음 행동 | 새 DB `reality_yago46_through_1899_20260929`는 **초안 적재 중**, 릴리스 미발행. `scan`은 Meta→facts→beyond→Meta 연결→context→taxonomy/labels를 순차 진행하고 완료 시 초안으로 정지하며 `publish`를 호출하지 않는다. [Luna 초기 실제 snapshot](../../data/research/yago-sot-through-1800-20260929/mechanical-review/initial-draft-check.json)은 facts 첫 700만 행 내 선택 claim 93,967건과 source byte 좌표 11표본을 확인했지만 전량 수락은 아니다. [다른 Sol의 ad4f 코드 검토](../../data/research/yago-sot-through-1800-20260929/independent-review/scan-code-acceptance-ad4f9466.md)는 가역 **draft scan만 수락**했다. 로컬 시간 규칙 8/8, [별도 synthetic PG 관통 및 발행 거부·불변 시험](../../data/research/yago-sot-through-1800-20260929/run-evidence/smoke/)과 [1880 출생·1905 사망 deathPlace 누출 0 회귀](../../data/research/yago-sot-through-1800-20260929/run-evidence/deathplace-regression-bundle.tgz)를 통과했다. [보고서 운영 절](../research/20260929-yago-history-sot-through-1899.md#운영-확인과-안전-재개-명령)에 실제 SSH·코드/manifest/DSN·진행 확인·**프로세스 종료 뒤에만** 재개하는 명령이 있다. 나머지 전량 receipt, 파일별 분모, PG readback, Luna 기계 대조·다른 Sol의 **정확한 출력 hash 수락** 뒤 별도 발행·재조회·복원검사를 수행한다. Wikidata 다운로드 PID 38511은 별도 진행 중이며 이번 DB에 적재하지 않았다. |

## 진행 작업 카드 — `WIKIDATA-STORAGE-20260929`

| 항목 | 확인된 결과와 재개 경계 |
|---|---|
| 부재·용량 | [H200 실측](../../data/research/wikidata-storage-20260929/preflight.json): 기존 `sources/original/`에는 YAGO만 있고 `wikidata/`는 없었다. 목적지는 RW NFS 영속 Storage로 사전 가용 1,676,399,345,664 byte, 계정별 quota 별도 미확인. 기존 YAGO 4.6 원본·SoT PGDATA는 변경하지 않았다. |
| 원본·실행 | 고정 `20260922` full current-entity JSON `.bz2` **103,222,517,992 byte**, 공식 SHA-1 `c5bfd59f16c6cdf906ead1190d99729108e961be` 한 종을 선택했다([독립 원천 조사](../../data/research/wikidata-storage-20260929/independent-review/source-selection.md)). [검토된 도구](../../tools/wikidata_storage/fetch_original.py) SHA-256 `0103f1158f2c5d61b65bf8cdf4ed69beb31ff84bb42b4f744e3c36bb3fddd9d0`를 H200에서 `nohup` 기동했으며 실제 Python PID `38511`, 로그 `/home/work/novel-toy-tune/tools/wikidata_storage/20260929/fetch.log`, 부분 원본 `/home/work/novel-toy-tune/sources/original/wikidata/20260922/wikidata-20260922-all.json.bz2.part`다. 2026-09-28 22:33:31 UTC [재접속 영수증](../../data/research/wikidata-storage-20260929/launch-receipt.json)은 `.part` 360,710,144 byte·manifest `downloading`을 확인했다. |
| 보고·다음 행동 | [비캐논 setup 보고](../research/20260929-wikidata-h200-original-setup.md) `doc-2b97339f-f9fd-4abb-b04f-c334fa841652`. 현재 원본 취득·최종 SHA/JSON 검증은 **미완료**다. H200 컴퓨트 세션이 지속되면 서버 프로세스가 다운로드·자동 검증하고 SSH 종료에는 영향을 받지 않는다. 세션 종료나 오류 시 영속 `.part`/sidecar·고정코드 hash를 확인해 재개한다. 완료 판정은 최종 manifest `complete`, 정확한 크기·공식 SHA-1·로컬 SHA-256·3개 JSON 표본·다른 Sol의 최종 증거 검토 뒤 기록한다. 전량 해제·DB 적재·현실 릴리스·A40 백업은 별도다. |

## 완료 작업 카드 — `YAGO-SOT-METHODOLOGY-20260929`

| 항목 | 확인된 결과와 재개 경계 |
|---|---|
| 요청·문서 | 사용자의 “방금 한 작업들을 역사전표sot 를 만들어내는 방법론으로 문서를 만들어라” 요청에 따라 [YAGO 기반 역사전표 SoT 구축 방법론](../methods/history-ledger-sot.md) v0.0.1 `doc-83bf24a4-082b-4cae-89f8-71664d5061dc`를 작성했다. 첫 비공백 본문 저장 `2026-09-28T22:13:05.157809Z`, 최종 파일/문서 DB SHA `2f8eaa88d3647bd4835d383dca8000907d34261053b0a56c0f00a2f124bb6847`. |
| 검토·채택 | [다른 Sol 최종 수락](../../data/analysis/private/yago-sot-methodology-20260929/independent-review/final-acceptance.json) `accepted/complete=true` SHA `f5686c20ca9855f15764f348a6bca61cb618a24246d4ee4b284e8fc894766749`. PRD의 제품 요구·날짜별 비캐논 실행 보고와 책임이 다른 반복 절차이므로 새 방법론 한 계통만 `canon=true`로 채택했다. `import` 시 초안 `false` 유지 후 `finalize adopt`; DB 재조회와 `verify --files` 38건 문제 0. [생애주기 영수증](../../data/analysis/private/yago-sot-methodology-20260929/document-lifecycle.json). |
| 범위·다음 행동 | 입력판·출처·결정적 H/K·세 시간 층·정책·불변 PG 발행·시점/시대 조회·검증·정정 릴리스의 반복 절차를 담았다. 실측 사례는 YAGO 다섯 대상 v1/r2/r3뿐이며 새 코드·원격 DB/GPU/원본 덤프·시험은 실행하지 않았다. 다음 범위에서는 별도 입력판과 `ReviewScope`, 시간·출처 검토를 새로 고정해야 한다. 문서 채택은 역사 사실 또는 작품 역사표 승인이 아니다. |

## 완료 작업 카드 — `YAGO-SOT-TEMPORAL-20260929`

| 항목 | 확인된 결과와 재개 경계 |
|---|---|
| 요청·산출 | 사용자의 “이 규칙으로 역사전표를 만들어보자” 요청에 따라 시간 미상 주장 23건에 별도 생몰 근거의 **숫자 시대 검색 범위**를 추가했다. [비캐논 r3 보고](../research/20260929-yago-history-temporal-ledgers.md) v0.0.1 파일/문서 DB SHA `9774d78dffe8c015c69962eadb818db96bb28e7f388100441d89f53991be761e`; [실제 PG 파생 23건 전표](../../data/analysis/private/yago-sot-temporal-20260929/ledgers.md) SHA `9ede339fb3857061c974f3355df19052cd1ce69abe187c5d698b9ed2200fbd06`. 원 주장 유효 시간 미상은 유지하고, 같은 인물 출생·사망 장소 6건만 더 좁은 파생 사건 범위를 둔다. |
| 실제 DB·조회 | 기존 H200 Storage의 전용 `reality_sot_pilot_20260929` DB에 `reality:yago46:five:640261c0eea9d3b0:r3`를 추가 발행했다. [새 프로세스 r3 readback](../../data/analysis/private/yago-sot-temporal-20260929/pg-readback.json) SHA `71161cba74d438dc7f0bef10875ba4f8022048fd9cb7316e0b43e649f7d60ed2`; 릴리스당 claim·decision·member 50, 전체 entity5/source152/Meta40/claim74/decision74/member150/release3/scope3. 시대 조회 1400–1499는 파생 사건6/일반 문맥17, 1450은 0/17, 1200·1890은 0/0이다. K/분류9는 시대 매치에서 제외한다. 1450 단종 사망지는 시간 미상·미래 사건 후보이고 당시 현재 상태는 아니다. |
| 불변·독립 검토 | 기존 v1/r2 PG readback 바이트 SHA는 이전판과 동일. 같은 r3 입력 재실행 `created=false`, 같은 ID 다른 payload 거부, 발행 후 claim/decision/멤버/원천 변경 SQLSTATE `P0001`([운영 검증](../../data/analysis/private/yago-sot-temporal-20260929/pg-verification.json) SHA `1986c1ade3d5c112c55d7d0aa93b0b0148ba75eb688c628990ea6c7b6475802b`). [Luna 23/6/23 기계 감사](../../data/analysis/private/yago-sot-temporal-20260929/mechanical-review/final-output-check.json) `scope_pass` SHA `bb3d092e86acd4698c9b55da3ede11d7c1758833dab009b26a03581af0d2175b`; [다른 Sol 최종 수락](../../data/analysis/private/yago-sot-temporal-20260929/independent-review/final-acceptance.json) `accepted/complete=true` SHA `7513fb767c906d0b68eb41a1f6298277c6dd9fb056dee5cf25b4717f1c899056`. 보고 문서 ID `doc-14367867-484b-4d0b-b44a-7dfcad370f0e`, canon=false, `verify --files` 37건 문제0([생애주기](../../data/analysis/private/yago-sot-temporal-20260929/document-lifecycle.json)). |
| 남은 경계 | `context_range`는 인물 생애에 기대는 발견 힌트로 부모·성별·국적·언어·직업·사후 칭호의 생애 전체 유효 판정이 아니다. 사건 범위도 별도 같은 YAGO 계열 진술을 연결한 후보이며 독립 증언·역사적 참이 아니다. 원 달력·원 Wikidata 전체 statement, 작품별 `ReviewScope`, A40 독립 백업은 여전히 별도 범위다. r3에서 새 복원 시험은 수행하지 않았다. |

## 완료 작업 카드 — `YAGO-HISTORY-SOT-PILOT-20260929`

| 항목 | 확인된 결과와 재개 경계 |
|---|---|
| 요청·범위 | 사용자의 “진짜 되는지 검증” 요청에 따라 기존 5대상 고정 YAGO capture를 결정적으로 변환했다. [비캐논 실행 보고](../research/20260929-yago-history-sot-pilot.md) v0.0.1 SHA `8afea67661ac074a3ede30a90873399c201b30df974dce6efeffe7c9606d2b7f`. 모델 재추론·원본 78GB 재스캔·작품 역사표 잠금은 하지 않았다. |
| 실제 PostgreSQL 릴리스 | H200 영속 Storage의 기존 PG16 클러스터 안 별도 `reality_sot_pilot_20260929` DB에 v1 `reality:yago46:five:640261c0eea9d3b0`과 그 작업 종료 시 r2 `reality:yago46:five:640261c0eea9d3b0:r2`를 발행했다. 릴리스당 source 152/Meta 40/claim·decision·member 각 50, 당시 전역은 entity 5/source 152/Meta 40/claim 51/decision 51/member 100/release 2다. r2는 한글 K `"1443"^^xsd:gYear`의 raw/year/calendar unknown을 새 claim·decision revision으로 구조화하고 v1을 불변으로 유지했다. [실행 영수증](../../data/analysis/private/yago-sot-pilot-20260929/execution-receipt.json), [r2 PG readback](../../data/analysis/private/yago-sot-pilot-20260929/v2/pg-readback.json) SHA `b144299f23f93a0b0b4a34829ab897f2a74098b25a12af48927d551f8eab275a`. |
| 조회·불변·복원 | `1450`은 연도 구간으로 질의한다. 문종 왕/태자 전환은 possible, 단종·세조 왕은 future, 미래 사망은 별도 future event, 한글/Bloomery는 당시 사용 B 미증명이다. 같은 입력 재실행 `created=false`, 같은 ID 변경·발행 후 수정/멤버 추가 거부, v1 발행 전후 파일 SHA `6f067950355c7203af5a79ec86b19c8dad10ca048348c8683daa824df7f1954b` 동일. 같은 Storage의 `pg_dump`를 별도 DB에 복원해 v1/r2 readback hash가 각각 운영판과 일치했다([복원 영수증](../../data/analysis/private/yago-sot-pilot-20260929/v2/restore-receipt.json)). 이는 A40 독립 백업이나 서버 측 NFS 내구성 검증이 아니다. 기존 `ontology_expanded` page255/unit1256/attempt1097/candidate6224는 앞 기준과 동일했다. |
| 독립 검토·문서 | [Luna r2 기계 감사](../../data/analysis/private/yago-sot-pilot-20260929/mechanical-review/v2-output-check.json) `scope_pass`, [다른 Sol 최종 수락](../../data/analysis/private/yago-sot-pilot-20260929/independent-review/final-acceptance.json) `accepted/complete=true` SHA `fced7f02531819a21b25e64ca375a45dafd709db120d04cb8923e067462d3d9d`. 보고 문서 ID `doc-e349a5a8-6df4-43f6-9d1e-26672d84fc91`은 `canon=false` 유지, 파일/문서 DB hash 일치·`verify --files` 36건 문제0([생애주기 영수증](../../data/analysis/private/yago-sot-pilot-20260929/document-lifecycle.json)). |
| 남은 경계·다음 행동 | 파일럿의 출처 결박과 시간 조회가 작동했다. 원 Wikidata 전체 statement/달력·반복 기간/위키 원문 검토, 실제 역사 사실 진위, 작품별 `ReviewScope` 사용 적격, A40 백업은 별도 후속 작업이다. 현재 작품의 역사표 정사·잠금 권한은 그대로 남는다. 후속 정정은 새 릴리스 ID·새 claim/decision revision으로 발행하고 이전판을 유지한다. |

## 실행 카드 — `WIKI-GEMMA31B-INFERENCE-EFFICIENCY-20260928`

| 항목 | 재개 기록 |
|---|---|
| 범위·산출 | 사용자는 4비트를 품질 우려로 제외하고 BF16 A·FP8 B2/B3 비교를 계획한 뒤 **H200 세팅과 기존 추출 중지**, 이어 **속도·품질 본측정**을 승인했다. [setup 보고](../research/20260928-h200-ontology-benchmark-setup.md)의 A/B2 합성 연결에 이어 [본측정 보고](../research/20260928-h200-ontology-benchmark-results.md)에서 같은 고정 100구간을 A/B2에 각 한 번씩 처리했다(총 200 원문 호출). B3는 길이 14,592의 BF16 KV 부족으로 첫 엔진부터 기동 불가여서 본측정하지 않았다. 원래 계획의 100×3=300회를 완료했다고 쓰지 않는다. |
| 100단위 선정 | [원문 없는 ID·좌표 CSV](../plans/20260928-ontology-benchmark-100-samples.csv) SHA `f70b30ab7b57355b719b14d8c81dd7d3820ba801d19cb36d80d28081f77cfbbd`, [선정 JSON](../../data/analysis/private/ontology-benchmark-100-20260928/selection.json) SHA `45f58bccc92f7b0455bd3c7902da200c24b579d3b706a495721132eeb9b856f0`. 로컬 재현 1,256단위에서 대상마다 20개, 총 100개 고유 `unit_id`를 고정했다. 길이층은 16/27/57, 실제 언어 23개다. 기존 45후보는 41고유 구간에 걸쳐 있고 원문 우선 9·상한실패 4·0응답 예시 3단위를 포함한다. 이 목록은 새 의미 정답셋이 아니다. 사용자 관측 약 1,600개 작업과 로컬 1,256개 입력이 같은 job인지는 미확인이다. |
| 기존 추출 보존 | PID 9508/9526·watcher10349 종료, 이전 raw·후보·원문 보존. [본측정 뒤 운영 DB 확인](../../data/analysis/private/ontology-benchmark-100-20260928/remote-receipts/benchmark-final-pg-status.json)도 setup 뒤와 같은 완료 1,090·실패 6·raw 없는 running 1·pending 159, 후보 검토 전 3,601·보류 2,623, span vector 2다. [최종 프로세스 확인](../../data/analysis/private/ontology-benchmark-100-20260928/remote-receipts/benchmark-final-process-state.json)은 GPU 143,771/0MiB, benchmark/vLLM 생존 프로세스·PID 기록 없음. [중지 기록](../../data/analysis/private/ontology-benchmark-100-20260928/setup-stop.json). |
| 본측정·의미 판정 | A는 100건 488.175초, 구조 검사 응답 95·실패 5·후보0 응답9; B2는 같은100건 625.787초, 구조 검사 응답96·실패4·후보0 응답11. 두 arm의 200원시 응답이 별도 SQLite에 있다(SHA `9493c6ab3ab3cb9ed4d4435a9645d0d2b6a17187d2653af142242ebd608ab961`). 독립 Sol 두 명이 서로 다른 50쌍씩 원문 정합성을 검토해 A 선호26/B2 선호31/동률40/판단불가3, 후보 중대오류 A111/B2 80건을 기록했다. **형식 통과·상대 선호는 역사 사실 승인이나 전수 정확도가 아니다.** [수치와 근거](../research/20260928-h200-ontology-benchmark-results.md). |
| 미결정·다음 행동 | 이번 고정 표본에서 B2는 A보다 느렸고 두 구성 모두 H/K/B 중대 오류가 남아 자동 운영 전환·후보 채택 근거가 없다. [H/K/B 보수 계획](../plans/20260927-wikipedia-multilingual-remediation-plan.md)에 따라 원문 표현·부정/행위자·K 내용판·B 실제 역사행위를 개발 입력에서 보수한 뒤 별도 미사용 확인셋에서 독립 검토한다. B3 입력 절삭·KV dtype 변경·강제 재시도, 이번100구간 자동 반복, 기존 추출 자동 재개는 하지 않는다. [실행 사용법](../../tools/wiki_ontology_trial/multilingual/README.md#h200-고정-100단위-추론-구성-점검). |

## 완료 작업 카드 — `DOCUMENT-HARNESS-METADATA-20260928`

| 항목 | 실제 기록 |
|---|---|
| 요청·범위 | 사용자가 최초 비공백 내용 저장판 기준의 `created_at`과 관리 Markdown YAML의 `canon` 불리언 표시를 승인했다. 선택 정본은 문서 SQLite로 유지하고 미관리 legacy 자동 편입·원문 DB·H200·제품 캐논 선택은 범위 밖이다. |
| 구현·검토 | [전용 CLI·사용법](../../tools/document_harness/README.md), [생애주기 규범](document-lifecycle.md), [이식 안내](portability.md), 이 안내·[세션 결정](session-decisions.md)을 갱신했다. 독립 Sol이 최종 코드 SHA `1e3c7deee855ed57dda12672041dd2a74d2fef9937dbf7f34bbc6b0a1b7424a7`와 테스트 SHA `8da831994e0bedc1e03b652d1e9bc2b411dcd48af1eca605535429955f29a219`를 수락했다. 테스트 18/18 통과. |
| 보완 근거·작업 기록 | [사전 DB 백업](../../data/document_harness/documents-20260928-before-metadata-sync.sqlite3) SHA `f08ad133da659822d6c0190a3663d6847f7386a9feebfe94d906e027eb918a1c`, [사전 관리 파일·선택 목록](../../data/document_harness/metadata-sync-20260928-preflight.json), [날짜·표시 보완 기록](../../data/document_harness/metadata-sync-20260928.json), [규범·도구 새판 기록](../../data/document_harness/metadata-sync-20260928-editions.json). 최초 내용판의 유효한 `updated_at`을 근거로 27계통·92관리판의 `created_at: null`을 보완했다. 이는 옛 원자료의 실제 최초 탄생시각을 복원했다는 뜻이 아니다. |
| 결과·검증 | 관리 파일 29/29의 DB 판·본문·메타·`canon`·파일 SHA 일치, DB 판수와 FTS 행수 일치·무결성 `ok`, `canon=1` 11판 유지. 기존 237판 본문 변경 0, legacy 142판의 본문·해시 변경 0. 규범·도구 안내의 수정 5건과 기존 본문이 달랐던 위키 시험 README 1건은 원판을 보존한 새 판으로 기록했고, 앞의 5개 규범 계통만 기존 선택을 교체했다. [다국어 보수 계획](../plans/20260927-wikipedia-multilingual-remediation-plan.md)의 `created_at`은 첫 내용판 `2026-09-27T06:23:18Z`로 보완됐고 `canon: false`로 표시한다. |
| 미결정·다음 행동 | 새 캐논 계통을 늘리지 않았다. 미관리 legacy의 근거 없는 날짜는 `null`로 유지한다. 후속 문서 작업은 새 YAML `canon` 표시와 `verify --files`를 사용하며 사용자 수동 표시 변경은 선택을 바꾸지 않는다. |

## 현재 작업 카드 — `WIKI-MULTILINGUAL-FIVE-TARGET-EXPANDED-20260927`

| 항목 | 실제 기록 |
|---|---|
| 요청·범위 | 사용자가 문종·단종·세조·한글·Bloomery 다섯 대상의 확인된 연결 언어판 본문 전체를 DB에 적재하고 31B 후보·K/B 관계·근거·벡터 및 재개를 실제 검증하도록 승인했다. A40 백업과 전 세계 위키의 독립 문서 전수는 이번 범위 밖이다. |
| 담당·입력 | Sol 한 명이 코드·H200·제품/문서 DB의 단일 writer이고, Luna는 별도 `sources/`에 공개 원문을 수집했으며 다른 Sol이 구현·결과를 독립 검토한다. 고정 sitelink 255건 SHA `98f466b19c137e53150b4fefd3f6b771e12681f44c9e4931b2e0b373018896a5`; 수집 manifest SHA `42393d8f5ade5b2b47e0636acc0d532ee64c752993a5a7bf9ba2a4f781ade98f`. 138 wiki의 255개 고정 본문 총 3,303,431 UTF-8 byte가 raw API 본문과 기계 대조됐다. 이는 후보 추출 완료 수가 아니다. |
| 당시 진행·현재 경계 | 사용자가 정확한 1,513,326-byte 묶음 SHA `95a3c762fb3bd12e01811f984589860b2f194bc8612d514ed1357906e1e273fe`의 H200 전송을 명시 승인한 뒤 원격 SHA 일치로 전송했다. 기존 두 구간 `ontology_trial`은 보존하고 같은 PG16 클러스터의 별도 `ontology_expanded` DB에 255개 전문·1,256개 고정 UTF-8 단위를 적재해 전체 byte coverage·receipt 255/255를 확인했다. 처음 3단위 31B 실추출에서 후보 9건·실패 0건을 기록했다. 독립 검토는 K/B 구조 링크 2쌍 중 한 쌍만 잠정 타당으로 보고 다른 K/B 2건은 DB `held`·사유로 전환했다. 첫 쌍의 근거 2개를 E5 벡터화해 한국어 질의가 afwiki 사용 문장을 반환했으나 2벡터 기능시험일 뿐 검색 품질 수락은 아니다. 당시 PID `9508`의 장기 추출은 `/home/work/novel-toy-tune/ontology-multilingual-expanded/remaining-progress.jsonl`·`remaining-stderr.log`·`remaining-exit-code.txt`를 썼고, **현재는 위 H200 구성 시험 카드대로 종료됐다.** 원시 응답·과거 영문시험·같은 PGDATA의 새 CPU 세션 재연결 기록은 보존한다. 후속 추출을 별도로 결정한다면 프로세스 종료와 DB 상태를 먼저 확인하고 raw 없는 미완료만 명시적으로 재개한다. A40 백업·현실 릴리스는 미실행이다. |
| 종료 후 색인 이력 | 독립 검토한 일회성 `post-extract.py` SHA `438967f386b0044591825448ae28c7337dd1212ca82b2713a6c3ee06d5689dc8`를 같은 Storage에 두고 당시 H200 PID `10349`로 기동했다. 위 추출 PID `9508`과 결박해 정상 종료할 때에만 CPU E5를 이어 실행하는 설계였지만, 사용자 승인 중단에 따라 watcher도 종료해 자동 색인은 시작하지 않았다. 최종 span vector는 2개이며 새 추출 job을 별도 승인·실행한다면 watcher도 새 PID에 맞춰 따로 결정해야 한다. |
| 2026-09-28 중간 감사 | [비캐논 결과 감사](../research/20260928-wikipedia-ontology-result-audit.md)에 읽기 전용 DB 상태, SHA로 고정한 45개 주표본·12개 참조 K 의미 검토, 별도 9단위 원문 우선 점검을 연결했다. 255페이지·1,256단위 전문 coverage와 그때의 `verify`는 문제 0건이다. **당시** `2026-09-27 23:28:54 UTC`에는 완료 934·실패 4·실행 중 1·미시작 317, 후보 5,413·span 벡터 2였고 두 PID가 살아 있었다. 이는 현재 수치가 아니며 위 H200 구성 시험 카드의 마지막 DB 확인을 따른다. 검토 전 후보에도 의미 오류가 있어 현실 역사 SoT·집필 입력 자동 채택은 보류한다. |
| 다음 품질 보수 계획 | [기존 다국어 보수 플랜](../plans/20260927-wikipedia-multilingual-remediation-plan.md)의 M3 후속 절에 고정 원문 표현 보존, H/K/B 유형과 난이도 분리, 명시 B의 31B 시험·복합 B 검토 대기, 별도 확인셋 독립 검토 순서를 기록했다. **M3 지침 변경·상위 모델 호출·DB 후보 수정·현실 릴리스 발행은 여전히 계획만**이다. 기존 batch 중지는 별도 승인된 효율 구성 setup의 실행이며 M3 적용이 아니다. 다음 행동은 원문·후보 개발 기준선과 독립 확인셋을 고정한 뒤 보수 구현을 별도 배정하는 것이다. |

## 이전 작업 카드 — `WIKI-MULTILINGUAL-DB-FIRST-TRIAL-20260927`

| 항목 | 실제 기록 |
|---|---|
| 요청·범위 | 사용자가 다국어 보수 플랜의 첫 절편을 실제 구현·H200에서 간단히 실행하도록 승인했다. enwiki·kowiki 문종의 고정 선택 구간 **각 하나**만 DB→31B→근거→벡터로 처리했다. 전 언어판·페이지 전문·세계 인벤토리 완료나 현실 릴리스 발행은 아니다. |
| 고정 입력·실행 | [비본문 검증](../../data/analysis/ontology-multilingual-trial-verification.json)에 source revision·slot·UTF-8 좌표·hash, 승인된 공개 코드/위키 묶음 SHA `faf0bacdb336eaab8fea9d9185c47e34e879eeeae1473513371ca2c6b71c42ff`가 있다. H200 연결 Storage의 `/home/work/novel-toy-tune/ontology-multilingual-trial/pgdata`에 전용 PostgreSQL 16.15·pgvector 0.6.0을 local-only로 구성했다. 기존 문체 자료·영어 시험 원자료는 보존했다. |
| 실제 결과 | Gemma 4 31B 고정판으로 두 선택 구간에서 H 후보 영어 4·한국어 1건을 만들었다. 원시 응답 2건·개별 후보 5행·F 출처/근거는 DB에 있고 K/B는 선택 구간에 없어 0건이다. E5-small 384차원 벡터 2행을 저장했다. 5건 모두 `candidate_unreviewed`; 정확 인용·좌표 연결과 독립 구조 검토는 통과했지만 역사적 의미는 승인하지 않았다. [사람용 시험 결과](../research/20260927-wikipedia-multilingual-db-trial.md)에 실제 검색과 결함을 분리했다. |
| 재개·복원·검색 | 같은 입력 재실행에서 31B 재호출 0·임베딩 추가 0. 전용 PostgreSQL 프로세스만 재시작한 뒤 2페이지/2구간/2시도/5후보/2벡터가 남았고, `pg_dump -Fc`의 별도 시험 DB 복원과 다섯 표 행 값 대조가 통과했다. 한국어 질의로 두 언어 구간을 찾았으나 승계 질의는 사망 구간이 1위이며 검색 hit의 인용은 구간 첫 후보라 질의별 근거 패킷으로 수락하지 않는다. |
| 미결정·다음 행동 | 원문의 `Grand Prince Seyong` 표기 동일성, 강제퇴위 수식어, 한국어 사건의 장소 역할과 영어 날짜의 달력 체계가 미해결이다. K/B 실자료 경로, 질의별 근거 선택, 대상의 확인된 전 언어판과 독립 문서, 새 컴퓨트 세션 재연결·NFS 서버 sync/장애 내구성·A40 백업은 미검증이다. 다음은 [보수 플랜](../plans/20260927-wikipedia-multilingual-remediation-plan.md)의 처리장부와 실제 비영어 구간을 늘리기 전에 이 후보의 의미 보류를 유지하고 검색 반환 계약을 보수하는 것이다. |

## 이전 작업 카드 — `WIKI-MULTILINGUAL-REMEDIATION-PLAN-20260927`

| 항목 | 실제 기록 |
|---|---|
| 요청·권한 | 사용자는 다른 언어 위키 순회 보수 플랜을 요청했고, DB는 **그 목표를 풀기 위한 수단**이라고 정정했다. 이번 허용 범위는 기존 계획·색인·체크포인트 문서뿐이며 다국어 덤프 다운로드·API 수집·코드·GPU·현실 DB 변경은 하지 않는다. |
| 발견된 편향 | 첫 31B 시험은 enwiki 선택 5구간, 보강 재시험의 추가 위키 근거 6구간도 enwiki였다. kowiki 본문 처리 0건이다. 국립한글박물관의 한국어 발췌 1건은 Wikipedia 언어판 처리로 세지 않는다. 기존 두 시험의 raw와 판·SHA는 그대로 보존한다. |
| 계획 산출 | [다국어 순회·입력 보수 플랜](../plans/20260927-wikipedia-multilingual-remediation-plan.md)은 전체 Wikipedia 사이트별 원문 목록의 합집합과, 선택 대상의 **확인된 모든 연결 언어판 본문 처리**를 별도 단계로 둔다. 영어판/QID 없는 문서의 독립 보존, site/revision/slot/span, 언어별 실패·미확보 상태, 공통 H/K/B/F·출처 계열·충돌 검토를 유지한다. 첫 절편은 H200의 DB 고정 구간 조회→31B 후보/근거→DB 재조회→한국어 질의로 비영어 원문 근거 반환→멱등 재개다. |
| 최신 저장 결정·관측 | 사용자는 H200 세션에 연결된 2TB Storage를 주저장으로 지정하고 A40에 원본 삭제 없는 주기적 백업을 두기로 했다. [읽기 전용 사전점검](../../data/analysis/h200-postgresql-preflight-20260927.json)은 사용자 할당 2TB·사용 192.91GB, Ubuntu 24.04·sudo·NFSv3 `rw,hard`와 PostgreSQL server/pgvector **미설치**를 확인했다. `pg_config` 16.11은 server 구동 증거가 아니다. 원문·온톨로지/근거·처리 상태와 재생성 가능한 임베딩/벡터를 DB에 두는 설계이며, PG16+pgvector는 이 보수 절편의 adapter 우선 후보다. 세션 보존·PGDATA 실동작·A40 백업/복원은 아직 확인하지 않았다. |
| 완료·다음 행동 | 현재는 **실행 가능한 통합 계획**까지이며 다국어 본문 추출·세계 인벤토리·현실 릴리스·DB 설치·A40 백업은 미실행이다. 앞서 중지한 GPU·코드 실행은 문서 개정만으로 재개하지 않는다. 후속 구현은 현재 세션과 기존 자료를 보존하며 새 전용 Storage 하위 경로에 DB를 준비하고, 한 비영어 page의 고정 본문·후보·근거·한국어 조회 수직 절편을 먼저 통과시킨다. 같은 Storage의 새 세션 재연결 및 A40 별도 복원은 후속 수락이고, 전세계 덤프 확보가 첫 절편의 선행 조건은 아니다. |

## 이전 작업 카드 — `WIKI-31B-ENRICH-20260927`

| 항목 | 실제 기록 |
|---|---|
| 요청·범위 | 사용자가 첫 시험의 누락·오분류를 보고 같은 5개 발췌에서 모델 자기진단, 선택적 근거 조회, 재추출 비교를 승인했다. 문서·덤프 전량 처리, 벡터 DB, 학습, 현실 릴리스는 실행하지 않았다. |
| 입력·역할 | 첫 [고정 패킷](../../data/analysis/private/ontology-trial/trial-packet.json) SHA `e47b8e0785d55d5928bce4766f80d65a5195f7e86c62333c2c621aa541f99918`과 `google/gemma-4-31B-it` revision `842da3794eaa0b77d5f08bae87a17459d91ff475`를 유지했다. Sol이 코드·H200 실행·비본문 보고를 맡고 Astra가 웹 출처를 직접 읽어 발췌를 제공했으며 다른 Sol이 코드와 의미 표본을 독립 검토했다. |
| 진단·보강 근거 | 5/5 진단 JSON과 질문 7개를 보존했다. 질문과 모델 기억은 증거가 아니다. 같은 위키 revision의 추가 구간 6개와 국립한글박물관·UNESCO에서 직접 읽은 짧은 발췌 4개를 [보강 입력](../../data/analysis/private/ontology-trial/enrichment/extra-evidence.json) SHA `7b2009fed318380239f689bbfdbc7549adf694f1a0d7ea1b68667197ceefe598`에 고정했다. 두 기관 페이지 위치는 기존 한글 결함을 토대로 진단 전 조사됐으므로 완전 자율 검색으로 주장하지 않는다. |
| 실제 재추출·검증 | 첫 시험 27후보·25원문 좌표 연결·2보류. 같은 개선 프롬프트의 wiki-only 5/5 파싱·30후보·21연결·9보류, 보강군 5/5·32후보·26연결·6보류. 원시 출력을 수정하지 않았다. [비본문 비교](../../data/analysis/ontology-trial-enrichment-comparison.json)와 [사람용 결과](../research/20260927-gemma4-31b-wikipedia-ontology-trial.md)에 군별 판·SHA·의미 검토를 분리했다. 좌표 연결은 역사 사실 수락이 아니다. |
| 독립 의미 검토 | 추가 위키 근거로 문종 사망 H가 회복됐고 한글 발표를 transmission으로 바꿨다. 한글 K·재위 H 분리, Bloomery 공정 K, 단종 actor/affected 분리도 나타났다. 그러나 보류된 K를 참조하는 B, 세조 생몰=재위 혼동, 문종 문서 `Seyong` 대 세조 문서 `Suyang`의 미확인 표기 충돌 확정화, 상충하는 단종 사망 경위에도 actor 확정, 훈민정음 소개 글·해례 주석을 한 K로 결합한 문제와 책 출판·문자 발표 관계 및 시기 과잉 결합이 남았다. `Seyong`은 오기 **의심**일 뿐 동일성 조사를 하지 않았다. 원래 `moved to create` 검토는 전체 단락 문맥을 반영해 확정 허위에서 짧은 인용·추론 지위 부족으로 정정했다. |
| 완료·다음 행동 | 실제 두 군의 31B 후보 생성과 표본 독립 검토 완료, **현실 온톨로지 릴리스 미발행**. 위키 6개와 웹 4개를 함께 더해 웹 단독 기여는 알 수 없다. 다음 작은 개선은 모델 재타이핑 인용 대신 고정 문장·source-unit ID를 참조하고, 사건 역할·K 참조 상태·문자/책·시간 역할을 검수하는 것이다. 이번 결과를 정본 DB나 작품에 자동 편입하지 않는다. |

## 이전 작업 카드 — `WIKI-31B-FIRST-TRIAL-20260927`

| 항목 | 실제 기록 |
|---|---|
| 요청·범위 | 사용자는 병렬 작업 구조 검토 도중 우선 H200에서 Gemma 4 31B로 실제 온톨로지화를 시켜 보고 싶다고 범위를 정했다. 문체 본학습이나 위키 전량 처리로 확대하지 않고 실제 덤프의 작은 선택 구간으로 추론했다. |
| 담당·소유 | Sol이 입력 추출·실행 코드와 원격 쓰기, 다른 Sol이 자원·결과 독립 검토, Astra가 범위와 보고를 맡았다. 기존 문체 학습 결과·코퍼스 DB를 변경하지 않았다. |
| 고정 입력 | 2026-09-01 enwiki의 두 bz2 shard를 동봉 `SHA256SUMS`와 대조했다. Bloomery·문종·단종·세조·한글 5페이지에서 각각 한 단락만 사용했다. 원문 합계 3,414바이트, [입력 패킷](../../data/analysis/private/ontology-trial/trial-packet.json) 6,759바이트·SHA `e47b8e0785d55d5928bce4766f80d65a5195f7e86c62333c2c621aa541f99918`. page/revision/main slot·UTF-8 좌표·원문 해시를 보존했다. |
| 실제 실행 | 기존 전용 H200에서 `google/gemma-4-31B-it` revision `842da3794eaa0b77d5f08bae87a17459d91ff475`를 BF16·단일 GPU·batch 1로 실행했다. 모델 파일 62,578,686,256바이트를 원격 전용 캐시에 보존했다. 이번에는 공개 위키 선택 구간과 실행기를 전송했으며 덤프 43.26GiB 전체를 업로드한 것은 아니다. |
| 결과·기계 대조 | 5/5 JSON 파싱, 모델 분류 H 14·K 4·B 9의 후보 27건과 원문 출처 F 5건. 25건은 정확한 인용을 원문 좌표에 연결했고, 2건은 모델이 인용에 `...`를 넣어 보류했다. 25건의 좌표 연결은 의미 수락이 아니다. 원격 원본 출력 5개의 로컬 해시 일치를 확인했다. [검증·검토 기록](../../data/analysis/ontology-trial-verification.json), [후보와 원문 좌표](../../data/analysis/private/ontology-trial/verified.json). |
| 의미 검토 | 다른 Sol이 한글 창제와 세종 재위 시기 혼동, 일반 제철 공정의 B 분류, 한글 독립 K 객체 부재, 단종 처형의 주체·대상 표현 오류, 문종 사망 사건 누락을 확인했다. 원본 모델 출력을 수정하거나 모두 수락으로 바꾸지 않았다. |
| 완료·다음 행동 | 31B의 실제 후보 추출 시험은 완료했고 현실 온톨로지 릴리스는 미발행이다. 현재 출력은 원문에 연결한 주장 후보이며 완성된 객체·사건·브리지 그래프가 아니다. 후속 작업은 확인된 유형·시간·역할·누락 문제를 출력 계약과 검증에 반영해 같은 원문으로 재시험하는 것이다. 대략적인 1950 범위와 원문 시기 불확실성 보존 원칙은 유지한다. |

## 이전 작업 카드 — `PRODUCT-I2-FIRST-RUN-20260927`

| 항목 | 실제 기록 |
|---|---|
| 요청·범위 | I1 완료 후 사용자가 실제 한 회차 DB 분석, 역할·분할 고정 학습 릴리스와 `toy-tune` 연결, 소규모 H200 시험 진행을 승인했다. 실행 장소는 [kt cloud AI Nexus](https://www.ainexus.ktcloud.com/start)다. |
| 담당·소유 | Astra 조율, Sol 단일 구현·DB writer, 새 문맥의 Luna가 Poland 공식 1화만 분석, 다른 Sol이 DB 제출판과 구현을 독립 검토한다. 원본 소설 파일 전체를 모델 입력으로 사용하지 않는다. |
| 실제 1화 완료 | 고정 task `analysis:098856379b3c23f4f3cd49452e817d65f4eea46fb75cf8c14ea276c247365711`, source revision 7·segmentation 16·segment 4599·CP `[0,6830)`. v1은 근거 보완을 요구한 `hold`로 보존했다. 운영 DB의 `poland-ch01-i2-luna-v2` SHA `70f756aefc1bff5d88cf0958785de10b7ec54316e98290c8e4f831f6304ec64a`를 다른 Sol이 수락했다. review `sol-poland-ch01-i2-r2` SHA `76e9790a94e05945d4a0bbb78ba4d344be4389da537784db31bd3636b4d10d29`, `resume=complete`. 이는 1화 분석 검수이며 학습 채택·작품 정사 승인이 아니다. |
| I2 운영 발행 | 운영 DB에 문체용 `ds-gemma-style-a1e745929adcaf879446ad42` 90건(56/16/18)과 기획용 `ds-sota-planning-d55cd8d4e7820b9bf479e997` 182건(117/35/30)을 발행했다. 같은 요청의 재발행은 `created=false`다. 운영 패킷 SHA `0933b27524205b86bb6898a7537f2cd0bf6125f644fe65c04c38d4f0aa2aaf49`는 사본과 같고 `toy-tune` 준비·검증을 통과했다. 후속 실제 실행 요청 `i2-gemma4-e2b-h200-20260927`·attempt `h200-a1`을 등록했다. CPU 데모는 운영 DB에 넣지 않았다. |
| 검증·복구 | [비본문 검증 기록](../../data/analysis/product-i2-training-verification.json)에 실제 DB·패킷·검토 근거를 남긴다. 다른 Sol이 CPU 구현을 수락했고 Luna도 source·legacy 11개 테이블의 행 해시, 승인 272건 결박, 패킷과 준비 파일을 대조해 불일치 0건을 확인했다. 운영 발행 전 [백업](../../data/analysis/novel-corpus-before-i2-release-20260927.sqlite3) SHA `da0d04cd47b9f991f5ccf09e9786d5b4e13ada7b9713965dc9ab78fc0cdca716`을 보존했다. 운영 전후 source·legacy 11개 표의 전행 digest·건수 변화 0, FK 오류 0, 무결성 `ok`다. CPU 준비 manifest의 `pending_real_tokenizer`는 당시 기록으로 보존하고 실제 모델 검사는 별도 결과에 남긴다. |
| 실제 토큰 검사 | 사용자가 승인한 고정 패킷을 AI Nexus에 전송해 SHA 일치를 확인했다. 고정 Gemma4Processor로 90/90건의 토큰화·입력 접두 일치·정답 손실 마스킹 경계를 확인했다. 최대 7,162토큰이며 49건이 이번 시험의 2,048토큰 한도를 넘는다. 학습할 train 표본 ID와 순서를 요청에 명시하고 한도 안의 두 건만 선택했다. 개발 검증·holdout 자료는 optimizer에 넣지 않았다. |
| 고정 실행판 | 원격 준비판 `ds-fcdce4cdb8ff8cb6a15190b7`·manifest SHA `994b223add315d5f6be6ac0baa434874f6fe810d1b248375204c7f318c4dedf8`는 로컬과 일치한다. a1은 실제 E2B 텍스트 계층 선택 검사에서 optimizer 0스텝으로 실패했고 DB에 보존했다. 수정한 a2 요청 SHA는 `b75a4480342071a34fc047c18b011d296ac5f2855191ccce9978edbf0365b04a`다. 학습 소스 SHA `5de784db91e51c3f62b3055f27ecee815a9a065971a2c46aec7630ff4d3b96b8`, CLI 반환 오류 수정 후 재로딩 소스 SHA `91e8f52affffa86c4d449a4469c6efa0ee82138049c4291bf924a259ec48489a`를 각각 다른 Sol이 수락했다. optimizer 입력은 `gogjong-001-005`(773토큰), `gogjong-009-001`(440토큰) 순서의 train 두 건이다. |
| H200 실제 실행 | 전용 세션 `novel-toy-i2-20260927`(ID `a8de8c46-daea-4cfe-8ede-9774b9755781`)과 영구 폴더 `/home/work/novel-toy-tune`를 사용했다. 실제 NVIDIA H200 143,771 MiB·Python 3.12.3·PyTorch `2.10.0a0+b558c986e8.nv25.11`·CUDA 13.0, 별도 venv의 Transformers 5.17.0·PEFT 0.18.0에서 Gemma E2B-it revision `3e22461f65e89153144f8adb70e3b8c2cc9845a7`을 실행했다. a2는 2스텝 학습·유한 손실값·LoRA 값 669,696개 변경·어댑터 저장에 성공했고 새 프로세스 재로딩 후 3토큰을 생성했다. 이는 실행 연결 검사이며 문체 품질·일반화 평가가 아니다. |
| 실제 결과 근거 | [a2 회수 결과](../../data/analysis/private/i2/remote-results/h200-a2/result.json) SHA `75ee0f19982f9c7fe130578a1fe121a973d36244641fc5d732329c4b59f7d168`, 학습 보고서 SHA `089f53f28e3f1969cc04ce783ffd1120c6ab9c7c4937628ef83bc6ebe1bf00a5`, 재로딩 보고서 SHA `6be9ff4002325c167a43cab47e979e6ad022e9bb12efd433879a805a74cd7436`, 어댑터 SHA `99988871b5e62b279ce40fc5b85a7ba579ae4673551cbdebcd603029ab5b8e77`. 원격과 로컬 파일의 SHA가 일치한다. 다른 Sol이 실제 결과와 반입 코드를 독립 수락했다. |
| DB 모델 후보 | 로컬 어댑터 경로로 연결한 결과 SHA `01e829dd88bdf7894eb862ae3b63c8f51b6e1ab7fa67d16fbf73bf5b5be02879`를 반입해 a2를 완료로 기록했다. 모델 후보는 `model-f2638e4194ec1c3057276497`, `writing_eligible=false`다. 같은 결과 재반입은 `created=false`이며 a1 실패를 보존했다. 반입 전 백업과 운영 DB 검증 근거는 [검증 기록](../../data/analysis/product-i2-training-verification.json)에 있다. 원문·legacy 11표의 전행 변화 0, 무결성 `ok`, FK 오류 0이다. |
| 재개·다음 행동 | 공식 1화 분석과 DB 릴리스→고정 패킷→H200 학습·저장·새 프로세스 재로딩→DB 모델 후보 연결 시험을 완료했다. 다음 문체 학습에서는 길이 초과 자료의 처리와 본 학습·문체 평가 범위를 정한다. 원격 영구 폴더와 로컬 private 결과를 보존하며 SSH 키를 본문·문서에 복제하지 않는다. 전체 350화 분석·현실 역사 DB·집필 RAG·집필 모델 채택은 이번 완료 범위에 포함하지 않는다. |

## 이전 작업 카드 — `PRODUCT-I1-MIGRATION-20260927`

| 항목 | 실제 기록 |
|---|---|
| 요청·범위 | 사용자가 상태 이관과 뷰어·반출 전환 설명 뒤 “그래 전환하자”라고 승인했다. 기존 역구성 결과·선정·검토 상태를 이관하고 뷰어와 학습 파일의 입력을 DB로 전환했다. 새 소설 분석이나 실제 모델 학습은 실행하지 않았다. |
| 담당·소유 | Sol 단일 DB writer가 이관기·제품 CLI·기존 명령 전환을 구현하고 별도 Sol이 뷰어·반출을 구현했다. 다른 Sol이 최종 실행 코드와 사본의 원자료·결과를 독립 검토·수락했다. Luna는 운영 전 기준선과 추가 기계 대조를 맡았다. |
| 실제 운영 상태 | `data/analysis/novel-corpus.sqlite3`의 고정 `import_id=reverse-20260925-i1`에 수락 후보 **272**·보류 후보 **21**, 선정 **174**·시도 **294**(후보 미생성 보류 **5**), 검토 수정본 **88**, 원자료 아티팩트 **990**을 보존했다. I1 이관 완료 당시 신규 분석용 window/task/submission/review 네 테이블은 0건이었으며 이관된 역구성 자료를 새 화별 분석으로 간주하지 않는다. |
| 검증·복구 | [비본문 검증 기록](../../data/analysis/product-i1-migration-verification.json)에 사본·운영 검사를 남긴다. [이관 직전 백업](../../data/analysis/novel-corpus-before-i1-20260927.sqlite3)의 복원 검사를 완료했다. 원문 4개 표의 7/7/17/5,233행 값은 전후 동일하고 무결성 검사·FK 검사를 통과했다. 재이관은 멱등이며 원자료 990개의 경로·바이트·SHA가 DB와 일치한다. |
| 실행판·산출물 | 독립 수락한 실행 Python 14개 파일의 집계 SHA-256은 `3d6d0b358f7044ed6a45ec5abd41a1ff537e5bc8d7b4fe849fba30774f30bec0`. 제품 11·역구성 도구 30·코퍼스 8 테스트를 통과했다. [운영 DB에서 만든 뷰어](../../data/training/db-derived/reverse-20260925-i1/private/viewer/index.html)와 [학습 파일 목록](../../data/training/db-derived/reverse-20260925-i1/private/export/release-manifest.json)은 파생물이다. 신규 JSONL 9개는 기존 합본 9개와 바이트·순서가 같고 역할·분할도 보존한다. 브라우저 직접 조작은 도구의 로컬 파일 URL 제한으로 미검증이다. |
| 재개 방법·한계 | [제품 CLI](../../src/novel_factory/README.md)의 `legacy-status`로 기존 보류·검토 이력과 후속 대상을 찾는다. 고정 이관판을 수정하지 않으며 보류 후보를 새 분석 작업으로 자동 전환하지 않는다. 새 분석·교정은 별도 DB 작업을 등록해 제출·독립 검토한다. [뷰어·반출 도구](../../tools/reverse_dataset/README.md)는 지정한 DB 판만 읽고, 옛 파일 쓰기 명령은 종료했다. |
| 다음 행동 | 이관·뷰어·반출 전환은 완료했다. 이후 구현은 [통합 실행 계획](../plans/20260918-current-system-execution-plan-v0-1.md)의 다음 절편으로 배정한다. 350화 의미 분석, Gemma 학습, 현실 역사·작품 개변 DB 및 집필 RAG는 이번 완료 범위가 아니다. |

## 이전 작업 카드 — `PRODUCT-I0-I1-FIRST-20260927`

| 항목 | 실제 기록 |
|---|---|
| 요청·범위 | 사용자가 “제품 구현 시작”을 승인했다. [통합 실행 계획](../plans/20260918-current-system-execution-plan-v0-1.md#5-하네스-연결과-실제-첫-작업-묶음)의 첫 절편만 구현했다. 기존 272건 전량 이관, 350화 의미 분석, GPU 학습, 현실 역사 DB·작품 정사는 이번 완료 범위가 아니다. |
| 담당·소유 | Sol 엔지니어가 제품 코드·운영 코퍼스 SQLite 단일 writer, 다른 Sol이 코드와 DB 제출물 조회 경로를 독립 검토, Luna가 실제 코퍼스 **사본**의 원문 위치·hash·상태 격리를 대조했다. |
| 입력·산출 | 기준은 [시스템 설계](../systems/README.md), [구현 계획](../plans/20260918-current-system-execution-plan-v0-1.md), 원문·분할판 `data/analysis/novel-corpus.sqlite3`. [제품 CLI·사용법](../../src/novel_factory/README.md)은 고정 회차/승인 구간의 `prepare → submit → DB의 view-result → 다른 검토자의 review → resume`를 제공한다. 기존 `show-window/show-unit`은 등록된 DB 구간과 동결 메타가 일치할 때만 본문을 낸다. |
| 코드판·검증 | [비본문 검증 기록](../../data/analysis/product-i0-i1-verification.json)의 runtime code 집계 SHA-256은 `958389d1605a94229affa66cea730b5398999f8522d53e763c2282a1dcdd8fd5`. 제품 7·코퍼스 8·역구성 도구 23 테스트, `.venv-product` editable CLI 실행, 원문 코퍼스 `verify`, `git diff --check`가 통과했다. Sol 독립 수락과 Luna 사본 대조를 완료했다. |
| 실제 DB 전환 | 운영 DB를 [복구용 백업](../../data/analysis/novel-corpus-before-i0-20260927.sqlite3)으로 보존·복원 시험한 뒤 **빈** 분석 window/task/submission/review 테이블만 추가했다. 원문 `works` 7·`source_revisions` 7·`segmentations` 17·`segments` 5,233행의 전체 행 hash가 전후 동일하고 무결성 `ok`/FK 오류 0이다. 운영 분석 네 테이블은 모두 0건이다. 합성 결과는 별도 사본에만 저장했다. |
| 검증 표본·한계 | Poland 공식 1화와 과거 검토된 별도 target span을 사본에서 source revision·segmentation·CP·SHA로 대조했고, 합성 제출·독립 검토·재개 및 DB 제출 원바이트 조회를 시험했다. `full.py` 순차 window의 다음 구간은 앞 구간 DB 검토 전 출력되지 않는다. 272개 역구성 JSONL·기존 HTML 뷰어/반출은 아직 DB 정본으로 이관되지 않았고 실제 화별 분석 카드·학습 투입도 생성하지 않았다. |
| 다음 행동 | Astra가 다음 I1 범위의 원본 JSON/CSV 검토·선정 상태 이관과 viewer/export 전환 작업 카드를 배정한다. 실제 분석자는 [CLI 사용법](../../src/novel_factory/README.md)에 따라 고정 입력을 받고, 결과·독립 검토가 없으면 `resume`을 완료로 취급하지 않는다. I2 문체학습·I3 역사 구축은 별도 단계다. |

## 이전 작업 카드 — `REVERSE-DATASET-20260925`

| 항목 | 실제 기록 |
|---|---|
| 요청·범위 | 사용자가 기존 원문으로 역구성 데이터셋 제작을 요청하고, 고종은 Gemma 문체용·고려와 폴란드는 SOTA 기획용으로 분리하며 각 작품 전체 원문에서 장면을 선정하도록 확정했다. 실제 모델 학습·원문 DB 변경·외부 게시·추가 Git 커밋은 이번 범위에 포함하지 않는다. |
| 역할·모델 | Astra가 조율하고 작품별 Luna가 후보를 작성·교정하며 작가별 Sol이 검토한다. 현재 실무·검토 모델은 **Sol 6.0**이다. 실행 수단은 모델과 별도로 기록하며 Codex CLI를 필수 조건으로 고정하지 않는다. |
| 원문·입력 | 원문 코퍼스는 `data/analysis/novel-corpus.sqlite3`. [초반 동결 manifest](../../data/training/reverse-20260925/source-manifest.json)의 SHA-256은 `ea0764d58e109bdb828b5143e2bf9d88a933594d3a7ab583b7b3c00b71046e80`, [전편 추가 선정 manifest](../../data/training/reverse-full-20260925/source-manifest.json)는 `938626b283e4fe93c9efcecb905c9cf025e297857cc40a16f0df0db82909a811`이다. 각 판의 [초반 분할 정책](../../data/training/reverse-20260925/split-policy.json)·[전편 분할 정책](../../data/training/reverse-full-20260925/split-policy.json)을 보존한다. 무번호 표제 구간은 공식 회차 번호로 간주하지 않으며 장면을 회차의 하위 단위로 강제하지 않는다. |
| 현재 산출 | [초반 수락본 150개](../../data/training/reverse-20260925/quality-report.json)와 [전편 추가 수락본 122개](../../data/training/reverse-full-20260925/quality-report.json)를 작품·분할별 JSONL 9개로 합쳤다. [합본 목록](../../data/training/reverse-full-20260925/bundle-manifest.json)의 SHA-256은 `25d4e6981b30062bfbc550eb9f1aab4d636ac1311c454c56db2f6da6f7aa004d`이다. 고종 90개(Gemma 문체), 고려 96개·폴란드 86개(SOTA 기획), 총 **272개**이며 `train` 173개·`development_validation` 51개·`development_holdout` 48개다. 고종의 실제 학습 분할은 56개다. 파일은 `data/training/reverse-full-20260925/private/bundle/`에 있다. |
| 검토·보류 | 작품별 Luna 작성·교정과 작가별 Sol의 현재 파일 SHA 재검토를 마쳤다. 전편 선정 창 144개에서 후보 141개를 만들었고 122개 수락·19개 후보 보류·3개 생성 보류로 끝냈다. 보류는 합본에서 제외했다. 초반판의 후보 보류 2개, 미확정 고종31 구간과 절차 위반 폴란드42 구간도 유지한다. 상세 근거는 [고종 최종 검토](../../data/training/reverse-full-20260925/private/orchestration/sol-gogjong-full-rereview.json)·[마늘맛스낵 최종 검토](../../data/training/reverse-full-20260925/private/orchestration/sol-garlic-full-rereview.json)에 있다. |
| 상태·검증 | 데이터셋 제작·출력·검토를 완료했다. [출력 실행 기록](../../data/training/reverse-full-20260925/private/orchestration/full-export-result.json)과 [Luna 독립 기계 검증](../../data/training/reverse-full-20260925/private/orchestration/luna-cross-release-verification.json)에 원본 출력 18개·합본 9개 파일의 실제 건수·해시, 수락 결정·원문 좌표 결박, 겹침·중복 없음, 정확한 합본을 기록했다. 독립 검증 보고서 SHA-256은 `425b69e16e8a4610f197fdbcfbd87c5043166aa83b1fb3f4f4d4c4983e37b117`이다. 실행 경로와 최종 담당 기록은 비공개 [작업 상태](../../data/training/reverse-20260925/private/orchestration/root-state.json)에서 재확인한다. |
| 실제 데이터 열람 | 사용자의 후속 요청으로 [단일 HTML 뷰어](../../data/training/reverse-full-20260925/private/viewer/index.html)를 만들었다. 실제 272개 레코드·입력·정답·근거 원문을 내장하고 작품·용도·분할·판본 필터, 검색, 원본 JSON 확인을 제공한다. [생성 스크립트](../../tools/reverse_dataset/viewer.py)는 원문·JSONL을 읽기 전용으로 대조한다. 외부 의존성이 없고 원문 포함 HTML은 Git에서 제외된다. 브라우저 도구의 로컬 파일 URL 정책으로 실제 UI 조작은 확인하지 못했으며 데이터 일치·JavaScript 구문·정적 점검 결과만 기록한다. 상세 실행은 [뷰어 작업 기록](../../data/training/reverse-full-20260925/private/orchestration/viewer-task.json)에 있다. |
| 다음 행동·한계 | 데이터셋 제작 다음 단계는 대상 Gemma 모델의 토크나이저·대화 템플릿·손실 마스킹과 입력 길이를 점검하고 평가 방법을 정하는 것이다. 이 단계와 실제 모델 학습·성능 평가는 아직 실행하지 않았다. 세 작품은 이미 읽은 개발 자료이며 어떤 분할도 미관측 최종 test로 주장하지 않는다. SOTA 기획 표본은 원문에서 역구성한 계획이며 작가의 실제 의도나 역사적 사실의 정본이 아니다. |

## 이전 작업 카드 — `DOC-HARNESS-IMPLEMENT-20260925`

| 항목 | 실제 기록 |
|---|---|
| 요청·권한 | 사용자가 문서 생애주기 계획 구현을 요청. 전용 CLI·SQLite·의미 검증·초기 비파괴 적재까지 허용하며 소설 원문 DB, 전체 문서 일괄 개정, Git commit은 범위 밖. |
| 담당·소유 | Astra 루트 조율, Sol 단일 구현·DB writer. Luna는 [초기 manifest](../../data/document_harness/initial-import-manifest.json)와 DB 읽기 점검, 다른 Sol은 독립 코드 검토. |
| 산출 | [CLI와 사용법](../../tools/document_harness/README.md), [설계·상태](document-lifecycle.md), `data/document_harness/documents.sqlite3`와 초기 manifest. 2026-09-25 초기 `docs/`·`plan/` Markdown 99개·1,178,728 bytes를 원본 불변의 legacy·`canon=false`로 적재. 이후 하네스 관리판 5개를 명시 채택했고 현재 DB는 총 108판이다. 기존 인벤토리 대비 소스 해시 변경 0건. |
| 검증 | Python 단위 테스트 7개 통과. 초기 DB `integrity_check=ok`, 문서판 99, `canon=1` 0, FTS 99. Luna가 manifest 99개 경로·크기·SHA-256과 DB 본문 재해시 99/99를 읽기 전용 확인. 하네스 문서 4개와 도구 안내를 같은 계통의 관리판으로 전환·명시 채택했다. 임시 목적지에 실제 SQLite backup→restore→verify를 실행해 복원본 108판·canon 5·무결성 ok를 확인했다. 다른 Sol의 독립 코드 검토는 `harness.py` SHA-256 `1748d50fd17c16640901f7410c0344997338b08b10dce630247652d99245dc35`, 테스트 SHA-256 `54af3db45663f2e52d49a4bfd39c364928b9ec1d8d81982ff1d8f0d3dced824d`를 기준으로 필수 미해결 없이 수락했다. |
| 다음 행동 | 최종 관리판과 [전용 DB 백업](../../data/document_harness/documents-20260925-final.sqlite3)의 복원 검증을 완료했다. 다음은 Astra의 읽기 전용 최종 스냅샷 대조·보고다. 후속 문서 선택은 사용자의 명시적 선택과 공용 `finalize` 경로를 따르며 미분류 legacy 문서는 임의 채택하지 않는다. `canon=false`인 기존 문서 99개의 적용 여부는 자동 결정하지 않는다. |

## 이전 작업 카드 — `HISTORY-ONTOLOGY-FUN-FIRST-DOC-20260924`

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
