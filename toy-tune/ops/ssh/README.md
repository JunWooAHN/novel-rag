# 다른 서버로 소스 반입

1. source-files.txt의 포함 목록을 검토한다. 원문과 workspace는 이 목록에 포함하지 않는다.
2. 프로젝트 루트에서 python3 ops/ssh/package_source.py --output <Git-밖-배포물-폴더>를 실행한다.
3. 만들어진 src-<hash>.tar만 확인된 SSH host/port로 전송한다.
4. 원격 영구 경로의 code/ 아래에 압축을 풀어 code/src-<hash>/를 만든다. 기존 실행 소스를 덮어쓰지 않는다.
5. source-manifest.json의 파일 checksum을 대조하고 별도 원격 venv에서 pip install .로 설치한다.
6. 원문 데이터는 명시적으로 선택한 source bundle을 별도 비공개 경로로 반입한다. 소스 압축 파일에 합치지 않는다.

source ID는 반입되는 파일 내용 전체의 해시로 결정한다. Git commit만 기록하는 것과 달리 아직 커밋되지 않은 실제 코드도 식별한다. source-files.txt가 새로운 코드·계약 파일을 빠뜨리지 않는지 테스트한다.

archive 도구는 로컬 파일만 작성하고 SSH·클라우드 호출을 수행하지 않는다. 같은 source ID 파일이 이미 있으면 중단한다. 실패한 전송·압축 파일은 완료 산출물로 사용하지 않는다.
