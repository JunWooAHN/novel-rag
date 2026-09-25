# 원문 코퍼스 SQLite

`corpus.py`는 `docs/references/manifest.json`의 로컬 UTF-8 사본 7편을 `data/analysis/novel-corpus.sqlite3`에 저장한다. DB의 각 `segments.body`는 실제 원문 텍스트다. BOM, CRLF/LF, 공백, 마지막 개행을 그대로 저장하며 회차 사이의 앞머리·후기·미분할 꼬리도 별도 구간으로 덮는다. 도구는 본문을 표준 출력에 쓰지 않는다. 원격 Drive와 바이트 동일성은 manifest의 로컬 검증 범위 밖이다.

```sh
python3 tools/novel_corpus/corpus.py ingest
python3 tools/novel_corpus/corpus.py verify
python3 tools/novel_corpus/corpus.py status
python3 tools/novel_corpus/corpus.py chapters mustache --start 1 --end 50
python3 tools/novel_corpus/corpus.py ranges gogjong --start 1 --end 10
python3 tools/novel_corpus/corpus.py titles goryeo
python3 tools/novel_corpus/corpus.py export mustache /tmp/mustache-source.txt
python3 tools/novel_corpus/corpus.py export mustache /tmp/mustache-01.txt --chapter 1
python3 tools/novel_corpus/corpus.py export gogjong /tmp/gogjong-range.txt --ordinal 2
python3 -m unittest discover -s tools/novel_corpus -p 'test_*.py'
```

`ingest`는 manifest 전체와 가능한 경계 JSON을 먼저 검사하고 단일 SQLite 트랜잭션으로 반영한다. 같은 원문 SHA-256과 같은 경계 JSON을 재적재하면 기존 행을 사용한다. 원문 바이트가 바뀌면 새 `source_revisions`, 같은 원문의 경계만 바뀌면 새 `segmentations`/`segments`를 추가하고 현재 조회가 새 분할판을 가리킨다. 과거 판은 남는다. `verify`는 현재 분할판의 모든 코드포인트 범위가 겹침 없이 연속되는지, 구간 텍스트 해시와 재구성한 raw byte SHA-256/크기가 source revision과 같은지, SQLite integrity/FK 검사를 수행한다.

경계 파일은 `docs/research/chapter-ingestion/<work-id>-boundaries.json`이다. `work_id`, `source_sha256`, `markers` 또는 `segments`가 필요하다. 좌표는 BOM과 개행을 보존해 UTF-8 디코딩한 Python 문자열의 코드포인트 `[start_cp,end_cp)`다. `markers`에서는 각 `start_cp`부터 다음 marker 또는 EOF까지를 구간으로 만들고 첫 marker 앞은 `frontmatter`로 보존한다. 표제가 없는 꼬리처럼 다른 범위 분할이 필요하면 전체 파일을 빠짐없이 덮는 `segments` 배열을 쓴다. `label`은 그 구간 시작의 원문과 정확히 일치해야 한다. 예:

```json
{
  "work_id": "example",
  "source_sha256": "<raw-byte-sha256>",
  "markers": [
    {"start_cp": 10, "label": "1화", "kind": "numbered", "number_claimed": 1, "confidence": "confirmed"},
    {"start_cp": 100, "label": "작가의 말", "kind": "note", "number_claimed": null, "confidence": "hold"}
  ]
}
```

`kind`는 `numbered`, `title_section`, `prologue`, `epilogue`, `note`, `frontmatter`, `tail`, `unresolved` 중 하나다. `confidence` 또는 `boundary_status`는 `confirmed`, `candidate`, `hold` 중 하나다. 번호 없는 표제는 `title_section`으로 두고 ordinal을 번호로 사용하지 않는다. 긴 미확정 구간은 `hold` 또는 `unresolved`로 표시한다. 동일 번호의 여러 구간은 `number_occurrence`를 분리해 모두 보존한다. `first_50_status` view는 1~50 목표마다 `mapped`, `hold`, `conflict`, `unmapped`를 반환하며, 유일한 `confirmed` `numbered` 구간만 `mapped`다. `chapters`는 그 상태와 좌표만 보여 주고 `export --chapter`는 유일하게 확정된 화만 파일로 쓴다. `ranges`와 `export --ordinal`은 미확정 구간까지 조회·추출한다. 이는 분석 완료 상태를 뜻하지 않는다.

`ranges`의 `ordinal`은 앞머리·후기·작가 메모까지 포함한 **전체 구간 순번**이다. 공식 화 번호가 아니다. 고종·고려처럼 무번호 표제가 많은 작품은 `titles`에서 `title_sequence`를 조회한다. 이것도 제목 구간의 등장 순서일 뿐 공식 회차 번호가 아니다. 번호 표제 다음 표제의 숫자가 건너뛰고 사이에 다른 경계가 없으면, 도구가 앞 구간을 자동 `hold`로 내려 누락 번호의 본문이 한 화에 확정 귀속되는 것을 막는다.

DB와 원문 `.txt`는 Git에서 제외한다. 스키마·CLI·경계 JSON·검증 코드는 추적 가능하다. 이 도구는 분석 카드, 학습 데이터, 운영 캐논 DB를 생성하지 않는다.
