# 고정 100구간 YAGO 문맥 시험

기존 [100구간 벤치마크](../multilingual/README.md)의 선정 JSON SHA `45f58bccc92f7b0455bd3c7902da200c24b579d3b706a495721132eeb9b856f0`, 원문 DB 검증, A/B2 모델·동시성·출력 2,600·문맥 14,592를 유지한다. 결과는 운영 PostgreSQL이 아닌 새 SQLite에 둔다. 이 시험은 YAGO 원본에서 **다섯 대상의 정확한 ID**에 직접 연결된 사실·분류와 일치하는 RDF* Meta만 문맥으로 사용한다. 전체 YAGO나 Wikidata statement를 적재하지 않는다.

`build_context.py`는 별도 보관한 `facts`·`meta`·`taxonomy` 대상 행 캡처, 고정 선정과 [원본 manifest](../../../data/research/yago-storage-20260928/manifest-final.json)를 검사해 KG-only JSON을 만든다. 문종·단종·세조·한글은 직접 사실을 가진 개체이고, Bloomery는 지명 동음이의어를 배제한 taxonomy class다. 각 진술은 출처형(`yago_fact`/`yago_taxonomy`), 원본 파일 SHA-256, 1부터 시작하는 행 번호, 원문, 해당 Meta의 별도 좌표를 가진다. KG 관계 자체는 위키 원문 span이 아니다.

기존 `benchmark_100.py`의 선택적 `--kg-context`는 단위마다 완결된 진술을 우선순위대로 붙여 보고 실제 BF16/FP8 토큰 ID와 chat template의 동치를 검사한다. 진술이 14,592−2,600 토큰 한도에 들어가지 않으면 그 진술 전체를 제외하며 원문·출력은 자르지 않는다. 진술이 하나도 못 들어간 단위는 원래 프롬프트와 `budget_omitted`, 직접 사실이 없는 class는 `class_only`, 직접 사실·분류가 모두 없는 대상은 `no_direct_fact`로 구별한다. 선택 ID·순서·프롬프트 SHA를 100단위 preflight와 새 결과 SQLite에 고정한다. 모델의 H/K/B 후보는 **기존 위키 SOURCE_SPANS만** 근거로 검증한다. YAGO 문맥은 근거 span을 대신하지 않는다.

이번 고정판은 `data/analysis/private/yago-benchmark-100-20260928/`에 KG-only 원장·preflight·실행 사본·기계 집계·검토 패킷을 보존한다. H200 실행 디렉터리는 `/home/work/novel-toy-tune/yago-benchmark-100-20260928/`이다. 새 모델 엔진은 기존 `benchmark_arm_control.py`를 이 전용 디렉터리의 PID 기록과 함께 사용했고 A를 종료한 뒤 B2를 순차 실행했다. 원본 YAGO의 `zip/`·`extracted/`, 기존 결과 SQLite, 운영 PostgreSQL의 원문·후보는 변경하지 않는다.

`make_quality_packets.py`는 기존 rank별 A/B2 패킷에 신규 YAGO-A/B2 후보와 사용된 KG 진술의 별도 출처 좌표를 결합한다. `analyze_results.py`는 결과 SQLite의 raw SHA·source hash·prompt hash와 분모를 검증해 구조 통과·후보 0개·후보 상태를 나눠 집계한다. Runner 요약의 `zero_output`은 **빈 생성 텍스트**이며 **후보 0개**와 다르다. `checked_nonempty`는 구조 처리 단계에 도달한 비어 있지 않은 응답을 가리키며 의미 검토 수락 수가 아니다. 시간 비교는 모델 로딩을 제외한 runner wall과 CPU 원문/프롬프트 준비를 분리한다. 최초 원본 KG 스캔과 새 A의 3초 간격 GPU 메모리 최대값은 측정하지 않았으므로 추정하지 않는다.
