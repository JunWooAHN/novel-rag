# 보유 소설 7편의 원문·경계 SQLite

기준일: 2026-09-24. 사용자가 승인한 **실제 원문 적재**를 [novel-corpus.sqlite3](../../../data/analysis/novel-corpus.sqlite3)에 수행했다. 구간 본문은 SQLite `segments.body`의 `TEXT`이며, 앞머리·무번호 제목·중복·미확정 구간·후기까지 보존한다. [원문 manifest](../../references/manifest.json)의 로컬 사본과 재결합한 DB 본문의 raw byte SHA-256이 일치한다. Drive 원격 객체와 독립적인 바이트 동일성까지 입증한 것은 아니다. 상세 독립 검증은 [review.md](review.md)에 있다.

**원문 저장과 회차 번호 확정은 다른 상태다.** 번호를 확정하지 못한 고종·고려도 원문 전체가 DB에 들어 있다. 반대로 첫 50화 번호 경계가 확정된 작품도 **50화씩의 의미 분석 카드 350건은 아직 작성·적재하지 않았다.** 학습과 운영 캐논 반영도 이번 작업에 포함되지 않는다.

| 작품 ID | 현재 구간 수 | 첫 50화 번호 매핑 | 현재 경계의 한계 |
|---|---:|---:|---|
| `gogjong` | 515 | 0/50 (`unmapped` 50) | `【…】` 제목은 번호 없는 구획. [경계 메모](gogjong-boundaries.md) |
| `sunjong` | 274 | 50/50 | 155화부터 313화 직전까지 큰 무번호 구간은 확정 회차로 귀속하지 않음. [경계 메모](sunjong-boundaries.md) |
| `mustache` | 58 | 49/50 (`conflict` 1) | 41편 표제가 두 번이라 자동 단일 매핑 불가. 45·47은 독립 줄·숫자 순서를 재검토해 확정. 55편 뒤 큰 무표제 구간은 보류. [경계 메모](mustache-boundaries.md) |
| `1588` | 650 | 50/50 | 14화 내부 인용 표제는 별도 경계가 아니다. 뒤쪽 누락 번호 직전의 긴 구간은 자동 보류. [경계 메모](1588-boundaries.md) |
| `fair-trade` | 411 | 50/50 | 144화 번호 공백 직전은 자동 보류; 중복 번호·작가의 말은 별도 보존. [경계 메모](fair-trade-boundaries.md) |
| `goryeo` | 807 | 0/50 (`unmapped` 50) | 앞부분 `◈`는 제목 순번이며 공식 회차 번호가 아님. [경계 메모](goryeo-boundaries.md) |
| `poland` | 577 | 50/50 | 1–524 번호 표제와 후기 표식 보존. [경계 메모](poland-boundaries.md) |
| **합계** | **3,292** | **249/350** | `unmapped` 100, `conflict` 1 |

원문 7편의 raw byte 합계는 **61,533,769 bytes**다. 현재 DB에는 작품 7개, 원문 revision 7개, 분할판 17개와 이력을 포함한 구간 5,233개가 있다. 구분판의 과거 구간도 삭제하지 않는다. 위 표는 **현재 분할판**만 센 것이다.

## 조회

[도구 안내](../../../tools/novel_corpus/README.md)의 명령은 본문을 표준 출력에 쓰지 않는다.

```sh
python3 tools/novel_corpus/corpus.py status
python3 tools/novel_corpus/corpus.py chapters mustache --start 40 --end 48
python3 tools/novel_corpus/corpus.py titles gogjong
python3 tools/novel_corpus/corpus.py ranges gogjong --start 1 --end 10
python3 tools/novel_corpus/corpus.py verify
```

`chapters`의 `target_number`는 **원문에 적힌 번호와 유일성**을 확인한 1–50 대상이다. `titles`의 `title_sequence`는 **번호 없는 제목 구간만** 센 등장 순서다. `ranges`의 `ordinal`은 앞머리·제목·후기·미확정 구간을 모두 포함한 **전체 segment 순번**이다. 어느 순번도 자동으로 공식 연재 회차 번호가 되지 않는다. 예를 들어 `titles gogjong`의 첫 제목 순번 1과 `ranges gogjong`의 구간 순번 1은 서로 다른 범위를 가리킬 수 있다. 미확정 원문은 `ranges`와 `export --ordinal`로 접근하고, `export --chapter`는 유일하게 확정된 번호만 허용한다.

경계 JSON과 메모는 이 디렉터리에, 원문 보관 목록은 [references](../../references/README.md)에 있다. DB와 원문 `.txt`는 Git 추적에서 제외한다.
