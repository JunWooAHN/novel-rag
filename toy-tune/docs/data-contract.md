# 데이터 계약 v1

현재 입력은 UTF-8 JSON source bundle이다. 공개 예시는 tests/fixtures/synthetic-source.json이다. 테스트 원문은 전부 합성 문장이다.

- schema_version: 1
- sources: source_id와 변경하지 않는 원문 text 목록
- samples: sample_id, work_id, scene_id, order, prompt, answer, source_id, source_sha256, answer_start, answer_end, question_method, 선택 packet_id
- SHA-256은 원문 text를 UTF-8로 인코딩한 바이트의 해시다.
- answer_start/end는 바이트나 token이 아닌 Python 문자열의 문자 인덱스이며 끝은 제외한다. 원문을 정규화하면 해시와 범위를 새로 계산해야 한다.
- answer는 지정 원문 범위와 정확히 일치해야 한다. prompt는 사람이 작성한 질문이며, 현재 명령은 질문을 자동 합성하지 않는다.
- packet_id가 있는 입력은 현재 명령에서 거부한다. 실제 패킷 반입·revision 검증이 구현되기 전 참조를 묵인하지 않는다.

현재 builder는 한 작품의 order를 기준으로 시간순 분할한다. 세 split의 양수 건수 합이 입력 수와 정확히 맞아야 한다. 여러 작품을 섞거나 일부 샘플을 조용히 제외하지 않는다.

중복 sample ID/order, split을 넘는 scene, split을 넘는 정규화된 동일 answer, 자신의 정답 전체가 포함된 prompt를 거부한다. 다른 split의 정답이 prompt에 포함되면 기본 거부하며, 명시적인 --allow-context-overlap일 때만 경고와 정책을 manifest에 기록한다. 부분 표현·의미 유출은 자동 검사의 보장 범위가 아니다.

published dataset에는 source-bundle.json, train.jsonl, validation.jsonl, test.jsonl, statistics.json과 manifest.json이 있다. ID는 파일 checksum과 builder 정책으로 결정한다. 동일 입력 재실행은 같은 ID이며 다른 내용을 같은 ID로 덮어쓰지 않는다. 파일 안의 외부 raw prose, 출처, 생성 결과도 비공개로 취급한다.

schemas/의 JSON Schema와 domain의 의미 검증을 구분한다. SHA 일치, 실제 원문 범위 일치, split 누수는 JSON Schema만으로 검사할 수 없다. 테스트는 직렬화 결과의 스키마 적합성 및 별도 의미 검증을 함께 실행한다.

학습에 필요한 tokenizer revision, token budget, chat template, loss mask 검증은 H200 엔진 단계에서 추가한다. 현재 통계의 문자 수를 token 수로 해석하지 않는다.
