# H200 Wikidata 원본 다운로드 기동 독립 검토

판정: **`launch_accepted, acquisition_pending`**. 이 판정은 서버의 재개 가능한 다운로드가 시작되어 진행 중이라는 인계 수락이다. 원본 취득 완료, 해시 검증 완료 또는 프로젝트 역사 SoT 입력 수락이 아니다.

## 확인한 근거

- 운영자 [기동 영수증](../launch-receipt.json) (2026-09-28 22:33:31 UTC)은 H200 프로세스 PID `38511`의 `python3 fetch_original.py` 실행과 `.part` 실제 크기 **360,710,144 bytes**를 기록한다. 같은 영수증의 manifest는 22:33:16 UTC `status=downloading`, **293,601,280 bytes**였고 로그 tail의 progress 값도 이에 일치한다. 실제 파일 크기가 67,108,864 bytes 더 커졌으므로 그 시점에는 다운로드가 증가 중이었다. 시간 차 때문에 manifest의 진행 수치가 파일보다 뒤처지는 것은 정상이다.
- [기동 영수증](../launch-receipt.json)의 manifest는 고정 URL `<https://dumps.wikimedia.org/wikidatawiki/entities/20260921/wikidata-20260922-all.json.bz2>`, 103,222,517,992 bytes, 공식 SHA-1 `c5bfd59f16c6cdf906ead1190d99729108e961be`, ETag `"6ab4b319-18088aa0e8"`, Last-Modified `Thu, 24 Sep 2026 05:20:25 GMT`를 **고정 입력값**으로 기록한다. [운영 설정 보고](../../../../docs/research/20260929-wikidata-h200-original-setup.md)는 H200의 HEAD 응답에서 HTTP 200, 동일 크기·ETag·Last-Modified와 `Accept-Ranges: bytes`를 관측했다고 명시하지만, 원시 HEAD 헤더를 별도 파일로 남기지는 않았다. [사전 점검](../preflight.json)은 재고·마운트·공간 기록이며 HTTP 증거가 아니다. 공식 SHA-1 대상 행은 독립 공식 웹 조회에서 확인했다.
- NFS Storage의 사전 점검 가용량 **1,676,399,345,664 bytes**는 선택 원본 **103,222,517,992 bytes**와 100,000,000,000 bytes reserve 합보다 크다. 선택 위치에는 다운로드 전 원본이 없었고 `sources/original` 목록에는 YAGO만 있었다. 이 검토자는 H200에 독립 SSH 재접속하지 않고 운영자 영수증과 스크립트 근거를 대조했다.
- [코드 사전 검토](preflight-review.md) SHA-256 `0103f1158f2c5d61b65bf8cdf4ed69beb31ff84bb42b4f744e3c36bb3fddd9d0` 판은 `.part`의 재개 요청에 정확한 `206 Content-Range`/validator가 아니면 append를 거부하고, 기존 최종 파일을 덮어쓰지 않는다. 프로세스 lock, chunk별 reserve 확인, 길이·공식 SHA-1·로컬 SHA-256·3개 JSON 표본 검증 전 `status=complete` 미표시 경계를 확인했다. 운영자 보고상 원격 실행 코드 hash도 같은 판이다.
- [운영 설정 보고](../../../../docs/research/20260929-wikidata-h200-original-setup.md)는 원격 코드 절대경로, 로컬·원격 동일 코드 SHA-256, `nohup` 실행 및 별도 SSH에서 PID 재확인, 로그 경로를 명시한다. H200 컴퓨트 세션 자체가 종료되면 프로세스는 멈추고 NFS의 `.part`에서 새 세션으로 재개해야 한다는 제한을 정확히 적었다. 해당 보고는 일회성 기록 `canon=false`로 작성되었다. 설명과 영수증·코드 사이에 완료 과장이나 주요 불일치를 찾지 못했다.
- 추가 [재접속 영수증](../progress-after-reconnect.json)은 2026-09-28 22:36:49 UTC에도 같은 PID `38511`이 살아 있고 `.part`가 **1,333,788,672 bytes**로 증가했다고 기록한다. `final_exists=false`, manifest `downloading`, checksum 사본·sidecar 존재, 코드 SHA 일치, 남은 가용 공간 1,675,114,840,064 bytes다. 22:33:31 영수증보다 973,078,528 bytes 증가했고 로그에도 분 단위 증가가 있다. 이는 `nohup`의 SSH 분리 실행과 진행성을 추가로 뒷받침하지만 H200 컴퓨트 종료 후 지속을 뜻하지 않는다.
- 문서 DB를 독립 읽기 재조회했다. 운영 setup 보고 `doc-2b97339f-f9fd-4abb-b04f-c334fa841652`는 `canon=false`, 파일/DB SHA-256 `eaef02137e1b8a6694f33e208a51747035ad75f6dc62935f2e279caa67ab4e5e`; 현재 체크포인트 `doc-00aad22b-c199-4e3d-9828-076127fd58da`는 `canon=true`, 파일/DB SHA-256 `93ded1c8ece4f901bfa1e8d1465a90887acb96d9e87cbed22d038c284a4e5f06`. `python3 tools/document_harness/harness.py verify --files`는 관리 파일 39개 문제 0, 무결성 `ok`다. 체크포인트는 원본 취득·최종 해시 검증을 미완료라고 명시한다.

`manifest.official_checksum.sha256`은 **공식 SHA-1 목록 파일 본문의 SHA-256**이다. 덤프 원본 자체의 SHA-256은 이 시점에 존재하지 않는다. 이를 최종 원본 hash로 읽으면 안 된다.

## 완료·재개 경계

다운로드 대상은 `/home/work/novel-toy-tune/sources/original/wikidata/20260922/wikidata-20260922-all.json.bz2.part`; 완료 대상은 같은 디렉터리에서 `.part` 없는 파일명이다. 현재 manifest는 `downloading`이며 partial을 `ORIGINAL` 완료 원본으로 세지 않는다. 운영 보고는 동일 코드판 재실행 절차를 설명하고 있으며, 재개는 사이드카 source identity가 같고 서버가 같은 ETag에 대해 `206`과 정확한 byte range를 반환할 때만 진행된다. 새 실행의 정확한 명령·PID·로그는 다음 재개 영수증에 남겨야 한다.

최종 수락에는 운영자의 실제 최종 파일 길이 103,222,517,992 bytes, 공식 SHA-1 일치, 별도로 계산한 덤프 SHA-256, 처음 3개 엔터티 JSON 표본, `status=complete` manifest를 별도로 읽어야 한다. 전체 bzip2 해제와 전체 의미 검증은 이 수락 범위에 포함하지 않는다. 현재 이 최종 증거가 없으므로 `acquisition_pending`을 유지한다. 현재의 `launch_accepted`는 **그 시점에 기동·재접속 확인된 다운로드를 안전하게 인계할 수 있다**는 의미이며 원본 취득 완료 판정이 아니다.
