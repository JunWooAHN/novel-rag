---
category_id: document-harness
lineage_id: lin-9de47fd1-ad99-4e44-9e39-edb5e9196375
document_id: doc-22c3ecee-559b-4872-bf30-9723f41a2f21
parent_lineage_id: null
abstract: 문서 생애주기 CLI를 실행하고 canon 판을 선택할 때 읽는다.
version: 0.0.2
created_at: null
updated_at: '2026-09-25T02:48:59Z'
tags:
- 하네스
---
# 문서 하네스 CLI

다른 프로젝트에 적용하는 절차는 [문서 하네스 이식 가이드](../../docs/harness/portability.md)를 따른다.

`python3 tools/document_harness/harness.py`로 실행한다. Python 3.10+, PyYAML, JSONB와 FTS5가 있는 SQLite 3.45+가 필요하다. 기본 DB는 `data/document_harness/documents.sqlite3`이며 `--db PATH`는 **명령 앞**에 둔다. 이 DB는 문서판 누적 본문과 현재 `canon` 선택의 정본이다. 소설 코퍼스 DB와 분리되어 있다.

```sh
python3 tools/document_harness/harness.py init
python3 tools/document_harness/harness.py import --legacy docs/example.md
python3 tools/document_harness/harness.py manage docs/example.md --category design --abstract '이 설계를 검토할 때 읽는다'
python3 tools/document_harness/harness.py create docs/new.md --category design --title '새 문서' --abstract '설계 판단을 볼 때 읽는다'
python3 tools/document_harness/harness.py list --all
python3 tools/document_harness/harness.py no-canon
python3 tools/document_harness/harness.py unknown-date
```

`import --legacy`는 기존 파일을 **수정하지 않고** 원문 바이트와 SHA-256을 저장한다. 날짜를 추정하지 않고 파일마다 독립 계통을 발급하며 `canon=false`로 둔다. 같은 파일·해시 재수입은 멱등이다. 변경된 legacy 파일은 자동으로 새 판에 합치지 않지만, 사용자가 지정한 파일에 `manage PATH --category ... --abstract ...`를 호출하면 **같은 계통**의 새 관리판으로 전환한다. 과거 legacy 본문판과 현재 canon 선택은 보존한다. 아직 수입하지 않은 기존 파일도 `manage`로 관리판을 만들 수 있다. 새 파일은 `create`로 YAML 머리말을 만들고 `canon=false`로 등록한다. 파일 본문을 편집한 다음 `revise PATH --bump patch|minor|major`를 호출하면 기존 본문판을 DB에 보존하면서 새 `document_id`·버전·실제 수정 시각을 발급한다. 등록 실패 시 파일을 이전 바이트로 복원한다. 직접 편집한 관리 문서는 `import PATH`로 등록하되 기존 `document_id`를 다른 내용에 재사용할 수 없다.

모든 생성·개정·수입은 적재 후 기존 선택 **유지(retain)**를 명시적으로 확인하고 DB에서 재조회한다. 채택이나 철회는 `finalize`만 사용한다. 사용자가 목록을 본 뒤 선택이 바뀌었을 수 있으므로 `--expected-current`에 목록에서 본 ID 또는 `none`을 지정한다. 계통당 `canon=true`는 DB 제약으로 최대 하나이며, 새 초안 등록은 오래된 현행판을 밀어내지 않는다. `withdraw`는 현행 자식이 있으면 거부한다.

```sh
python3 tools/document_harness/harness.py show DOCUMENT_ID --body
python3 tools/document_harness/harness.py diff OLD_ID NEW_ID
python3 tools/document_harness/harness.py candidates
python3 tools/document_harness/harness.py finalize LINEAGE_ID --action adopt --document-id DOCUMENT_ID --expected-current none --message '무엇을 바꿈'
python3 tools/document_harness/harness.py finalize LINEAGE_ID --action retain
python3 tools/document_harness/harness.py finalize LINEAGE_ID --action withdraw --expected-current DOCUMENT_ID --message '적용 해제'
python3 tools/document_harness/harness.py list --category design --tag 역사
python3 tools/document_harness/harness.py list --lineage LINEAGE_ID --history
python3 tools/document_harness/harness.py search 역사 --all
```

`list`와 `search`는 기본으로 `canon=true`만 읽는다. `--all` 또는 `--history`는 비정본판도 표시한다. `candidates`는 적용판보다 수정 시각이 늦은 미채택판 목록이며 자동 오류나 자동 승격이 아니다. 적용판이 없는 계통과 날짜 미상판은 각각 `no-canon`, `unknown-date`로 본다. 검색은 FTS5 색인을 만들고 본문 부분 문자열도 확인한다. 한국어 검색의 품질은 별도 실제 질의로 판단한다.

```sh
python3 tools/document_harness/harness.py verify
python3 tools/document_harness/harness.py backup data/document_harness/backup.sqlite3
python3 tools/document_harness/harness.py --db data/document_harness/restored.sqlite3 restore data/document_harness/backup.sqlite3
python3 tools/document_harness/harness.py --db data/document_harness/restored.sqlite3 verify
python3 -m unittest discover -s tools/document_harness -p 'test_*.py' -v
```

백업·복원은 SQLite backup API로 본문판과 `canon` 선택·로그를 함께 복사한다. 이미 존재하는 백업/복원 목적지를 덮어쓰지 않는다. 데이터 작업에는 단일 writer를 유지한다. 이 하네스의 `canon`은 **문서 탐색에서 실제 적용할 판**이며 사용자 승인 역사표나 작품 정사로 자동 승격하는 값이 아니다.
