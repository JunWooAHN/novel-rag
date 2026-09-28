# YAGO 4.6 기계적 조사 기록

조사 시각: 2026-09-28 (KST). 공개 페이지와 표시된 디렉터리 인덱스만 확인했다. 덤프 아카이브는 다운로드하지 않았다.

| # | 확인 사실 | 확인값 / 범위 | 출처 |
|---:|---|---|---|
| 1 | 사이트가 표시한 최신 릴리스 | YAGO 4.6, 2026년 7월 출시(월만 표시; 일자는 미표기). | [홈](https://yago-knowledge.org/) |
| 2 | `yago-4.6-schema.zip` | 19,471 bytes (ZIP archive size; uncompressed size not listed). | [디렉터리 인덱스](https://yago-knowledge.org/data/yago4.6/) |
| 3 | `yago-4.6-taxonomy.zip` | 41,519,942 bytes (ZIP archive size; uncompressed size not listed). | [디렉터리 인덱스](https://yago-knowledge.org/data/yago4.6/) |
| 4 | `yago-4.6-facts.zip` | 829,349,027 bytes (ZIP archive size; uncompressed size not listed). | [디렉터리 인덱스](https://yago-knowledge.org/data/yago4.6/) |
| 5 | `yago-4.6-labels.zip` | 2,188,238,999 bytes (ZIP archive size; uncompressed size not listed). | [디렉터리 인덱스](https://yago-knowledge.org/data/yago4.6/) |
| 6 | `yago-4.6-beyond-wikipedia.zip` | 2,535,563,171 bytes (ZIP archive size; uncompressed size not listed). | [디렉터리 인덱스](https://yago-knowledge.org/data/yago4.6/) |
| 7 | `yago-4.6-beyond-wikipedia-labels.zip` | 3,507,195,426 bytes (ZIP archive size; uncompressed size not listed). | [디렉터리 인덱스](https://yago-knowledge.org/data/yago4.6/) |
| 8 | `yago-4.6-meta.zip` | 106,018,818 bytes (ZIP archive size; uncompressed size not listed). | [디렉터리 인덱스](https://yago-knowledge.org/data/yago4.6/) |
| 9 | `yago-4.6-fact-log.zip` | 413,825,430 bytes (ZIP archive size; uncompressed size not listed). | [디렉터리 인덱스](https://yago-knowledge.org/data/yago4.6/) |
| 10 | `yago-4.6-range-log.zip` | 57,694,789 bytes (ZIP archive size; uncompressed size not listed). | [디렉터리 인덱스](https://yago-knowledge.org/data/yago4.6/) |
| 11 | `yago-4.6-taxonomy-log.zip` | 155,673 bytes (ZIP archive size; uncompressed size not listed). | [디렉터리 인덱스](https://yago-knowledge.org/data/yago4.6/) |
| 12 | `yago-4.6-tiny.zip` | 91,188,862 bytes (ZIP archive size; uncompressed size not listed); download index/page does not define this bundle's content. | [디렉터리 인덱스](https://yago-knowledge.org/data/yago4.6/) |
| 13 | `yago-entities.jsonl.zip` | 136,639,474 bytes (ZIP archive size; uncompressed size not listed); download page/index does not describe the JSONL bundle further. | [디렉터리 인덱스](https://yago-knowledge.org/data/yago4.6/) |
| 14 | 데이터 라이선스 | YAGO 4.6 dataset page says Creative Commons Attribution by the YAGO team of Télécom Paris; Getting Started says CC Attribution allows commercial use. No component-specific license split is given on these pages. | [YAGO 4.6](https://yago-knowledge.org/downloads/yago-4-6), [Getting Started](https://yago-knowledge.org/getting-started) |
| 15 | SPARQL instructions | Published API endpoint `https://yago-knowledge.org/sparql/qlever`; page states 1-minute timeout and anonymized queries may be used by DIG/Télécom Paris. This is page documentation, not a successful live health check. | [SPARQL page](https://yago-knowledge.org/sparql) |

## 파일 구분, 체크섬, 언어 표본

YAGO 4.6 페이지는 schema를 상위 taxonomy·제약·property 정의(SHACL), taxonomy를 전체 class taxonomy, facts/labels를 English Wikipedia 페이지가 있는 entity의 사실/라벨, beyond-wikipedia facts/labels를 해당 페이지가 없는 entity의 사실/라벨, meta를 RDF* fact annotations로 설명한다. 로그는 제외된 statement의 로그 3개라고 설명한다. 파일명상 세 로그 ZIP은 fact-log, range-log, taxonomy-log다. `tiny`와 `yago-entities.jsonl`의 정의는 공개 페이지에서 확인되지 않아 이름 이상으로 분류하지 않았다.

디렉터리 인덱스에 보이는 각 ZIP의 크기는 위 표의 byte 값이며 인덱스 표기상 파일 시각은 2026-08-03 03:04–03:06이다(시간대 미표기). 같은 인덱스에는 별도 checksum manifest/sidecar나 압축 해제 크기가 표시되지 않는다. 이는 그 인덱스에서 확인한 범위다.

공식 [labels sample](https://yago-knowledge.org/data/yago4.6/samples/labels.txt)에서 `@ko`와 `한국`을 검색했으며 일치 항목이 없었다. 이것은 표시된 sample 파일에 관한 결과이며 전체 labels dump의 언어 coverage를 뜻하지 않는다. 이 sample에는 다국어 label이 보인다(예: Belgium의 `@de`, `@nl`, `@fr`, `@zh`).

## SPARQL 실행 시도 및 HTTP 확인

최초 sandbox 내 요청(2026-09-28T03:38:01.305020Z)은 DNS 오류를 받았다. 이후 제한 승격 요청으로 공식 endpoint에서 한 개체 질의를 실행했다. URI는 YAGO sample에서 확인된 `George_Washington`이며, 날짜·국적·역할 관련 8개 predicate를 `VALUES`로 고정하고 최대 10행으로 제한했다. 실행은 2026-09-28T03:41:45.058345Z–03:41:45.982904Z, HTTP 200, 0.924초였다. 응답은 6행이며 질의 실행시간 메타데이터는 21 ms다. 질의, 정확한 요청 URL, 원 응답 JSON은 [endpoint-query-02.txt](endpoint-query-02.txt)에 보존했다.

확인된 응답값: `schema:birthDate` = `1732-02-22`; `schema:deathDate` = `1799-12-14`; `schema:birthPlace` = Westmoreland County, Virginia; `schema:deathPlace` = Mount Vernon; `schema:nationality` = Kingdom of Great Britain 및 United States of America. 이 질의에서 지정한 `schema:hasOccupation`, `schema:jobTitle`, `ys:occupation` 결과는 없었다. 이는 단일 개체·선택한 predicate의 표본이며 전체 데이터에서 역할/직업 값이 없다고 뜻하지 않는다.

요청 URL은 공식 `https://yago-knowledge.org/sparql/qlever`다. 성공 응답은 요청 시 endpoint가 접근 가능했음을 보여주며, 최초 sandbox DNS 오류와 함께 보면 sandbox 네트워크 제약 가능성과 일치한다. 별도 한 번의 공식 `yago-4.6-schema.zip` HEAD 요청도 2026-09-28T03:42:14.454357Z–03:42:15.324601Z에 HTTP 200으로 완료됐다. `Content-Length: 19471`, `Last-Modified: Mon, 03 Aug 2026 03:04:52 GMT`였고 본문은 받지 않았다. HEAD 기록은 [head-check.txt](head-check.txt)다.

## 확인 한계

- 전체 덤프 및 대형 파일은 다운로드하지 않았다. ZIP 내부 구성과 압축 해제 크기는 확인하지 않았다.
- 2026년 7월은 사이트의 월 단위 출시 표기다. 인덱스/HEAD의 8월 3일 파일 시각을 release date로 바꾸어 말하지 않는다.
- 공개 페이지가 “latest”라고 표시한 것은 사이트 진술이다. 성공한 endpoint의 서버 데이터 버전이 다운로드 릴리스와 같은지는 응답에서 확인되지 않았다.
- 역사 coverage 확인은 George Washington 한 개체의 선택 predicate 표본 6행에 한정한다. 다른 역사 대상·인과관계 coverage를 주장하지 않는다.
