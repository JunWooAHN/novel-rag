# 구현된 경계

`domain`은 Python 자료형과 의미 규칙, `application`은 port와 use case, `adapters`는 JSON·파일·현재 머신 접근, `bootstrap`은 설정과 adapter 조립을 담당한다.

```text
CLI → bootstrap → application → domain
          └────→ adapters ─────→ 내부 port와 domain
```

실행 위치는 `runtime.execution`, 엔진은 `runtime.engine`, 지식 입력은 `runtime.knowledge`, 저장 위치는 `workspace_root`다. runtime profile은 원격 접속을 수행하지 않는다. 먼저 SSH로 접속한 뒤 원격 머신에서 동일 CLI를 실행한다.

실제 구현된 adapter는 LocalEnvironmentInspector, JsonSourceReader, FilesystemArtifactStore, FilesystemRunStore다. KnowledgeReader/PacketReader/TrainingEngine/GenerationEngine은 교체 계약만 정의되어 있다. 나중에 엔진을 추가할 때 지원 모델과 dtype을 확인하고 미지원 요청은 실패시킨다.

CPU 기본 패키지는 GPU 라이브러리, SQLite 또는 PostgreSQL 드라이버를 가져오지 않는다. 의존성 방향은 AST 테스트로 검사한다. 학습 iteration에서 live DB를 조회하지 않고 데이터 준비 단계에서 고정한 근거를 소비한다.

## 저장 책임

`workspace/datasets/<id>`는 원본 source bundle, 세 split, 통계와 manifest를 함께 보존하는 현재 구현이다. 별도 source 저장소로 중복 제거하는 기능은 아직 없다. 작은 토이 입력의 계보를 먼저 완전하게 보존한다.

FilesystemArtifactStore는 flat 파일 묶음을 발행한다. 객체 저장소 materialize와 엔진 checkpoint 디렉터리 변환은 후속 계약 확장이다. FilesystemRunStore는 상태 전이와 writer 충돌을 검증하며, 실제 학습 attempt·checkpoint 재개 프로토콜은 아직 구현하지 않았다.

실행·학습·DB의 책임은 서로 독립이다. SQLite/PostgreSQL의 SQL·연결 객체가 domain으로 들어오지 않게 하며, 정사 쓰기·공개·schema migration은 지식 DB 소유 프로젝트에 둔다.
