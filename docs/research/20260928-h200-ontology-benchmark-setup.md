---
category_id: research
lineage_id: lin-86b97f07-ba49-4164-b50d-9cde4e44c599
document_id: doc-ec183212-3b09-4e7a-b05a-9826bf6f2a4c
parent_lineage_id: null
abstract: 기존 추출 보존과 H200 BF16·FP8 배치 구성 점검의 실제 결과와 다음 실행 경계를 확인할 때 읽는다.
version: 0.0.2
created_at: '2026-09-28T02:37:55.000000Z'
updated_at: '2026-09-28T02:54:31Z'
tags:
- H200
- 위키백과
canon: false
---
# H200 고정 100단위 추론 구성 기록

이 기록은 사용자 승인으로 기존 위키 추출을 안전하게 멈추고, 같은 H200에 BF16 단일 vLLM 엔진(A)과 FP8 2·3엔진(B2·B3)을 **설치·기동·합성 응답**까지만 점검한 결과다. 고정 원문 100개를 각 구성에 한 번 넣는 총 300회 본측정은 아직 실행하지 않았다. 합성 요청은 위키 source-unit을 포함하지 않으므로 처리량·긴 출력 안정성·H/K/B 의미 품질의 증거가 아니다. 이 시험의 원문·후보 운영 정본은 기존 `ontology_expanded` PostgreSQL이며 별도 벤치마크 SQLite는 본측정 시에만 원시응답과 상태를 저장하도록 준비했다.

## 기존 추출 중지와 보존

중지 전 PID 9508 wrapper, 9526 extractor, 10349 post-extract watcher의 명령행과 작업 루트를 확인했다. watcher 다음 extractor에 TERM을 보내고 세 PID 종료·`remaining-exit-code.txt=143`을 확인했다. 중지 전후 DB 수는 **완료 1,090(모두 raw 보존), 실패 6(모두 raw 보존), 실행 중 1(raw 없음), 미시작 159**, 후보 검토 전 3,601·보류 2,623, 임베딩 2로 같았다. 원문은 255 page·138 wiki·3,303,431 byte를 그대로 유지했다. 실행 중 한 건 `ukwiki:413738:48336161:main:byte-35174-37858`은 완료로 바꾸지 않았고 watcher 최종 파일도 생성되지 않았다. GPU 사용 메모리 중지 전 81,287MiB와 후 0MiB는 두 순간 관측값이며 장기 활용률이 아니다. [중지 근거](../../data/analysis/private/ontology-benchmark-100-20260928/setup-stop.json) SHA-256 `5b4db5156c929a528e37f5f62c6324de12fdd4eb1520893cfc20fdbcb7b96d8a`.

## 고정 입력과 격리된 설치

H200 `main1`(143,771MiB, compute capability 9.0, driver 580.126.20)에 기존 가상환경·모델 캐시·PGDATA를 보존하면서 `/home/work/novel-toy-tune/venv-vllm-benchmark`에 `vllm==0.30.0`, Torch `2.13.0+cu130`을 설치했다. FP8은 `RedHatAI/gemma-4-31B-it-FP8-dynamic` revision `d4ab4f579dd3516f97d8a6a4c98d0653480bad15`의 18파일·33,300,479,335 byte를 전용 `models/fp8`에 두었다. A는 기존 `google/gemma-4-31B-it` 고정 revision `842da3794eaa0b77d5f08bae87a17459d91ff475`를 읽는다. FP8 모델 카드에 base 계통은 적혔지만 그 변형이 위 BF16의 **같은 base revision**에서 만들어졌는지는 확인되지 않았다. 따라서 향후 A/B 차이를 양자화만의 효과로 분해할 수 없다. INT8·4bit로 바꾸지 않았다.

기존 앱의 `expanded.py`, `domain.py`, 정식 매핑 CSV 7개의 원격·로컬 SHA 9/9가 같음을 확인했다. 전송한 새 파일은 benchmark runner·HTTP adapter·엔진 제어기 Python 3개와 원문 없는 [선정 JSON](../../data/analysis/private/ontology-benchmark-100-20260928/selection.json) 하나뿐이다. [전송 archive](../../data/analysis/private/ontology-benchmark-100-20260928/setup-bundle.tar.gz) SHA-256 `c02131f63a2af26191bdf5a7fbcb44b71b1f8401826cfb0e0eb773c6f2cf978b`, [4파일 manifest](../../data/analysis/private/ontology-benchmark-100-20260928/setup-bundle-manifest.json) SHA-256 `e4d6105f4dd9d87dbdf48caf9771c688dd2a8c336166c6de567492919905a46c`, [원격 배치 영수증](../../data/analysis/private/ontology-benchmark-100-20260928/remote-receipts/transfer-receipt.json) SHA-256 `3bd39b2c82c4ed77aabc2e75c20e3b519b640e387a31a7ed8353fd2dbfc6bbce`. `.env` 계열·키·소설 자료·원문은 묶음에 없다. 최초 archive에 든 엔진 제어기는 아래 실제 A 시작 오류를 해결하며 **해당 파일만** 독립 검토한 SHA `300c9674e0933c04ee369c1c2c137acc049c3bf8fbe8915cfc6e4a96ef724276`으로 원격 교체했다. 원 archive/selection과 원격 영수증은 덮지 않았다.

로컬 선정은 [100행 CSV](../plans/20260928-ontology-benchmark-100-samples.csv)와 SHA `45f58bccc92f7b0455bd3c7902da200c24b579d3b706a495721132eeb9b856f0`의 JSON으로 고정됐다. CPU preflight는 PostgreSQL을 읽기 전용으로 조회해 100/100의 page revision·target link·byte 범위·unit/page SHA를 대조했다. BF16/FP8의 `enable_thinking=false` 템플릿 문자열과 토큰 ID도 100/100 같았다. 최대 입력 11,904 + 출력 상한 2,600 = 필요 14,504토큰이므로 동일 `max_model_len=14,592`를 선택했고 입력은 자르지 않는다. [preflight 영수증](../../data/analysis/private/ontology-benchmark-100-20260928/remote-receipts/preflight.json) SHA-256 `b4b56b6c14d8d78baa443030c70511fd6ab4e3bc9417dded9106fe4891bfeab8`; 100개 ID는 선정 목록과 같음을 별도 Luna가 확인했다. 토큰 ID를 vLLM completion 요청에 직접 넘겨 서버의 BOS 중복 삽입을 피한다.

## 엔진 구성과 합성 연결 점검

모든 엔진은 localhost에만 바인딩하고 `--language-model-only`, BF16 KV cache, greedy temperature 0, 동일 길이 14,592를 쓴다. GPU 전체 예산의 설정 합은 A `0.85`, B2 `0.42×2=0.84`, B3 `0.28×3=0.84`다. 구성 간에는 서버를 함께 띄우지 않고, 한 구성의 FP8 엔진은 하나씩 로드해 health를 확인한다. 짧은 합성 문장에 최대 16토큰을 생성하며 원문 호출 수는 0이다.

| 구성 | 적재·health | 합성 응답 | 종료 후 GPU | 판단 |
|---|---|---|---|---|
| A BF16×1 | PID 20536, 8101, 길이 14,592, health OK; 로드 뒤 사용 119,371MiB 순간값 | 18 input/2 output token, nonempty | 0MiB | **합성 연결 통과**. 지속 동시 6개의 2,600토큰 출력은 아직 미검증 |
| B2 FP8×2 | PID 21144/21543, 8101/8102, 각 health OK; 두 엔진 준비 후 사용 117,167MiB 순간값 | 각 18 input/2 output token, 동시 요청 모두 nonempty | 0MiB | **합성 연결 통과**. 100개 본측정은 미실행 |
| B3 FP8×3 | 첫 엔진부터 기동 실패(rc 1); 나머지 두 엔진 미시작 | probe 없음, 원문 0회 | 0MiB | **현재 조건에서 실행불가**. 0.28 예산의 BF16 KV 가용 5.34GiB < 길이 14,592의 단일 요청 필요 12.26GiB; 엔진 추정 허용 길이 6,336 |

텍스트 전용으로 쓰려던 최초 A 설정에서 video encoder 3개/8,192토큰 profiling을 관찰해 ready 전에 중단했다. 그때 weights 58.99GiB/13.18초 적재를 봤지만 정상 완료로 세지 않았다. TERM 30초에 launcher가 남아 동일 PID·명령행·모델·port·PGID `19877`을 재검증한 그룹에만 KILL했고 GPU 0MiB를 확인했다. 이후 `--language-model-only`와 동일 소유 그룹만 bounded 종료하는 제어기로 보수해 위 표의 A를 **다시** 통과시켰다. 최종 합성 응답의 [A 기록](../../data/analysis/private/ontology-benchmark-100-20260928/remote-receipts/probe-A.json) SHA `7b477ba99fb07f758f8dd1130d010e1a98f55a2440e2b1b1de2c57ecfc923d1d`, [B2 기록](../../data/analysis/private/ontology-benchmark-100-20260928/remote-receipts/probe-B2.json) SHA `b52af43a6851fea4923c7d706521dd36a811228096eae0189c57a950a3373a95`. 짧은 합성 요청의 응답시간은 처리량이나 A/B 속도차로 해석하지 않는다. B3의 실제 KV 오류는 [첫 엔진 로그](../../data/analysis/private/ontology-benchmark-100-20260928/remote-receipts/B3-0.vllm.log) SHA `314c825e7ebda5fcf356685dce7dbb6713f29da240ce3510d56bdf52ea122c32`에 남겼다.

마지막 읽기에서 benchmark/vLLM 관련 프로세스와 setup PID 기록은 없고 GPU 메모리는 **143,771/0MiB**였다. [기존 DB 최종 상태](../../data/analysis/private/ontology-benchmark-100-20260928/remote-receipts/final-pg-status.json) SHA `eebd90683da23b2a105b635d40880e8d1c7ba1efc3d2eb8e520ebc3b953ac4f3`에는 attempts 완료 1,090·실패 6·미완료 running 1, outcomes 미시작 159, 후보 6,224(검토 전 3,601·보류 2,623), page 255·unit 1,256·span vector 2가 기록돼 중지 전 분모와 같다. 완료 1,090 중 후보 생성 995·0후보 95라는 outcome 구분도 유지됐다. 이번 setup이 기존 raw·후보를 다시 추출하거나 색인하지 않았음을 이 상태와 중지 전후 기록으로 확인한다.

## 다음 실행 경계

원래 [보수 계획](../plans/20260927-wikipedia-multilingual-remediation-plan.md)의 동일 100개×A/B2/B3는 300 source-unit inference 비교였다. **현재 고정 길이·BF16 KV·전체 메모리 예산에서는 B3가 첫 엔진도 로드하지 못해 300회 3안 비교는 실행할 수 없다.** 입력 길이 절삭, KV dtype 변경, 예산 초과 복제나 무한 재시도로 B3 성공을 위장하지 않는다. 다음 본측정을 별도로 진행한다면 현재 준비된 구성은 A 100회와 B2 100회, 총 **최대 200회**뿐이다. 이것도 아직 시작하지 않았으며 A/B2의 성능·의미 품질 우위는 미정이다.

이번 setup에서 `run-arm`은 실행하지 않았고 별도 SQLite 실험 파일·운영 후보/attempt DB는 생성·변경하지 않았다. 향후 실행 시 정확한 명령·결과 DB/로그 경로와 조회법은 [시험 README](../../tools/wiki_ontology_trial/multilingual/README.md#h200-고정-100단위-추론-구성-점검)를 따른다. 본측정 전에는 남은 server/PID와 GPU 메모리를 확인하고 새 `run_id`를 한 번만 쓴다. A40 백업, 기존 미완료 추출 재개, H/K/B 지침 변경, 의미 품질 승인도 이번 setup 범위 밖이다.
