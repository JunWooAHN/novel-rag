# 명령어 상세

## `/webnovel-init`

용도：소설 프로젝트 초기화（디렉토리, 설정 템플릿, 상태 파일）。

산출물：

- `.webnovel/state.json`
- `설정집/`
- `개요/총강.md`

## `/webnovel-plan [권번호]`

용도：권 단위 계획 및 챕터 개요 생성。

예시：

```bash
/webnovel-plan 1
/webnovel-plan 2-3
```

## `/webnovel-write [챕터번호]`

용도：전체 챕터 창작 프로세스 실행（컨텍스트 → 초안 → 심사 → 윤색 → 데이터 저장）。

예시：

```bash
/webnovel-write 1
/webnovel-write 45
```

일반 모드：

- 표준 모드：전체 프로세스
- 빠른 모드：`--fast`
- 최소 모드：`--minimal`

## `/webnovel-review [범위]`

용도：과거 챕터에 대한 다차원 품질 심사。

예시：

```bash
/webnovel-review 1-5
/webnovel-review 45
```

## `/webnovel-query [키워드]`

용도：캐릭터, 복선, 리듬, 상태 등 런타임 정보 조회。

예시：

```bash
/webnovel-query 소염
/webnovel-query 복선
/webnovel-query 긴급
```

## `/webnovel-resume`

용도：작업 중단 후 자동으로 중단점을 식별하고 복구。

예시：

```bash
/webnovel-resume
```

## `/webnovel-dashboard`

용도：읽기 전용 시각화 패널을 시작하여 프로젝트 상태, 엔티티 관계, 챕터 및 개요 내용을 확인。

예시：

```bash
/webnovel-dashboard
```

설명：

- 기본 읽기 전용으로 프로젝트 파일을 수정하지 않음
- 컨텍스트, 엔티티 관계 및 챕터 진행 상황 확인에 적합

## `/webnovel-learn [내용]`

용도：현재 세션 또는 사용자 입력에서 재사용 가능한 글쓰기 패턴을 추출하여 프로젝트 메모리에 기록。

예시：

```bash
/webnovel-learn "이번 챕터의 위기 훅 설계가 매우 효과적이었고, 서스펜스가 최고조에 달했다"
```

산출물：

- `.webnovel/project_memory.json`
