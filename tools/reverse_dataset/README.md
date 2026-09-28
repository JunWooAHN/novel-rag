---
category_id: corpus-tools
lineage_id: lin-1b3d4431-50f1-4ff7-814d-c99863998c59
document_id: doc-03b39f75-5efb-4dc6-9452-744a1d3bb92c
parent_lineage_id: null
abstract: 원문 역구성 개발 데이터의 순차 입력, 역할별 target, split 검증과 로컬 JSONL 생성 절차를 사용할 때 읽는다.
version: 0.1.0
created_at: '2026-09-25T04:26:01.000000Z'
updated_at: '2026-09-27T03:09:40Z'
tags:
- 학습데이터
- 역설계
canon: false
---
# 원문 역구성 데이터셋 도구

이 도구의 이전 파일 원장은 [제품 코퍼스 DB](../../src/novel_factory/README.md)의 고정 import 판 `reverse-20260925-i1`로 이관했다. 첫 50 source-order 구간은 공식 회차가 아니며, 고종 `gemma_style`의 정답은 원문 장면이고 고려·폴란드 `sota_planning`의 target은 독립 검토한 역구성 계획이다. 역구성은 원저자의 실제 의도·작품 정사가 아니다. 개발 split의 `development_holdout`은 미관측 최종 시험이 아니다.

## 현행 DB 경로

`.venv-product/bin/python`으로 실행한다. 운영 DB는 `data/analysis/novel-corpus.sqlite3`이고, 분석·검토 상태와 고정 import 판의 정본도 이 DB다. 이관은 원문·분할판 백업과 사본 검증 후 수행했고 [검증 기록](../../data/analysis/product-i1-migration-verification.json)에 결과를 남겼다. 같은 import ID/원장 SHA의 재실행은 멱등이며 다른 내용은 거부한다. 원본 리뷰·결정·JSONL 파일은 삭제하지 않고 감사 근거로 보존한다. 사용자에게 보여 주는 HTML/JSONL은 DB에서 다시 만들 수 있는 파생물이다.

```sh
.venv-product/bin/novel-factory --db data/analysis/novel-corpus.sqlite3 import-legacy
.venv-product/bin/novel-factory --db data/analysis/novel-corpus.sqlite3 legacy-summary
.venv-product/bin/novel-factory --db data/analysis/novel-corpus.sqlite3 legacy-status --work goryeo
.venv-product/bin/novel-factory --db data/analysis/novel-corpus.sqlite3 legacy-status --selection-id goryeo-b01-w01
.venv-product/bin/python tools/reverse_dataset/build.py show-unit goryeo 1 --db data/analysis/novel-corpus.sqlite3
.venv-product/bin/python tools/reverse_dataset/full.py show-window goryeo 1 1 --db data/analysis/novel-corpus.sqlite3
.venv-product/bin/python tools/reverse_dataset/full.py show-window goryeo 1 2 --inspect --db data/analysis/novel-corpus.sqlite3
```

`legacy-status`는 수락·후보 보류·후보 미생성 attempt·검토 수정판 경로와 SHA를 보이며 원문 본문은 출력하지 않는다. 이관판은 불변이다. 보류 건을 해결하거나 새 분석을 제출할 때는 제품 CLI의 고정 입력 `prepare`/`prepare-window`, `submit`, DB 제출판 `view-result`, 독립 `review`, `resume`를 사용한다. 과거 수락 272건은 350화 분석 카드, 학습 투입 승인, 작가 캐논으로 승격되지 않는다.

```sh
.venv-product/bin/python tools/reverse_dataset/export.py build \
  --db data/analysis/novel-corpus.sqlite3 --import-id reverse-20260925-i1 \
  --output-dir data/training/db-derived/reverse-20260925-i1/private/export
.venv-product/bin/python tools/reverse_dataset/viewer.py \
  --db data/analysis/novel-corpus.sqlite3 --import-id reverse-20260925-i1 \
  --output data/training/db-derived/reverse-20260925-i1/private/viewer/index.html
```

`full.py export --db ... --output-dir ...`도 같은 DB 내보내기에 위임한다. 내보내기 함수는 기존 디렉터리를 덮어쓰지 않으므로 위 두 내보내기 명령을 **같은 경로에 연달아** 실행하지 않는다. 원본 JSONL 9개와 신규 9개는 각 파일의 바이트와 순서를 대조한다. 뷰어는 DB에 고정된 272개 accepted 행의 정확한 JSONL과 필요한 원문 answer span만 조회한다. 전체 소설 원본을 매번 모델 문맥에 넣지 않는다.

## 보존한 이전 입력 원장

`data/training/reverse-20260925`의 30개 batch/150개 시도와 `data/training/reverse-full-20260925`의 144개 window/144개 시도는 선정 좌표·역할·split·검토·결정 근거를 보존한다. 전체 review revisions와 작업 초안도 이관 아티팩트로 남는다. 원본 파일을 쓰던 `build.py freeze/batch`와 `full.py freeze/init-review/save-review/checkpoint`는 DB 상태와 관계없이 차단한다. 이관 전 파일 작성 절차는 과거 산출물의 유래로만 읽는다. 기존 원장 파일을 수정해도 DB release가 조용히 바뀌지 않는다.

기존 후보 계약은 [초반 schema](review-batch.schema.json)와 [전체 창 schema](full-review.schema.json)에 있다. 원문 좌표·SHA와 관찰/해석은 모델 payload 밖의 근거로 유지한다. 결정을 교정할 때는 이전 검토 원바이트 SHA와 새 판정 이력을 보존하고 새 독립 검토를 거친다.
