# 7편 원문 SQLite 적재 독립 검토

검토일: 2026-09-24. **판정: 원문 코퍼스의 무손실 적재 수락.** [실제 DB](../../../data/analysis/novel-corpus.sqlite3), [원문 manifest](../../references/manifest.json), [경계 파일](README.md), [도구·테스트](../../../tools/novel_corpus/README.md)를 대조했다. 코드·DB·원문·경계 JSON은 이 검토에서 수정하지 않았다. 이 판정은 **7편 원문 전체를 보존하고 번호 경계를 신뢰도대로 조회할 수 있다**는 뜻이다. 1–50화 의미 분석 350건, 학습, 운영 캐논 반영이 끝났다는 뜻이 아니다.

## 직접 검증한 결과

| 검사 | 결과 |
|---|---|
| DB 구조·무결성 | 읽기 전용 연결에서 `works=7`, `source_revisions=7`, `segmentations=17`, 이력 포함 `segments=5,233`. `PRAGMA user_version=1`, `integrity_check=ok`, `foreign_key_check` 위반 0. 현재 분할판은 3,292구간. |
| 원문 전체성 | 7편 **61,533,769 raw bytes**. 작품마다 현재 구간의 `ordinal` 연속, `[start_cp,end_cp)` 시작 0부터 끝까지 비중첩·연속, `len(body)`와 구간 길이, 각 `TEXT` UTF-8 SHA-256과 `text_sha256`, 저장 라벨의 시작 위치를 독립 Python 읽기 전용 조회로 확인했다. 구간을 순서대로 UTF-8 인코딩하여 재조합한 바이트 크기·SHA-256은 DB source revision, manifest, 로컬 보관본 7편 모두 일치했다. BOM·CRLF를 정규화하지 않았다. |
| 전체 이력 | 도구의 `verify`가 **17개 분할판 모두**에 대해 원문 재구성 hash·크기와 SQLite/FK·manifest 대조를 통과했다. 이전 분할판은 남아 있고 `current_segmentation_id`가 현재판을 가리킨다. |
| 멱등·rollback fixture | `python3 -m unittest discover -s tools/novel_corpus -p 'test_*.py' -v` **5/5 통과**. 동일 입력 재적재 수·ID 불변, 같은 원문에 새 경계 revision 유지, 원문 SHA와 경계 불일치·잘못된 연속 범위의 실패 시 배치 내용 불변을 fixture에서 확인한다. 엔지니어의 실제 동일입력 재적재도 `7/7/17/5233` 행 수 불변이었다. |
| Git 제외 | `git check-ignore -v data/analysis/novel-corpus.sqlite3`가 `.gitignore`의 `data/analysis/*.sqlite3`를 가리킨다. sidecar 제외 패턴도 있다. |

| 작품 | 현재 구간 | 첫 50화 `mapped` | 남은 번호 상태 | 현재 재조합 원문 hash |
|---|---:|---:|---|---|
| `gogjong` | 515 | 0 | `unmapped` 50 | 일치 |
| `sunjong` | 274 | 50 | 없음 | 일치 |
| `mustache` | 58 | 49 | 41편 `conflict` 1 | 일치 |
| `1588` | 650 | 50 | 없음 | 일치 |
| `fair-trade` | 411 | 50 | 없음 | 일치 |
| `goryeo` | 807 | 0 | `unmapped` 50 | 일치 |
| `poland` | 577 | 50 | 없음 | 일치 |

첫 50 번호 대상은 `249 mapped + 100 unmapped + 1 conflict = 350`이다. **`unmapped`는 본문 미저장이 아니다.** 고종의 `【…】`와 고려 앞부분의 `◈`는 번호 없는 제목 구간으로 원문 전체가 저장되어 있으나, 제목 순번을 공식 회차 1–50으로 바꾸지 않았다. [순종 경계 기록](sunjong-boundaries.md)의 155화→313화 사이와 [콧수염 경계 기록](mustache-boundaries.md)의 55편 이후 큰 무번호 범위도 단일 `confirmed` 회차로 승격하지 않았다. 중복 41편의 두 출현은 각각 보존되어 `conflict`로 남는다.

## 경계 위험의 별도 대조

- 콧수염 45·47은 독립 줄의 작품명·숫자·제목, 44→45→46→47→48의 순서와 인접 원문 범위를 재확인한 뒤 `confirmed`로 변경되었다. `편` 글자 생략만으로 보류하지 않는 판단은 근거에 맞는다. 41편 중복과 55편 뒤 미확정 상태는 유지됐다.
- 1588의 14화는 현재 DB에서 단일 `numbered/confirmed` 구간 `[95210,101816)`이며 내부의 `【사람이 사람을 구함에 이유를 찾지 말라. 그는 곧 주님의 비탄이라.】` 문구가 그 `body` 안에 남아 있다. 이 인용문을 별도 경계로 적재하지 않았다.
- 1588에서 명시 번호가 건너뛰는 **10개 직전 구간 모두 `hold`**로 확인했다(210→212부터 557→559까지). 공정무역 143→145 직전도 `hold`다. 빠진 번호의 본문을 앞 화에 확정 귀속하지 않는다.
- 현재 DB에서 `numbered/confirmed` 바로 다음에 `title_section`이나 `unresolved`가 와 확정 본문을 임의로 자르는 사례는 0건이다. 첫 50화 중 폴란드 14화 뒤의 `*작가의 말 (1)`·`(2)`는 명시적 작가 노트로 별도 `note` 구간에 보존되고 15화가 뒤따른다. 원문은 손실되지 않으며, 해당 번호 화만 추출하면 이 노트는 제외된다는 점을 조회 때 구별해야 한다.

## 조회 도구 수정 확인과 범위

초기 코드의 `export --ordinal`은 `--chapter`가 없으면 작품 전체를 추출하는 분기 오류가 있었다. 엔지니어가 `--ordinal` 분기를 먼저 처리하도록 수정했고, BOM/CRLF fixture에서 ordinal 2의 **해당 구간 바이트만** 추출하는 회귀 검증을 추가했다. 수정 후 5개 테스트와 `verify`가 통과했다. `titles`의 `title_sequence`는 번호 없는 제목 구간만 센 순서이고 `ranges`의 `ordinal`은 앞머리·후기를 포함한 전체 구간 순번이다. 둘 다 공식 회차 번호가 아니다.

남은 자료상 한계는 고종·고려의 공식 1–50 회차 대응 근거와 콧수염 중복 41편의 단일 대응이다. 현재 DB는 이를 보류/충돌로 표시한다. 구간별 의미 분석 카드나 독자·판매 성과는 이 코퍼스 검토에서 생성·판정하지 않았다.
