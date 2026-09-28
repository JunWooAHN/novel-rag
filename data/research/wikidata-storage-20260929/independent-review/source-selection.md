# Wikidata 원본 선택 독립 조사

- 관측: 2026-09-28 22:27 UTC. 공식 Wikimedia 디렉터리와 Wikidata/Wikibase 문서를 웹에서 직접 읽었다. 원격 H200 인벤토리·다운로드·무결성 검사는 운영자 담당이며 이 조사에서 수행하지 않았다. 로컬 `curl`은 DNS 제한으로 실패해 HTTP 헤더의 `ETag`·`Last-Modified`·Range 지원은 관측하지 못했다.
- 목적: [PRD](../../../../docs/prd/wikipedia-history-ontology.md) FR-01/17·AC-01/13과 [방법론](../../../../docs/methods/history-ledger-sot.md) §1에 필요한 현재 엔터티의 모든 statement, rank, qualifier, reference 및 원 시간 정밀도·달력 값 보존.

## 권고하는 단일 원본

| 항목 | 공식 관측값 |
| --- | --- |
| 형식 | **all JSON `.bz2`**, 현재 엔터티 스냅샷. JSON은 공식 권장 형식이며 각 엔터티가 한 줄을 차지한다. |
| 고정 URL | <https://dumps.wikimedia.org/wikidatawiki/entities/20260921/wikidata-20260922-all.json.bz2> |
| 원본 파일명·스냅샷 표기 | `wikidata-20260922-all.json.bz2`; 파일명의 날짜는 **2026-09-22**. 상위 디렉터리명은 `20260921`이다. |
| 공식 인덱스 표시 수정 시각·크기 | 2026-09-24 05:20 (인덱스 표시), **103,222,517,992 bytes** = 약 96.133 GiB. 인덱스 표시 시각을 스냅샷 날짜로 바꾸지 않는다. |
| 공식 체크섬 | SHA-1 `c5bfd59f16c6cdf906ead1190d99729108e961be`; MD5 `7f70e4a1858ba6182ea9329a1ef588c5`. [SHA-1 원본](https://dumps.wikimedia.org/wikidatawiki/entities/20260921/wikidata-20260922-sha1sums.txt), [MD5 원본](https://dumps.wikimedia.org/wikidatawiki/entities/20260921/wikidata-20260922-md5sums.txt). 공식 SHA-256은 이 두 목록에서 제공되지 않는다. 취득 후 로컬 SHA-256을 새로 계산해 manifest에 남긴다. |
| 저작권 | Wikidata [공식 다운로드 안내](https://www.wikidata.org/wiki/Wikidata:Database_download#License)는 main/Property/Lexeme/EntitySchema의 구조화 데이터를 CC0라고 명시한다. |

[공식 엔터티 인덱스](https://dumps.wikimedia.org/wikidatawiki/entities/)의 `latest-all.json.bz2`는 같은 크기(103,222,517,992 bytes)로 나열되나 변동 별칭이다. 실행 입력에는 위 날짜 고정 URL과 파일명·체크섬을 쓰고, 별칭이 같은 바이트를 가리킨다는 근거를 크기 일치만으로 확정하지 않는다. 인덱스의 가장 늦은 `20260925/` 디렉터리는 lexeme RDF만 담고 있으며, `20260921/` 디렉터리에 `20260922` all JSON 파일이 실려 있다. [고정 디렉터리 목록](https://dumps.wikimedia.org/wikidatawiki/entities/20260921/), [20260925 목록](https://dumps.wikimedia.org/wikidatawiki/entities/20260925/).

선택 이유: [Wikibase JSON 형식](https://doc.wikimedia.org/Wikibase/master/php/docs_topics_json.html#Statements)은 `claims`에 각 statement의 ID, `rank`, `mainsnak`, `qualifiers`, `references`를 정의한다. [시간 값 형식](https://doc.wikimedia.org/Wikibase/master/php/docs_topics_json.html#time)은 `time`, `precision`, `calendarmodel`, `before`, `after` 등을 보존한다. 위키데이터 [공식 덤프 안내](https://www.wikidata.org/wiki/Wikidata:Database_download#JSON_dumps_(recommended))도 all JSON을 권장한다. 반면 [truthy RDF 설명](https://www.wikidata.org/wiki/Wikidata:Database_download#RDF_dumps)은 주체·속성별 최고 비폐기 rank의 직접 트리플만 담고 qualifier와 reference를 빼므로 이 과업의 원본으로 부족하다. `all` RDF도 가능하지만 원 JSON과 RDF를 중복 보관할 필요가 없으며 JSON이 원 시간값을 더 직접 보존한다. `20260922` all JSON `.gz`는 인덱스에서 156,251,408,231 bytes이므로 같은 스냅샷의 `.bz2`만 권고한다.

이 파일은 **2026-09-22 현재 엔터티 내용**의 스냅샷이다. 오래된 사건을 설명하는 현재 진술은 담지만 Wikidata의 모든 편집 revision 이력을 담는다는 뜻은 아니다. [Wikimedia XML 덤프 형식 FAQ](https://meta.wikimedia.org/wiki/Data_dumps/FAQ#What_do_the_affixes_mean?)는 `pages-meta-history`를 전체 revision 이력, `current`를 최신 revision으로 구별한다. 모든 편집 이력 복원이 이번 YAGO 진술 보강 목적은 아니며 별도 요구다. YAGO 4.6의 생성 당시 Wikidata 입력판도 이 새 스냅샷과 같다고 가정하지 않는다. 따라서 이번 원본은 YAGO 생성판의 정확한 재현본이 아니라 **새 시점의 보강·대조 입력**으로 manifest에 별도 출처판으로 기록해야 한다.

## 운영자에게 제안하는 취득·검사 경계

1. 기존 동일 바이트 원본·마운트·실제 사용 가능 공간과 quota를 확인하고, 크기 **103,222,517,992 bytes**의 `.part` 파일과 보수적인 잔여 공간을 확보할 수 있을 때만 시작한다. 파일시스템 sparse 예약만 믿지 않고 실제 가용량/동시 작업을 기록한다. 운영자 실측은 persistent NFS 총 2 TB, 가용 1,676,399,345,664 bytes, 기존 원본 폴더에는 YAGO만 있음(프로젝트 깊이 5 이하 Wikidata 0건)이다. 루트가 최소 100 GB 잔여 reserve 유지하에 이 한 파일 다운로드를 승인했다. 압축 원본을 전량 해제할 공간은 이 작업에 배정하지 않는다.
2. 고정 URL을 사용하고 별도 `.part` 경로에 받는다. 최초 응답의 `Content-Length`·가능하면 `ETag`·`Last-Modified`·`Accept-Ranges`를 기록한다. 재개할 때 서버가 `206 Partial Content`와 기존 파일 길이부터 시작하는 `Content-Range`를 반환하고 validator가 같을 때만 append한다. `200` 또는 validator 변화·길이 불일치면 기존 부분 파일에 이어 쓰지 않는다. `curl -C -` 등 재개 기능을 쓰더라도 이 응답 검사를 생략하지 않는다.
3. 완료 주장 전 실제 압축 파일 길이를 확인하고 공식 SHA-1과 대조하며, 취득본 SHA-256도 계산한다. 작은 앞부분 JSON 표본을 스트리밍 해제해 형식·statement 구조를 확인한다. 전체 압축 파일을 별도 수시간 동안 해제·검사할 필요는 없다. 따라서 전체 bzip2 스트림의 구문적 완결성은 **별도 검증하지 않은 상태**로 정확히 표시한다. Wikidata [다운로드 안내](https://www.wikidata.org/wiki/Wikidata:Database_download#JSON_dumps_(recommended))는 병렬 압축 때문에 일부 해제기가 실패할 수 있어 Unix에서 `lbzip2`를 권고한다. 이후 처리할 때 `lbzip2 -dc` 출력을 소비자에 스트리밍해 엔터티별 한 줄 JSON을 처리한다. 전량 평문 파일 생성은 용량 근거가 없으면 하지 않는다.
4. 길이·공식 SHA-1·로컬 SHA-256·표본 검사를 기록한 뒤에만 최종 원본명으로 원자적 이동하고 `ORIGINAL`, `complete/verified` 상태를 부여한다. 여기서 `verified`는 **공식 게시 바이트와의 대조 및 표본 형식 확인**을 뜻하고 전체 엔터티 의미 검증을 뜻하지 않는다. manifest에는 고정 URL·관측 시각·파일명/snapshot date·크기·공식 SHA-1/MD5·로컬 SHA-256·표본 검사 결과·라이선스·실제 Storage 경로·다운로드 응답 validator·YAGO와의 시점 차이를 남긴다. 검사 전 `.part`는 `in_progress`/`unverified` 상태이며 원본 완료로 세지 않는다.

미결: 원격 HTTP 재개 validator, 실제 취득·체크섬·JSON 표본 결과. 기존 파일 부재·가용 공간은 운영자 측 실측값을 위에 인용했으며 이 조사자가 독립 SSH 재측정하지 않았다. 이 조사 자체는 다운로드 완료를 입증하지 않는다.
