# toy-tune

웹소설 문체 학습 실험용 독립 Python 프로젝트. 실행 머신·학습 엔진·지식 DB·산출물 저장소를 분리한다.

현재 구현: CPU 기반 프로젝트 경계, runtime 설정, 환경 inventory, 원문 검증·동결 데이터셋 발행·검증, 파일 저장소와 run 상태 계약. H200 학습, MLX, SQLite/PostgreSQL 연결은 후속 단계다. 모델을 다운로드하거나 학습했다고 표시하지 않는다.

## 설치와 테스트

프로젝트 디렉터리에서 실행한다. 모노레포 루트의 기존 venv는 사용하지 않는다.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/toy-tune --help
```

Python 3.11 이상. 기본 설치에는 외부 runtime 의존성이 없으며 JSON Schema 테스트만 선택 의존성이다. PyTorch/CUDA/MLX 설치는 이 명령에 포함되지 않는다.

## 합성 데이터로 실행

다음 명령은 Git 밖 임시 디렉터리에 데이터셋을 만든다. 이 경로는 연습용이며 장기 보존용이 아니다.

```sh
TOY_WORKSPACE=$(mktemp -d)
.venv/bin/toy-tune doctor --runtime configs/runtimes/local-cpu.toml
.venv/bin/toy-tune prepare \
  --runtime configs/runtimes/local-cpu.toml \
  --workspace "$TOY_WORKSPACE" \
  --source tests/fixtures/synthetic-source.json \
  --split configs/datasets/synthetic.toml
```

출력의 artifact_id를 사용해 확인한다.

```sh
.venv/bin/toy-tune verify-dataset \
  --runtime configs/runtimes/local-cpu.toml \
  --workspace "$TOY_WORKSPACE" \
  --dataset-id <artifact-id>
```

`verified: true`는 파일 checksum 검증이다. Tokenizer, assistant loss mask, 문체 품질은 별도이며 현재 결과에는 `pending`으로 표시한다.

## 경계와 다음 단계

- [아키텍처](docs/architecture.md)
- [데이터 계약](docs/data-contract.md)
- [로컬 실행·복구](docs/runbook.md)
- [Backend.AI 접속·실행](ops/backendai/README.md)
- [다른 서버로 코드 반입](ops/ssh/README.md)
- [환경 분리](environments/README.md)

현재 CLI는 `doctor`, `prepare`, `verify-dataset`만 제공한다. H200 접속 후 엔진 및 토큰화 통합을 구현한다. `mac-mlx` profile은 머신 설정 경계를 보여주는 예시이며 MLX 학습 엔진 구현을 의미하지 않는다.
