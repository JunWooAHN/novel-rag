# Backend.AI 시작 절차

1. 사용자 WebUI에서 쓰기 가능한 toy-tune vfolder를 만든다.
2. H200 Interactive 세션을 생성하고 해당 폴더를 마운트한다.
3. 앱에서 SSH/SFTP를 실행하고 표시된 사용자·호스트·포트를 확인한다.
4. 개인 키는 로컬에만 저장하고 권한 600으로 제한한다. 키 내용은 코드·문서·채팅에 복사하지 않는다.
5. SSH 호스트 식별 확인 후 접속한다. 문서의 예시 호스트나 포트를 그대로 사용하지 않는다.
6. ops/ssh 절차로 소스 묶음을 code/<source-id>에 반입한다.
7. 원격 Python 환경에서 패키지를 설치하고 아래 명령을 실행한다.

```sh
toy-tune doctor --runtime configs/runtimes/backendai-cuda.toml --probe-gpu
```

이 명령은 현재 머신의 Python·배포 패키지 metadata와 nvidia-smi를 읽는다. Torch를 import해 실제 연산을 수행하거나 모델을 다운로드하지 않는다. 작업 경로는 명시된 /home/work/toy-tune/workspace이며 실제 마운트가 다르면 --workspace로 바꾼다.

prepare로 합성 데이터셋을 발행한 뒤 파일이 vfolder에 있는지 확인한다. 영구성 검증은 결과를 보존한 후 안전하게 새 세션에서 같은 vfolder를 마운트하고 verify-dataset을 다시 실행한다. GPU가 할당돼 있다는 사실만으로 세션을 임의 종료하지 않는다.

다음 엔진 구현에 필요한 사실: 실제 GPU 모델·메모리, 이미지 이름, Python/Torch/CUDA 조합, 스토리지 여유·파일시스템, 세션 회수 정책, Hugging Face 접근 가능 여부. 키와 로그인 token을 제외한 결과만 실험 기록에 남긴다.

참고: https://webui.docs.backend.ai/26.8/ko/sftp_to_container.html
