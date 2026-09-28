# YAGO 4.6 원본 보관 배치

공식 배포 디렉터리의 12개 ZIP을 H200의 영속 Storage에 **원본(original, upstream unchanged)** 으로 보관한다. `release.json`의 압축 크기와 ZIP 중앙 디렉터리 해제 크기는 사전 Range 조사 값이다. 실행기는 원 URL에서 직접 내려받아 ZIP 바이트를 변경하지 않고 `zip/`에 두며, 압축을 푼 파일을 `extracted/`에 ZIP별로 분리한다. 인덱스·RDF 변환·정제·DB 적재 등 파생물은 이 원본 디렉터리가 아닌 별도 경로에 둔다.

원격에서 `findmnt`와 `statvfs`로 `/home/work/novel-toy-tune`가 영속 Storage 마운트이고 여유 공간이 충분한지 먼저 확인한다. 그 결과의 mount target을 후속 명령에 그대로 넣는다. 기존 모델·DB·세션은 변경하지 않는다.

```sh
python3 fetch_original.py preflight --storage-base /home/work/novel-toy-tune \
  --root /home/work/novel-toy-tune/sources/original/yago/4.6
python3 -u fetch_original.py fetch --storage-base /home/work/novel-toy-tune \
  --root /home/work/novel-toy-tune/sources/original/yago/4.6 \
  --expected-mount-target /home/work/novel-toy-tune
python3 -u fetch_original.py verify --storage-base /home/work/novel-toy-tune \
  --root /home/work/novel-toy-tune/sources/original/yago/4.6 \
  --expected-mount-target /home/work/novel-toy-tune
```

`fetch`는 진행 중 `.part`를 재개할 때 기존 ETag 또는 Last-Modified와 서버의 `206 Content-Range`를 검증한다. 변경된 원본·잘못된 부분 파일·이미 완료된 원본의 내용 차이는 덮어쓰지 않고 중단한다. ZIP CRC, 추출 파일의 CRC·SHA-256·크기와 예상 전체 크기를 검사하고 파일마다 URL, HTTP 헤더, 수신 시각, 압축/해제 크기, SHA-256을 `manifest.json`에 기록한다. 검증이 끝난 새 ZIP과 추출 파일만 읽기 전용(`0444`)으로 만들고 실제 모드도 기록한다. 상위 Storage 권한은 바꾸지 않는다. `ORIGINAL_UPSTREAM.txt`와 디렉터리 이름에도 원본임을 표시한다. 중단 시 같은 `fetch` 명령으로 재개하며, 재접속 후 `verify`를 다시 실행해 원본을 확인한다.

원격 전송 대상은 이 디렉터리의 `fetch_original.py`, `release.json` 두 파일뿐이다. SSH 키와 `.env` 계열 파일을 함께 전송하거나 기록하지 않는다.

공식 서버에서 H200으로 직접 받는 속도가 매우 낮으면, 동일 URL의 병렬 HTTP Range를 로컬 임시 폴더에서 받아 검증한 뒤 `relay_original.py`로 같은 Storage에 중계한다. 기본 병렬 수는 4이며 `--workers`로 1–16 사이에서 지정할 수 있다. 각 ZIP은 로컬 부분 Range를 재개하고 전체 CRC·SHA-256을 확인한 뒤 원격 `*.relay.part`로 보낸다. 중계 대상의 NFS 마운트·하위 경로를 업로드 직전에 다시 확인하고, 기존 직접수신 `.part`는 별명으로 보존한다. 원격 `stage → fetch --only`가 ZIP별 추출·manifest를 자동 진행하고 마지막 파일에서 전체 검증까지 마친다. 중단되면 같은 로컬 명령을 재실행한다. 로컬 작업 폴더·SSH 키·known_hosts 경로는 실행 인자로만 받고 원본 manifest에 기록하지 않는다.

```sh
python3 -u relay_original.py --work-dir /tmp/yago-relay-20260928 \
  --key /path/to/private-session-key --known-hosts /path/to/known_hosts \
  --workers 8
```
