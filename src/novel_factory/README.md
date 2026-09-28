---
category_id: implementation-guide
lineage_id: lin-4658ef89-2a17-4bd6-bd9f-b8a55f073814
document_id: doc-ab931f78-f31b-4d1a-b3e4-1b54ba4eaf5d
parent_lineage_id: legacy-b73dc239-4fdc-51c4-b92b-91ce34c876e9
abstract: 고정 코퍼스 입력·제출·검토·재개 CLI와 첫 수직 절편의 사용 범위를 확인할 때 읽는다.
version: 0.2.1
created_at: '2026-09-27T02:30:07.000000Z'
updated_at: '2026-09-27T04:55:31Z'
tags:
- 제품CLI
- DB정본
canon: false
---
# 첫 코퍼스 분석 절편

개발 환경: `python3 -m venv .venv-product` 후 `.venv-product/bin/python -m pip install -e .`. 아래 `novel-factory`는 `.venv-product/bin/novel-factory`를 뜻한다. 원문·분할판은 `data/analysis/novel-corpus.sqlite3`에 있고, 분석 작업·제출·독립 검토 상태도 이 DB가 정본이다. 첫 절편의 빈 분석 테이블 추가는 [I0/I1 검증 기록](../../data/analysis/product-i0-i1-verification.json)에, 기존 역구성 원장 이관과 백업·원문 불변 대조는 [I1 이관 검증 기록](../../data/analysis/product-i1-migration-verification.json)에 남겼다. 새 흐름과 합성 제출·검토는 SQLite backup **사본**에서 검증했고 합성 결과를 운영 DB에 넣지 않았다.

```sh
novel-factory --db COPY prepare --work WORK --source-revision REV_ID \
  --source-sha RAW_SHA256 --segmentation SEG_ID --chapter CHAPTER_NUMBER
novel-factory --db COPY register-window --window-id WINDOW_ID --work WORK \
  --source-revision REV_ID --source-sha RAW_SHA256 --segmentation SEG_ID \
  --start-cp START --end-cp END --text-sha SPAN_SHA256 \
  --role gemma_style --split train --workflow-kind reverse_window \
  --approval-ref DECISION_ID --approved-by REVIEWER_ID
novel-factory --db COPY prepare-window WINDOW_ID
novel-factory --db COPY submit TASK_ID SUBMISSION_ID AUTHOR_ID result.json
novel-factory --db COPY view-result TASK_ID SUBMISSION_ID
novel-factory --db COPY review TASK_ID SUBMISSION_ID REVIEW_ID OTHER_REVIEWER_ID \
  accepted SUBMISSION_SHA256 '원문 근거와 입력 범위를 대조함'
novel-factory --db COPY resume TASK_ID
```

`prepare`는 핀으로 지정한 유일한 확정 번호 회차만, `prepare-window`는 사전에 결정 근거와 함께 등록한 구간만 본문을 출력한다. `--chapter`에 구간 순번을 넣거나 `--window-id`를 공식 화 번호로 쓰지 않는다. UTF-8 디코딩 후 BOM·CRLF를 보존한 코드포인트 `[start_cp,end_cp)`와 SHA-256을 고정한다. 조회 실패 시 원본 TXT나 동결 JSON 본문으로 돌아가지 않는다. `view-input TASK_ID`와 `export-input TASK_ID OUTPUT`도 같은 DB 핀에서 해당 작업의 본문만 읽는다. 기존 `full.py show-window`/`build.py show-unit`은 고정 이관판의 원문 좌표·역할·split과 DB 근거가 맞을 때에만 출력한다. 기존 272개 역구성 수락 결과와 보류·검토 수정 이력은 고정 import 판 `reverse-20260925-i1`로 이관했고, 뷰어와 JSONL은 DB에서 생성한다. 이관된 기록은 새 `analysis_tasks` 작업이나 350화 카드가 아니다.

기존 `*-bNN-wNN:primary|alternative` 전체 구간은 앞선 window의 DB 독립 검토가 끝나야 본문을 읽을 수 있고, alternative는 같은 window의 primary가 hold된 뒤에만 열린다. 이 검사는 `prepare-window`, `view-input`, 기존 `full.py show-window`에 공통으로 적용된다. `full.py show-window --inspect`는 순서와 관계없이 메타데이터만 보이며 본문 작업을 만들지 않는다. 별도 승인한 독립 구간에는 전체 구간의 순차 규칙을 덧씌우지 않는다.

이관된 역구성의 조회·내보내기는 [DB 이관 사용법](../../tools/reverse_dataset/README.md#현행-db-경로)을 따른다. `legacy-status`는 보류·후보 미생성·검토 수정판을 읽어 다음 검토 대상을 찾지만, 이 불변 이관판을 자동으로 새 분석 작업에 연결하거나 교정하지는 않는다. 필요한 구간을 새로 고정해 `prepare`/`submit`/`review` 경로로 처리한다.

제출물 JSON은 별도 Native Codex 작업에서 만들고 `submit`은 그 파일의 정확한 바이트 SHA를 저장한다. 독립 검토자는 `view-result TASK_ID SUBMISSION_ID`로 **DB에 저장된 제출 원문·SHA·작성자·고정 source 판과 판정**을 조회한다. 바이트 파일이 필요하면 `export-result TASK_ID SUBMISSION_ID OUTPUT`을 쓴다. 두 명령은 잘못 연결된 작업·제출 ID를 거부하며, 제출 당시 CRLF도 보존한다. 다른 검토자가 해당 SHA를 `review`로 판정하기 전에는 `resume`이 완료라고 표시하지 않는다. 같은 제출 ID의 다른 내용, 같은 검토 ID의 다른 판정, 자기 검토는 거부한다. 수락 결정의 교정은 새로운 `REVIEW_ID`와 기존 `review_sha256`을 `review --previous-review-sha256`에 주어 명시적으로 남긴다. `rejected`·`hold`로 교정한 뒤에는 새 제출 ID로 다시 제출할 수 있고 과거 행은 보존된다. `gemma_style`과 `sota_planning`의 역할·split은 등록된 window에 고정되며, 학습 가설은 작품의 잠금판·정사가 아니다.

검사: `.venv-product/bin/python -m unittest discover -s tests/novel_factory -v`, 같은 방법으로 `tools/novel_corpus`와 `tools/reverse_dataset` 테스트를 실행한다. 첫 실데이터 검증은 원문을 출력하지 않고 사본에서 선택 span·해시·상태만 비교한다.

## I2 문체 학습용 고정 릴리스

검토 완료된 역구성 import `reverse-20260925-i1`에서 역할별 `DatasetRelease`를 만든다. `gemma_style`의 원문 정답과 `sota_planning`의 역구성 가설은 분리되며, 기존 `train`·`development_validation`·`development_holdout` 배정을 다시 나누지 않는다. 아래 데이터셋 명령은 먼저 DB **사본**에서 확인했다. 운영 DB에는 style 90건(`ds-gemma-style-a1e745929adcaf879446ad42`)과 planning 182건(`ds-sota-planning-d55cd8d4e7820b9bf479e997`)의 불변 릴리스를 발행했다. H200의 짧은 실제 시험에서 style train 두 건을 2 step 학습·별도 프로세스 재로드했고, 검증된 결과를 `model-f2638e4194ec1c3057276497` 후보로 등록했다. `writing_eligible=0`이며 집필용 채택이나 문체 향상 판정은 아니다. 범위와 백업·원문 불변 검사는 [I2 기록](../../data/analysis/product-i2-training-verification.json)에 있다.

DB의 후보 기록은 모델 가중치가 아니라 경로·판본·해시·상태를 보존한다. 어댑터 보관과 나중 재사용 조건은 [toy-tune 사용법](../../toy-tune/README.md#저장된-lora-모델-재사용)에 있다.

```sh
novel-factory --db COPY release-dataset --import-id reverse-20260925-i1 --role gemma_style
novel-factory --db COPY release-dataset --import-id reverse-20260925-i1 --role sota_planning
novel-factory --db COPY dataset-summary STYLE_RELEASE_ID
novel-factory --db COPY export-style-packet STYLE_RELEASE_ID PRIVATE/frozen-style-packet.json
toy-tune prepare --runtime toy-tune/configs/runtimes/local-cpu.toml \
  --workspace PRIVATE/toy-artifacts --frozen-packet PRIVATE/frozen-style-packet.json
toy-tune verify-dataset --runtime toy-tune/configs/runtimes/local-cpu.toml \
  --workspace PRIVATE/toy-artifacts --dataset-id PREPARED_DATASET_ID
```

`toy-tune`은 별도 설치된 CLI를 뜻한다. `export-style-packet`은 새 파일만 만들며 내용은 stdout에 출력하지 않는다. 준비 manifest와 모든 payload SHA 및 DB 정본 packet SHA를 대조한 뒤 `request-training REQUEST.json`, `import-training-result RESULT.json`, `training-status RUN_ID`를 사용할 수 있다. `real` 요청은 순서 있는 1–4개 train ID를 `selected_sample_ids`에 명시해야 한다. 완료 결과는 동일 시도의 요청·학습·재로드 보고서와 실제 adapter SHA를 대조한 뒤 후보로만 반입하며, `demo`와 `real` 모두 `ModelArtifact.writing_eligible=0`이다. 실패한 시도와 그 뒤의 새 시도는 별도 판으로 보존한다. 이 명령들은 모델을 작품에 채택하거나 작품 정사를 바꾸지 않는다.
