---
category_id: research
lineage_id: lin-ad7cf060-70c6-421e-9e5e-3dc0bbd7a481
document_id: doc-3639f92f-5a86-4c00-b3e1-713268bfc409
parent_lineage_id: null
abstract: BF16 단일 엔진과 FP8 두 엔진의 고정 100단위 속도·품질 비교를 실제 결과에서 확인할 때 읽는다
version: 0.0.2
created_at: '2026-09-28T03:42:27.000000Z'
updated_at: '2026-09-28T04:03:12Z'
tags: []
canon: false
---
# H200 고정 100단위 온톨로지 추론 본측정

이 문서는 같은 고정 원문 100구간을 A(BF16 단일 vLLM 엔진)와 B2(FP8 두 엔진)에 **각각 한 번**, 합계 200회 넣은 본측정의 기록이다. 두 구성 모두 100행을 끝냈지만, 아래의 `validated`는 원시 응답을 구조 검증기로 처리했다는 뜻일 뿐 역사 사실이나 H/K/B 의미 품질의 수락이 아니다. B3(FP8 세 엔진)는 [구성 점검](20260928-h200-ontology-benchmark-setup.md)에서 고정 문맥의 BF16 KV 메모리 부족으로 첫 엔진부터 기동할 수 없어 본측정 분모에 넣지 않았다. 결과는 운영 온톨로지 PostgreSQL 후보·시도에 쓰지 않고 별도 SQLite에 보존했다.

## 고정 입력과 비교 조건

[선정 100구간](../../data/analysis/private/ontology-benchmark-100-20260928/selection.json) SHA-256 `45f58bccc92f7b0455bd3c7902da200c24b579d3b706a495721132eeb9b856f0`은 다섯 대상에서 20구간씩 고른 층화 개발 표본이다. 각 arm은 동일한 100 `unit_id`·원문 revision/byte/hash·프롬프트·토크나이저/템플릿·`enable_thinking=false`·greedy temperature 0·출력 상한 2,600·최대 문맥 14,592·BF16 KV를 사용했다. [사전 점검 영수증](../../data/analysis/private/ontology-benchmark-100-20260928/remote-receipts/preflight.json)은 운영 PostgreSQL의 지정 100구간 byte/hash와 두 모델 토큰 ID 100/100 동치를 기록한다. A는 엔진 1개×동시 요청 6개, B2는 엔진 2개×각 3개로 총 동시 요청 수가 같다. B2는 고정 rank 순환 배분으로 각 엔진 50구간을 맡았다. 실패 자동 재시도와 추가 위키 구간 워밍업은 하지 않았다.

A의 고정 모델은 `google/gemma-4-31B-it` revision `842da3794eaa0b77d5f08bae87a17459d91ff475`, B2는 `RedHatAI/gemma-4-31B-it-FP8-dynamic` revision `d4ab4f579dd3516f97d8a6a4c98d0653480bad15`이다. FP8 카드가 같은 **원본 base revision**에서 만들어졌는지는 확인되지 않았다. 따라서 아래 차이는 이 구성·이 모델판의 비교이며 양자화 자체의 인과 효과가 아니다. vLLM 0.30.0의 두 엔진 구성은 순서대로 따로 띄웠고 내부 compile/warmup을 마친 health 이후 본측정을 시작했다. 로딩시간은 runner wall에 없다.

## 처리량과 구조 결과

| 관측값 | A: BF16×1 | B2: FP8×2 |
|---|---:|---:|
| 고정 입력 / 완료된 요청 / 운영 재시도 | 100 / 100 / 0 | 100 / 100 / 0 |
| runner wall, 모델 로딩 제외 | 488.175초 | 625.787초 |
| 완료 요청 처리량, 실패 포함 | 737.44구간/시 | 575.28구간/시 |
| 비어 있지 않은 구조 검사 응답 | 95건, 700.57건/시 | 96건, 552.26건/시 |
| 실패 / 무출력 / 미완료 | 5 / 0 / 0 | 4 / 0 / 0 |
| 후보 0개인 구조 검사 응답 | 9 | 11 |
| `finish_reason=stop` / `length` | 100 / 0 | 100 / 0 |
| queue 대기 p50 / p95 | 255.184 / 447.242초 | 327.307 / 572.466초 |
| enqueue→응답 종료 p50 / p95 | 279.649 / 468.651초 | 360.463 / 593.683초 |
| 3초 간격 GPU 사용 메모리 최대 관측 | 123,059MiB | 122,995MiB |

B2는 같은 100요청에서 A보다 wall이 137.612초(약 28.2%) 길었다. 이는 같은 총 동시성·전체 GPU 조건에서의 **이번 한 번의 처리 결과**이며 반복 오차나 다른 입력에 대한 속도 우위를 확정하지 않는다. GPU 수치는 각각 168·213개 3초 간격 표본의 최대값이지 순간 peak VRAM이 아니다. 실패까지 포함한 완료 요청 100건/시간과 구조 검사 단계까지 간 비어 있지 않은 응답/시간을 구별했다. 구조 검사 응답에도 보류 후보와 의미 오류가 남을 수 있다.

두 arm의 200행은 원시 HTTP 응답 bytes·길이·SHA와 DB readback이 맞았다. A의 실패 5건은 후보 배열 10개 초과 4건과 JSON 파싱 오류 1건, B2의 실패 4건은 후보 배열 10개 초과 2건과 JSON 파싱 오류 2건이다. 응답 종료 사유 `stop`은 200건 모두에서 확인했지만 JSON/후보 구조 오류를 배제하지 않는다. 후보 0개 9/11건은 **무출력 0건과 다른 상태**이며 원문에 대응 사실이 있는지는 독립 품질 검토에서 판단한다. [원시 SQLite](../../data/analysis/private/ontology-benchmark-100-20260928/remote-receipts/benchmark-100.sqlite3) SHA-256 `9493c6ab3ab3cb9ed4d4435a9645d0d2b6a17187d2653af142242ebd608ab961`; [속도·오류 집계](../../data/analysis/private/ontology-benchmark-100-20260928/results-analysis/speed-analysis.json) SHA-256 `8f0571d7e05d2aa2f6730cf789111dd29389124d241243e52e4c44b0d245ef77`. 별도 Luna의 [200행 기계 대조](../../data/analysis/private/ontology-benchmark-100-20260928/benchmark-mechanical-check.json) SHA-256 `d732efded628a4e3cd513a4aa3a1e9b39fa1a982f6dae5ce397e433e9aa60fcd`는 100 고유 ID·원문 revision/hash·200 raw·B2 50/50·분모·요약 수치와 저장조건을 수락했다. 이 기계 대조는 의미 판정이 아니다.

## 원문·후보 의미 품질

고정 100구간의 [DB 원문 회수본](../../data/analysis/private/ontology-benchmark-100-20260928/remote-receipts/source-100.json) SHA-256 `e2a3a74f0e4863859d7ae6a86dd09924230dab9539557b4328d27c649119aefc`와 A/B2 후보를 `unit_id`로 맞춘 [10구간씩 10개 검토 패킷](../../data/analysis/private/ontology-benchmark-100-20260928/results-analysis/quality-packets-manifest.json) SHA-256 `1eb60475e2dc77b0f8f26ad672f45dd36c0af4297607767cd56e7f562a1fed64`을 두 Sol이 **서로 다른 50쌍씩** 나눠 검토했다. 각 구간에서는 한 검토자가 A/B2를 함께 대조했고, 두 arm 모두 문제가 없는 구간도 한 줄 근거를 남겼다. [1–50 검토](../../data/analysis/private/ontology-benchmark-100-20260928/quality-review/semantic-001-050.json) SHA-256 `50beb47e9d3e5e920f191aff4ac922952597e5cbacf63f60fd7e1e96b5ac2433`, [51–100 검토](../../data/analysis/private/ontology-benchmark-100-20260928/quality-review/semantic-051-100.json) SHA-256 `8222579076bf39c04ce68e1d58178f740644771ce1f84b2d90229140a05358a8`. 두 검토는 고정 출처에 대한 정합성·중요 누락·정당한 유보를 보는 개발/회귀 표본 판정이며 전문가가 만든 역사 정답셋의 정확도 평가나 실제 역사 진실 검증이 아니다.

| 출처 정합성 판정 | A | B2 |
|---|---:|---:|
| 구조 검사 후보 전부(검토 전+보류) | 583 | 541 |
| 원문 지지 / 중대 의미 오류 / 문맥 부족 | 446 / 111 / 26 | 437 / 80 / 24 |
| 그중 `candidate_unreviewed` 후보 | 413: 지지 368 / 오류 31 / 부족 14 | 394: 지지 349 / 오류 33 / 부족 12 |
| 그중 `held` 후보 | 170: 지지 78 / 오류 80 / 부족 12 | 147: 지지 88 / 오류 47 / 부족 12 |
| 중대 오류의 H / K / B 분류 | 14 / 33 / 64 | 17 / 18 / 45 |

100개의 A/B2 **짝 비교**에서는 A 선호 26, B2 선호 31, 동률 40, 판단 불가 3이었다. 후보 수와 보류 상태가 다르고 한 구간에 복수 후보가 묶이므로 위 후보 수를 단순히 나눠 모델 정확도나 통계적 우위로 발표하지 않는다. 검토 전 후보에도 중대 오류가 A 31·B2 33건 있어 `candidate_unreviewed`는 원문 수락 상태가 아니다. B2의 중대 오류 수가 더 적어도 B2가 빠른 것은 아니며, A보다 지지 후보 수도 적다. [비본문 집계·대조 기록](../../data/analysis/private/ontology-benchmark-100-20260928/results-analysis/semantic-aggregate.json) SHA-256 `3342e0391a44d3948e74dff0331a2cef0014c472f10bba0a37539739f464c90b`은 100구간·1,124후보의 출처 ID/좌표/hash, 원본 SQLite 후보 ordinal·층·DB 상태, 직접 인용과 요약 분모를 재조회해 일치시켰다.

대표적인 차이와 공통 실패는 다음과 같다.

- 문종 한국어 1위 구간에서 A의 모델 응답은 후보 10개 상한을 넘어 **원시 응답은 보존됐지만 후보 전체가 실패**했고, B2는 원문 지지 후보 8개를 남겼다. 세조 영어 55위에서는 B2가 강제 퇴위·강등을 더 명시했지만, **두 구성 모두** 원문의 독약 자살 명령을 사망 완료·직접 살해로 과장했다.
- 단종 일본어 37위에서는 양쪽 모두 원문의 **수렴청정이 불가능했다**는 부정을 긍정 적용 관계로 뒤집었다. A의 B→K 참조도 잘못 연결됐다. 세조 프랑스어 56위의 저작물 제목·존재는 K 객체로 허용되지만, 목록만으로 직접 저술 행위 B를 확정할 수 없다. A의 B→K 번호는 다른 작품을 가리켰고 B2는 그 연결을 맞췄어도 **검토에서는** 저술 귀속을 유보했다. B2의 DB 후보 상태는 `candidate_unreviewed`로 남아 있다.
- Bloomery 영어 82위의 제련 절차는 지식 K의 공정 설명을 지지한다. **역사상의 실제 도입·사용 사례**를 말하지 않는데도 두 구성은 일반 절차를 B 사건으로 만들었다. B2는 환원·괴련·단철 K 내용을 더 남겨 이 구간의 짝 비교에서는 선호됐지만 그 B 오류가 사라진 것은 아니다. Bloomery 스페인어 100위는 참고문헌·분류 목록이어서 B2의 0후보가 정당한 반면 A는 서지 제목의 지명·시대를 실제 제련 사용으로 오인했다. A의 일부 K는 `is_a`의 `object:null`로 관계 자체가 미완성인 문제이며 **저작물 제목 K 자체를 금지한 판정은 아니다.**

후보가 원문과 맞아도 보류되거나 내용판·시점이 부족할 수 있다. 반대로 실제 저작물·정보 객체가 원문에 명시됐다는 이유만으로 K를 오류라고 하지 않았다. K의 내용·조건을 제목에서 발명하거나, 일반 공정 K를 특정 역사행위 B로 올리는지를 구분했다. 특히 82위는 두 모델의 상대 선호가 **둘 다 올바름**을 뜻하지 않는 사례다.

## 운영 보존과 해석 경계

마지막 원격 확인에서는 두 벤치마크 엔진을 정상 종료했고 GPU 메모리 143,771/0MiB, PID 기록과 관련 생존 프로세스가 없었다. [최종 프로세스 영수증](../../data/analysis/private/ontology-benchmark-100-20260928/remote-receipts/benchmark-final-process-state.json) SHA-256 `b34860cc9a9295f14c52fb9cfa2ab829ad848e453a24040f8497dabb8921d165`. [기존 운영 PostgreSQL 최종 상태](../../data/analysis/private/ontology-benchmark-100-20260928/remote-receipts/benchmark-final-pg-status.json) SHA-256 `eebd90683da23b2a105b635d40880e8d1c7ba1efc3d2eb8e520ebc3b953ac4f3`는 setup 종료 때의 보존 상태와 같다: 완료 1,090·실패 6·raw 없는 미완료 1·미시작 159, 후보 6,224(검토 전 3,601·보류 2,623), source page 255·unit 1,256·span vector 2. 이번 비교 결과는 기존 추출 재개·후보 수정·색인·현실 역사 SoT 채택으로 이어지지 않았다.

현재 출력의 스키마·근거 검사는 역사 원문 정합성이나 집필 사용 가능성을 증명하지 않는다. B2의 처리시간·후보 개수 차이는 엔진 복제, 모델 weight 형식/계통, 실행조건의 복합 결과이며 FP8 하나의 단독 효과로 나눌 단일 FP8 대조군·반복 실험은 없다. 품질 독립 검토까지 포함한 이번 개발 표본도 255페이지/1,256구간 전체나 새 원문에 대한 일반화 보증은 아니다.

이번 고정 100구간에서는 **FP8 두 엔진이 BF16 한 엔진보다 처리량을 높이지 못했다.** 짝 비교 의미 검토는 약간 더 많은 구간에서 B2를 선호했으나 40쌍은 동률이고 양쪽 모두 원문과 어긋난 H/K/B 후보가 있다. 따라서 이 결과만으로 B2를 운영 추출기로 전환하거나 어느 쪽 후보도 현실 역사 릴리스·집필 입력으로 자동 채택할 수 없다. 우선 [H/K/B 보수 계획](../plans/20260927-wikipedia-multilingual-remediation-plan.md)의 원문 표현 보존·부정/행위자·K 내용판·B 실제 역사행위 구분을 개발 입력에서 보수하고 별도 미사용 확인셋으로 검토해야 한다. 이번 측정 자체를 자동 반복하거나 실패 후보를 운영 DB에 덮어쓰지 않는다.

본측정의 H200 Storage 원본은 `/home/work/novel-toy-tune/ontology-benchmark-100-20260928/results/benchmark-100.sqlite3`이며 run ID는 `fixed100-A-20260928`과 `fixed100-B2-20260928`이다. 사용한 runner는 [benchmark_100.py](../../tools/wiki_ontology_trial/multilingual/benchmark_100.py) SHA-256 `1f930baf7dff533a739c8b1988985930278edb26ccc3c3fb72a443f03b9fc009` 판이고 관련 테스트 7/7이 통과했다. 결과 SQLite와 검토 JSON은 분석을 위한 별도 보존물이며 기존 `ontology_expanded` PostgreSQL의 원문·후보 정본을 대체하지 않는다.
