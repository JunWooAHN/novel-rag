---
category_id: implementation-guide
lineage_id: lin-7ce34941-b635-4550-8ee3-f6f8ad0b0c66
document_id: doc-c68c52d1-fd77-4dc0-a663-df1bc64543de
parent_lineage_id: legacy-b73dc239-4fdc-51c4-b92b-91ce34c876e9
abstract: 위키피디아 선택 단락의 31B 후보 추출 입력 고정, 실행, 근거 좌표 검증 절차를 볼 때 읽는다.
version: 0.1.1
created_at: '2026-09-27T05:26:25.000000Z'
updated_at: '2026-09-28T00:19:47Z'
tags:
- 위키백과
- 온톨로지
- 사용법
canon: false
---
# 위키피디아 31B 소량 추출 시험 도구

후속 enwiki+비영어 wiki의 **DB 원문→후보·근거 행→한국어 벡터 조회** 작은 수직 절편은 [다국어 시험 사용법](multilingual/README.md)에 둔다. 이 절의 기존 영어판 패킷·원시 출력은 변경하지 않는다.

이 폴더는 영어 위키피디아 덤프의 다섯 **선택 단락**에서 H/K/B 후보를 한 번 생성한 실험 코드다. 결과는 `candidate_unreviewed` 또는 `held`이며 현실 온톨로지 정본이 아니다. 실행 결과와 의미상 결함은 [시험 보고](../../docs/research/20260927-gemma4-31b-wikipedia-ontology-trial.md)에 있다.

1. `prepare.py`가 로컬 `wiki-dump/`의 해당 page ID XML을 스트리밍으로 읽어 페이지·revision·main slot과 hash를 `data/analysis/private/ontology-trial/pages/`에 고정한다. `make_packet.py`는 `selections.json`의 `[start,end)` UTF-8 byte 범위와 `shard-hashes.json`을 확인해 `trial-packet.json`을 만든다. 패킷에는 문서 전체가 아니라 5개 선택 구간만 들어간다.
2. `run.py --packet PACKET --output-dir RESULTS --cache-dir MODEL_CACHE`는 고정 `google/gemma-4-31B-it` revision을 BF16 단일 GPU에서 로드해 단위별 원시 JSON을 보존한다. 이 시험에서는 H200의 별도 `ontology-trial/` 폴더에 코드와 선택 패킷만 전송했다. 원격 실행에는 해당 모델 가중치와 호환되는 `transformers`·`torch` 설치가 필요하다.
3. `verify.py --packet PACKET --result-dir RESULTS --mapping-dir docs/plans/wikipedia-history-sot-mapping --out VERIFIED`가 모델·프롬프트·패킷 SHA와 매핑 ID를 확인하고, 짧은 인용을 원본 slot byte 좌표로 역매핑한다. 좌표 연결은 사실성·분류의 승인이 아니다. 원본 결과를 고쳐 통과시키지 않는다.

이번 고정 입력의 파일은 `data/analysis/private/ontology-trial/`에 있으며 소설 원문·키·작품 DB와 분리했다. 새 시험을 할 때는 다른 출력 경로를 사용하고 결과의 모델판·프롬프트 SHA를 다시 확인한다. 다섯 결과 중 정확 인용 실패 2건은 재시도로 덮어쓰지 않고 보류했다.

## 같은 구간의 근거 보강 비교

`diagnose.py`는 `--packet`, `--baseline-result-dir`, `--output-dir`, `--cache-dir`를 받아 첫 후보의 부족한 근거와 검색 질문을 별도 JSON으로 기록한다. 질문·모델 기억은 근거가 아니다. `build_evidence.py --packet ... --pages ... --out ...`은 같은 revision의 위키 추가 구간을 고정하고, 이번에는 루트가 직접 읽은 기관 페이지의 짧은 발췌를 출처·URL·열람일과 함께 패킷에 연결했다. 고정 결과는 `data/analysis/private/ontology-trial/enrichment/extra-evidence.json`이다. 웹 발췌 문자열의 SHA는 실제 페이지 전체의 재검증을 뜻하지 않는다.

`reextract.py --packet ... --mode wiki_only|enriched --output-dir ... --cache-dir ...`로 **같은 모델·프롬프트**의 두 군을 실행했다. `enriched`에만 `--extra-evidence`를 준다. `verify_reextract.py`는 해당 모드와 `--packet`, `--pages`, `--result-dir`, `--mapping-dir`, `--out` 및 보강군의 `--extra-evidence`를 받아 모델·프롬프트·근거 좌표·매핑 ID를 기계 대조한다. 원시 응답은 각 군의 `raw/`에 보존하며 결과를 고쳐 통과시키지 않는다. 이번 시험의 [비본문 비교 기록](../../data/analysis/ontology-trial-enrichment-comparison.json)은 wiki-only **30후보/21연결/9보류**, 보강군 **32/26/6**을 남긴다. 기계 연결과 독립 의미 검토는 별개이고 둘 다 현실 온톨로지 릴리스가 아니다. 외부 근거만의 효과는 분리해 측정하지 않았다.
