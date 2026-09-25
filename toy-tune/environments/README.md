# 환경 프로파일

기본 패키지는 Python 3.11+ 표준 라이브러리로 실행한다. 테스트 선택 그룹은 JSON Schema validator를 추가한다.

2026-09-14 로컬 검증: macOS arm64, Python 3.14.3, 독립 임시 venv. 이 기록은 H200 또는 MLX 학습 환경 보증이 아니다.

- CPU: 현재 패키지와 테스트 설치 가능.
- CUDA: Backend.AI 또는 다른 서버에서 doctor --probe-gpu로 환경부터 확인한다. 기존 PyTorch를 교체하거나 최신 CUDA를 임의 설치하지 않는다.
- MLX: macOS 환경 확인 후 별도 엔진 의존성을 선택한다.
- PostgreSQL: DB adapter 구현 시 읽기용 드라이버·접속 설정을 별도로 추가한다.

CUDA/MLX용 extras나 거짓 lockfile은 아직 없다. 모델 지원 및 실제 실행 이미지가 확인되면 환경별 의존성 잠금과 실험 설정을 추가한다.
