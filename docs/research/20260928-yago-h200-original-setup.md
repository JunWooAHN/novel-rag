---
category_id: research
lineage_id: lin-7283dac3-ac48-4bef-893d-346d60f83143
document_id: doc-c547c683-4c4c-4c42-ac31-f42578e7cd7c
parent_lineage_id: lin-1a78dc59-6af9-4445-88e4-858f5327a856
abstract: H200 영속 Storage의 YAGO 4.6 전체 원본 보관 작업의 실행 경로, 검증 근거, 진행 상태와 재개 조건을 기록한다.
version: 0.0.2
created_at: '2026-09-28T06:21:30.973242Z'
updated_at: '2026-09-28T09:35:19Z'
tags:
- YAGO
- H200
- 원본보관
canon: false
---
# YAGO 4.6 H200 Storage 원본 보관 실행 기록

## 완료 판정과 범위

[공식 YAGO 4.6 배포 디렉터리](https://yago-knowledge.org/data/yago4.6/)의 ZIP 12개를 기존 H200 세션에 연결된 **영속 Storage**의 `/home/work/novel-toy-tune/sources/original/yago/4.6/`에 보관했다. 원 ZIP 바이트는 `zip/`, ZIP별 해제본은 `extracted/`에 있다. `ORIGINAL_UPSTREAM.txt`와 `manifest.json`은 판·원 URL·수신일·ETag/Last-Modified·ZIP/해제 크기·SHA-256·CRC·실제 모드를 기록한다. 인덱스·변환·정제·DB 적재는 이 원본 경로 밖에서 별도 작업으로 수행해야 한다. 모델·제품 DB·기존 세션 설정은 바꾸지 않았다.

**2026-09-28 09:32:43 UTC 자동 최종 검증 성공:** [로컬 중계 종료 코드](../../data/research/yago-storage-20260928/relay-final.exit)는 `0`이고 [실행 로그](../../data/research/yago-storage-20260928/relay-final.log)는 12개 각각의 ZIP CRC·SHA-256, 해제 파일 CRC·SHA-256·크기·`0444` 점검을 마친 뒤 `verified_at=2026-09-28T09:32:43.394637Z`, `zip_count=12`, 압축 합계 **9,907,409,082 byte**, 해제 합계 **78,426,497,491 byte**를 출력한다. [최종 원격 manifest 사본](../../data/research/yago-storage-20260928/manifest-final.json)은 `status=complete`, 12개 원본의 원 URL과 실제 SHA·크기·모드를 담는다. 그 파일의 SHA-256은 `da0d761331e3ccb070bfebbc5ecf4ad5db4165eac0ef5bc619444d95f78a70bb`이다. 이 수치는 파생 인덱스나 백업의 크기를 포함하지 않는다.

새 SSH 연결에서 실시한 [읽기 전용 재접속 점검](../../data/research/yago-storage-20260928/post-reconnect-check.json)은 `/home/work/novel-toy-tune`가 RW NFS 마운트이고, 실제 ZIP 12개와 해제 파일 12개의 이름·크기가 manifest와 일치하며 완료파일이 전부 `0444`, 원본 표식이 존재하고 문제 목록이 비어 있음을 확인했다. `du -sb` 실측은 원본 루트 **88,346,501,056 byte**이며 manifest/보조파일과 보존된 초기 부분파일도 포함한다. 재접속 점검은 파일 메타데이터를 읽었고 78 GB 전체 SHA/CRC를 반복하지 않았다. 원본의 최종 내용 검증 근거는 위 자동 검증 로그다. 현재 점검에서 Storage 가용량은 1,676,437,094,400 byte였다.

이 문서는 일회성 실행 증거여서 `canon=false`로 유지한다. 반복 적용할 역사 자료의 입력·검증 계약은 [채택된 역사 PRD](../prd/wikipedia-history-ontology.md)에 있다. 이 보관 완료는 현실 역사 릴리스·작품 역사표·A40 백업·NFS 서버 측 내구성 검증의 완료를 뜻하지 않는다.

## 보관 경로와 초기 Storage 근거

기존 H200 세션 `novel-toy-i2-20260927`에 재접속했으며 새 세션은 만들지 않았다. [실행 전 `findmnt`·`statvfs` 결과](../../data/research/yago-storage-20260928/preflight.json)는 `/home/work/novel-toy-tune` 자체가 RW NFS Storage 마운트이고 당시 가용량이 1,764,511,186,944 byte였음을 보여준다. ZIP 12개 압축·해제 추정 합계와 5 GB 여유를 더한 초기 요구 93,333,906,573 byte를 넘었다. 완료 검증된 신규 ZIP·추출 파일에만 `0444`를 적용했고 기존 파일이나 상위 Storage 권한은 바꾸지 않았다. 보관 및 재확인 방법은 [도구 사용법](../../tools/yago_storage/README.md)에 있다.

`zip/`에는 공식 `.zip` 12개 외에 수신 메타데이터용 `.part.json`과 중단된 최초 직접수신의 taxonomy 부분파일 `*.direct-preserved-*.part` 및 sidecar가 남아 있다. 이 보조파일은 원본 ZIP 12개 또는 해제본으로 세지 않으며 [재접속 목록](../../data/research/yago-storage-20260928/post-reconnect-check.json)에 별도 열거했다. 부분파일과 캐시를 임의로 완성본으로 승격하거나 삭제하지 않았다.

## 실행 경로와 실패 방어

처음 H200 직접 수신은 공식 taxonomy ZIP의 원격 수신이 느려 다운로드 PID `25290`만 종료했다. 완료한 schema와 taxonomy 부분파일·출처 sidecar를 보존한 근거는 [직접 수신 중단 로그](../../data/research/yago-storage-20260928/direct-fetch-stopped.log)다. 이후 공식 URL의 동일 판 ETag/Last-Modified와 각 Range 길이를 묶어 확인하는 로컬 중계를 사용했다. 독립 Sol은 실행 전에 직접 수신·중계 코드의 Storage 마운트/경계·symlink, 부분파일 출처 결속, 추가 추출파일 검사와 `--workers` 옵션을 검토·수락했다.

로컬 16-worker 시도에서 두 번의 짧은 Range 응답을 길이 검사가 거부했다. 해당 범위를 완료로 기록하지 않고 정상 종료·단일 writer 확인 뒤 8-worker로 재개했다. 한때 사용자의 이동 요청에 따라 서버 독립 runner를 준비했으나 **기동하지 않았다**. 이후 사용자가 로컬 진행을 허용해 기존 완료 ZIP·Range를 보존한 채 최종 `relay-8c`를 실행했다. 최종 로컬 shell PID `8013`, 도구 세션 ID `56028`, 로그 경로 `/tmp/yago-relay-20260928/relay-8c.log`, 종료 파일 `/tmp/yago-relay-20260928/relay-8c.exit`였다. 로그와 종료 파일의 프로젝트 사본은 위 완료 근거로 보존했다. 최종 실행기는 `stage → fetch --only`를 파일별로 수행하고 마지막 파일에서 자동으로 전량 `verify`를 마쳤다. 원격 도구는 `/home/work/novel-toy-tune/tools/yago_storage/20260928/`에 있으며 전송한 `fetch_original.py` SHA-256은 `6b37ad69478b8a75de25140b6e217383ad506d86b98b5c82d550c146c0a48629`, `release.json` SHA-256은 `b86921152231c6aff951cd67bcf89ad75fbbee61a8edd540ece62edebb067dad`였다. SSH 키·자격증명은 도구 번들·원본 manifest·보고서·프로젝트 evidence에 넣지 않았다.

초기 [2/12 manifest](../../data/research/yago-storage-20260928/manifest-in-progress.json)와 [facts 뒤 3/12 manifest](../../data/research/yago-storage-20260928/manifest-after-facts.json)는 실행 중 상태의 스냅샷이다. 전량 판정은 최종 manifest·자동 검증 로그·재접속 점검을 기준으로 한다. 로컬 재개 캐시와 접속 키는 최종 독립 검토가 끝나기 전 삭제하지 않았다. 남은 확인은 독립 검토자의 증거 간 정합성 수락이며, 데이터 수신·해제·자동 검증 자체는 완료했다.
