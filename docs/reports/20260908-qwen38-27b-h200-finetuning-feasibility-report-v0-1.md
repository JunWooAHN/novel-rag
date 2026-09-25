# Qwen3.8-27B Uncensored GGUF H200 파인튜닝 타당성 검토 v0.1

- 작성일: 2026-09-08
- 대상 GPU: KT Cloud AI Nexus H200 141GB 1장
- 사용자 제시 모델: `HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF`
- 결론 수준: 사전 타당성 검토. 아직 모델 다운로드나 학습을 실행하지 않음

## 1. 요약 결론

제시된 링크의 모델은 Gemma 31B가 아니다. 실제 모델은 **Qwen3.8-27B dense multimodal 모델의 Aggressive uncensored GGUF 변형**이다.

H200 141GB 한 장에서 다음은 가능하다.

- Qwen3.8-27B BF16 기반 text-only LoRA SFT: 가능성이 높고 권장
- Qwen3.8-27B 4bit QLoRA: 가능하지만 H200 용량을 고려하면 우선 선택할 이유가 약함
- 27B 전체 파라미터 BF16 파인튜닝: 단일 H200에서는 비현실적
- 링크의 GGUF 파일을 그대로 일반적인 Unsloth/Swift/LLaMA-Factory 학습에 사용: 비권장
- 링크의 Q8 GGUF를 BF16으로 역양자화한 뒤 LoRA: 기술적으로 시도 가능하지만 실험 경로

가장 안전한 1차 경로는 **공식 `Qwen/Qwen3.8-27B` Safetensors를 BF16으로 로드하여 LoRA를 학습하고, 학습 후 배포용 GGUF로 변환하는 것**이다.

제시된 Aggressive uncensored 가중치 자체를 반드시 출발점으로 써야 한다면, 제작자에게 BF16/F16/Safetensors 원본 또는 LoRA adapter 공개 여부를 먼저 확인한다. 현재 링크 저장소에는 양자화된 GGUF들만 있고 full-precision 학습 체크포인트는 보이지 않는다.

## 2. 모델 식별

| 항목 | 확인 결과 |
|---|---|
| 계열 | Qwen3.8 |
| 파라미터 | language model 27B dense |
| 구조 | Qwen3.5 계열 hybrid attention, 64 layers, hidden size 5,120 |
| 모달리티 | text, image, video |
| 기본 context | 262,144 tokens |
| MTP | 내장 NextN/MTP 및 별도 FastMTP sidecar |
| 라이선스 | Apache-2.0 표기 |
| 배포 형식 | GGUF quantization only |

제시된 저장소가 제공하는 대표 파일 크기는 다음과 같다.

| quant | 파일 크기 |
|---|---:|
| Q8_K_P | 31.46GB |
| Q6_K_P | 25.92GB |
| Q4_K_P | 17.92GB |
| IQ4_XS | 15.71GB |
| IQ2_M | 10.32GB |
| Vision projector BF16 | 931MB |
| FastMTP sidecar | 903MB |

참고:

- [사용자 제시 GGUF 모델](https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF)
- [제시 모델의 파일 목록](https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF/tree/main)
- [공식 Qwen3.8-27B Safetensors](https://huggingface.co/Qwen/Qwen3.8-27B)
- [Qwen3.8 공식 저장소](https://github.com/QwenLM/Qwen3.8)

## 3. GGUF를 그대로 학습하지 않는 이유

GGUF는 주로 llama.cpp 계열 추론을 위한 단일 파일 형식이다. 양자화된 GGUF는 원래 가중치의 정밀도를 이미 잃은 상태다.

최신 Transformers는 일부 GGUF를 역양자화하여 일반 dense model로 로드할 수 있고, 문서상 이후 학습도 가능하다. 그러나 이 경우 다음 문제가 있다.

- 로드 시 양자화 메모리 절감 효과가 사라진다.
- 낮은 bit GGUF에서 시작하면 이미 발생한 양자화 오차를 되돌릴 수 없다.
- 제시 모델의 K_P custom quant와 Qwen3.8/MTP tensor가 학습 도구 전체에서 동일하게 보존되는지 별도 검증이 필요하다.
- FastMTP sidecar는 현재 target 가중치에 맞춘 추론 가속물이다. target을 파인튜닝하면 draft acceptance와 호환성이 달라질 수 있다.
- llama.cpp 자체 학습 예제는 현재 FP32와 제한된 하드웨어를 대상으로 한 WIP 성격이므로 27B 실전 학습 경로로 부적합하다.

따라서 표준 흐름은 다음이어야 한다.

```text
HF Safetensors BF16
-> LoRA/SFT 학습
-> 평가
-> adapter 보존
-> 필요 시 base와 merge
-> 새 GGUF로 quantize
-> llama.cpp/vLLM 추론 평가
```

관련 문서:

- [Transformers GGUF 로드 및 역양자화](https://huggingface.co/docs/transformers/main/quantization/gguf)
- [llama.cpp training 예제의 현재 제약](https://github.com/ggml-org/llama.cpp/blob/master/examples/training/README.md)

## 4. 단일 H200 141GB에서 가능한 학습 방식

### 4.1 전체 파라미터 학습

27B 모델의 BF16 가중치만 약 54~56GB다. 전체 학습에서는 가중치뿐 아니라 gradient, optimizer state, 경우에 따라 FP32 master weight와 activation이 필요하다.

일반적인 AdamW 계열 전체 학습의 대략적인 모델 상태만 계산해도 다음 규모다.

```text
BF16 weights          약 54GB
BF16 gradients        약 54GB
FP32 master weights   약 108GB
FP32 Adam moments     약 216GB
activation/temporary  별도
```

구현에 따라 일부 항목을 줄일 수 있어도 단일 141GB HBM에 전체 학습을 안정적으로 넣기는 어렵다. full fine-tuning은 이 단계의 대상에서 제외한다.

### 4.2 BF16 LoRA

권장 방식이다.

- base weight 약 56GB를 BF16으로 유지한다.
- base를 freeze하고 LoRA adapter만 학습한다.
- gradient checkpointing을 사용한다.
- vision tower와 MTP/FastMTP는 우선 학습 대상에서 제외한다.
- 8K sequence부터 시작하여 16K까지 실제 peak VRAM을 측정한다.
- batch size 1과 gradient accumulation으로 effective batch를 만든다.

H200 141GB라면 base weight를 BF16으로 유지하면서 adapter, optimizer, activation을 위한 여유를 확보할 수 있다. 8K~16K text-only LoRA는 가능성이 높지만, 실제 최대 길이와 throughput은 설치된 PyTorch, attention kernel, packing, LoRA target 범위에 따라 달라지므로 짧은 burn-in이 필요하다.

### 4.3 QLoRA

4bit QLoRA도 충분히 가능하다. 다만 이 GPU에서는 메모리 절약보다 품질과 구현 단순성이 우선이므로 BF16 LoRA를 먼저 검증한다.

QLoRA는 다음 경우에 후순위로 고려한다.

- 32K 이상의 긴 sequence 학습이 반드시 필요할 때
- 동시에 더 큰 batch를 요구할 때
- 여러 실험을 한 세션에서 병렬로 돌려야 할 때
- BF16 LoRA가 실제로 OOM일 때

## 5. Aggressive uncensored 변형을 출발점으로 쓸 수 있는가

### 5.1 가장 좋은 경우

HauhauCS가 동일 가중치의 BF16/F16 Safetensors 또는 원래 uncensor adapter를 제공한다면 그것을 사용한다. 이 경우 일반적인 LoRA 도구 체인에 바로 연결할 수 있다.

### 5.2 현재 공개물만 사용하는 경우

현재 링크에서 고를 수 있는 현실적인 입력은 Q8_K_P GGUF다. 반드시 이 변형에서 시작해야 한다면 다음 실험이 가능하다.

1. Q8_K_P를 Transformers의 GGUF loader로 BF16에 역양자화한다.
2. 로드된 text model의 출력이 llama.cpp 원본과 충분히 유사한지 검증한다.
3. MTP, vision, unknown tensor의 누락 경고를 모두 기록한다.
4. 아주 작은 LoRA와 100~500개 샘플로 학습 smoke test를 한다.
5. 저장·재로드·추론·GGUF 재변환까지 왕복 검증한다.

Q4 이하를 역양자화한 모델을 장기 학습의 출발점으로 삼는 것은 권장하지 않는다. Q8도 원본 BF16과 동등하지 않으므로 이 경로는 재현성·품질 비교가 필요한 실험이다.

### 5.3 모델 선택상 위험

모델 제작자는 Aggressive 변형을 거부 행동이 거의 없고 직접적인 응답을 내는 버전으로 설명하면서, 장문 agentic reliability가 중요한 경우 Balanced 변형이 더 안전할 수 있다고 직접 적고 있다.

웹소설 생성에서는 "uncensored" 자체가 좋은 문장력, 장기 일관성, 한국어 자연스러움, 역사 사실 준수를 보장하지 않는다. 이 모델을 확정하기 전에 공식 Qwen3.8-27B와 동일 프롬프트로 비교해야 한다.

평가 항목은 최소한 다음을 포함한다.

- 한국어 문장 자연스러움과 번역투
- 5천~1만 자 장면에서 인물 말투 유지
- 역사적 제약 준수
- 제공된 역사전표에서 사실 누락·왜곡 비율
- 선정적·폭력적 장면에서 불필요한 수위 상승 여부
- 지시를 무조건 따르는 성향 때문에 설정 충돌까지 수용하는지
- 반복 문구, 장면 늘이기, 결말 급발진

## 6. 권장 1차 학습 범위

첫 실험에서 모델 하나에 모든 역할을 동시에 학습하지 않는다. 우선 **한국어 웹소설 작가 역할**만 LoRA로 학습한다.

입력 예시:

- 작품 설정 요약
- 현재 정사 상태
- 이번 화의 chapter contract
- 관련 오리진 역사 검색 결과
- 직전 화 요약과 이어쓰기 지점

출력 예시:

- 이번 화 본문만 출력

역사전표 추출, 일관성 검수, 수정 제안은 별도 데이터와 별도 adapter 또는 base model 평가로 분리한다. 작가와 사실 추출기를 같은 초기 SFT에 섞으면 출력 형식과 문체가 서로 오염될 가능성이 있다.

## 7. 권장 초기 설정 범위

아래 값은 확정 하이퍼파라미터가 아니라 H200 smoke test의 시작 범위다.

| 항목 | 시작값/범위 |
|---|---|
| base | 우선 `Qwen/Qwen3.8-27B` Safetensors |
| modality | text-only |
| dtype | BF16 |
| method | LoRA SFT |
| sequence length | 8,192부터 시작, 16,384 검증 |
| micro batch | 1 |
| gradient accumulation | 데이터 기준으로 조정 |
| gradient checkpointing | 활성화 |
| attention | H200/CUDA 12.x에서 검증된 FlashAttention 또는 SDPA |
| optimizer | LoRA용 AdamW 계열, 상태 메모리 실측 |
| validation | 작품·시대·작가 단위 누수 방지 split |
| checkpoint | adapter 중심 저장 |

Qwen3.8은 일반 Qwen2와 다른 hybrid Gated DeltaNet 구조를 포함한다. LoRA target module은 기존 예제의 `q_proj/v_proj` 목록을 그대로 복사하지 말고 실제 `named_modules()`를 덤프하여 결정한다. 초기에는 text backbone의 `all-linear` 후보를 만들고 vision tower, output head, MTP 관련 모듈을 명시적으로 제외하는 편이 안전하다.

공식 Qwen은 Qwen3.8 파인튜닝에 Unsloth, Swift, LLaMA-Factory를 권장한다. 실제 첫 구현에서는 새 모델 지원 상태를 smoke test로 비교한 뒤 하나를 고른다.

- [Qwen3.8 공식 파인튜닝 안내](https://github.com/QwenLM/Qwen3.8#finetuning)
- [Transformers Qwen3.5/3.8 계열 모델 구현](https://github.com/huggingface/transformers/blob/main/docs/source/en/model_doc/qwen3_5.md)
- [PEFT LoRA 개념과 구현](https://huggingface.co/docs/peft/main/conceptual_guides/lora)

## 8. KT Cloud AI Nexus 환경 반영

첨부된 KT Cloud GPU 서비스 사용자 가이드 v1.0에서 다음 제약을 확인했다.

- 제공 환경은 VM이 아니라 Docker container 기반 session이다.
- container 내부 Docker 실행은 지원하지 않는다.
- NGC PyTorch 계열 실행 환경과 CUDA 12.6, 12.8, 13.0 이미지가 제공된다.
- H200은 Hopper `sm_90`이며 CUDA 12.x가 권장된다.
- 세션이 삭제되면 기본 폴더도 삭제되므로 데이터 폴더를 반드시 마운트해야 한다.
- 마운트된 데이터 폴더는 `/home/work/` 아래에 연결된다.
- 4GB를 넘는 업로드는 drag-and-drop 대신 file browser 또는 SFTP를 사용해야 한다.
- 최근 6시간 평균 CUDA utilization이 1 미만이면 유휴 자원이 회수될 수 있다.

이에 따른 실행 원칙은 다음과 같다.

1. Docker-in-Docker 방식의 학습 이미지를 계획하지 않는다.
2. 우선 NGC PyTorch + CUDA 12.8 계열 환경에서 pip/conda로 학습 도구를 설치한다.
3. 모델, 데이터셋, adapter, checkpoint, 로그를 모두 `/home/work/<mounted-folder>/` 아래에 둔다.
4. 다운로드·전처리처럼 GPU를 오래 쓰지 않는 작업은 가능하면 별도 CPU 세션에서 먼저 끝낸다.
5. 학습은 중단 가능하도록 주기적 adapter checkpoint와 trainer state를 저장한다.
6. GGUF 역양자화 실험을 한다면 CPU RAM과 임시 디스크를 충분히 할당한다.

스토리지는 다음 정도를 시작점으로 잡는다.

| 용도 | 대략적 공간 |
|---|---:|
| 공식 BF16 모델 | 약 56GB |
| tokenizer/config/cache 여유 | 수 GB |
| 데이터셋과 전처리 산출물 | 규모에 따라 수십 GB |
| merged model 1개 | 약 56GB |
| 배포용 GGUF 여러 개 | 약 10~32GB씩 |
| 권장 영속 공간 | 최소 200GB, 가능하면 300GB 이상 |

출처: [KT Cloud GPU 서비스 사용자 가이드 v1.0](../kt%20cloud%20GPU%20서비스%20사용자%20가이드_v1.0.pdf)

## 9. 실행 전 필수 게이트

### Gate A: 하드웨어 확인

- `nvidia-smi`에서 H200과 실제 141GB HBM 확인
- CPU RAM, `/dev/shm`, 로컬 임시 디스크, 마운트 용량 확인
- CUDA, driver, PyTorch의 Hopper 호환 확인

### Gate B: 모델 로드

- 공식 BF16 text-only load 성공
- `use_cache=false`, gradient checkpointing 동작 확인
- 2K synthetic batch forward/backward 성공

### Gate C: LoRA 도구 선택

- Unsloth, Swift 또는 LLaMA-Factory 중 Qwen3.8-27B single-H200 smoke test 성공
- target module 목록과 trainable parameter 수 확인
- vision과 MTP가 의도대로 freeze 또는 제외됐는지 확인

### Gate D: 데이터 계약

- 학습 샘플의 입력·출력 경계를 확정
- 공개 가능한 데이터만 사용
- 평가 세트가 학습 세트 및 동일 작품 문맥에 누출되지 않도록 분리
- 한국어 문체, 연속성, 역사 사실성 지표 확정

### Gate E: 100~500 sample pilot

- 8K sequence에서 peak VRAM과 tokens/sec 측정
- 저장 후 adapter 재로드 확인
- base 대비 품질 회귀와 과적합 확인
- 충분한 개선이 있을 때만 전체 데이터 학습으로 확대

## 10. 최종 판정

```text
H200에 모델을 올릴 수 있는가?                 예
H200 한 장으로 LoRA 파인튜닝할 수 있는가?       예, 가능성이 높음
27B full fine-tuning이 가능한가?                현실적으로 아니오
링크의 GGUF를 그대로 학습하는 것이 좋은가?       아니오
Aggressive GGUF에서 반드시 시작할 수 있는가?      Q8 역양자화 실험은 가능, 비권장
권장 출발점은 무엇인가?                         공식 BF16 Safetensors + text LoRA
```

따라서 다음 행동은 대규모 다운로드나 본 학습이 아니라, H200 세션에서 환경·로드·2K backward를 검증하는 최소 smoke test 설계다. 그 결과를 확인한 뒤 모델 비교 평가와 데이터셋 설계로 넘어가야 한다.
