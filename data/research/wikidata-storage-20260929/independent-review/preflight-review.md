# 다운로드 초안 독립 검토

최초 검토: 2026-09-28 22:29 UTC. 재검토: 2026-09-28 22:30 UTC, 대상 `tools/wikidata_storage/fetch_original.py` SHA-256 `0103f1158f2c5d61b65bf8cdf4ed69beb31ff84bb42b4f744e3c36bb3fddd9d0`. 이 문서는 **다운로드 시작 전 코드 검토**이며 실행·원격 원본 검증의 수락 기록이 아니다. 소유 밖 코드·Storage는 수정하지 않았다.

## 통과한 설계 요소

- 공식 고정 URL, 날짜, 103,222,517,992 bytes 및 SHA-1 값이 공식 목록과 일치한다. HTTP HEAD의 URL·크기·ETag·Last-Modified·Range를 고정 확인하고, 부분 재개는 `If-Range` 및 `206`, 정확한 `Content-Range`/`Content-Length`를 요구한다. `200` 응답에 부분 파일을 append하지 않는다.
- 기존 최종 원본이 있으면 덮어쓰지 않는다. `.part`의 사이드카 ID를 확인한다. 파일 길이·공식 SHA-1·로컬 SHA-256과 앞부분 엔터티 JSON 3개를 완료 판정에 사용하고, 전체 bzip2 해제 검사는 수행하지 않았다고 manifest에 표시한다.
- 100,000,000,000 bytes reserve를 초기 계산에 포함한다.

## 최초 초안의 보완 요청과 재검토

1. **단일 writer 보장 — 해결**: `fcntl.flock(LOCK_EX | LOCK_NB)`를 `.fetch.lock`에 걸고 실행 전체에 유지한다. 같은 `.part`에 두 프로세스가 함께 append하는 경로를 막는다.
2. **reserve 지속 검사 — 해결**: 시작 시 남은 전체 바이트와 100 GB reserve를 확인하고, 8 MiB chunk를 쓸 때마다 `statvfs`의 가용 공간이 reserve와 해당 chunk 크기 이상인지 확인한다. 임계치 이하에서는 완료 표시 없이 멈춘다.
3. **시점 관계 기록 — 해결**: manifest에 YAGO 4.6의 입력 statement revision과 개별 매칭이 이루어지지 않았고 이번 JSON은 별도 2026-09-22 보강판이라고 명시한다.
4. **서버에서의 독립 지속성 — 운영 증빙 대기**: 스크립트 자체는 daemon이 아니다. 운영자가 분리 실행하여 실제 PID·로그 경로·재개 명령을 영수증에 남겨야 한다.

**기동 판정: 가능.** 이 코드판에서 기존 최종 원본 덮어쓰기, 잘못된 `200` 재개 append, 길이·공식 SHA-1·JSON 표본 확인 전 `status=complete` 표시 경로는 찾지 못했다. 수정이 필요한 선행 차단점은 없다. 실행 후 수락은 별도 증거로 판단한다.

미결: 실제 원격 HTTP validator와 분리 실행 영수증, 시작/진행 및 종료 manifest와 공식 SHA-1·정확 bytes·로컬 SHA-256·JSON 표본 읽기 근거. 원본 전체 엔터티의 의미 품질이나 모든 bzip2 block의 독립 해제 검사는 수락 범위가 아니다.
