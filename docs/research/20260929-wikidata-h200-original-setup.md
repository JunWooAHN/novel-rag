---
category_id: research
lineage_id: lin-573998c1-5624-4a92-978e-3a2a74d0889b
document_id: doc-2b97339f-f9fd-4abb-b04f-c334fa841652
parent_lineage_id: lin-1a78dc59-6af9-4445-88e4-858f5327a856
abstract: H200 영속 Storage에서 Wikidata 원본 부재를 확인하고 공식 JSON 덤프의 다운로드를 기동한 근거와 재개 조건을 기록한다.
version: 0.0.1
created_at: '2026-09-28T22:34:11Z'
updated_at: '2026-09-28T22:34:11Z'
tags:
- Wikidata
- H200
- 원본보관
canon: false
---
# Wikidata 원본 H200 Storage 취득: 실행 중

## 현재 판정

**2026-09-28 22:33:31 UTC 현재 다운로드 중이며 원본 취득 완료가 아니다.** [H200 읽기 전용 재고·공간 검사](../../data/research/wikidata-storage-20260929/preflight.json)에서 기존 `/home/work/novel-toy-tune/sources/original/`에는 YAGO 4.6만 있었다. `wikidata/` 경로는 없었고 프로젝트 경로 깊이 5 이하의 Wikidata 이름 파일·디렉터리도 0건이었다. 이는 조사 범위의 원본 부재 판정이다. YAGO에 있는 Wikidata 유래 ID·사실을 Wikidata 원본 full statement 보관과 같다고 세지 않는다.

목적지 `/home/work/novel-toy-tune`는 기존 H200 세션에 연결된 별도 **RW NFS 영속 Storage** 마운트다. 사전 `statvfs` 가용량은 **1,676,399,345,664 byte**(전체 2,000,000,385,024 byte)였다. `quota` 명령은 없어서 계정별 quota를 별도로 확정하지 못했다. 도구는 시작 시 필요한 잔여 다운로드량에 **100,000,000,000 byte**를 더한 여유를 확인하고, 매 8 MiB 쓰기 전에 가용량이 이 reserve 아래로 내려가는 것을 막는다. 기존 YAGO 원본, 모델, DB, 소설 자료는 건드리지 않았다.

## 고정 원천과 선택

선택한 원본은 [Wikimedia 공식 디렉터리](https://dumps.wikimedia.org/wikidatawiki/entities/20260921/)의 `wikidata-20260922-all.json.bz2` 한 종이다. **파일명상 스냅샷 날짜는 2026-09-22, 디렉터리명은 `20260921`**이다. 고정 URL은 <https://dumps.wikimedia.org/wikidatawiki/entities/20260921/wikidata-20260922-all.json.bz2>, 정확한 크기는 **103,222,517,992 byte**, [공식 SHA-1 목록](https://dumps.wikimedia.org/wikidatawiki/entities/20260921/wikidata-20260922-sha1sums.txt)의 값은 `c5bfd59f16c6cdf906ead1190d99729108e961be`다. H200에서 직접 읽은 HEAD는 HTTP 200, 같은 `Content-Length`, `Accept-Ranges: bytes`, ETag `"6ab4b319-18088aa0e8"`, Last-Modified `Thu, 24 Sep 2026 05:20:25 GMT`였다. 공식 SHA-1 목록의 대상 행도 H200에서 다시 확인했다.

[Wikidata 공식 다운로드 안내](https://www.wikidata.org/wiki/Wikidata:Database_download#JSON_dumps_(recommended))와 [독립 원천 조사](../../data/research/wikidata-storage-20260929/independent-review/source-selection.md)에 따라 이 파일은 현재 엔터티의 all JSON으로 rank·qualifier·reference와 시간값을 담는 보강 입력이다. truthy RDF의 축약 진술이나 전체 편집 revision history와 다르다. YAGO 4.6 생성 당시의 Wikidata 입력판과 이 **새 시점** 스냅샷의 개별 진술 대응은 아직 검증하지 않았다. 구조화 데이터의 [공식 라이선스 안내](https://www.wikidata.org/wiki/Wikidata:Database_download#License)는 CC0다.

## 실행·검증 경로

서버에는 독립 Sol이 [기동 가능 판정](../../data/research/wikidata-storage-20260929/independent-review/preflight-review.md)을 한 [고정 downloader](../../tools/wikidata_storage/fetch_original.py)를 `/home/work/novel-toy-tune/tools/wikidata_storage/20260929/fetch_original.py`로 전송했다. 로컬·원격 SHA-256은 모두 `0103f1158f2c5d61b65bf8cdf4ed69beb31ff84bb42b4f744e3c36bb3fddd9d0`다. H200에서 `nohup python3 fetch_original.py > fetch.log 2>&1 < /dev/null &`로 SSH 연결과 분리해 기동했다. 실제 Python PID는 **38511**이며, 원격 `fetch.pid`를 그 값으로 기록했다. 22:33:31 UTC의 별도 SSH 접속에서 프로세스 생존과 `.part` **360,710,144 byte**, [원격 manifest](../../data/research/wikidata-storage-20260929/launch-receipt.json) `status=downloading`, 첫 진행 로그를 재확인했다. 그 시점 평균은 약 **4.6 MB/s**이고 단순 외삽 완료시간은 약 **6.3시간**이다. 속도·종료 시각은 보장하지 않는다.

원본 작업 경로는 `/home/work/novel-toy-tune/sources/original/wikidata/20260922/`다. 공식 SHA-1 목록의 원바이트 사본과 `ORIGINAL_UPSTREAM.txt`, 현재 `manifest.json`, `wikidata-20260922-all.json.bz2.part` 및 고정 출처 `.part.json`을 보존한다. 최종 이름 `wikidata-20260922-all.json.bz2`은 검사 성공 전 만들지 않는다. 원격 로그는 `/home/work/novel-toy-tune/tools/wikidata_storage/20260929/fetch.log`다. [기동 영수증](../../data/research/wikidata-storage-20260929/launch-receipt.json)의 manifest 진행 수치는 주기적 기록이라 같은 순간의 `.part` 실제 바이트보다 작을 수 있다.

도구는 재개 때 고정 URL의 HEAD 크기·ETag·Last-Modified를 먼저 다시 확인한다. 기존 `.part`의 크기부터 `Range`와 `If-Range`를 보내고 HTTP **206**, 정확한 `Content-Range`·응답 길이·validator가 일치할 때만 덧쓴다. 프로세스 잠금은 `.fetch.lock`의 비차단 `flock`이며 동시 두 writer를 거절한다. 네트워크 오류는 유한 횟수 재시도하고 부분 바이트는 보존한다. 실제 완료 전에 정확한 바이트 길이, 공식 SHA-1, 새로 계산한 SHA-256 및 압축을 앞부분만 풀어 JSON 엔터티 3개를 파싱한다. 모두 통과하면 `.part`를 최종명으로 원자 이동해 읽기 전용으로 바꾸고 manifest를 `complete`로 기록한다. **현재 그 검증과 이동은 아직 일어나지 않았다.** 전체 bzip2 해제·전량 JSON 의미 검사는 이 작업의 완료 검사에 포함하지 않는다.

재접속 시 `fetch.pid`의 실제 프로세스와 manifest·`.part` 증가를 먼저 확인한다. 프로세스가 **정지한 것을 확인한 뒤에만** 원격에서 아래 명령을 쓴다. `sha256sum` 출력이 위 고정 코드 SHA-256과 다르면 실행하지 않는다. `.part.json`의 URL·크기·validator는 스크립트가 재개 전에 대조한다.

```sh
cd /home/work/novel-toy-tune/tools/wikidata_storage/20260929
sha256sum fetch_original.py
nohup python3 /home/work/novel-toy-tune/tools/wikidata_storage/20260929/fetch_original.py > "fetch-resume-$(date -u +%Y%m%dT%H%M%SZ).log" 2>&1 < /dev/null &
printf '%s\n' "$!" > fetch.pid
```

잠금 획득 후 남은 바이트를 재개하며 기존 로그·`.part`·sidecar를 삭제·초기화하지 않는다. SSH 연결이 끊겨도 현재 H200 프로세스는 계속 실행되지만 **H200 컴퓨트 세션 자체가 종료되면 다운로드도 중단**된다. 그때는 영속 Storage의 부분파일에서 새 세션으로 재개해야 한다.

이번 실행은 압축 원본 취득만이다. 전량 해제, DB 적재, 현실 역사 릴리스, 작품 역사표, A40 별도 백업은 수행하지 않았다. 이 보고는 일회성 실행 증거이므로 문서 DB에서 `canon=false`로 유지한다.
