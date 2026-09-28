---
category_id: research
lineage_id: lin-29a57b9b-1f6c-4747-b478-6e7fb790629e
document_id: doc-d21a5daa-765c-4e03-885d-932a92c7c615
parent_lineage_id: null
abstract: YAGO 4.6 세계사 1899년 이전 시간 근거 전역 스캔의 실제 진행, 증거, 발행 전 검증과 남은 범위를 기록한다.
version: 0.0.4
created_at: '2026-09-28T23:07:21.000000Z'
updated_at: '2026-09-28T23:40:36Z'
tags:
- YAGO
- 역사온톨로지
- PostgreSQL
- 현실전표
canon: false
---
# YAGO 4.6 세계사 기초 SoT — 1899년까지

**상태: H200 전역 스캔 진행 중, 현실 릴리스 미발행.** `meta`와 `facts` 파일 단계는 완료됐지만 뒤의 파일·연결·보조층·전량 독립 수락은 대기 중이다. 이 보고의 중간 수치를 전체 파이프라인의 최종 분모로 읽지 않는다. 사용자 결정의 “1800년도까지”는 1800년대 전체를 포함한 **1899년 이하 모든 명시 연대**다. 앞선 다섯 대상 r3 파일럿은 그대로 보존하며 이번 범위의 전역 분모로 세지 않는다. 이 릴리스가 완성되더라도 YAGO 출처에 결박한 기초판이며 사료 원문 대조로 확정한 역사적 참, 작품의 사용 적격·정사 또는 작가 역사표 잠금은 아니다.

## 고정 입력과 작업 경계

- [YAGO 4.6 원본 manifest](../../data/research/yago-storage-20260928/manifest-final.json) SHA-256 `da0d761331e3ccb070bfebbc5ecf4ad5db4165eac0ef5bc619444d95f78a70bb`. H200 Storage `/home/work/novel-toy-tune/sources/original/yago/4.6/extracted/`의 해제 원본 12개, 합계 78,426,497,491B를 덮어쓰지 않는다. 이번 사실 분모 대상은 `facts` 5,087,821,943B, `beyond-wikipedia` 17,209,268,126B, 시간 부모 근거 `meta` 720,870,838B다. `taxonomy` 218,444,322B 및 두 labels 파일 13,868,829,973B·31,891,847,744B는 연대 사실과 분리한 보조층으로 스캔한다. schema·log·tiny·entity JSONL은 어휘·생성 기록·중복 절편/인덱스이므로 현재 사실 분모에 넣지 않는다.
- 기준 절차는 [YAGO 역사전표 SoT 방법론](../methods/history-ledger-sot.md) SHA-256 `2f8eaa88d3647bd4835d383dca8000907d34261053b0a56c0f00a2f124bb6847`이다. 실제 선택/제외는 [새 배치 코드](../../tools/yago_history_sot/build.py), [회귀시험](../../tests/yago_history_sot/test_build.py)의 별도 정책 `yago46-world-through-1899-v1`을 쓴다. 파일럿의 다섯 대상 상수와 4자리 양수 연도 parser를 전역 규칙으로 재사용하지 않았다.
- 새 전용 Storage 작업 폴더는 `/home/work/novel-toy-tune/reality-yago46-through-1899-20260929`, 새 PG16 DB는 `reality_yago46_through_1899_20260929`다. 기존 `reality_sot_pilot_20260929`, `ontology_expanded`, GPU/모델과 Wikidata 원본 다운로드 PID 38511을 변경하지 않았다. 이 문서 시점 PID 38511은 살아 있었다.

## 선택 정책과 재구성

원본 TTL을 한 줄씩 읽어 입력 SHA와 줄·byte 좌표, raw RDF 진술, RDF* Meta 부모 key를 보존한다. Meta 원본의 술어는 `schema:startDate`·`schema:endDate`·`yago:onDate`를 인식하며, 원 문자열·정밀도·원 달력 미상을 유지한다. 명시 생몰일만 `H_event`, 대상 자체 `startDate`/`endDate`는 `H_boundary`, 양쪽 Meta 구간이 있고 제한된 상태 술어에 속하는 진술만 `H_state`다. 1890~1910처럼 경계를 넘는 상태는 원 종료 1910을 보존하고 1899 이하 조회 범위만 제한한다. Meta 한쪽 경계만 있으면 열린 무한 상태로 수락하지 않고 `dated_boundary_candidate`로 격리한다. `onDate`의 임의 속성은 관찰 후보, `rdf:type`·분류는 K/보조층으로 남긴다. 1900년 이후 날짜는 1800년대 수락 주장으로 누출하지 않는다.

직접 `schema:startDate`의 `H_boundary`는 주체 유형을 가리지 않는 **원 진술의 시작 경계**다. 예컨대 작품·언어·문자 체계에 붙은 시작일을 해당 시대의 사용 증명이나 K 자료의 기원 검증으로 읽을 수 없다. 기존 다섯 대상 r3와 동일한 역할 분류를 강제하지 않으며, r3의 50개 원진술이 새 claim·보조층·보류 장부 어디에 놓이는지는 전량 stage 완료 뒤 원 source 줄로 대조한다.

기원전 부호 연도는 원문과 명목 signed year를 함께 기록하고 역법은 `unknown`으로 둔다. 0년·미지원 날짜·불가능한 월일은 사유와 좌표를 가진 `unknown` 장부에 남긴다. 출생 연도가 이전이라는 이유만으로 같은 주체의 후대 개별 진술을 앞당기지 않는다. 시간 없는 주장은 자체 유효시간이 계속 미상이다. 같은 주체의 **유일하고 순서가 맞는 출생·사망 앵커 둘 모두**를 가진 경우에만 별도 `context_anchor` 근거를 저장하고, 관련 무시간 진술을 `context_hint` 보조층에 둔다. 이것은 생애 전체의 주장 유효성이나 출생·사망 장소 발생일 확정이 아니다. 모든 채택 claim 주체의 label·type 연결은 disk index로 선별하며 역사 사실 분모와 분리한다.

이 보수적 문맥 규칙은 **1900년 이후 사망일이 알려진 인물**을 양쪽 앵커 문맥층에서 제외한다. 따라서 1880년 출생·1905년 사망자의 무시간 `deathPlace`가 1899년 이전 상태·문맥 조회에 누출되지 않지만, 같은 인물의 `birthPlace`도 이번 문맥층에는 들어오지 않는 누락이 있다. 양쪽 앵커가 모두 1899년 이하인 인물의 `birthPlace`·`deathPlace`는 현재 일반 `context_hint`일 뿐, r3처럼 출생·사망일에 결박한 좁은 `inferred_event_bound` 후보를 구현하지 않았다. 이 보조층을 당시 현재 상태나 특정 발생 연도라고 읽지 않는다.

각 대상 파일의 모든 행은 압축 TSV 장부에서 `line → mapped/excluded/unknown/failed + reason`으로 추적한다. 선택 claim은 전용 PG에 source 파일·줄·byte 좌표·raw·triple key·시간 근거와 lane을 둔다. 원본 Meta 6,221,745행은 stage SQLite에 보존해 선택 부모와 연결한다. stage는 완료 파일 receipt의 원본 SHA·압축 장부 SHA·PG 행수와 Meta bloom 검증 후 재사용하며 미완료 파일은 해당 파일 시작부터 삭제·재처리한다. 최종 `publish`는 독립 Sol의 code/manifest/**정확한 staging readback**·receipt bundle·행수 수락 영수증 없이는 거부한다. 전체 DB readback, 부모 링크, 파일별 회계, 불변 trigger를 발행 때 다시 검사한다.

## 실제 실행·검증 상태

첫 코드 SHA `e46070d3ef8336caefa7145c5b41e6b1be4c03cf6c5ccff58161f886bc2b1eaf`는 Meta 전체를 읽고 원본 SHA `d6ddcf0803a13fcf69f3b32df2c6f817fc6a807c27bd9cae429287dbc460c020`과 대조했다. Meta **6,221,779행/720,870,838B** 중 시간 Meta 6,221,745·헤더 34였고 최대 RSS 72MiB, 약 41초였다. 다음 facts 시작에서 `time` 이름 충돌로 종료되어 첫 실행은 **exit 1, 사실 파일 적재 0**이다. [실패판 코드·receipt·로그](../../data/research/yago-sot-through-1800-20260929/run-evidence/first-attempt/)를 보존했다. 수정판은 Meta SQLite 부모 key로 32MiB bloom을 재생성해 원본 bloom과 일치시킨 [재개 검증](../../data/research/yago-sot-through-1800-20260929/run-evidence/first-attempt/meta-bloom-verification.json)을 남긴 뒤 진행했다.

수정 실행 코드 SHA `ad4f94668b380e4344c391deaaecc8b2ec104291100b0b4544879063a8534932`로 `scan-v2.log`/PID 39714가 H200에서 실제 실행 중이다. [완료된 `facts` 영수증](../../data/research/yago-sot-through-1800-20260929/run-evidence/facts.receipt.json) SHA-256 `a1a20000092e3a49e859d813475d44547e0683d3eaaa84a2894e2c66453d9f81`은 원본 **74,497,030행·5,087,821,943B**, 원본 SHA `17da906cefea15aa076ccfd5ce0bd2956b2e95ae06b225cca18059bbaf5eb1e4`와 manifest 일치를 기록한다. 분모는 mapped 918,825 + excluded 4,170,181 + unknown 69,408,024 + failed 0 = 74,497,030이며 전용 PG의 `source_file='facts'` claim 918,825행과 일치했다. 압축 장부 SHA는 receipt에 고정했다. 이 완료는 `facts` 한 파일 단계의 입력·회계·행수 대조이며 선택 주장의 역사적 참이나 전체 릴리스 수락이 아니다.

**2026-09-29 08:37 KST 무렵 `scan-v2.log` 중간 관찰**은 이어진 `beyond-wikipedia` 33,000,000행·2,157,461,609B, 해당 단계 532.1초·평균 62,022행/초·최대 RSS 95MiB였다. 그 파일 17,209,268,126B의 완료 receipt는 아직 없고 Meta 연결, 두 번째 context pass, taxonomy·labels 전체 처리도 대기 중이다. 따라서 현재 **릴리스 ID 없음, 완성 DB 주장 없음**이다. detached 프로세스가 멈췄다면 `scan-v2.exit`, `scan-v2.log`, 단계 receipt·PG 행수를 먼저 대조한다.

[Luna의 초기 실제 초안 기계 점검](../../data/research/yago-sot-through-1800-20260929/mechanical-review/initial-draft-check.json) SHA-256 `4f8dbfde67805fb8bad9ee583017498bb73fc55cee6d98a6414d515f6deeb4cf`은 `facts` **1~7,000,000행 범위**의 고정 읽기 전용 snapshot에서 선택 claim 93,967건을 확인했다. 명시 point year 1899 초과 0, `H_state` 원 종료가 1899를 넘는 694건 모두 검색 상한 1899, 원본 byte 좌표 표본 11건 일치를 보았다. 이는 전량 `facts`나 아직 실행 전인 Meta 연결·문맥·보조층 검사가 아니다. [다른 Sol의 코드 검토](../../data/research/yago-sot-through-1800-20260929/independent-review/scan-code-acceptance-ad4f9466.md) SHA-256 `68036d1d0560a34fb246da961174a2337daeff73aa91f4c51cbcf769fc28d3ab`은 **ad4f 코드의 가역 초안 스캔만** 수락했다. 실제 전량 출력·불변 릴리스의 독립 수락은 아직 없다.

로컬 순수 회귀시험은 `python3 -m pytest -q tests/yago_history_sot/test_build.py` **8/8 통과**했다. [synthetic 별도 PG 관통 시험](../../data/research/yago-sot-through-1800-20260929/run-evidence/smoke/)은 원본과 분리한 작은 fixture에서 Meta→facts/beyond→context→taxonomy/labels→재개 readback을 실행했다. claim 7·연결 Meta 4·auxiliary 10·context anchor 1, readback SHA `160a0f7a49719478ae8d50d7169ce8e7eb2e9a78cf2738e8a8359a6fcc4c22dc`; 잘못된 수락 readback hash의 발행 거부와 synthetic 발행 뒤 claim UPDATE 거부를 확인했다. 별도 [1905년 사망 장소 회귀 fixture](../../data/research/yago-sot-through-1800-20260929/run-evidence/deathplace-regression.py)·[출력 묶음](../../data/research/yago-sot-through-1800-20260929/run-evidence/deathplace-regression-bundle.tgz) SHA `5727c9c71475226e7874dcdceb7256fe8d1f919d78dc9557ced6a404d5357cb4`에서는 1880년 출생·1905년 사망 주체의 deathPlace가 1899년 이전 문맥 매치 0건이었다. 이것들은 **합성 기능시험**이고 YAGO 전량·의미 수락을 대신하지 않는다. 독립 Sol은 현 코드의 가역 초안 스캔을 검토했으며 전량 출력 수락은 아직 없다.

## 운영 확인과 안전 재개 명령

로컬에서 다음 고정 SSH 명령으로 H200에 접속한다. 비밀키 내용은 출력하지 않는다.

```bash
ssh -i /tmp/yago-h200-access-20260928/id_container -p 10659 -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/tmp/yago-h200-access-20260928/known_hosts work@proxy1.ainexus.ktcloud.com
```

원격 작업 폴더는 `/home/work/novel-toy-tune/reality-yago46-through-1899-20260929/`, 고정 실행 파일은 그 안의 `build.py`, 원본 선택 manifest는 `manifest-final.json`, Python은 `/home/work/novel-toy-tune/venv-gemma4/bin/python`이다. 이 파일의 DSN은 `host=/tmp/novel-ontology-pg-1100 port=55432 dbname=reality_yago46_through_1899_20260929`이다. 아래는 **상태 확인만** 한다.

```bash
cd /home/work/novel-toy-tune/reality-yago46-through-1899-20260929
sha256sum build.py manifest-final.json
ps -p 39714 -o pid,etime,rss,state,cmd
tail -n 5 scan-v2.log
test -f scan-v2.exit && cat scan-v2.exit
/home/work/novel-toy-tune/venv-gemma4/bin/python build.py status --manifest manifest-final.json
```

기대 SHA는 코드 `ad4f94668b380e4344c391deaaecc8b2ec104291100b0b4544879063a8534932`, manifest `da0d761331e3ccb070bfebbc5ecf4ad5db4165eac0ef5bc619444d95f78a70bb`다. **스캔 프로세스가 살아 있으면 재기동하지 않는다.** 프로세스가 끝난 뒤 `scan-v2.exit`와 오류 원인, `*.receipt.json`·`*-ledger.tsv.gz` 및 초안 DB 행수를 확인한다. 종료가 실패이고 입력·코드 hash가 기대값이며 오류가 해결된 경우에만 다음을 원격 작업 폴더에서 실행한다. `scan`은 완료 단계의 원본·장부·DB 행수를 확인해 재사용하고 미완료 파일은 처음부터 안전하게 재처리한다. 새 프로세스도 완료 시 **미발행 초안으로 정지**한다.

```bash
cd /home/work/novel-toy-tune/reality-yago46-through-1899-20260929
if pgrep -f '[p]ython -u build.py scan --manifest manifest-final.json' >/dev/null; then
  echo 'scan already running; do not restart'
else
  nohup sh -c 'nice -n 10 /home/work/novel-toy-tune/venv-gemma4/bin/python -u build.py scan --manifest manifest-final.json > scan-resume.log 2>&1; printf "%s\n" "$?" > scan-resume.exit' </dev/null >/dev/null 2>&1 &
fi
```

전체 단계 완료 후 `build.py prepublish --manifest manifest-final.json`의 출력과 실제 DB/receipt를 독립 검토한다. 구현자가 만든 수락 JSON을 쓰지 않으며, 다른 Sol이 정확한 `readback_sha256`·행수·receipt bundle을 결박한 수락 파일을 준 뒤에만 별도 `build.py publish --manifest manifest-final.json --acceptance <검토된-절대경로>`를 실행한다. 이 문서의 실행·재개 명령은 `publish`를 자동 호출하지 않는다.

## 재개와 미결정

실제 H200 `scan-v2`가 완료되고 모든 파일 receipt의 원본 SHA·분모 합계, PG 선택 행/Meta 부모, 1899/1900·BCE·미상·K 분리와 readback을 대조해야 한다. 그 뒤 Luna 기계 점검과 구현자가 아닌 Sol의 정확한 staging 출력 수락을 받아 `publish --acceptance`로 한 번 발행한다. 새 프로세스 질의, 동일 Storage `pg_dump`·별도 DB 복원/readback 대조, 문서 최종판 등록과 체크포인트 갱신을 남긴다. 완료 전 시점의 Wikidata 다운로드는 별도 진행 중인 원본 보존 작업이며 이번 YAGO DB에 적재하지 않는다. 전역 자료의 역사적 누락·오류, 원 Wikidata statement/rank/reference, 사료 원문 독립 검토, 작품별 ReviewScope는 이 기초 스캔만으로 해결되지 않는다.
