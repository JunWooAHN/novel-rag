# Gemma 4 31B Heretic 웹소설 문체 파인튜닝 심층 조사 v0.2

- 작성일: 2026-09-08
- 목표 모델 계보: `Stabhappy/gemma-4-31B-it-heretic-Gguf`
- 목표: 사용자가 보유한 한국어 웹소설로 사용자의 문체를 재현하면서 SQLite 역사·벡터 DB의 근거를 지키는 장편 생성 모델
- 하드웨어 가정: KT Cloud AI Nexus, NVIDIA H200 141GB 1장
- 접근 원칙: 기존 프로젝트 설계·기존 파인튜닝 계획·다른 모델 결정을 전제로 하지 않고 처음부터 재검토
- 문서 성격: 의사결정용 조사 보고서. 모델 다운로드·데이터 가공·학습은 아직 시작하지 않음

## 1. 결론부터

가능하다. 다만 **Stabhappy의 GGUF 파일을 직접 학습하는 방식은 아니다.**

권장 흐름은 다음과 같다.

```text
coder3101/gemma-4-31B-it-heretic (BF16 Safetensors)
  -> text-only BF16 LoRA 문체 SFT
  -> 장편·문체·복제 평가
  -> LoRA adapter 보존
  -> 필요 시 base와 merge
  -> 새 GGUF로 변환·양자화
  -> Stabhappy GGUF 및 원본 Heretic과 동일 조건 비교
```

핵심 판단은 다음과 같다.

| 쟁점 | 판단 |
|---|---|
| 정확한 학습 원본 | `coder3101/gemma-4-31B-it-heretic` BF16 Safetensors |
| Stabhappy GGUF 직접 학습 | 제외 |
| 1차 학습법 | text-only, completion-focused BF16 LoRA SFT |
| sequence length | 4K smoke test → 8K 기본 후보 → 필요한 경우 16K 검증 |
| BF16 LoRA가 16K에서 OOM | NF4 + BF16 compute QLoRA로 전환 |
| full fine-tuning | 단일 H200에서는 제외 |
| raw 소설 continued pretraining | SFT와 분리한 2차 대조 실험 |
| DPO | 실제 선호쌍이 축적된 뒤에만 시행 |
| DB의 역할 | 역사와 작품 정사를 가중치에 암기시키지 않고 생성 시점에 검색·주입 |
| 첫 adapter의 역할 | 근거 패킷을 받아 웹소설 본문 작성. 설정 추출·역사전표·검수 역할은 섞지 않음 |
| 성공 판정 | 문체 + DB 근거 준수 + 장편 일관성 + 반복 + train 원문 복제 검사 |

`uncensored` 또는 Heretic이라는 사실은 문체, 한국어 자연스러움, 장기 일관성을 보장하지 않는다. 따라서 학습 전에도 원본 Heretic과 공식 Gemma 4 IT를 같은 프롬프트로 비교해야 한다.

## 2. 우리가 실제로 다루는 모델

확인된 계보는 다음과 같다.

```text
google/gemma-4-31B
  -> google/gemma-4-31B-it
  -> coder3101/gemma-4-31B-it-heretic
  -> Stabhappy/gemma-4-31B-it-heretic-Gguf
```

Stabhappy 저장소는 `coder3101` 체크포인트를 GGUF로 양자화한 추론 배포물이다. 언어모델 파일은 Q4_0 약 17.7GB에서 Q8_0 약 32.6GB까지이며, 별도 vision projector도 들어 있다. 저장소 README는 사실상 비어 있고 변환에 사용한 source revision SHA도 고정하지 않는다. 따라서 현재 `coder3101`의 `main`과 Stabhappy GGUF가 bit-identical한 원본에서 만들어졌다고 단정할 수 없다. [Stabhappy 모델](https://huggingface.co/Stabhappy/gemma-4-31B-it-heretic-Gguf), [파일 목록](https://huggingface.co/Stabhappy/gemma-4-31B-it-heretic-Gguf/tree/main), [모델 API](https://huggingface.co/api/models/Stabhappy/gemma-4-31B-it-heretic-Gguf)

반면 `coder3101/gemma-4-31B-it-heretic`에는 두 개의 BF16 Safetensors shard, config, tokenizer, processor, chat template가 모두 있다. 총 가중치 크기는 약 62.6GB이며 adapter가 아니라 full checkpoint다. 이것이 같은 Heretic 계보에서 가장 보존도가 높은 공개 학습 출발점이다. [coder3101 모델 카드](https://huggingface.co/coder3101/gemma-4-31B-it-heretic), [Safetensors 파일 목록](https://huggingface.co/coder3101/gemma-4-31B-it-heretic/tree/main)

제작자 설명에 따르면 이 체크포인트는 `google/gemma-4-31B-it`에 Heretic v1.2.0의 Arbitrary-Rank Ablation을 적용한 full-weight 변형이다. 모델 카드의 KL divergence와 refusal 수치는 제작자 자기보고이며, 한국어 소설 품질이나 장편 안정성 검증은 아니다. [Heretic 프로젝트](https://github.com/p-e-w/heretic)

### 왜 GGUF를 다시 학습하지 않는가

GGUF는 주로 llama.cpp 계열 추론용 단일 파일 형식이다. 현행 llama.cpp 학습 코드는 FP32 소형 모델과 제한된 환경을 대상으로 한 WIP라고 명시한다. Transformers가 일부 GGUF를 역양자화할 수는 있지만, Q4~Q8에서 잃은 정밀도가 원 BF16으로 복구되지는 않는다. Gemma 4 multimodal GGUF를 역양자화하여 PEFT 학습하고 다시 GGUF로 왕복하는 이 정확한 경로도 공식 검증 사례가 없다. [llama.cpp training 현황](https://github.com/ggml-org/llama.cpp/blob/master/examples/training/README.md), [Transformers GGUF 문서](https://huggingface.co/docs/transformers/main/quantization/gguf)

따라서 GGUF 역양자화는 원본 Safetensors가 사라졌을 때의 구조 실험이지, 이번 작업의 주경로가 아니다.

## 3. H200 141GB 한 장에서 가능한가

### 3.1 full fine-tuning은 제외

Gemma 4 31B의 공개 파라미터 수 30.7B를 사용하면 일반 BF16 + FP32 AdamW 전체 학습의 정적 모델 상태 하한은 다음과 같다.

```text
BF16 weights          약 61.4GB
BF16 gradients        약 61.4GB
FP32 Adam m/v         약 245.6GB
--------------------------------
합계 하한             약 368.4GB
activation/temp       별도
```

일부 구현은 FP32 master weight까지 추가한다. 8-bit optimizer로 optimizer 상태를 크게 줄여도 activation을 넣기 전 약 184GB 수준이므로 H200 141GB 한 장에는 맞지 않는다. bitsandbytes도 8-bit optimizer가 optimizer 상태 메모리를 줄이는 방법이지 activation 문제까지 없애는 방법은 아니라고 설명한다. [bitsandbytes 8-bit optimizer](https://huggingface.co/docs/bitsandbytes/main/optimizers)

### 3.2 BF16 LoRA가 1순위

BF16 LoRA는 약 61GB의 base weight를 동결하고 작은 저랭크 adapter만 학습한다. H200 141GB라면 4K와 8K는 가능성이 높으며, 16K는 gradient checkpointing, fused attention, 데이터 길이 분포, LoRA target 범위에 따라 조건부로 가능하다. LoRA는 base weight를 고정하고 저랭크 행렬만 학습하여 학습 파라미터와 optimizer 상태를 줄이는 방법이다. [LoRA 논문](https://arxiv.org/abs/2106.09685)

권장 초기 프로파일은 다음과 같다.

| 항목 | 1차 설정 |
|---|---|
| base | `coder3101/gemma-4-31B-it-heretic` |
| dtype | BF16 |
| modality | text-only |
| method | LoRA SFT |
| micro batch | 1 |
| effective batch | gradient accumulation으로 조정 |
| length | 4,096 → 8,192 → 필요 시 16,384 |
| gradient checkpointing | 사용 |
| model cache | `use_cache=False` |
| attention | 우선 PyTorch SDPA, 이후 FlashAttention 비교 |
| loss | assistant/completion prose token만 |
| checkpoint | resume용 최근 2개 + 최종 adapter 별도 보존 |

Gemma 4는 60개 layer, 30.7B dense 모델이며 최대 context는 256K다. 그러나 “256K를 지원한다”와 “256K로 학습하는 것이 필요하거나 경제적이다”는 다른 이야기다. global attention layer의 비용과 262K vocabulary의 logits 메모리 때문에 긴 sequence에서 activation과 logits가 병목이 된다. batch 1의 BF16 full logits만 단순 계산해도 4K/8K/16K에서 약 2.1/4.3/8.6GB다. [Gemma 4 공식 모델 카드](https://ai.google.dev/gemma/docs/core/model_card_4), [Transformers Gemma 4 문서](https://huggingface.co/docs/transformers/model_doc/gemma4)

gradient checkpointing은 activation을 재계산하는 대신 메모리를 줄이며 속도 비용이 있다. PyTorch SDPA는 조건에 맞으면 fused backend를 고르지만 실제 선택 여부는 실행 로그와 peak VRAM으로 검증해야 한다. [Transformers Trainer](https://huggingface.co/docs/transformers/en/main_classes/trainer), [PyTorch SDPA](https://docs.pytorch.org/docs/stable/generated/torch.nn.functional.scaled_dot_product_attention.html)

### 3.3 QLoRA는 16K 안전 대안

BF16 LoRA 16K가 OOM이거나 더 긴 sequence가 반드시 필요하면 다음 단계는 QLoRA다.

```text
load_in_4bit = true
quant type   = NF4
double quant = true
compute      = BF16
train        = LoRA adapter only
```

QLoRA는 4-bit NormalFloat와 double quantization으로 동결 base의 메모리를 줄이고 LoRA adapter를 학습한다. Google도 Gemma 4 31B를 선택할 수 있는 공식 Transformers + TRL + PEFT QLoRA 예제를 제공한다. [QLoRA 논문](https://papers.neurips.cc/paper_files/paper/2023/file/1feb87871436031bdc0f2beaa62a049b-Paper-Conference.pdf), [Google Gemma QLoRA 가이드](https://ai.google.dev/gemma/docs/core/huggingface_text_finetune_qlora), [PEFT 양자화 가이드](https://huggingface.co/docs/peft/developer_guides/quantization)

H200의 메모리를 고려하면 처음부터 QLoRA로 품질·속도 변수를 추가할 필요는 없다. **8K BF16 LoRA를 기준선으로 삼고, 동일 데이터의 소규모 QLoRA 대조군을 만든 뒤 16K가 필요한 경우에만 전환**하는 것이 해석하기 쉽다.

### 3.4 text-only로 한정

Gemma 4는 text와 image를 받을 수 있지만 이번 목표에는 vision tower가 필요 없다. vision tower와 projector는 삭제하기보다 freeze하고, LoRA target을 language model layer로만 한정한다. PEFT에는 Gemma 4 language layer용 기본 target이 있으나, vision의 `Gemma4ClippableLinear`까지 `all-linear`로 잡으면 실패할 수 있다는 upstream 이슈가 있다. 따라서 실제 `named_modules()`와 trainable parameter 목록을 학습 전에 출력해 검증해야 한다. [PEFT target mapping](https://github.com/huggingface/peft/blob/main/src/peft/utils/constants.py), [PEFT Gemma 4 vision LoRA 이슈](https://github.com/huggingface/peft/issues/3130)

## 4. ‘내 문체’를 무엇으로 학습할 것인가

문체 학습과 세계관 기억, 줄거리 계획, 사실 추출은 같은 문제가 아니다. 첫 adapter의 목표는 아래 한 문장으로 좁히는 편이 좋다.

> 주어진 직전 문맥, 장면 조건, SQLite에서 컴파일된 역사·정사 근거를 받아, 그 근거를 위반하지 않으면서 사용자의 웹소설 문체로 다음 장면 또는 한 화의 본문을 작성한다.

초기 adapter에 JSON 역사전표 추출, 설정 DB 갱신, 비평, 교정까지 섞으면 출력 형식과 문체 loss가 충돌한다. 이 역할들은 추후 별도 adapter나 외부 파이프라인으로 분리한다.

### 4.1 권장 1차 데이터: 실제 문맥 → 실제 다음 장면

사용자가 가진 원고가 raw 본문뿐이어도 synthetic 소설을 만들 필요는 없다. 작품의 자연스러운 경계를 사용해 다음 형태의 pair를 만든다.

```json
{
  "messages": [
    {
      "role": "system",
      "content": "한국어 웹소설 본문을 작성한다. 설명이나 분석 없이 본문만 출력한다."
    },
    {
      "role": "user",
      "content": "[작품 메타]\n장르: 대체역사\n시점: 3인칭 제한\n\n[정사 근거]\nCANON-FACT-0041: 문종은 1453-10-12 현재 생존\nORIG-EVENT-Q123: 원역사의 사망 사건은 prevented\nKNOWLEDGE-017: 주인공은 이 사실을 알고 있음\n\n[직전 문맥]\n...실제 앞 장면...\n\n[요청]\n근거를 위반하지 말고 바로 다음 장면을 이어서 작성하라."
    },
    {
      "role": "assistant",
      "content": "...사용자가 실제로 쓴 다음 장면..."
    }
  ]
}
```

학습 loss는 assistant의 실제 본문에만 적용한다. TRL의 prompt-completion/conversational dataset과 `completion_only_loss` 또는 label `-100` masking을 사용할 수 있다. [TRL SFTTrainer](https://huggingface.co/docs/trl/sft_trainer)

이 형식의 장점은 세 가지다.

- 실제 집필 시 입력인 “직전 문맥 → 다음 장면”과 훈련 형식이 같다.
- 목표 문체는 사용자의 실제 문장만에서 loss를 받는다.
- 장면·화 경계를 보존하면서 대화, 서술, 후킹의 리듬을 학습할 수 있다.

개요→한 화 생성이 최종 목표라면, 사용자가 실제로 사용했던 플롯 메모·시놉시스가 있는 샘플만 별도 유형으로 추가한다. 완성 원고를 보고 LLM이 사후에 만든 개요는 target의 표현을 유출할 수 있으므로 원본 개요와 구분하여 provenance를 기록한다.

### 4.2 raw continued pretraining은 별도 실험

raw 본문을 next-token 방식으로 계속 사전학습하는 DAPT는 어휘 분포와 문장 리듬을 학습하는 후보지만, instruction 입력에 맞추는 효과는 직접 보장하지 않는다. in-domain continued pretraining의 효과는 널리 보고됐지만, 근거 연구의 과제가 한국어 장편 문체 모사는 아니다. [Don’t Stop Pretraining](https://arxiv.org/abs/2004.10964)

따라서 첫 실험부터 DAPT와 SFT를 섞지 않는다.

```text
A: untouched Heretic
B: Heretic + completion-only SFT
C: Heretic + 짧은 DAPT
D: Heretic + 짧은 DAPT + 동일 SFT
```

우선 A와 B로 문체 SFT의 순효과를 확인한다. 데이터가 충분하고 B의 문체 변화가 약할 때만 C/D를 추가한다.

### 4.3 DPO는 처음부터 하지 않는다

DPO는 같은 prompt에 대해 `chosen`과 `rejected`가 있을 때 사람의 선호를 학습한다. 원고만 보유한 상태에서는 자연스럽게 생기는 pair가 없다. SFT 모델의 여러 출력 중 사용자가 더 자기다운 문장을 고른 기록이 충분히 쌓인 뒤, 반복·번역투·과잉 설명·인물 말투 붕괴를 rejected로 삼는 2차 단계가 적합하다. [DPO 논문](https://arxiv.org/abs/2305.18290)

## 5. SQLite 역사·벡터 DB를 사용하는 생성 구조

기존 SQLite 논의에서 확정한 원칙을 그대로 따른다.

```text
original.sqlite                     작품별 canon.sqlite
불변에 가까운 현실 역사       +     공개된 단일 개변 정사
구조화 사실·사건·관계               사건·fact ledger·override·인물 지식
FTS5 + sqlite-vector                 작품 기억 vector + 최근 delta
```

구조화된 사실·사건·역사전표가 진실의 원본이며 벡터는 검색용 파생 데이터다. 작품 정사는 여러 영구 세계선으로 분기하지 않고 공개된 화가 하나의 선형 정사에 누적된다. 자세한 기준은 [SQLite 정사 구조 검토 보고서](/Users/ahnjunwoo/dev/novel/docs/reports/20260908-alternate-history-sqlite-canon-report-v0-1.md)에 정리돼 있다.

### 5.1 역할 분리

파인튜닝된 Gemma에 위키백과 전체 역사와 작품 정사를 다시 암기시키지 않는다.

| 구성 요소 | 책임 |
|---|---|
| `original.sqlite` | 현실 역사, 출처, 시공간 범위, 사건·관계 제공 |
| `canon.sqlite` | 공개된 작품 사건, 현재 상태, original override, 인물별 지식 제공 |
| FTS5/vector 검색 | 현재 장면과 의미상 관련된 후보를 넓게 찾음 |
| overlay resolver | `active/contested/overridden`를 계산해 현재 작품 세계의 유효 사실 확정 |
| context compiler | 검색 결과를 짧고 구조화된 근거 패킷으로 변환 |
| Gemma writer | 근거 패킷과 집필 계약을 문체가 적용된 본문으로 렌더링 |
| verifier | 생성문에서 사건·상태를 추출해 DB 근거 및 앵커와 대조 |
| 사람 | 최종 수정·공개 승인 및 역사전표 정사 편입 |

Gemma는 역사 DB의 최종 판정자도, 정사 DB의 직접 작성자도 아니다. 본문과 `history-delta` 후보를 만들 수는 있지만 공개 정사 반영은 별도 검증과 SQLite transaction이 담당한다.

### 5.2 회차 생성 폐루프

```text
chapter contract + 현재 story time + 등장인물
        │
        ▼
structured SQL filter
  - 현재 유효 canon facts
  - 인물별 knowledge ledger
  - original override 상태
        │
        ▼
FTS5 / sqlite-vector 후보 검색
  - 관련 현실 역사 근거
  - 앞선 화의 서술 기억
        │
        ▼
rerank + overlay resolution + context compile
        │
        ▼
Gemma 4 writer: 한 장면 또는 한 화 생성
        │
        ▼
사실·사건 추출 → 정사/앵커 대조
        │
        ├─ 통과 → 사람 검수 → 공개 → history-delta를 canon에 transaction 반영
        └─ 실패 → 부족한 근거 재검색 → 해당 구간만 재작성
```

문장 하나를 생성할 때마다 DB를 호출하지 않는다. 장면 시작 전 한 번 근거 패킷을 만들고 대략 한 장면 단위로 생성한 뒤 검증한다. 문장별 검색은 latency를 늘리고 문체 호흡을 깨뜨리며, 중간 검색 결과가 바뀌어 장면 내부의 전제가 흔들릴 수 있다. 새 인물·사건·시대로 넘어갈 때만 다음 패킷을 만든다.

### 5.3 검색 순서: SQL이 먼저, vector가 다음

벡터 유사도가 높다는 이유만으로 사실로 채택하면 안 된다. 권장 검색 순서는 다음과 같다.

1. story time, 지역, 등장인물, anchor, 현재 canon revision으로 SQL 필터를 건다.
2. `canon.sqlite`에서 공개된 사건·활성 fact·인물 지식을 가져온다.
3. `original_overrides`를 적용해 원역사 사건을 `active`, `contested`, `overridden`으로 분류한다.
4. 남은 범위에서 FTS5와 `sqlite-vector`로 관련 설명·선행 사건·서술 기억 후보를 찾는다.
5. reranker로 top-N을 줄이고, 구조화 행과 provenance를 다시 붙인다.
6. 서로 모순되는 후보는 context compiler가 숨기지 말고 `contested`로 표시한다.

즉 vector 검색은 recall을 높이고, 구조화 SQL과 overlay resolver가 truth를 결정한다.

### 5.4 Gemma에 전달할 근거 패킷

근거 패킷은 raw DB row나 위키 문서 수십 개를 그대로 붙이는 것이 아니라 다음 고정 섹션으로 컴파일한다.

```text
[WRITING_CONTRACT]
- 이번 장면의 목적, POV, 분량, 금지사항
- 고정 앵커와 허용 가능한 가이드라인

[CANON_FACTS — HARD]
- fact/event ID, 현재 값, 유효 시점, 근거 chapter/revision

[ORIGINAL_HISTORY]
- original ID, 사건/인물 요약, 날짜, 출처
- status: active | contested | overridden

[CHARACTER_KNOWLEDGE — HARD]
- POV 인물이 현재 아는 것과 모르는 것

[NARRATIVE_MEMORY]
- 앞선 화의 관련 약속·복선·관계 변화
- vector 결과에는 source chapter와 similarity/rerank score 포함

[RECENT_PROSE]
- 바로 앞 문단 또는 장면 원문

[SCENE_TASK]
- 이번에 써야 할 장면
```

`CANON_FACTS`, `CHARACTER_KNOWLEDGE`, 고정 anchor는 hard constraint다. `ORIGINAL_HISTORY`의 `active`는 기준 사실, `contested`는 불확실성, `overridden`은 사용 금지 또는 대체 사실 참조다. `NARRATIVE_MEMORY`와 vector 검색 결과는 soft evidence이며 정사와 충돌하면 버린다.

근거 패킷에는 항상 ID와 유효 시점을 남긴다. 그래야 생성 뒤 “어느 근거를 위반했는가”를 기계적으로 보고하고 재작성할 수 있다.

### 5.5 파인튜닝 데이터도 실제 근거 패킷을 닮아야 한다

추론 때만 DB 근거를 넣고 학습 때는 순수 이어쓰기만 시키면 모델이 구조화 근거를 무시할 수 있다. 문체 SFT sample의 user 입력에도 production과 같은 섹션과 상태 표현을 사용한다.

- 과거 원고 시점의 canon을 역사전표에서 재생하여 당시 사용 가능했던 사실만 넣는다.
- target 장면 이후에 확정된 사실을 prompt에 넣지 않는다. 이는 미래 정보 누수다.
- target 본문과 관련 없는 DB 후보를 소량 포함해 중요한 근거를 골라 쓰는 능력도 평가한다.
- hard constraint를 위반하는 distractor는 명시적으로 `overridden` 또는 `contested`로 표시한다.
- prompt와 근거 패킷은 loss에서 제외하고 사용자가 쓴 assistant prose만 학습한다.
- 작가 원문 자체를 style exemplar로 vector 검색해 prompt에 반복 주입하는 것은 피한다. 문체는 adapter가 담당하고, vector DB는 역사·정사·서사 기억을 공급한다. 원문 exemplar 주입은 복제 위험과 context 낭비를 키운다.

첫 dataset에서 정확한 DB snapshot을 재구성하기 어렵다면 두 단계를 분리한다. 우선 `recent prose + 최소 canon facts → next scene`으로 문체를 학습하고, 그 다음 실제 context compiler 출력 형식으로 작은 grounding SFT를 추가한다. 허구로 만든 역사 근거를 대량 합성해 문체 SFT와 섞는 것은 권장하지 않는다.

### 5.6 생성 전후의 책임 경계

생성 전 context compiler가 처리해야 하는 것:

- 중복 제거와 token budget 할당
- 날짜·인물·지역 범위 제한
- original/canon overlay 계산
- 인물별 knowledge 제한
- source ID와 불확실성 표시

Gemma writer가 처리해야 하는 것:

- hard constraint를 자연스러운 장면과 문장으로 표현
- 근거에 없는 세부를 창작할 때 기존 사실과 충돌하지 않기
- DB 용어와 ID를 본문에 노출하지 않기

생성 후 verifier가 처리해야 하는 것:

- 새 사건·상태 변화·인물 지식 후보 추출
- hard constraint 위반과 시대착오 탐지
- 원문·이전 화의 장문 복제 및 반복 탐지
- `history-delta` 제안 생성

### 5.7 이 구조가 파인튜닝 목표를 바꾸는 부분

파인튜닝의 성공은 단순한 저자 유사도가 아니다. 같은 근거 패킷을 주었을 때 다음 네 가지를 동시에 만족해야 한다.

1. 사용자의 문체로 쓴다.
2. `canon.sqlite`의 hard fact와 인물 지식을 어기지 않는다.
3. 원역사 `overridden` 사건을 사실처럼 되살리지 않는다.
4. 근거 패킷이 부족할 때 임의의 핵심 사실을 확정하지 않는다.

따라서 untouched Heretic과 문체 LoRA를 비교할 때 동일한 retrieval packet을 사용하고, 문체 점수와 grounded fact violation rate를 별도로 측정한다.

## 6. 장편 데이터셋 설계

### 6.1 먼저 보존할 구조

원고를 token window로 자르기 전에 다음 계층을 보존한다.

```text
author
  └─ work
      └─ volume / arc
          └─ episode / chapter
              └─ scene
                  └─ paragraph
```

각 sample에는 최소한 다음 metadata를 남긴다.

- `author_id`, `work_id`, `volume_id`, `chapter_id`, `scene_id`
- 원문 파일과 문자 offset 또는 paragraph 범위
- 집필/공개 순서
- 장르, POV, 시제, 주요 화자
- 앞 문맥과 target의 token 수
- 데이터 권리와 출처
- 사람이 쓴 원문인지, 후편집인지, AI 보조인지

이 provenance가 있어야 누수·복제·작품 편향을 추적할 수 있다.

### 6.2 split은 작품·권·연재 구간 단위

인접 window를 random train/validation split하면 같은 장면의 앞뒤 문장이 양쪽에 들어가 평가가 무의미해진다. 권장 우선순위는 다음과 같다.

1. 여러 작품이 있다면 작품 전체를 held-out test로 둔다.
2. 작품 수가 적다면 마지막 권 또는 마지막 연재 구간 전체를 test로 둔다.
3. validation도 별도 권·arc·시간 구간으로 분리한다.
4. 동일 장면에서 파생된 모든 window는 한 split에만 둔다.

중복 데이터는 암기와 train/test 오염을 늘린다. 공개본/수정본/플랫폼 mirror, 회차 말미의 다음 화 예고, 이전 화 요약, 작가의 말 반복을 exact 및 near-duplicate 단계에서 처리해야 한다. [Deduplicating Training Data Makes Language Models Better](https://arxiv.org/abs/2107.06499)

### 6.3 길이는 데이터 분포로 결정

무조건 16K 또는 256K로 학습할 이유는 없다. 권장 데이터 혼합의 출발점은 다음과 같다.

| 유형 | 대략적 total tokens | 목적 |
|---|---:|---|
| 짧은 장면 | 2K–4K | 대화·문장 리듬·장면 전환 |
| 일반 장면/화 | 4K–8K | 기본 문체와 화 단위 전개 |
| 긴 화/다중 장면 | 8K–16K | 인물 말투와 장면 간 지속성 |
| long-context probe | 16K 이상 소수 | 긴 문맥 사용 능력 평가, 필요 시 후속 학습 |

실제 원고의 token 길이 histogram을 낸 뒤 8K가 대부분을 덮으면 8K가 경제적인 기본값이다. 고정 16K padding은 피하고, compatible한 FlashAttention을 쓸 때 document boundary를 보존하는 packing을 검토한다. [TRL 메모리 절감 가이드](https://huggingface.co/docs/trl/reducing_memory_usage)

### 6.4 Gemma 4 thinking/channel 처리

31B IT 모델은 thinking channel을 지원한다. Google은 no-thinking 데이터로 31B를 fine-tune할 때 model response 시작에 빈 thought channel을 두는 형식을 권장한다. 이전 turn의 raw thought는 다음 입력 history에서 제거해야 한다. 소설 본문 학습에서는 생각 과정을 target에 넣지 않고 빈 thought block 뒤 final prose만 loss 대상으로 삼는 것이 안전하다. 반드시 체크포인트가 제공하는 official processor/chat template를 사용하고 특수 token 문자열을 손으로 이어 붙이지 않는다. [Gemma 4 prompt formatting](https://ai.google.dev/gemma/docs/core/prompt-formatting-gemma4)

## 7. 첫 실험의 권장 순서

이것은 아직 구현 계획이 아니라, 어떤 순서로 불확실성을 줄일지에 대한 연구 결론이다.

### Gate 0 — 데이터와 권리

- 작품별 저작권자, 출판·플랫폼 계약, 학습·모델 배포 가능 범위를 확인한다.
- 실존 인물의 개인정보와 실제 사연이 섞였는지 검사한다.
- 작품/권/화/장면 구조를 복원하고 중복을 제거한다.
- tokenizer 기준 token 수와 길이 분포를 계산한다.
- `original + canon overlay`의 질의 결과와 근거 패킷 schema를 먼저 고정한다.

### Gate 1 — 학습 전 baseline

같은 30~50개 held-out prompt와 동일한 DB 근거 패킷으로 최소 다음을 비교한다.

- `google/gemma-4-31B-it`
- `coder3101/gemma-4-31B-it-heretic`
- Stabhappy Q8_0 GGUF

이 비교에서 Heretic이 한국어 문장력이나 반복 안정성을 크게 잃었다면, “거부가 적다”는 이유만으로 고정하지 않는다. 학습이 base model의 결함을 가리는 데 쓰이면 안 된다.

### Gate 2 — 100~500 sample 파이프라인 smoke test

- 정확한 pinned revision으로 Safetensors를 받는다.
- text-only model load, chat template, empty thought channel을 검증한다.
- trainable module과 parameter 수를 출력한다.
- SQLite snapshot에서 근거 패킷을 재현하고 prompt token이 loss에서 가려지는지 검사한다.
- 4K에서 forward/backward/save/reload/generate 전 과정을 수행한다.
- 수십 step 동안 loss, tokens/s, peak VRAM, sample generation을 기록한다.

### Gate 3 — 짧은 문체 LoRA 대조 실험

- 동일 데이터로 rank와 LR을 넓게 훑지 말고 작은 두세 조건만 비교한다.
- 우선 BF16 LoRA 8K를 기준으로 한다.
- QLoRA는 동일 sample의 대조군 또는 16K OOM fallback으로 둔다.
- train step 기준이 아니라 본 token 수와 전체 corpus 반복 횟수를 기록한다.

### Gate 4 — 전체 SFT 및 장편 평가

- validation loss만으로 checkpoint를 고르지 않는다.
- 고정된 held-out prompt에서 문체·가독성·DB 근거 준수·일관성·복제·반복 scorecard를 사용한다.
- 통과한 adapter만 merge/GGUF 변환한다.

### Gate 5 — 선택적 DAPT/DPO

- SFT만으로 문체가 약할 때 DAPT control arm을 추가한다.
- 실제 사용자 선호 데이터가 쌓였을 때 DPO를 추가한다.
- 각 단계는 이전 단계와 같은 평가셋으로 비교한다.

## 8. 성공 기준

자동 점수 하나로 ‘내 문체’를 판정할 수 없다. 다음 다섯 축을 분리한다.

### 8.1 문체 유사도

- 사용자가 저자 원문, base 출력, fine-tuned 출력을 모른 채 pairwise 선택
- 문장 길이 평균·분산, 문장 종결, 조사, 구두점, 기능어
- 대화/서술 비율, POV, 비유 밀도, 단락 리듬, 화 끝 hook
- 장르나 소재가 같아서 비슷해 보이는 것과 실제 문체 유사성을 분리

### 8.2 읽기 품질

- 한국어 자연스러움과 번역투
- 문법, 호흡, 몰입, 정보 전달, 장면의 감정 곡선
- 평균뿐 아니라 가장 나쁜 10% sample을 별도 확인

### 8.3 장편 일관성

- 1K/8K/16K 문맥에서 인물 성격·말투·관계 유지
- 시점, 시간선, 장소, 소지품, 부상 상태 유지
- 미해결 플롯과 복선의 회수
- 같은 내용을 다른 말로 반복하거나 설정을 재설명하는지

256K context나 needle retrieval benchmark 점수가 서사 일관성을 보장하지는 않는다.

### 8.4 DB 근거 준수

- hard canon fact 위반 건수
- `overridden` 원역사 사건을 되살린 건수
- POV 인물이 모르는 정보를 말하거나 생각한 건수
- 근거 ID별 entailment/contradiction 판정과 사람 재검수
- 동일 prompt에서 retrieval packet 한 항목을 바꾸었을 때 본문도 올바르게 바뀌는지 확인

DB 근거 준수 평가는 역사 지식을 모델이 원래 알고 있는지 측정하는 시험이 아니다. **제공된 현재 정사를 우선해 사용하는 능력**을 측정한다. 공식 Gemma, Heretic, 문체 LoRA 모두 동일한 근거 패킷으로 비교한다.

### 8.5 암기·복제

- 생성 문장을 train corpus에서 exact/normalized n-gram 검색
- semantic nearest-neighbor로 완곡한 복제 후보 검색
- train 문단의 짧은 prefix만 줬을 때 장문을 그대로 재현하는지 검사
- 전화번호·이메일·주소 등 PII 출력은 zero tolerance

중복 제거는 memorized output 가능성을 줄이는 것으로 보고돼 있다. [Google Research의 deduplication 요약](https://research.google/pubs/deduplicating-training-data-makes-language-models-better/)

### 8.6 반복 붕괴

- unique n-gram ratio, 반복 문장·문단, loop 길이, EOS 실패
- 1K/8K/16K generation에서 같은 decoding 설정 사용
- 자동 반복률과 사람이 읽은 서사 품질을 함께 기록

Gemma 4 31B의 장문 생성에서 반복·word doubling이 발생한다는 공개 upstream 이슈가 있으므로 독립 gate로 둔다. 이는 사용자 모델의 확정 결함이 아니라 재현 여부를 확인해야 하는 community report다. [Gemma issue #622](https://github.com/google-deepmind/gemma/issues/622)

## 9. 권리와 개인정보

“내가 가지고 있는 웹소설”이 다음 중 무엇인지가 실행 전 필수 조건이다.

- 사용자가 직접 창작했고 학습·모델 사용 권리를 보유한 원고
- 공동 저작 또는 출판사·플랫폼 계약이 걸린 원고
- 구매·수집했지만 타인이 저작권을 가진 작품
- 여러 작가의 작품을 섞은 자료

파일을 보유했다는 사실만으로 학습과 파생 모델 배포 권리를 가정할 수 없다. 특히 제3자 작품이라면 계약, 이용 범위, 출력의 실질적 유사성을 별도로 검토해야 한다. 한국저작권위원회도 생성형 AI 출력이 기존 작품의 구조·특성을 모방해 동일·유사한 결과를 낼 위험과 접근 가능성·실질적 유사성 판단을 설명한다. [한국저작권위원회 생성형 AI 저작권 분쟁 예방 안내서](https://www.copyright.or.kr/eng/doc/etc_pdf/Guide_to_Preventing_Copyright_Disputes_Related_to_Generative_AI_Outputs.pdf)

공개돼 있던 개인정보도 자동으로 자유로운 학습 데이터가 되는 것은 아니다. 실명, 전화번호, 이메일, 주소, 실제 사연과 민감정보는 사전에 탐지하여 삭제·가명화하고 원문·dataset·checkpoint·로그 접근을 통제해야 한다. [개인정보보호위원회 공개 개인정보 처리 안내](https://pipc.go.kr/np/cop/bbs/selectBoardArticle.do?bbsId=BS210&mCode=C020020000&nttId=10665)

모델 측에서는 공식 Gemma 4와 `coder3101` 저장소가 Apache-2.0을 표기한다. 그러나 Stabhappy GGUF 페이지는 실질적인 README와 독립적인 라이선스 설명이 부족하다. 재배포할 때는 공식·파생 모델의 라이선스 및 고지 파일과 정확한 source revision을 함께 보존해야 한다. Heretic 도구 자체는 AGPL-3.0이고 `coder3101` 모델 카드는 결과 모델을 Apache-2.0으로 표시하므로, 공개 배포 전에는 도구 라이선스와 파생 가중치 고지의 관계도 별도로 확인한다. [공식 Gemma 4 모델](https://huggingface.co/google/gemma-4-31B-it), [coder3101 모델](https://huggingface.co/coder3101/gemma-4-31B-it-heretic), [Heretic 라이선스](https://github.com/p-e-w/heretic)

이 문서는 법률 자문이 아니며, 계약 조건이 있는 원고는 별도 확인이 필요하다.

## 10. 도구 선택

이번 exact model의 첫 구현에는 **최신 Transformers + TRL + PEFT를 명시적으로 고정한 작은 학습 스크립트**가 가장 판단하기 쉽다. Google의 Gemma 4 전용 QLoRA 예제가 이 조합을 사용하고, 어떤 module과 label이 학습되는지 직접 검사할 수 있기 때문이다.

대안은 다음과 같다.

| 도구 | 판단 |
|---|---|
| Transformers + TRL + PEFT | 1순위. Gemma 4 공식 예제와 가까우며 디버깅 투명성이 높음 |
| Axolotl | Gemma 4 31B QLoRA 설정과 multimodal 지침이 있어 강한 2순위 |
| Unsloth | Gemma 4 31B 지원을 발표했으나 exact Heretic checkpoint end-to-end 검증 필요 |
| LLaMA-Factory | 최신 v0.9.5가 Gemma 4를 지원하지만 초기 `mm_token_type_ids` 실패 이력이 있어 smoke test 필수 |
| llama.cpp training | 이번 31B 학습 경로에서 제외. 최종 GGUF 추론·검증에 사용 |

참고: [Axolotl Gemma 4](https://docs.axolotl.ai/docs/models/gemma4.html), [Unsloth Gemma 4](https://unsloth.ai/docs/models/gemma-4), [LLaMA-Factory v0.9.5](https://github.com/hiyouga/LlamaFactory/releases), [LLaMA-Factory issue #10372](https://github.com/hiyouga/LlamaFactory/issues/10372)

버전 번호는 지금 보고서에서 추측해 고정하지 않는다. 실제 H200 session을 만들 때 모델 카드 요구사항, 현재 release compatibility, CUDA/PyTorch 조합을 다시 확인하고 lockfile과 환경 manifest를 남긴다.

## 11. KT Cloud 운영상 주의

첨부된 KT Cloud 가이드에 따르면 환경은 container session이며 Docker-in-Docker를 전제로 할 수 없다. 마운트된 영속 경로는 `/home/work/` 아래에 두고, 세션 삭제 시 사라지는 기본 영역에 모델·dataset·checkpoint를 저장하지 않는다. 4GB 초과 파일은 file browser 또는 SFTP 경로를 사용하며, 최근 6시간 GPU 저활용 회수 조건도 고려해야 한다. [KT Cloud GPU 서비스 사용자 가이드 v1.0](../kt%20cloud%20GPU%20서비스%20사용자%20가이드_v1.0.pdf)

실행 전 확인할 항목은 다음과 같다.

- `nvidia-smi`에서 H200 full 141GB인지, MIG slice가 아닌지
- host driver와 PyTorch CUDA 12.x 호환성
- SDPA가 실제 fused backend를 선택하는지
- `/home/work`의 모델 cache, dataset cache, output 경로와 남은 용량
- 학습 전에 preprocessing·tokenization을 끝내 GPU 유휴 시간을 만들지 않을 것
- 6시간보다 짧은 간격으로 resume 가능한 checkpoint를 남길 것

NVIDIA 문서는 H200의 141GB profile과 Hopper compute capability 9.0을 확인해 준다. 실제 할당이 full profile인지 여부는 클라우드 session 안에서만 확정할 수 있다. [NVIDIA H200 profile](https://docs.nvidia.com/ai-enterprise/release-8/latest/infra-software/vgpu/reference/hopper-h200.html), [NVIDIA CUDA architecture matrix](https://docs.nvidia.com/datacenter/tesla/drivers/cuda-toolkit-driver-and-architecture-matrix.html)

저장공간은 base 62.6GB뿐 아니라 원본 cache, adapter checkpoint, optimizer state, merged BF16 약 62.6GB, GGUF 여러 quant, 평가 output을 함께 고려해야 한다. **최소 250~350GB, 반복 실험까지 고려하면 500GB 안팎의 영속 공간**이 편하다. 이는 실제 checkpoint 정책에 따라 달라지는 운영 추정치다.

## 12. 아직 결정하지 말아야 할 것

다음 값은 원고 통계를 보기 전에 고정하면 안 된다.

- epoch와 total steps
- learning rate
- LoRA rank/alpha와 exact target module
- 8K 대 16K의 최종 선택
- DAPT 적용 여부
- DPO 적용 여부
- train/validation/test 비율
- 최종 GGUF quant
- 근거 패킷의 top-K/top-N과 token budget
- 한 장면당 retrieval refresh 주기

특히 “3 epoch”, “rank 64”, “16K” 같은 숫자를 관행으로 먼저 고르는 대신, 실제 token 수·길이 분포·작품 수·held-out 구조와 작은 대조 실험으로 정해야 한다.

## 13. 다음 대화를 위해 필요한 답

실행 계획을 다시 쓰기 전에 아래 네 가지를 먼저 확정해야 한다.

1. 원고는 전부 사용자가 직접 쓴 작품이며, 학습과 개인용 모델 사용 권리를 사용자가 보유하는가?
2. 작품 수, 총 글자 수 또는 파일 용량, 회차 수, 작품별 대략적인 길이는 얼마인가?
3. 최종 사용 방식은 주로 무엇인가: `직전 문맥 이어쓰기`, `개요/장면표 → 한 화`, `초고 퇴고`, 또는 이들의 조합인가?
4. 한 번에 원하는 생성 길이는 대략 몇 자 또는 몇 token인가?
5. `original.sqlite`와 작품별 `canon.sqlite`가 이미 실제 파일로 존재하는가, 아니면 현재는 설계 단계인가? 실제 파일이 있다면 경로와 schema version은 무엇인가?

이 답을 받은 다음 단계는 **원고를 읽지 않고도 먼저 metadata와 token 통계를 내는 데이터 감사 계획**을 세우는 것이다. 그 결과가 있어야 SFT sample 구성, 8K/16K 선택, 실험 수와 H200 시간 예산을 현실적으로 확정할 수 있다.

## 14. 출처와 신뢰도 메모

본 보고서는 Google/Google DeepMind, Hugging Face, PyTorch, NVIDIA의 공식 문서와 LoRA·QLoRA·DAPT·DPO·deduplication 1차 논문을 우선했다. `coder3101`과 Heretic의 변형 성능은 제작자 자기보고이므로 중간~높은 신뢰도로 취급했고, GitHub issue는 호환성·반복 위험의 재현 후보이지 일반화된 사실로 취급하지 않았다.

확실한 것:

- 공개 BF16 Heretic 체크포인트가 존재한다.
- Stabhappy 저장소는 그 계보의 GGUF 양자화 배포물이다.
- full FT는 H200 141GB 한 장에 맞지 않는다.
- LoRA/QLoRA의 표준 학습 경로와 Gemma 4 공식 QLoRA 예제가 존재한다.

실측이 필요한 것:

- 이 exact Heretic checkpoint의 8K/16K peak VRAM과 tokens/s
- pinned toolchain에서 text-only Gemma 4 collator와 thought channel 처리
- Heretic이 공식 IT보다 실제 한국어 웹소설 baseline에서 나은지
- 사용자의 데이터 규모에서 SFT만으로 충분한지, DAPT가 추가 이득을 주는지
