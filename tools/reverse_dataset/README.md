---
category_id: corpus-tools
lineage_id: lin-1b3d4431-50f1-4ff7-814d-c99863998c59
document_id: doc-94330c6b-6db8-48c7-b22b-324e5155226c
parent_lineage_id: null
abstract: 원문 역구성 개발 데이터의 순차 입력, 역할별 target, split 검증과 로컬 JSONL 생성 절차를 사용할 때 읽는다.
version: 0.0.2
created_at: null
updated_at: '2026-09-25T06:21:48Z'
tags:
- 학습데이터
- 역설계
---
# 원문 역구성 데이터셋 도구

현재 실무·검토 모델: Sol 6.0. 실행 수단은 작업 기록에 별도로 남기며 CLI로 고정하지 않는다. 고종의 `gemma_style`은 정확한 원문 장면을 문체 target으로, 고려·폴란드의 `sota_planning`은 원문을 근거로 독립 검토한 재구성 계획을 target으로 쓴다. 이 작품들은 이미 관찰한 **개발 자료**다. `development_holdout`도 미관측 최종 시험이 아니며, 재구성 계획은 원저자의 실제 기획 의도가 아니다.

초기 릴리스 `data/training/reverse-20260925`는 각 작품의 첫 50개 source-order 구간을 동결한다. `section_order`는 공식 화 번호가 아니다. `source-manifest.json`과 `split-policy.json`은 원문 없는 메타데이터이고, `private/batches/`는 텍스트 없는 작업 색인이다. `private/sections/<work>-<order>.json`은 현재 구간까지만 보여 준다. 이전 문맥이 필요할 때 `show-unit --prior-start-cp N`으로 현재 split의 앞부분을 선택한다. 각 구간에 attempt 하나를 기록하고, 장면이 여러 구간에 걸치면 해당 후보를 모든 관련 attempt에 연결한다.

```sh
python3 tools/reverse_dataset/build.py freeze
python3 tools/reverse_dataset/build.py batch goryeo 1 5
python3 tools/reverse_dataset/build.py show-unit goryeo 1
# 초반 검토·독립 결정을 모두 마친 뒤에만:
python3 tools/reverse_dataset/export.py build --release initial
```

별도 릴리스 `data/training/reverse-full-20260925`는 같은 세 작품의 **전체 원문에서 장면을 선정할 작업**이다. 첫 50구간 이후를 여섯 진행 대역으로 나누고 대역당 여덟 선정창, 작품당 48개를 준비했다. 48은 이번 제작의 표본 목표이지 영구적인 유효성 하한이 아니다. 창은 읽기 작업이지 회차 하위 장면 모델이 아니다. 각 창의 primary는 인접한 원문 구간 둘, primary가 보류될 때만 읽는 alternative도 인접 구간 둘이다. 장면은 창 부분 안에서 원문 구간 경계를 가로지를 수 있지만 split·창 부분 경계를 넘지 못한다. 고종의 미확정 마지막 구간은 원천 메타데이터에 남기고 선정 대상에서 제외했다. 이 색인 생성은 전편의 장면 분석이나 후보·학습 완료를 뜻하지 않는다.

```sh
python3 tools/reverse_dataset/full.py freeze
python3 tools/reverse_dataset/full.py show-window goryeo 1 1
python3 tools/reverse_dataset/full.py init-review goryeo 1 1 > /tmp/goryeo-review.json
# 파일에 원문 좌표, 장면 기능, 선정 이유, observed와 reconstructed를 작성한 뒤:
python3 tools/reverse_dataset/full.py save-review goryeo 1 1 /tmp/goryeo-review.json
# 4창마다 내구 체크포인트를 남긴다:
python3 tools/reverse_dataset/full.py checkpoint goryeo
# primary가 hold로 저장된 경우에만:
python3 tools/reverse_dataset/full.py show-window goryeo 1 1 --alternative
# 모든 창의 후보와 독립 결정이 준비된 뒤에만:
python3 tools/reverse_dataset/export.py build --release full
python3 -m unittest discover -s tools/reverse_dataset -p 'test_*.py'
```

초기 후보 형식은 [review-batch.schema.json](review-batch.schema.json), 전체 원문 선정창 형식은 [full-review.schema.json](full-review.schema.json)을 따른다. `writer_input`에는 문자열 `prior_context`, 객체 배열 `virtual_history`·`character_knowledge`, 객체 `scene_spec`이 필요하다. `planner_input`에는 문자열 `prior_state`·`goal`, 문자열 배열 `constraints`가, `plan_target`에는 객체 배열 `virtual_history`·`character_knowledge`와 객체 `scene_spec`이 필요하다. 관찰 좌표·원문 해시와 재구성 가정은 모델 payload 밖의 근거로 남긴다. 미래 장면 사실을 prior에 넣거나 출처 좌표를 모델 입력에 싣지 않는다. 자르거나 길이를 맞추기 위해 장면을 임의로 끝내지 않으며 근거가 부족하면 hold한다.

독립 검토자는 결정 파일에 `schema_version: 2`, 해당 `batch_id` 또는 `window_id`, **리뷰 파일 원시 바이트 SHA-256**인 `review_sha256`, `reviewer`, 수락·보류·반려 후보 ID 목록을 기록한다. 전체 원문 선정창의 리뷰는 `private/reviews/<window_id>.json`, 결정은 `private/decisions/<window_id>.json`이다. 저장한 리뷰를 교정할 때는 현재 파일의 SHA와 구체적 교정 사유를 명시한다.

```sh
python3 tools/reverse_dataset/full.py save-review goryeo 1 1 /tmp/goryeo-corrected.json --replace-review-sha <현재-리뷰-SHA256> --correction-reason '원문 근거 좌표 교정'
```

교정 저장은 이전 원시 바이트를 `private/review-revisions/`에 남긴다. 기존 결정 파일은 보존되지만 새 리뷰 SHA와 일치하지 않아 **독립 재수락** 전에는 export할 수 없다. export는 전체 attempt와 결정, 원문 SHA, CP 좌표, 역할별 타입, split, target 겹침·중복을 검사한 뒤 각 릴리스의 별도 `private/export/`에 JSONL을 쓴다. JSONL의 `messages`만 모델 입출력이고 `metadata`는 출처·검토용이며 출력은 무절단이다. 전체 원문 확장 후보 생성, 두 릴리스의 최종 JSONL, tokenizer·chat template·loss mask 검증, 학습은 아직 완료되지 않았다. 원문을 포함한 `private/`와 JSONL은 Git에서 제외한다.
