# toy-tune 클린 아키텍처 및 실행 환경 구축 계획 v0.1

- 작성일: 2026-09-14
- 상태: 승인 후 1차 구현. Phase A 및 B/C의 로컬 기반 완료; 원격·학습 검증 대기
- 목적: 웹소설 문체 파인튜닝을 작은 실험부터 수행하면서 실행 머신, 학습 엔진, 지식 저장소를 독립적으로 교체한다.
- 첫 실행 환경: KT Cloud Backend.AI의 할당된 H200. 실제 이미지·자원·접속 정보는 접속 후 확인한다.
- 프로젝트 위치: `/Users/ahnjunwoo/dev/novel/toy-tune`
- 설계 기준: 이번 계획에는 Ponytail 원칙을 적용하지 않는다. 필요한 경계를 충분히 설계하고 구현 범위는 단계별로 정한다.

## 1. 기존 계획과의 관계

상위 기준은 [핵심 시스템 설계](../systems/README.md), 상세 계약은 [통합 아키텍처 v5](../20260914-novel-factory-architecture-v5.md)를 따른다. 이 문서는 toy-tune의 구현 단계·폴더·실행 계약을 상세화한다. 전체 지식 구축·집필·정사 공개 책임은 상위 문서에서 정의하며 toy-tune에 합치지 않는다.

전체 시스템은 작가 앵커 → 역설계·Backfilling → 정방향 검토 → 역사표 승인·잠금 → Gemma 집필을 중심으로 한다. toy-tune의 확장 목표는 그 역사표·장면 명세를 지정 문체의 본문으로 실현하는 모델이다. 승인된 중간 사건도 Writer가 임의로 바꿀 수 없다. 핵심 엔진은 별도 책임으로 구현하며 첫 문체 토이 학습의 선행 조건으로 만들지 않는다. 인과 확률·임팩트 등급·전파 속도 점수는 사용하지 않는다.

모델 역할은 운영 본문 생성·재작성 Gemma, 소설 문체 임베딩 Munche, 지식 의미 임베딩 Granite 검증, 기획·검수·추출 SOTA로 구분한다. 원역사·과학·인물 자료는 영어 위키백과부터 구축한다. Granite 97M/384차원이 첫 기준선이며 311M/256차원과 대량 인덱싱 전에 비교한다. 작은 토이 생성 모델도 Gemma 계열을 사용한다. SOTA 본문 생성은 중간 품질 비교용이며 운영 writer를 대체하지 않는다. 정확한 SOTA 모델·버전·provider는 역할별 설정으로 지정한다.

[2026-09-11 토이 학습 계획](20260911-gemma4-toy-finetuning-practice-plan-v0-1.md)의 목표인 소량 원문, 짧은 LoRA 학습, adapter 저장·재로드, baseline 비교를 유지한다. 그 문서의 `experiments/gemma4-toy/` 및 단일 `run.py` 산출물 구조는 이 문서로 대체한다. 날짜별 일정은 준비 상태에 맞춰 재배치한다.

[2026-09-08 초기 학습 계획](20260908-gemma4-finetuning-plan-v0-1.md)은 실행 기준으로 사용하지 않는다. 소형 모델 식별자와 31B 계보, 구체적인 패키지 버전은 실행 시점에 호환성을 검증한다. 이 아키텍처는 특정 Gemma 크기나 변형에 종속되지 않는다.

다음 논의의 데이터·모델 역할 분리를 이어받는다.

- [웹소설 문체 학습 조사](../reports/20260908-gemma4-31b-heretic-style-finetuning-deep-research-v0-2.md)
- [SQLite 역사·정사 구조 논의](../reports/20260908-alternate-history-sqlite-canon-report-v0-1.md)
- [Munche 문체 임베딩 통합 계획](20260914-munche-style-embedding-integration-plan-v0-1.md): 2026-09-14 추가. 데이터 선별·평가와 후속 문체 예문 검색을 다룬다. 계획 편입이며 구현 완료를 뜻하지 않는다.
- [영어 위키백과·Granite 지식 구축 계획](20260914-enwiki-granite-knowledge-ingestion-plan-v0-1.md): 영어 우선 수집·지식 의미 검색. toy-tune은 고정된 근거 패킷을 소비하며 전체 수집을 소유하지 않는다.

## 2. 독립적으로 바뀌어야 하는 네 가지 축

| 축 | 첫 구현 | 후속 선택 | 바뀌지 않아야 할 부분 |
|---|---|---|---|
| 실행 위치 | Backend.AI H200 세션 | 다른 NVIDIA 서버, 로컬 맥북 | 데이터 계약, 실험 목적, 평가 기준 |
| 학습·생성 엔진 | Transformers/PEFT 계열 | MLX 계열, 다른 학습 엔진 | 애플리케이션 입출력, 모델·결과 식별 규칙 |
| 지식 저장소 | 정적 근거 패킷, 이후 로컬 SQLite | 별도 서버의 PostgreSQL | 유효 정사, 원역사 override, 인물 지식의 의미 |
| 산출물 저장소 | 영구 파일시스템 | 다른 디스크, 객체 저장소 | dataset/run/artifact 식별자와 manifest |

H200은 하드웨어이고 Backend.AI는 세션 운영 환경이며 Transformers는 학습 엔진이다. 세 가지를 하나의 `H200Backend`로 묶지 않는다. PostgreSQL의 위치 역시 학습 머신의 위치와 독립이다.

목표 조합은 다음과 같다. 조합 가능성은 구조적 목표이며, 모델·엔진 호환성과 네트워크 접근은 각 실행 전에 검증한다.

| 실행 위치 | 엔진 | 지식 입력 |
|---|---|---|
| Backend.AI H200 | Transformers/PEFT | 사전 추출한 SQLite 근거 패킷 |
| 다른 GPU 서버 | Transformers/PEFT | 클라우드 PostgreSQL에서 추출한 패킷 |
| 로컬 맥북 | MLX | 로컬 SQLite 또는 클라우드 PostgreSQL 패킷 |
| DB에 접근할 수 없는 머신 | 지원되는 엔진 | 반입한 불변 데이터셋·근거 패킷 |

학습 머신이 원격 PostgreSQL에 항상 접속할 수 있어야 하는 구조를 피한다. 데이터 준비 단계에서 지식을 고정한 뒤 학습은 그 결과물을 소비한다.

## 3. 프로젝트 책임과 모노레포 경계

`toy-tune`은 데이터셋 준비, 모델 학습, 생성 평가, 산출물 내보내기를 소유한다. 작품 본문 원본, 공개 역사전표, 공용 오리진 역사, 운영 정사 DB는 각각의 소유 프로젝트가 관리한다.

- 모노레포 루트와 기존 `venv/`, `webnovel-writer` 의존성을 공유하지 않는다.
- 독립 `pyproject.toml`, 패키지 이름 `toy_tune`, CLI 이름 `toy-tune`을 사용한다.
- 다른 작품 폴더를 Python import 또는 `sys.path` 변경으로 연결하지 않는다.
- 원문 반입은 사용자가 지정한 경로와 반입 명세로 수행한다. 모노레포 전체 자동 탐색·업로드는 하지 않는다.
- 학습기가 운영 `canon`을 갱신하지 않는다. 생성 결과도 자동으로 공개 정사가 되지 않는다.
- 정사 쓰기·마이그레이션·공개 처리는 해당 데이터 소유 프로젝트의 책임이다.
- 모노레포 밖 다른 서버에서도 `toy-tune` 소스 묶음만으로 설치·실행할 수 있어야 한다.

## 4. Clean Architecture 의존성 규칙

```text
CLI / 작업 요청
      │
      ▼
application ────────→ domain
  │ ports 정의          ▲
  ▲                     │
outbound adapters ───────┘

bootstrap: 설정을 읽고 adapter를 port에 연결
ops: 실행 머신 준비·전송·프로세스 시작을 담당
```

`domain`은 표준 Python 자료형으로 학습 샘플, 출처, 근거 패킷, 모델 참조, 실행 상태의 의미와 규칙을 정의한다. Torch tensor, ORM 객체, DB connection, SSH client, 절대 파일 경로를 핵심 모델에 넣지 않는다.

`application`은 준비→검증→학습→평가 흐름과 필요한 port를 정의한다. `transformers`, `torch`, `mlx`, `sqlite3`, PostgreSQL 드라이버, Backend.AI SDK를 직접 import하지 않는다.

`adapters`는 외부 엔진·DB·파일 표현을 내부 계약으로 변환한다. 내부 port에 대한 의존 방향을 지키며, application이 구체 adapter를 가져와 호출하지 않는다.

`bootstrap`은 설정과 capability를 검증하고 구체 구현을 조립한다. `ops`는 이미 설치된 동일 CLI를 어떤 머신에서 실행할지 담당한다. 학습 use case 안에서 SSH 접속이나 Backend.AI 세션 생성을 하지 않는다.

### 4.1 포트의 의미와 범위

| 포트 | 제공하는 계약 | 초기·후속 구현 |
|---|---|---|
| `SourceReader` | 선택된 원문과 출처 정보 읽기 | 지정 파일 반입 |
| `KnowledgeReader` | 질의 시점·정사 revision에 맞는 구조화 근거 읽기 | SQLite, PostgreSQL |
| `PacketReader` | 이미 고정된 근거 패킷 읽기 | JSONL snapshot |
| `DatasetStore` | dataset manifest와 불변 샘플 묶음 읽기·발행 | 파일시스템 |
| `TrainingEngine` | capability 확인, 학습 요청 실행, checkpoint 참조 반환 | Transformers/PEFT, MLX |
| `GenerationEngine` | 모델 참조와 입력으로 생성 결과 반환 | Transformers, MLX |
| `StyleEncoder` (후속) | 텍스트의 문체 벡터와 인코딩 계보 반환 | Munche v1/v2 검증 후 SentenceTransformers/PEFT adapter |
| `SemanticEncoder` (지식 구축·검색 영역의 후속 계약) | 질의·근거 구간의 의미 벡터와 계보 반환 | Granite adapter. toy-tune의 패킷 소비만으로는 구현 불필요 |
| `ArtifactStore` | 산출물 발행·검증·로컬 materialize | 파일시스템, 이후 객체 저장소 |
| `RunStore` | 실행 manifest·상태·시도 이력 기록 | 파일시스템 |

정적 패킷과 실제 DB 질의는 서로 다른 입력 계약이다. 정적 샘플 파일이 모든 DB 질의를 지원하는 것처럼 가장하지 않는다. `ContextCompiler`가 DB 근거를 패킷으로 만드는 흐름과 `PacketReader`가 그 패킷을 재사용하는 흐름을 구분한다.

학습과 추론을 한 거대 backend 인터페이스에 묶지 않는다. 추론만 가능한 모델 형식도 표현할 수 있어야 한다. 포트에 벤더별 인자를 그대로 펼치지 않고 공통 실행 명세와 검증된 엔진 전용 설정을 분리한다.

## 5. 소스 폴더 목표 구조

다음은 책임을 배치할 목표 지도다. 후속으로 표시된 구현은 필요 단계에서 추가하고 빈 구현 파일로 미리 생성하지 않는다.

```text
toy-tune/
├── README.md
├── pyproject.toml
├── .gitignore
├── configs/
│   ├── experiments/             # 모델·학습·평가 실험 설정
│   ├── datasets/                # 원문 선택·split·패킷 생성 설정
│   ├── runtimes/                # backendai-cuda / generic-cuda / mac-mlx
│   └── knowledge/               # snapshot / sqlite / postgres 설정 예시
├── environments/
│   ├── cpu/                     # 데이터 준비·단위 테스트 환경
│   ├── cuda/                    # 검증된 이미지·의존성 잠금 정보
│   └── mlx/                     # 후속 Apple Silicon 환경
├── schemas/                     # 외부 JSON 계약, 버전 관리
├── src/toy_tune/
│   ├── __init__.py
│   ├── __main__.py
│   ├── domain/
│   │   ├── samples.py
│   │   ├── knowledge.py
│   │   ├── experiments.py
│   │   ├── artifacts.py
│   │   └── errors.py
│   ├── application/
│   │   ├── ports/
│   │   │   ├── sources.py
│   │   │   ├── knowledge.py
│   │   │   ├── engines.py
│   │   │   └── stores.py
│   │   ├── services/
│   │   │   ├── context_compiler.py
│   │   │   ├── dataset_builder.py
│   │   │   └── evaluation.py
│   │   └── use_cases/
│   │       ├── preflight.py
│   │       ├── prepare_dataset.py
│   │       ├── generate.py
│   │       ├── train.py
│   │       ├── evaluate.py
│   │       └── export.py
│   ├── adapters/
│   │   ├── inbound/cli.py
│   │   └── outbound/
│   │       ├── files/           # 원문·JSONL·manifest·artifact
│   │       ├── knowledge/
│   │       │   ├── sqlite.py    # 후속
│   │       │   └── postgres.py  # 후속
│   │       └── engines/
│   │           ├── hf_peft/     # tokenizer·template·collator·train·generate
│   │           └── mlx/         # 후속
│   ├── configuration.py
│   └── bootstrap.py
├── tests/
│   ├── fixtures/                # 합성 원문·합성 지식·작은 manifest
│   ├── architecture/            # 금지 import·의존 방향
│   ├── unit/                    # GPU·DB·네트워크 없이 실행
│   ├── contract/                # 동일 의미를 구현하는 adapter 공통 검사
│   └── integration/             # cuda / mlx / sqlite / postgres 선택 실행
├── ops/
│   ├── backendai/               # 세션·SSH·마운트 실행 안내
│   ├── ssh/                     # 다른 서버에도 쓰는 코드 전송 절차
│   └── local/                   # 로컬 실행 안내
└── docs/
    ├── architecture.md
    ├── data-contract.md
    └── runbook.md
```

`schemas/`는 외부 파일 계약, domain 모델은 내부 표현이다. 동일 규칙을 서로 다르게 수작업 복제하지 않는다. 구현 시 직렬화 경계를 정하고 round-trip 계약 테스트로 불일치를 탐지한다. 문서·아키텍처 계획은 모노레포 `docs/plans`에, 실행자가 필요한 프로젝트 안내는 `toy-tune/docs`에 둔다.

## 6. 소스와 실행 데이터의 물리적 분리

Backend.AI vfolder를 `toy-tune`으로 만들고 기본 마운트 후보를 `/home/work/toy-tune`으로 잡는다. 이 경로는 runtime 설정에만 존재한다. 다른 서버·맥북에서는 서로 다른 절대 경로를 지정할 수 있다.

```text
<persistent-root>/
├── code/
│   └── <source-id>/             # 실행에 사용한 불변 소스 묶음
└── workspace/
    ├── sources/<source-id>/     # 선택 반입한 원문과 출처, 불변
    ├── knowledge/<snapshot-id>/ # DB snapshot 또는 추출된 근거 패킷
    ├── datasets/<dataset-id>/
    │   ├── manifest.json
    │   ├── train.jsonl
    │   ├── validation.jsonl
    │   ├── test.jsonl
    │   └── statistics.json
    ├── cache/                   # 재다운로드·재계산 가능한 데이터
    ├── runs/<run-id>/
    │   ├── manifest.json
    │   ├── resolved-config.json
    │   ├── attempts/<attempt-id>/
    │   │   ├── environment.json
    │   │   ├── logs/
    │   │   └── checkpoints/
    │   ├── generations/
    │   └── evaluations/
    └── exports/<artifact-id>/   # adapter·계보·검증 결과·checksum
```

- 로컬 개발용 workspace도 원칙적으로 Git checkout 밖 사용자 지정 경로를 사용한다.
- 코드 전송은 `code/<source-id>`만 대상으로 한다. 실행 중인 소스 묶음은 덮어쓰지 않는다.
- 원문·출력·모델은 파일명이나 확장자 하나에 기대지 않고 저장 경로 전체로 Git 추적에서 분리한다.
- `cache`는 삭제해도 재생성 가능해야 한다. 최종 모델이 캐시의 상대 symlink에만 의존하지 않게 한다.
- 엔진이 로컬 파일 경로를 요구하면 artifact를 로컬 scratch로 materialize하고 checksum을 확인한다.
- scratch는 가속용이다. 보존해야 할 checkpoint·manifest는 영구 저장소에 발행한다.
- 하나의 run에는 동시에 하나의 writer만 허용한다. 향후 여러 머신에서 실행하면 run별 소유권을 관리하며 동일 경로를 동시 갱신하지 않는다.

## 7. DB 위치·제품 교체와 지식 계약

### 7.1 논리 식별과 물리 접속 정보 분리

내부 요청은 `work_id`, `canon_revision`, `original_release`, `story_time`, `pov_character_id`와 질의 조건을 사용한다. SQLite 파일명·PostgreSQL DSN·테이블명은 adapter 설정에 둔다.

`original.sqlite`, `canon.sqlite`은 현재 물리 구현 이름이다. 도메인에서는 원역사 기준선과 작품별 단일 공개 정사로 취급한다. PostgreSQL에서는 같은 의미를 schema·table·work ID 등으로 구현할 수 있다.

`KnowledgeReader`는 raw SQL이나 ORM 객체를 돌려주지 않는다. 안정 ID, 사실 상태, 유효 시점, 출처, 인물 지식, revision을 가진 자료형을 반환한다. 벡터는 후보 검색용이며 유효 정사·override 판정을 대체하지 않는다.

### 7.2 학습 데이터에 들어간 지식 고정

```text
SQLite 또는 PostgreSQL
    → 일관된 revision의 구조화 근거
    → ContextCompiler
    → 불변 패킷 + provenance + checksum
    → 불변 학습 데이터셋
    → H200 / 다른 서버 / Mac에서 학습
```

학습 iteration마다 운영 DB를 질의하지 않는다. 원격 DB 장애가 진행 중 학습을 중단시키지 않고, 이후 정사가 바뀌어도 이전 실험을 다시 평가할 수 있어야 한다.

실제 집필 추론에서는 장면별 최신 근거를 조회할 수 있다. 이 경우에도 해당 생성에 사용한 패킷과 revision을 기록한다. toy-tune이 이를 조회할 때 사용하는 계정은 읽기 전용을 기본으로 한다.

후속 패킷 계약은 현재 공개 사실과 승인된 역사표 명세를 분리한다. `plan_revision`, 승인·잠금 범위, 필수 사건·금지 전개·완료 조건을 기록하며 이를 인물의 지식으로 자동 취급하지 않는다. 운영 계획은 계획 승인 use case만 변경할 수 있고, 학습기는 snapshot을 소비한다. 이 확장은 아직 구현된 `packet_id` 기능이 아니다.

### 7.3 교체 검증

SQLite→PostgreSQL 전환은 단순 DSN 변경으로 간주하지 않는다. schema migration과 데이터 이관은 소유 프로젝트에서 수행하고, toy-tune에서는 adapter를 검증한다.

- 동일 합성 전표·정사 fixture에서 안정 ID, 필터, override, 인물 지식 결과를 대조한다.
- 날짜, timezone, NULL, 정렬·동률 처리, JSON 표현 차이를 명시한다.
- snapshot 추출 중 여러 질의가 같은 정사 revision을 보는 일관성을 보장한다. 재현 불가 상태면 데이터 발행을 실패시킨다.
- 벡터 확장·임베딩 모델 변경 시 검색 순위의 완전 일치를 보장하지 않는다. embedding revision과 retrieval 설정을 기록하고 검색 품질을 별도로 평가한다.
- SQLite 활성 파일은 파일시스템 특성을 확인하고, 실행 중 DB를 단순 복사하는 대신 일관된 snapshot을 사용한다.
- 맥북의 SQLite가 H200에서 자동으로 보인다고 가정하지 않는다. 선택 데이터·패킷 반입을 기본으로 하고 네트워크 노출은 별도 결정한다.

### 7.4 문체 임베딩은 지식 검색과 분리

소설 문체 임베딩은 Munche 전용, 역사·과학·인물 자료의 의미 검색은 Granite 경로로 분리한다. 구조화·키워드 조회와 Granite 의미 검색으로 근거를 찾고, Munche는 표현을 참고할 소설 예문을 찾는다. 문체 점수로 정사 유효성이나 역사전표를 변경하지 않는다. 생성용 Gemma의 LoRA와 Munche encoder의 LoRA도 별개다.

초기에는 파일 기반 문체 벡터 artifact를 사용한다. 이후 SQLite-vector 기반 `style_store`, 필요 시 PostgreSQL adapter를 검증한다. Granite 지식 벡터와 Munche 문체 벡터는 별도 공간·index로 두고 차원·revision·전처리를 manifest로 검증한다. 학습·평가에 사용한 문체 reference와 전처리는 불변 snapshot으로 보존한다. 문체 실험은 [Munche 계획](20260914-munche-style-embedding-integration-plan-v0-1.md), 지식 수집·검색은 [영어 위키백과·Granite 계획](20260914-enwiki-granite-knowledge-ingestion-plan-v0-1.md)을 따른다. 두 encoder의 완성을 첫 Gemma 저장·재로드 연습의 선행 조건으로 만들지 않는다.

## 8. 설정·의존성·capability

설정은 실험, 데이터, runtime, knowledge profile을 명시적으로 선택해 합성한다. 우선순위는 기본값→선택 profile→명시 CLI override로 고정한다. 비밀값은 별도 환경변수·credential 참조로 주입하고 resolved config에 저장하지 않는다.

예시 개념:

```text
experiment = smoke-lora
runtime = backendai-cuda | generic-cuda | mac-mlx
knowledge = frozen-packets | local-sqlite | cloud-postgres
workspace_root = 실행 머신별 경로
```

엔진이 선언해야 할 capability에는 지원 모델 계열·형식, 학습/생성, dtype, LoRA 대상, 길이 제약, checkpoint 재개·export 형식이 포함된다. 미지원 조합은 실행 전 명확히 실패한다. 설정을 조용히 무시하거나 BF16을 임의로 다른 dtype으로 바꾸지 않는다.

Python 기본 설치는 데이터·계약·CLI 테스트가 가능해야 한다. CUDA, MLX, PostgreSQL 의존성은 선택 그룹으로 격리하고 지연 import한다. CPU 또는 맥북에서 `doctor`·데이터 검증을 실행할 때 CUDA 패키지가 요구되지 않아야 한다.

환경 잠금은 CUDA와 macOS의 차이를 표현한다. 단일 lock이 플랫폼별 조건을 정확히 표현할 수 있는지 검증한 뒤 도구를 고른다. 불가능하면 환경별 잠금 명세를 사용한다. 제공 이미지의 PyTorch는 먼저 조사하고, 임의 업그레이드 없이 호환 환경을 확정한다. 이미지 식별자와 해석된 의존성 목록을 실행마다 보존한다.

## 9. 데이터 계보·평가 누수

원문에서 질문을 역으로 만드는 방식의 provenance를 보존한다. sample에는 작품·화·장면 ID, 입력·정답 원문 범위, 원문 해시, 질문 작성 방식, 사용한 도구·템플릿 버전, 근거 패킷 ID가 연결된다.

조건부 집필 학습에서는 원문 씬 확정 → SOTA 장면·사건 추출 → 이전 씬까지의 가상 역사표·문맥 복원 → 이번 씬의 집필 명세 → 원문 정답 순서로 입력을 구성한다. 가상 역사표는 학습 fixture이며 운영 정사가 아니다. 학습과 집필의 의미 필드·schema 버전은 맞추되 특정 XML 문자열의 완전 일치가 목표는 아니다. 목표 씬의 개요를 역구성한 경우 이를 표시하고, 실제 기획자가 제공할 수 있는 수준으로 제한한다. 미래 씬의 결과나 정답 문장을 입력에 숨기지 않는다.

- 실제 target은 선택한 원문을 유지하고 임의 재작성본과 구분한다.
- 같은 장면에서 파생된 샘플은 하나의 split에 둔다.
- target의 표현을 요약 질문에 복사한 경우를 자동 후보 탐지와 사람 검토로 점검한다. 자동 검사만으로 완전한 누수 제거를 보장하지 않는다.
- 정사 질의는 target 이후 공개 사실을 제외한다.
- 시간순 split에서 직전 target이 다음 split의 입력에 나타나는 경우를 명시한다. 이를 허용한 이어쓰기 평가는 독립 작품 일반화 평가와 구분한다. 엄격한 분리가 필요하면 경계에 제외 구간을 둔다.
- 반복 튜닝에 사용하는 validation과 최종 test를 구분한다. 같은 5개 prompt를 계속 보며 수정했다면 이를 개발 평가로 표시한다.
- 길이 초과 샘플은 조용히 잘라내지 않는다. 제외·분할·문맥 축소 정책과 통계를 남긴다.
- chat template, 특수 토큰, assistant loss mask는 엔진 adapter에서 변환하고 실제 학습 대상 토큰을 검사한다.

원문뿐 아니라 manifest의 파일명, provenance, 질문, 생성 결과에도 비공개 내용이 들어갈 수 있다. workspace 전체를 비공개로 관리하고 Git에는 합성 fixture와 검토된 집계 결과만 넣는다.

### 9.1 SOTA 역할과 중간 품질 비교

학습 입력의 역질문·개요 추출은 SOTA 역할 adapter로 연결한다. 원문 정답은 그대로 유지하고 SOTA가 쓴 대체 소설로 바꾸지 않는다. 현재 CLI의 수동 prompt 입력은 유지하며 자동 추출은 후속 구현이다.

선택 checkpoint와 집필 중간 결과에 독립 비교 use case를 둔다. 같은 장면 지시·직전 문맥·정사/문체 패킷으로 원본 Gemma, 학습 Gemma, SOTA 기준선을 생성한다. `comparison_id`, 입력·출력 hash, exact model/version, decoding, 비용·지연, 평가 rubric을 보존한다. SOTA에게 Gemma 초안을 수정시킨 결과는 독립 생성 비교와 분리한다.

반복 비교는 development/validation에서 수행하고 최종 test를 보존한다. Munche 문체 평가·블라인드 사람 평가·정사/지시 준수를 함께 보고, SOTA judge의 자기 모델 선호를 점검한다. SOTA 교체 시 이전 기준선은 남기고 새 비교를 추가한다. 원문 외부 전송 범위·호출 예산·재시도 상한을 명시하며, 비교 실패는 `not_run`/실패로 남기고 운영 writer를 바꾸지 않는다. 상세 조건은 [상위 아키텍처 §11.5](../20260914-novel-factory-architecture-v5.md)를 따른다.

이 경로와 SOTA adapter는 아직 미구현이다. 첫 저장·재로드 연습은 비교 API 연결 없이도 완료할 수 있고, 실제 품질 평가는 비교 실행 여부를 구분해 보고한다.

## 10. 실행 상태·재개·모델 계보

`run-id`는 실험 식별자, `attempt-id`는 프로세스 실행 시도 식별자다. 실패·재개를 기존 로그 덮어쓰기로 처리하지 않는다.

```text
created → validated → running → completed
                         ├── failed
                         └── interrupted
```

강제 세션 종료 시 `interrupted`를 기록할 기회가 없을 수 있다. 다음 접속에서 프로세스·완료 표식·마지막 checkpoint를 확인해 상태를 판정하고 근거를 남긴다.

checkpoint는 임시 위치에 기록하고 검증을 마친 뒤 완료 manifest를 발행한다. 복사 중 끊긴 디렉터리는 재개 후보에서 제외한다. 저장소별 원자성·업로드 완료 의미는 adapter가 책임진다. 보존할 유효 checkpoint가 확인되기 전에 이전 checkpoint를 삭제하지 않는다.

| 이동 종류 | 요구 사항 |
|---|---|
| 동일 머신·동일 환경 재개 | optimizer·scheduler·RNG·step 상태까지 복구 검증 |
| 다른 CUDA 서버로 이동 | 동일 base·데이터·엔진·의존성 및 checkpoint 호환 검증 |
| CUDA→MLX 이동 | format 변환·모델 지원 확인 후 별도 실행. optimizer 상태의 직접 재개를 약속하지 않음 |
| adapter→merged→양자화 | 부모 artifact, base revision, 변환 도구·설정·checksum과 품질 평가 연결 |

각 run에는 소스 commit과 실제 반입 소스 해시, dataset manifest 해시, base/tokenizer revision, 환경, seed, 유효 설정, 학습 token 수, GPU 메모리·시간, 평가 조건을 기록한다. dirty 소스로 smoke test할 경우 실행한 변경분 또는 소스 묶음을 보존한다. Git SHA만으로 현재 코드를 재현했다고 주장하지 않는다.

최종 adapter는 캐시가 아닌 export로 보존한다. 정확한 base 참조와 필요한 tokenizer/template 자산을 함께 명시한다. 서로 다른 하드웨어·커널·양자화에서 bit 단위 동일 출력은 보장하지 않으며, 재현 기준을 실행 계보와 허용 오차·생성 품질로 정한다.

## 11. 운영·접속·보존

SSH는 원격 실행 수단이다. 최초에는 WebUI에서 준비된 세션의 SSH 연결을 사용하고, 안정화되면 Backend.AI Batch 또는 다른 서버 작업 스케줄러에서도 동일 CLI를 실행한다. 세션 생성 자동화는 독립 운영 작업이다.

- SSH 키, DB 비밀번호, HF token은 Git·소스 묶음·run 로그·환경 덤프에 넣지 않는다.
- SSH 호스트 식별을 확인하고 자격증명은 로컬 credential 경로 또는 런타임 환경변수로 주입한다.
- DB 접속은 provider가 제공하는 TLS·접근제어 방식에 맞춘다. dataset metadata에 DSN이나 비밀번호를 저장하지 않는다.
- 외부 로깅 서비스는 기본 비활성화한다. 오류 로그의 원문·token·DSN 노출을 제거한다.
- Git ignore는 이미 추적된 파일을 보호하지 못한다. 소스 발행 전 포함 파일 목록을 검사한다.
- 모델·dataset·checkpoint 예상 사용량과 여유 디스크를 preflight에서 확인한다.
- 영구 vfolder의 존속과 백업은 별개다. 대체 불가능한 원문과 채택 adapter는 별도 사본을 확인한다.
- 세션 회수 정책과 저장 주기는 실제 운영 환경에서 확인한다. `tmux`를 세션 수명 보장 수단으로 취급하지 않는다.

## 12. 단계별 구현과 완료 조건

| 단계 | 구현 범위 | 완료 조건 |
|---|---|---|
| A. 프로젝트 경계 | `toy-tune` 패키지, domain/ports, CLI 조립, 설정·합성 fixture | 루트 venv 없이 설치; CPU에서 계약 검사; 금지 import 없음 |
| B. 실행·스토리지 | Backend.AI runbook, 코드 발행, preflight, filesystem stores | 경로·권한·GPU·환경 기록; 영구 저장 검증; code/workspace 분리 |
| C. 데이터 | 원문 반입, snapshot packet, dataset builder, split·manifest | 소량 장면 데이터 생성; 계보·누수·토큰·loss mask 검사 |
| D. CUDA 학습 | HF/PEFT engine, baseline, 1-step→30-step, checkpoint | adapter 저장·새 프로세스 로드·고정 조건 비교; 중단·재개 검증 |
| E. 이동성 | 다른 경로·깨끗한 환경에서 소스와 dataset 재실행 | 경로 하드코딩 없음; 원 DB 없이 동결 dataset 소비 가능 |
| F. 실제 지식 DB | SQLite KnowledgeReader와 ContextCompiler | 합성 전표 계약 통과; snapshot과 생성 근거 재현 |
| G. PostgreSQL | 독립 DB adapter와 이관 결과 검증 | 동일 fixture 의미 일치; 원격 일관 읽기·장애 처리 검증 |
| H. Mac | MLX engine·환경 profile·변환 검증 | 지원 모델로 저장·재로드·평가; 차이와 재개 한계 기록 |

첫 토이 실행의 범위는 A~D다. E는 이동성 조기 점검이며 두 번째 GPU를 구매·할당할 필요 없이 경로와 패키지 독립성부터 검사한다. F~H는 실제 필요와 자원에 따라 순서를 바꿀 수 있다. PostgreSQL·MLX 전체 구현을 첫 학습의 선행 조건으로 만들지 않는다.

### 필수 검증

추가 문체 트랙 S0/S1은 C/D 옆에서 소량 원문으로 검증한다. 문체 데이터 탐색과 학습 전후 평가부터 시작하며, SQLite 문체 검색·PostgreSQL·Mac encoder 구현을 첫 학습의 선행 조건으로 만들지 않는다. Munche 관련 포트와 adapter는 현재 미구현이다. 문체 점수만으로 모델을 선정하거나 초기 학습 reward로 사용하지 않는다.

- architecture: domain/application의 외부 기술 및 구체 adapter import 차단.
- unit: split, provenance, revision 필터 규칙, 설정 검증, 실패 상태.
- contract: store 발행·재읽기·checksum; SQLite/PostgreSQL 근거 의미; 엔진 capability 오류.
- integration: 실제 tokenizer/mask, 언어모델 LoRA target, 1-step update, 저장·재로드, 재개.
- recovery: 부분 checkpoint와 중복 run writer를 거부하고, 완료된 이전 산출물을 보존.
- portability: CPU 설치가 GPU·MLX·DB를 요구하지 않으며 workspace 경로를 바꿔도 동작.

테스트별로 CPU/CUDA/MLX/DB 요구를 표시한다. GPU 없는 로컬 검사가 성공했다는 이유로 학습 통합 검증까지 완료됐다고 판단하지 않는다.

## 13. 지금 확정한 것과 실행 전 확인할 것

확정: 프로젝트 이름 `toy-tune`, 독립 패키지, 네 가지 교체 축, 안쪽으로 향하는 의존성, 코드·비공개 workspace 분리, 지식 snapshot 기반 학습, 운영 정사 읽기 경계, run/artifact 계보, 단계별 구현.

실행 전 확인: SSH 접속 정보, 실제 GPU 자원, 이미지·Python·Torch 조합, 마운트 경로·용량·파일시스템, 원문 선택, 현재 SQLite 파일 존재와 schema, 모델 접근·지원 revision. PostgreSQL 주소나 MLX 세부 설정은 해당 단계에서 결정한다.

이 문서는 폴더와 책임의 설계 기준이다. 후속 구현은 B의 원격 환경 사실을 확인한 뒤 C~D의 모델·실제 원문 경로로 진행한다.

### 2026-09-14 구현 기록

- A: 독립 pyproject, domain/application/adapter/bootstrap, 교체 포트, runtime 설정, 합성 fixture, JSON 계약, 의존성 방향 테스트 구현.
- B 로컬 기반: doctor inventory, 불변 파일 묶음 발행·검증, run 상태 저장소, 명시적 소스 allowlist 기반 전송 archive, Backend.AI/SSH runbook 구현.
- C 로컬 기반: 선택 원문 bundle의 SHA-256·정답 범위 검증, 시간순 split, 정확히 일치하는 누수 후보 차단, 원문을 포함한 동결 dataset 발행 구현. 실제 원문·근거 packet 반입·tokenizer·loss mask는 미완료.
- E 일부: Git checkout 밖으로 옮긴 소스 묶음이 설치된 패키지·GPU·DB 없이 합성 dataset을 생성하는 smoke test 구현.
- D/F/G/H: 아직 미구현. HF/PEFT 학습, CUDA checkpoint 재개, 실제 SQLite/PostgreSQL, MLX는 실행된 것으로 간주하지 않는다.
- 인터페이스 중 실제 구현이 없는 기능은 stub 실행으로 성공 처리하지 않는다. 현재 CLI는 doctor, prepare, verify-dataset만 제공한다.
- 현재 filesystem 구현은 flat 파일 묶음과 단일 호스트 lock을 검증했다. 네트워크 vfolder 내구성, 모델 checkpoint 디렉터리, 객체 저장소 materialize는 후속 검증·구현 대상이다.
- 상세 사용법: [toy-tune README](../../toy-tune/README.md).
- 검증: macOS arm64/Python 3.14.3의 독립 임시 venv에 설치, unittest 28개 통과. GPU·DB 드라이버가 설치되지 않은 환경과 checkout 밖 소스 이동 실행을 포함한다.

## 14. 운영 문서 참고

- [Backend.AI 26.8 빠른 시작](https://webui.docs.backend.ai/26.8/ko/quickstart.html)
- [Backend.AI SSH/SFTP 접속](https://webui.docs.backend.ai/26.8/ko/sftp_to_container.html)
- [Backend.AI 스토리지 설명](https://webui.docs.backend.ai/26.8/en/vfolder.html)
- [Backend.AI 연산 세션 설명](https://webui.docs.backend.ai/26.8/en/sessions_all.html)

배포된 KT 환경의 동작은 위 문서와 대조해 확인한다. 이전 조사 문서의 패키지·모델 지원 정보는 실행 전 재검증한다.
