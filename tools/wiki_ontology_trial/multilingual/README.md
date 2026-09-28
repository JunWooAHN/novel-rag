---
category_id: implementation-guide
lineage_id: lin-65be9c9f-3188-428f-95db-f9eebafd081e
document_id: doc-1c9be47d-cfcf-43d0-a7fe-ca6faa969eb7
parent_lineage_id: lin-1a78dc59-6af9-4445-88e4-858f5327a856
abstract: 다국어 위키의 두 구간 시험과 다섯 대상 255본문 확장 시험의 DB·31B·E5 명령과 재개 경계를 확인할 때 읽는다.
version: 0.0.4
created_at: '2026-09-27T07:48:58.000000Z'
updated_at: '2026-09-28T04:03:22Z'
tags:
- 위키백과
- 다국어
- 사용법
canon: false
---
# 다국어 원문 DB 수직 절편

이 도구는 enwiki·kowiki의 **선택한 고정 구간 두 개**만 PostgreSQL에서 읽어 Gemma 4 31B의 H/K/B 후보를 만들고, 원문 F(출처)와 근거 좌표·검토 전/보류 상태를 별도 행으로 보존하는 작은 시험이다. 위키 page 전체나 연결된 모든 언어판을 처리하지 않는다. 이 DB의 후보는 현실 릴리스·작품 정사가 아니다. [상위 다국어 보수 계획](../../../docs/plans/20260927-wikipedia-multilingual-remediation-plan.md)의 M3 첫 절편이다.

Storage 전용 하위 경로의 PostgreSQL 16·pgvector를 로컬 Unix socket으로 사용한다. 기존 PostgreSQL 자동 클러스터·문체 학습 DB와 섞지 않는다. 승인된 공개 위키·코드 묶음 `trial-source.tar.gz`는 SHA-256 `faf0bacdb336eaab8fea9d9185c47e34e879eeeae1473513371ca2c6b71c42ff`를 대조한 뒤 `/home/work/novel-toy-tune/ontology-multilingual-trial/app`에 풀었다. 소설 자료와 키는 전송하지 않았다.

같은 연결 Storage에서 **전용 DB 프로세스만** 재시작할 때의 최소 경로는 다음과 같다. 이미 실행 중이면 재시작할 필요가 없으며, 기존 `pgdata`에 `initdb`를 다시 실행하지 않는다. 아래의 두 구간 시험 **당시에는** 새 컴퓨트 세션의 Storage 재연결을 검증하지 않았고, 후속 확장 시험에서 별도로 확인했다.

```sh
trial_root=/home/work/novel-toy-tune/ontology-multilingual-trial
pgbin=/usr/lib/postgresql/16/bin
install -d -m 700 /tmp/novel-ontology-pg-1100
"$pgbin/pg_ctl" -D "$trial_root/pgdata" status
# 위 명령이 stopped를 보고할 때에만:
"$pgbin/pg_ctl" -D "$trial_root/pgdata" -l "$trial_root/postgres.log" \
  -o '-k /tmp/novel-ontology-pg-1100 -p 55432 -c listen_addresses=' start
psql -h /tmp/novel-ontology-pg-1100 -p 55432 -U work -d ontology_trial -At -c 'select 1'
```

실제 실행기는 아래와 같이 `app` 디렉터리에서, 설치된 `/home/work/novel-toy-tune/venv-gemma4/bin/python`으로 호출한다. `init`은 새 DB 생성 직후 한 번만 사용했고, 기존 DB 재개에는 생략한다.

```sh
cd /home/work/novel-toy-tune/ontology-multilingual-trial/app
export PYTHONPATH="$PWD/src"
python=/home/work/novel-toy-tune/venv-gemma4/bin/python
trial_dsn='dbname=ontology_trial host=/tmp/novel-ontology-pg-1100 port=55432 user=work'
"$python" tools/wiki_ontology_trial/multilingual/cli.py --dsn "$trial_dsn" status
"$python" tools/wiki_ontology_trial/multilingual/cli.py --dsn "$trial_dsn" verify
"$python" tools/wiki_ontology_trial/multilingual/cli.py --dsn "$trial_dsn" candidates
"$python" tools/wiki_ontology_trial/multilingual/cli.py --dsn "$trial_dsn" search --model-cache /home/work/novel-toy-tune/ontology-multilingual-trial/model-cache --query '문종은 언제 세상을 떠났나?'
```

최초 적재·추출·임베딩 명령은 `cli.py --help`의 `init`, `ingest`, `extract --limit 2 --mapping-dir docs/plans/wikipedia-history-sot-mapping --model-cache /home/work/novel-toy-tune/ontology-trial/model-cache`, `embed --limit 2 --model-cache /home/work/novel-toy-tune/ontology-multilingual-trial/model-cache`다. 이미 완료된 두 구간에 `extract`를 다시 호출하면 `requested=0, model_loaded=false`로 끝나 GPU를 다시 호출하지 않는다.

Gemma는 고정 `google/gemma-4-31B-it` revision `842da3794eaa0b77d5f08bae87a17459d91ff475`; 임베딩은 이 시험만의 `intfloat/multilingual-e5-small` revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`(384차원)이다. E5는 `passage:`/`query:` 접두어를 쓰고 512토큰 초과 구간을 조용히 자르지 않는다. 앞선 두 구간 시험에서는 E5를 CPU에서 Gemma 추출 **종료 후** 실행했다. 아래 확장 시험의 좁은 K/B 근거 확인은 GPU 추출과 별도로 CPU에서 실행했다.

원문은 `wiki_id/page/revision/slot`·UTF-8 본문 hash·`[start_byte,end_byte)`로 고정한다. 추출 시 `source_unit_id`와 prompt SHA로 attempt를 결박하며, 정확한 짧은 인용이 원문에서 유일하게 발견된 후보만 `candidate_unreviewed`, 그 외는 `held`다. B는 같은 출력의 K를 가리키는 관계 인덱스가 없거나 그 K가 보류되면 보류한다. 원시 31B 응답은 별도 attempt 행에 남는다. `extract --limit 2` 재실행은 완료된 입력을 다시 GPU에 넣지 않는다. 입력·인용·파싱 실패는 DB 상태로 남고 성공인 척 진행하지 않는다.

`search`는 두 선택 구간의 벡터 거리와 실제 원문 언어·revision·span·검토 전 근거를 반환한다. 현재 표시하는 인용은 **구간의 첫 번째 후보**이므로 질의에 맞는 후보 근거를 고른 결과가 아니다. 두 문서만 있는 시험에서 검색 결과가 나왔다고 검색 품질 또는 역사 사실성을 인증할 수 없다. 두 구간 시험 당시에는 같은 세션의 PostgreSQL 프로세스 재시작과 별도 DB 복원만 통과했고, 새 컴퓨트 세션 재연결·NFS 서버 측 sync/장애 내구성·A40 백업은 검증하지 않았다. 후속 확장 시험의 새 CPU 세션 재연결은 [현재 체크포인트](../../../docs/harness/current-checkpoint.md)에 따로 기록한다.

## 다섯 대상의 연결 언어판 전문 시험

`expanded_cli.py`는 위의 두 구간 시험과 분리된 **새 `ontology_expanded` DB**에서만 사용한다. 동결된 sitelink 255건과 각 고정 revision 본문 255개를 대조해 원문 UTF-8 byte 전체를 단위로 나누고, 단위별 31B 시도·개별 H/K/B 후보·보류 사유·정확한 근거를 DB에 기록한다. 공백 단위도 원문 byte 장부에 남는다. 추출·임베딩은 `--limit`만큼 단위별로 확정하므로 중단 뒤 `status`를 확인하고 같은 명령을 재실행할 수 있다. 이 고정 시험의 추출 모델·프롬프트 판은 하나이며, **다른 판의 재추출은 별도 DB 또는 색인 재구축 전에는 섞지 않는다.** 이 단계의 후보와 벡터는 검토 전 자료이지 현실 릴리스가 아니다.

실행 환경에서 `--mapping-dir`는 일곱 CSV가 든 같은 고정 디렉터리를 모든 명령에 전달한다. `init`은 새 DB에서 한 번만, `ingest`는 동결 원문 묶음의 저장 경로를 `--source-root`로 지정한다. `extract`는 현재 미완료 단위만 모델에 넣으며 `status`의 page·unit·attempt·후보 분모를 섞지 않는다. `embed`는 약 1950년 전의 근거 있는 검토 전 후보 span만 E5로 처리한다. 지원 언어 밖의 생성 벡터가 그 언어의 검색 품질 검증을 뜻하지는 않는다. 기존 영어 시험 파일과 두 구간 `ontology_trial` DB는 그대로 보존한다.

이번 실행의 H200 작업 디렉터리는 `/home/work/novel-toy-tune/ontology-multilingual-expanded/app`이다. 기존 PGDATA·socket을 재사용하되 DB 이름만 `ontology_expanded`로 분리한다. 장기 작업은 이 디렉터리에서 `PYTHONPATH="$PWD/src"`를 설정한 뒤 다음 명령으로 실행하며, 이번 작업의 비본문 로그는 상위 폴더의 `remaining-progress.jsonl`, `remaining-stderr.log`, `remaining-exit-code.txt`에 남긴다.

```sh
python=/home/work/novel-toy-tune/venv-gemma4/bin/python
cli=tools/wiki_ontology_trial/multilingual/expanded_cli.py
dsn='dbname=ontology_expanded host=/tmp/novel-ontology-pg-1100 port=55432 user=work'
mapping=docs/plans/wikipedia-history-sot-mapping
"$python" "$cli" --dsn "$dsn" --mapping-dir "$mapping" status
"$python" "$cli" --dsn "$dsn" --mapping-dir "$mapping" verify
"$python" "$cli" --dsn "$dsn" --mapping-dir "$mapping" extract \
  --model-cache /home/work/novel-toy-tune/ontology-trial/model-cache \
  --limit 10000 --max-new-tokens 2600
```

`extract`는 완료된 입력을 다시 모델에 넣지 않는다. 장기 프로세스가 갑자기 끝나 raw 응답이 없는 `running`/`failed` 한 단위가 남았다면 **기존 추출 프로세스 종료를 확인한 뒤에만** 위 명령에 `--retry-no-raw-failure`를 추가한다. 살아 있는 프로세스에 이 플래그를 동시에 쓰면 중복 GPU 호출 위험이 있다. 커밋 전 응답이 유실된 단위는 재호출될 수 있으며, 이미 raw가 보존된 실패를 조용히 성공으로 바꾸지는 않는다. 페이지 255개 적재와 단위 1,256개 모델 처리의 완료 수치는 별도이므로 `status`·`verify`로 각각 확인한다.

## H200 고정 100단위 추론 구성 점검

2026-09-28에는 setup 뒤 사용자 승인으로 **A와 B2의 동일 고정 100구간 본측정 각 1회**를 실행했다. 실제 시간·오류·품질 검토와 원시 SQLite 위치는 [본측정 기록](../../../docs/research/20260928-h200-ontology-benchmark-results.md), 현재 재개 상태는 [체크포인트](../../../docs/harness/current-checkpoint.md)를 따른다. 아래 setup·run 명령은 당시 절차의 재현 설명이며 기존 `run_id`로 자동 재실행하지 않는다.

`benchmark_100.py`는 [고정 선정 목록](../../../data/analysis/private/ontology-benchmark-100-20260928/selection.json)의 정확한 100개 `unit_id`를 운영 PostgreSQL **읽기 전용**으로 조회하고 revision·대상 링크·byte 좌표·원문 SHA를 대조한다. `preflight`는 BF16/FP8의 no-thinking 템플릿과 토큰 ID 동치를 CPU에서 확인하고 입력 최대 토큰 수와 출력 상한 2,600을 합쳐 엔진 길이를 정한다. 추론 HTTP에는 이미 확인한 **토큰 ID**를 전달하므로 서버가 문자열에 BOS를 다시 붙이지 않는다. `probe`는 위키 원문 없이 합성 한 줄만 생성한다.

서버 제어기는 `benchmark_arm_control.py`다. 순서대로 A(원본 BF16 한 엔진, 동시 6), B2(FP8 두 엔진, 각 동시 3), B3(FP8 세 엔진, 각 동시 2)를 **각각 따로** 기동하고, 같은 구성의 FP8 엔진은 하나씩 로드해 건강 상태를 확인한다. 세 구성의 GPU 메모리 총 설정은 각각 0.85/0.84/0.84이고, KV cache는 BF16으로 고정한다. vLLM `--language-model-only`로 모든 멀티모달 입력을 막고 전부 localhost에 바인딩하며, 서버 로그·PID는 전용 setup 경로에 둔다. 한 구성의 `probe`와 GPU 상태 확인 뒤 해당 `stop`을 수행해야 다음 구성을 시작할 수 있다. 중단은 기록된 모델·port·PID와 PGID가 일치하는 그룹에만 TERM을 보낸 뒤, 30초 동안 남으면 다시 같은 소유를 확인해 KILL하고 10초 안에 재확인한다. B3가 GPU 메모리 부족이면 그 상태를 기록하고 반복 강제 기동하지 않는다.

원격 전용 경로는 `/home/work/novel-toy-tune/ontology-benchmark-100-20260928`다. 격리 vLLM 환경 `/home/work/novel-toy-tune/venv-vllm-benchmark`, 고정 FP8 체크포인트 `models/fp8`, 기존 BF16 cache snapshot을 사용한다. `app`은 기존 `/home/work/novel-toy-tune/ontology-multilingual-expanded/app`이며 `PYTHONPATH="$app/src"`를 설정한다. 아래 명령은 경로 예시다. **최초 setup 단계에서는 `run-arm`을 실행하지 않았다.** 이후 별도 본측정에서 A/B2 각 100회를 완료했다. B3는 `0.28` 예산에서 BF16 KV cache가 부족해 첫 엔진부터 기동 불가였고 본측정을 하지 않았다.

```sh
root=/home/work/novel-toy-tune/ontology-benchmark-100-20260928
app=/home/work/novel-toy-tune/ontology-multilingual-expanded/app
base=/home/work/novel-toy-tune/ontology-trial/model-cache/models--google--gemma-4-31B-it/snapshots/842da3794eaa0b77d5f08bae87a17459d91ff475
fp8="$root/models/fp8"
python=/home/work/novel-toy-tune/venv-gemma4/bin/python
vllm=/home/work/novel-toy-tune/venv-vllm-benchmark/bin/vllm
dsn='dbname=ontology_expanded host=/tmp/novel-ontology-pg-1100 port=55432 user=work'
cd "$app"
export PYTHONPATH="$app/src"
runner=tools/wiki_ontology_trial/multilingual/benchmark_100.py
control=tools/wiki_ontology_trial/multilingual/benchmark_arm_control.py
"$python" "$runner" --selection "$root/selection.json" --base-processor "$base" --fp8-processor "$fp8" \
  preflight --dsn "$dsn" --mapping-dir docs/plans/wikipedia-history-sot-mapping --output "$root/setup/preflight.json"
"$python" "$control" start --arm A --root "$root" --preflight "$root/setup/preflight.json" \
  --vllm "$vllm" --base-model "$base" --fp8-model "$fp8"
"$python" "$runner" --selection "$root/selection.json" --base-processor "$base" --fp8-processor "$fp8" \
  probe --arm A --urls http://127.0.0.1:8101/v1 --output "$root/setup/probe-A.json"
"$python" "$control" stop --arm A --root "$root"
# B2와 B3는 위의 start/probe/stop을 각각 별도로 수행한다.
# B2 probe URLs: http://127.0.0.1:8101/v1 http://127.0.0.1:8102/v1
# B3 probe URLs: 위 두 URL과 http://127.0.0.1:8103/v1
```

측정용 `run-arm`은 전용 SQLite 한 파일에 100행 분모를 먼저 고정하고 한 writer가 응답 수신 직후 **원시 HTTP bytes를 먼저 커밋**한 다음 JSON·후보 검증을 기록한다. 비정상 HTTP/잘린 JSON도 원시 bytes·hash·크기를 보존한다. SQLite는 NFS Storage에서 `journal_mode=DELETE`, `synchronous=FULL`을 쓰고 종료 시 별도 read-only 연결로 100행·bytes/hash·quick_check를 재검증한다. 이 파일은 일회 실험 원시응답·상태 보관용이며 운영 온톨로지 PostgreSQL의 원문·후보·attempt나 SoT를 바꾸지 않는다. 자동 재시도·작업 선점·범용 큐는 없다. 합성 16토큰 probe가 통과해도 2,600토큰 상한과 동시 6개의 지속 처리 성능이나 의미 품질을 판정하지 않는다.

본측정에서는 **각 arm의 start·health 직후** 아래 형태로 동일 100개를 한 번씩 호출하고 stop한 다음 다음 arm으로 넘어갔다. 별도의 합성 probe는 setup 점검에서만 수행했으며 본측정 직전에는 반복하지 않았다. B2의 URL 두 개는 고정 순위의 짝/홀 50/50이다. `results/benchmark-100.sqlite3`에는 아래 두 `run_id`가 이미 있으므로 재실행은 거부된다. **B3 명령은 현재 조건에서 사용하지 않는다**. 14,592토큰의 단일 요청에 KV 12.26GiB가 필요한데 `0.28` 예산의 가용 KV는 5.34GiB였으며, 입력 절삭·KV dtype 변경·반복 재시도는 하지 않았다.

```bash
db="$root/results/benchmark-100.sqlite3"
mkdir -p "$root/results"
common=(--selection "$root/selection.json" --base-processor "$base" --fp8-processor "$fp8")
args=(--dsn "$dsn" --mapping-dir docs/plans/wikipedia-history-sot-mapping \
  --preflight "$root/setup/preflight.json" --sqlite "$db")
# 본측정 당시 A start/health 이후(이미 실행된 run_id):
"$python" "$runner" "${common[@]}" run-arm "${args[@]}" --arm A \
  --urls http://127.0.0.1:8101/v1 --run-id fixed100-A-20260928 | tee "$root/results/A-summary.json"
# A stop → B2 start/health 이후(이미 실행된 run_id):
"$python" "$runner" "${common[@]}" run-arm "${args[@]}" --arm B2 \
  --urls http://127.0.0.1:8101/v1 http://127.0.0.1:8102/v1 \
  --run-id fixed100-B2-20260928 | tee "$root/results/B2-summary.json"
# B2 stop. 재개 시 먼저 setup의 PID 기록·포트 health, run ID를 확인한다.
"$python" -c 'import sqlite3,sys; db=sqlite3.connect(sys.argv[1]); print(db.execute("select run_id,arm,started_at,finished_at from runs").fetchall()); print(db.execute("select run_id,status,count(*) from results group by run_id,status").fetchall())' "$db"
```

이번 PID `9508`에 결박한 일회성 `post-extract.py`는 `remaining-exit-code.txt`와 해당 추출 프로세스의 종료를 모두 확인한 뒤, 추출 명령이 정상 종료한 경우에만 적격 근거를 CPU E5로 반복 색인한다. 결과는 같은 Storage의 `embed-round-*.jsonl`, `final-status.json`, `final-verify.json`, `post-extract-summary.json`에 남는다. 추출 명령의 exit 0만으로 개별 단위 성공이나 전체 의미 검토를 선언하지 않는다. **새 세션이나 재개로 추출 PID가 바뀌면 이 watcher도 새 PID에 맞춰 명시적으로 재기동해야 한다.** 이미 실행 중인 추출기와 두 번째 GPU 추출기를 동시에 띄우지 않는다.

2026-09-28의 H200 구성 시험 준비에서 위 PID 9508의 추출기와 결박된 watcher는 사용자 승인 아래 함께 종료했다. 그 시점의 1,090 완료·6 실패·1 미완료 단위와 원시응답·후보는 DB에 남고, `remaining-exit-code.txt`는 종료 코드 143을 기록한다. 위 watcher 설명은 과거 실행 구조이며 현재 작동 중인 프로세스를 뜻하지 않는다. 구 시험이 중단됐다고 DB의 미완료 단위를 성공으로 바꾸거나 전량 재시작하지 않는다.
