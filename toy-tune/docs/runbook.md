# 로컬 실행과 복구

runtime TOML과 split TOML의 알 수 없는 필드는 오류다. workspace는 CLI --workspace가 profile보다 우선한다. 비밀값을 담은 자유형 설정이나 전체 환경변수 덤프는 저장하지 않는다.

workspace는 절대 경로이며 Git checkout 및 pyproject.toml이 있는 소스 디렉터리 밖 전용 디렉터리여야 한다. 홈 디렉터리 자체와 파일시스템 루트는 거부한다. 읽기 전용 doctor는 디렉터리를 생성하지 않으며, prepare는 검증된 입력이 있을 때만 datasets 디렉터리를 만든다.

## 파일 발행

writer가 artifact ID별 exclusive lock을 획득한 뒤 같은 파일시스템의 임시 디렉터리에 파일과 manifest를 쓰고 최종 디렉터리로 이동한다. 파일 단위 fsync를 수행한다. checksum 검증 후에만 정상 결과를 반환한다.

이 구현은 단일 호스트 파일시스템에서 테스트했다. 파일시스템·서버 전원 장애 내구성과 Backend.AI 네트워크 스토리지의 rename/lock 의미는 별도 검증해야 한다. lock 파일이 남으면 프로세스 종료 여부와 산출물을 확인한 뒤 운영자가 복구한다. 자동으로 stale lock을 삭제하지 않는다.

부분 데이터셋에 같은 ID로 덮어쓰지 않는다. 기존 디렉터리에 manifest가 없거나 payload가 틀리면 verify가 실패한다. 잘못된 대상은 사용자 확인 후 별도 위치로 보관하고 재시도한다.

## 구현 범위

run store 상태 전이는 created → validated → running → completed/failed/interrupted다. 상태는 expected 값과 비교한 뒤 바꾸므로 뒤늦은 writer가 변경을 덮어쓰지 않는다. 이 단계는 실제 trainer나 scheduler에 연결되지 않았다.

H200 학습 중단·재개, optimizer/RNG 복원, 최종 export, 모델 변환 검증은 후속 작업이다. 현재 CPU 테스트를 통과했다고 학습 가능 상태로 판정하지 않는다.
