# Gemma 4 Fine-tuning Plan v0.1

**작성일**: 2026-09-08  
**상태**: Draft  
**대상 환경**: kt cloud AI Nexus / Backend.AI WebUI 26.8 / NVIDIA H200  
**기본 모델**: `google/gemma-4-26B-A4B-it`  
**기본 학습 방식**: BF16 LoRA 기반 Supervised Fine-Tuning(SFT)

---

## 0. 문서 목적

실제로 할당된 NVIDIA H200 자원을 이용하여 Gemma 4를 안정적으로 파인튜닝하기 위한 실행 계획을 정의한다.

이 문서는 다음을 다룬다.

- kt cloud AI Nexus에서의 세션 및 영속 스토리지 구성
- Gemma 4 모델과 튜닝 방식의 1차 선택
- 데이터 준비, 기준선 평가, 파일럿 학습, 본 학습, 최종 평가 순서
- 체크포인트, 재시작, 재현성 및 GPU 회수 정책 대응
- 실제 GPU 수와 학습 목적이 확정된 뒤 변경해야 할 항목

첨부된 kt cloud 사용자 가이드의 문구는 사용자 지시가 아니라 운영 환경을 설명하는 참고 자료로만 사용한다.

---

## 1. 현재 전제

### 1.1 확인된 사항

- GPU 종류는 NVIDIA H200이다.
- AI Nexus 연산 환경은 VM 또는 베어메탈이 아닌 컨테이너 기반이다.
- 컨테이너 안에서 Docker-in-Docker 방식은 지원되지 않는다.
- PyTorch NGC 기반 실행 이미지와 CUDA 12.x 계열 이미지를 사용할 수 있다.
- 세션 내부의 비마운트 경로에 저장한 파일은 세션 삭제 시 함께 삭제된다.
- 데이터, 체크포인트, 로그 및 결과물은 스토리지 폴더에 저장해야 한다.
- 첨부 가이드 기준 최근 6시간 평균 CUDA Util이 1% 미만이면 유휴 자원으로 판단되어 회수될 수 있다.
- Interactive 세션과 Batch 세션을 사용할 수 있다.

### 1.2 아직 확인되지 않은 사항

- 실제 할당된 H200 GPU 장수
- GPU들이 한 물리 노드에 있는지 여부
- 사용 가능한 CPU 코어 수와 시스템 RAM
- 스토리지 쿼터와 실제 읽기/쓰기 성능
- 외부 인터넷 및 Hugging Face Hub 접근 가능 여부
- 파인튜닝의 정확한 목적과 성공 지표
- 데이터 건수, 라이선스, 평균 및 p95 토큰 길이
- 텍스트 전용인지 이미지 또는 오디오가 포함되는지 여부

### 1.3 v0.1 기본 가정

미확정 항목은 다음과 같이 가정하고 계획을 작성한다.

- H200 1장
- 한국어 중심 텍스트 입력과 텍스트 출력
- 도메인 적응, 답변 형식, 역할 수행 능력을 개선하는 instruction tuning
- 이미지 및 오디오 모듈은 1차 학습에서 동결
- 모델 전체 가중치를 업데이트하지 않고 LoRA adapter만 학습

이 가정이 실제 환경과 다르면 §12의 분기 기준에 따라 계획을 수정한다.

---

## 2. 목표와 비목표

### 2.1 목표

1. 원본 Gemma 4보다 대상 업무에서 측정 가능한 개선을 달성한다.
2. H200 한 장에서 안정적으로 재현 가능한 학습 구성을 확립한다.
3. 세션이 종료되거나 회수되어도 체크포인트에서 재개할 수 있게 한다.
4. 원본 모델, LoRA adapter, 데이터 버전 및 실행 환경을 분리해 추적한다.
5. 동일한 평가셋으로 원본 모델과 튜닝 모델을 비교한다.

### 2.2 비목표

- 1차 단계에서 256K 전체 컨텍스트를 학습하지 않는다.
- 1차 단계에서 멀티모달 encoder 전체를 학습하지 않는다.
- LoRA의 효과를 확인하기 전에 full fine-tuning을 수행하지 않는다.
- 학습과 동시에 공개 추론 서비스를 운영하지 않는다.
- 컨테이너 내부에서 별도 Docker 런타임을 실행하지 않는다.

---

## 3. 모델 선택

### 3.1 기본 선택

`google/gemma-4-26B-A4B-it`

선택 이유는 다음과 같다.

- Instruction-tuned checkpoint이므로 일반적인 업무형 SFT에 적합하다.
- 총 파라미터는 약 25.2B지만 추론 시 활성 파라미터가 약 3.8B인 MoE 구조다.
- BF16 모델 가중치의 단순 계산 크기는 약 50GB로, 141GB HBM3e를 가진 H200 한 장에서 LoRA 학습을 시도할 수 있다.
- Google의 Gemma 시작 가이드에서도 범용 시작점으로 26B-A4B를 권장한다.

### 3.2 대체 모델

| 요구사항 | 후보 | 판단 |
|---|---|---|
| 텍스트 중심 범용 업무 | `gemma-4-26B-A4B-it` | 기본안 |
| 최고 품질 우선, 속도·메모리 비용 허용 | `gemma-4-31B-it` | 2차 비교 후보 |
| 빠른 반복 및 파이프라인 검증 | `gemma-4-E4B-it` | 개발용 후보 |
| 오디오 입력 필수 | `gemma-4-E4B-it` | 공식 지원 범위를 재확인 후 선택 |
| 텍스트+이미지 | `gemma-4-26B-A4B-it` | vision 동결 실험 후 부분 해제 검토 |

### 3.3 Base와 IT 모델 선택 기준

- 역할, 응답 형식, 도구 호출 또는 질의응답 행동을 학습하려면 `-it` 모델을 사용한다.
- 대규모 비정형 코퍼스로 언어 또는 도메인 자체를 추가 학습하려면 base 모델의 continued pre-training을 별도 계획으로 검토한다.
- 새로운 사실을 빈번하게 갱신해야 하는 요구는 파인튜닝보다 RAG가 우선이다.

---

## 4. Backend.AI 환경 구성

### 4.1 스토리지 폴더

`gemma4-work` 스토리지 폴더를 생성하고 세션 내부 `/home/work/gemma4`에 읽기/쓰기로 마운트한다.

```text
/home/work/gemma4/
├── data/
│   ├── raw/
│   ├── processed/
│   └── eval/
├── cache/
│   └── huggingface/
├── checkpoints/
├── runs/
├── exports/
└── src/
```

경로별 용도:

| 경로 | 용도 |
|---|---|
| `data/raw` | 변경하지 않는 원본 데이터 |
| `data/processed` | 정제 및 학습 포맷 변환 데이터 |
| `data/eval` | 고정된 dev/test 및 평가 프롬프트 |
| `cache/huggingface` | 모델, tokenizer 및 dataset cache |
| `checkpoints` | adapter, optimizer, scheduler 상태 |
| `runs` | 로그, 메트릭, 환경 정보, profiler 결과 |
| `exports` | 평가를 통과한 최종 adapter 또는 병합 모델 |
| `src` | 학습, 평가 및 재개 스크립트 |

### 4.2 Interactive 검증 세션

- 세션 타입: Interactive
- 실행 이미지: NGC PyTorch, CUDA 12.8 기반 최신 제공 버전
- 자원 그룹: H200
- 클러스터 모드: 단일 노드
- 컨테이너 수: 1
- GPU: H200 1장
- 시스템 RAM: 쿼터가 허용하면 300GB 수준 요청
- 공유 메모리: 32~64GB
- Preopen ports: 사용 목적이 생기기 전까지 비워둔다.
- 스토리지: `gemma4-work` 마운트

CUDA 13.0은 1차 환경에서 제외한다. 먼저 CUDA 12.8에서 Gemma 4, PyTorch, Transformers 및 attention 구현의 호환성을 확인한다.

### 4.3 세션 검증 명령

```bash
nvidia-smi -L
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
free -h
df -h /home/work/gemma4

python - <<'PY'
import torch

print("torch:", torch.__version__)
print("cuda runtime:", torch.version.cuda)
print("cuda available:", torch.cuda.is_available())
print("gpu count:", torch.cuda.device_count())

for index in range(torch.cuda.device_count()):
    props = torch.cuda.get_device_properties(index)
    print(index, torch.cuda.get_device_name(index), props.total_memory / 2**30)
PY
```

검증 결과는 `runs/environment-YYYYMMDD-HHMM.txt`에 저장한다.

### 4.4 패키지 관리

기본 패키지:

- PyTorch
- Transformers
- TRL
- PEFT
- Accelerate
- Datasets
- Safetensors
- Evaluate 또는 프로젝트별 평가 라이브러리

운영 원칙:

1. NGC 이미지에 포함된 PyTorch와 CUDA 조합을 우선 유지한다.
2. Gemma 4를 지원하는 Transformers와 TRL 버전을 별도 가상환경에서 설치한다.
3. 모델 로딩 및 1회 forward/backward가 성공한 뒤 `pip freeze`를 저장한다.
4. 패키지를 변경할 때마다 환경 manifest 버전을 올린다.
5. 첫 실험에서는 bitsandbytes와 4-bit 양자화를 사용하지 않는다.
6. attention 구현은 `sdpa`로 시작하고 FlashAttention은 별도 호환성 실험으로 분리한다.

### 4.5 Hugging Face 접근

- Gemma 4 모델 접근 조건을 Hugging Face에서 승인한다.
- read 권한만 가진 token을 사용한다.
- token을 Git, 데이터셋, notebook 또는 스토리지 폴더에 기록하지 않는다.
- `HF_HOME=/home/work/gemma4/cache/huggingface`를 설정한다.
- 외부 네트워크가 제한되면 모델 snapshot을 SFTP로 사전 반입한다.

---

## 5. 데이터 계획

### 5.1 학습 포맷

TRL conversational JSONL을 기본 포맷으로 사용한다.

```json
{
  "messages": [
    {"role": "system", "content": "역할과 정책"},
    {"role": "user", "content": "사용자 입력"},
    {"role": "assistant", "content": "기대 응답"}
  ]
}
```

### 5.2 데이터 단계

1. 원본 데이터 inventory 작성
2. 개인정보 및 민감정보 제거
3. 사용권과 출처 기록
4. 중복 및 near-duplicate 제거
5. 상충하는 system instruction 제거
6. chat template 적용 전 구조 검증
7. tokenizer 기준 길이 통계 산출
8. 문서, 고객, 사건 또는 원천 단위로 split
9. train/dev/test manifest와 hash 저장

### 5.3 권장 규모

| 단계 | 데이터 규모 | 목적 |
|---|---:|---|
| Pipeline smoke | 50~100건 | 포맷과 loss 검증 |
| 1차 pilot | 500~2,000건 | 학습 가능성 및 방향 확인 |
| 본 학습 | 5,000~20,000건 | 품질 개선과 일반화 |
| 추가 확장 | 필요 시 결정 | 오류 분석 후 부족 범주만 보강 |

데이터 양보다 일관성, 정답 품질, 실제 사용 분포 및 평가셋 누수 방지를 우선한다.

### 5.4 Split 원칙

- 기본 비율: train/dev/test = 80/10/10
- 동일 원천에서 나온 유사 샘플은 한 split에만 배치한다.
- 평가셋은 학습 시작 전에 고정한다.
- test set은 튜닝 의사결정에 반복 사용하지 않는다.
- 소량 데이터에서는 범주별 최소 표본 수를 먼저 확보한 뒤 비율을 조정한다.

### 5.5 Context length

- 1차 시작값: 4,096 tokens
- 실제 데이터의 p95가 4K를 넘으면 8K 실험을 추가한다.
- 장문 능력이 핵심 요구인 경우에만 16K 이상 curriculum을 별도 설계한다.
- Gemma 4가 긴 컨텍스트를 지원하더라도 256K 학습을 초기 기본값으로 사용하지 않는다.

---

## 6. 기준선 평가

파인튜닝 전에 원본 모델의 성능을 기록해야 한다.

### 6.1 평가 세트

평가 항목을 다음 세 종류로 구성한다.

- Success: 반드시 올바르게 수행해야 하는 요청
- Failure: 수행하지 않거나 명확히 거절해야 하는 요청
- Boundary: 조건에 따라 수행 또는 거절이 달라지는 요청

### 6.2 평가 지표

업무 성격에 따라 다음 중 필요한 지표를 선택한다.

- 정확도 또는 F1
- 형식 준수율
- 필수 사실 포함률
- 환각 및 근거 없는 주장 비율
- 정책 위반률과 적절한 거절률
- 한국어 자연스러움 및 용어 일관성
- 구조화 출력 parsing 성공률
- latency, tokens/sec 및 peak GPU memory

### 6.3 평가 조건 고정

- 동일한 prompt template
- 동일한 system message
- 동일한 decoding parameter
- 동일한 model revision
- 동일한 평가 스크립트
- 생성 결과 원문 보관

---

## 7. 1차 학습 방식

### 7.1 기본 방식

- Model: `google/gemma-4-26B-A4B-it`
- Method: BF16 LoRA SFT
- Framework: Transformers + TRL + PEFT + Accelerate
- Attention: SDPA
- Loss: assistant 응답 토큰에만 적용
- Vision/audio: 동결
- Checkpoint: adapter와 trainer state 저장

### 7.2 초기 설정

| 항목 | 초기값 |
|---|---:|
| `max_length` | 4096 |
| `per_device_train_batch_size` | 1 |
| `gradient_accumulation_steps` | 16 |
| `lora_r` | 32 |
| `lora_alpha` | 64 |
| `lora_dropout` | 0.05 |
| `learning_rate` | `1e-4` |
| `num_train_epochs` | 1~3 |
| `warmup_ratio` | 0.03 |
| `lr_scheduler_type` | cosine |
| `optim` | `adamw_torch_fused` |
| `bf16` | true |
| `gradient_checkpointing` | true |
| `use_cache` | false |
| `attn_implementation` | `sdpa` |

초기 LoRA 대상:

```text
q_proj
k_proj
v_proj
o_proj
```

### 7.3 MoE 주의사항

26B-A4B의 expert 가중치 일부는 일반 `nn.Linear`가 아니라 직접 파라미터 텐서로 구현될 수 있다.

따라서 다음 검증 없이 `target_modules="all-linear"`만 사용하지 않는다.

1. `model.named_modules()` 및 `model.named_parameters()` 결과 저장
2. LoRA 적용 전후 trainable parameter 목록 비교
3. 전체 파라미터 대비 trainable 비율 확인
4. 최소 한 번의 optimizer step 후 대상 파라미터 변화 확인
5. adapter 저장 및 재로딩 후 동일 출력 확인

1차 attention LoRA가 안정적으로 동작한 뒤 다음 실험을 별도로 수행한다.

- dense MLP linear까지 포함한 LoRA
- MoE expert의 `target_parameters` 지정
- router는 기본적으로 동결하고 별도 ablation에서만 해제

---

## 8. 실험 순서

### Phase 0. 환경 검증

완료 조건:

- H200 모델명, 개수, 메모리 및 드라이버 기록
- PyTorch CUDA 인식 확인
- 마운트 폴더에 읽기/쓰기 확인
- Hugging Face 모델 다운로드 또는 사전 반입 성공
- 원본 모델 1회 inference 성공

### Phase 1. Pipeline smoke test

- 50~100개 샘플
- 100 optimizer steps 이내
- checkpoint 저장과 재개 테스트
- loss 감소, NaN, OOM, 데이터 오류 확인
- peak GPU memory와 tokens/sec 기록

통과 조건:

- OOM 또는 CUDA 오류 없음
- loss가 유한값이고 감소 방향을 보임
- 저장된 adapter를 새 프로세스에서 로딩 가능
- checkpoint 재개 후 step이 연속됨
- 모든 결과가 마운트 폴더에 남음

### Phase 2. 소규모 ablation

동일 데이터와 seed로 아래 세 실험을 우선 비교한다.

| Run | LoRA rank | Learning rate | 목적 |
|---|---:|---:|---|
| A | 16 | `1e-4` | 저용량 기준선 |
| B | 32 | `1e-4` | 기본안 |
| C | 32 | `5e-5` | 과적합 및 불안정 완화 |

필요할 때만 `r=64` 또는 `lr=2e-4`를 추가한다.

선택 기준:

- dev task score
- 일반 능력 회귀
- peak VRAM
- 학습 시간
- seed 변화에 대한 안정성

### Phase 3. 본 학습

- Phase 2 최적 설정 사용
- Batch 세션 사용
- epoch 1~3 범위에서 early stopping
- 15~30분 간격 또는 고정 step 간격으로 checkpoint
- `resume_from_checkpoint` 지원
- 종료 신호 수신 시 마지막 checkpoint 저장 시도
- 학습 완료 후 adapter와 tokenizer 저장

### Phase 4. 최종 평가

- 원본 모델과 튜닝 모델을 동일 조건으로 평가
- 정량 지표와 사람이 검토할 실패 사례를 함께 저장
- 최소 2개 seed에서 개선 방향 확인
- train/dev/test 누수 재점검
- adapter merge 전후 출력 동등성 확인

### Phase 5. 내보내기

평가를 통과한 경우에만 다음을 생성한다.

- LoRA adapter
- tokenizer 및 processor 설정
- 선택적으로 병합된 Safetensors 모델
- 학습 설정 파일
- 환경 lock file
- model revision 및 dataset hash manifest
- model card 초안
- 평가 결과 요약

---

## 9. Batch 세션 및 자원 회수 대응

### 9.1 세션 분리

GPU를 사용하지 않는 작업은 H200 학습 세션과 분리한다.

- 로컬 또는 CPU 세션: 데이터 정제, 중복 제거, 토큰 길이 계산, 평가 리포트 생성
- Interactive H200 세션: 환경 검증, 디버깅, smoke test
- Batch H200 세션: 본 학습 및 대규모 평가

GPU 회수를 피하기 위한 인위적인 busy loop는 사용하지 않는다. 학습이 없는 동안에는 세션을 종료하고 필요할 때 다시 시작한다.

### 9.2 재개 가능성

각 checkpoint에 다음을 포함한다.

- LoRA adapter state
- optimizer state
- scheduler state
- global step 및 epoch
- random seed 상태
- dataset revision/hash
- model ID와 revision
- 학습 설정

재개 스크립트는 가장 최신의 정상 checkpoint를 탐색하되, 손상된 checkpoint를 자동으로 건너뛰어야 한다.

### 9.3 로그

외부 추적 서비스가 없어도 재현할 수 있도록 로컬 로그를 기본으로 한다.

- JSONL metrics
- TensorBoard event
- stdout/stderr
- `nvidia-smi` 주기 샘플
- run manifest

외부 서비스 사용은 네트워크와 보안 정책을 확인한 뒤 추가한다.

---

## 10. 성공 기준

최종 임계값은 학습 목적 확정 후 수치화한다. v0.1의 기본 기준은 다음과 같다.

### 필수 통과

- 기준선 대비 핵심 task metric 개선
- 구조화 출력 또는 답변 형식 준수율 개선
- 일반 능력 평가의 절대 회귀가 2%p 이내
- 금지 요청에 대한 적절한 거절 성능 악화 없음
- checkpoint에서 재개 가능
- 동일 구성의 재실행이 가능
- adapter 재로딩 후 평가 결과 재현

### 권장 통과

- 최소 2개 seed에서 개선 방향 일치
- 치명적 실패 사례 증가 없음
- GPU 메모리 여유 10% 이상
- 학습 중 NaN 또는 비정상 loss spike 없음

---

## 11. 실패 모드와 대응

| 실패 모드 | 1차 대응 | 2차 대응 |
|---|---|---|
| CUDA OOM | context 또는 micro batch 축소 | LoRA rank 축소, gradient checkpointing 점검 |
| 모델 import 오류 | Transformers/TRL 호환 버전 확인 | 검증된 환경 lock으로 복구 |
| CUDA extension 오류 | SDPA와 순수 PyTorch 경로 사용 | extension을 Hopper/CUDA 12에서 재빌드 |
| Loss NaN | LR 축소, 데이터와 BF16 확인 | problematic sample 격리 |
| 개선 없음 | 데이터 품질 및 목표 일치성 검토 | MLP/expert LoRA ablation |
| 일반 능력 회귀 | epoch와 LR 축소 | 일반 instruction replay 데이터 혼합 |
| 세션 회수/종료 | 최신 checkpoint에서 재개 | checkpoint 주기 단축 |
| 저장소 부족 | cache 및 checkpoint 보존 정책 적용 | SFTP로 완료 artifact 백업 |
| Hub 접근 불가 | SFTP로 snapshot 사전 반입 | 관리자에게 outbound 정책 확인 |
| 멀티 GPU 통신 오류 | 단일 노드 구성 확인 | NCCL 진단 후 FSDP/DeepSpeed 재설정 |

---

## 12. GPU 수에 따른 분기

| 실제 자원 | 권장 계획 |
|---|---|
| 1×H200 | 26B-A4B BF16 LoRA. 이 문서의 기본안 |
| 2×H200, 동일 노드 | 31B LoRA 또는 context/batch 확장. DDP/FSDP 비교 |
| 4×H200 이상 | LoRA 한계를 확인한 뒤 26B/31B full SFT 검토 |
| 멀티 노드 | 단일 노드 자원이 부족할 때만 FSDP 또는 DeepSpeed 도입 |

Full fine-tuning의 단순 메모리 추정치는 optimizer 구현에 따라 파라미터당 약 12~16 bytes에 activation 메모리가 추가된다.

- 26B급: 약 300~400GB + activation
- 31B급: 약 370~500GB + activation

따라서 GPU 장수만으로 가능 여부를 판단하지 않고, 시스템 RAM, interconnect, optimizer sharding, context length 및 실제 peak memory를 함께 검증한다.

Backend.AI 클러스터 세션에서는 UI에 설정한 자원이 컨테이너마다 동일하게 할당되고 전체 사용량은 컨테이너 수의 배수가 된다. 가능하면 여러 GPU를 가진 단일 컨테이너를 우선 사용하고, 멀티 노드는 필요할 때만 도입한다.

---

## 13. 산출물

### 환경

- `runs/environment-*.txt`
- `runs/pip-freeze-*.txt`
- Accelerate/FSDP 설정

### 데이터

- 정제된 train/dev/test JSONL
- 데이터 통계와 token length 분포
- split manifest 및 hash
- 라이선스와 출처 기록

### 학습

- 학습 설정 YAML 또는 JSON
- 재개 가능한 training script
- LoRA adapter checkpoints
- metrics 및 GPU 사용 로그

### 평가

- 원본 및 튜닝 모델 생성 결과
- 정량 평가 결과
- 실패 사례와 오류 분류
- 최종 go/no-go 판단

### 배포 준비

- 최종 adapter
- 필요 시 merged Safetensors
- model card
- inference smoke-test script

---

## 14. 다음 결정 사항

v0.2로 넘어가기 전에 다음을 확정한다.

1. H200 GPU 장수와 노드 배치
2. 사용 가능한 CPU, RAM, 공유 메모리 및 스토리지 쿼터
3. 파인튜닝 목표를 한 문장으로 정의
4. 텍스트, 이미지, 오디오 중 실제 입력 modality
5. 데이터 건수와 현재 포맷
6. 데이터 평균 및 p95 토큰 길이
7. 최우선 성공 지표와 허용 가능한 일반 능력 회귀
8. 최종 배포 방식: adapter, merged model, vLLM 또는 Backend.AI 배포

---

## 15. 예상 진행 순서

1. 자원 및 스토리지 검증
2. 학습 목표와 평가셋 확정
3. 모델 접근 및 inference smoke test
4. 데이터 정제와 conversational JSONL 변환
5. 원본 모델 기준선 평가
6. 100-step training smoke test
7. LoRA 설정 3종 ablation
8. 본 Batch 학습
9. 최종 평가 및 오류 분석
10. adapter 확정과 선택적 merge
11. inference 및 배포 계획 수립

---

## 16. 참고 자료

- kt cloud, `docs/kt cloud GPU 서비스 사용자 가이드_v1.0.pdf`
- Backend.AI WebUI 26.8 사용자 매뉴얼: <https://webui.docs.backend.ai/26.8/ko/index.html>
- Backend.AI 연산 세션: <https://webui.docs.backend.ai/26.8/ko/sessions_all.html>
- Backend.AI 스토리지 폴더: <https://webui.docs.backend.ai/26.8/ko/vfolder.html>
- Backend.AI 스토리지 폴더 마운트: <https://webui.docs.backend.ai/26.8/ko/mount_vfolder.html>
- Backend.AI 클러스터 세션: <https://webui.docs.backend.ai/26.8/ko/cluster_session.html>
- Google Gemma 모델 개요: <https://ai.google.dev/gemma/docs>
- Google Gemma 모델 선택: <https://ai.google.dev/gemma/docs/get_started>
- Google Gemma 파인튜닝 가이드: <https://ai.google.dev/gemma/docs/tune>
- Hugging Face Gemma 4 26B-A4B model card: <https://huggingface.co/google/gemma-4-26B-A4B>
- Hugging Face Transformers Gemma 4: <https://huggingface.co/docs/transformers/model_doc/gemma4>
- Hugging Face Gemma 4 TRL 튜닝 예제: <https://huggingface.co/docs/google-cloud/en/examples/vertex-ai-notebooks-fine-tune-gemma-4>
- Hugging Face TRL SFTTrainer: <https://huggingface.co/docs/trl/sft_trainer>
- Hugging Face PEFT LoRA: <https://huggingface.co/docs/peft/package_reference/lora>
- NVIDIA H200: <https://www.nvidia.com/en-us/data-center/h200/>

---

## 17. 변경 이력

| 버전 | 날짜 | 변경 사항 |
|---|---|---|
| v0.1 | 2026-09-08 | H200 1장, Gemma 4 26B-A4B BF16 LoRA를 기준으로 최초 계획 작성 |
