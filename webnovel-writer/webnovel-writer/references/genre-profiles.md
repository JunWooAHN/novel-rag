# 장르 설정 프로필 (Genre Profiles)

> **정의**: 본 문서는 각 장르의 추독력 설정 파라미터를 정의하며, Step 1.5 / Context Agent / Checkers가 읽을 수 있도록 합니다.
>
> **원칙**: 설정은 "가중치와 제안 조정"에 사용되며, 경직된 판정은 하지 않습니다.
>
> **설명**: xslca.cc 인기 순위 실증 데이터를 기반으로 확장하여, history-travel / game-lit을 신규 추가하고, shuangwen / xianxia / urban-power 핵심 파라미터를 업데이트했습니다.

---

## 1. Profile 필드 설명

### 1.1 핵심 필드

| 필드 | 유형 | 설명 |
|------|------|------|
| `id` | string | 장르 고유 식별자(영문 소문자) |
| `name` | string | 장르 한국어 이름 |
| `description` | string | 한 줄로 핵심 매력 설명 |
| `tags` | string[] | 중첩 가능한 장르 태그(다중 태그 확장 예약) |

### 1.2 훅 설정 (hook_config)

| 필드 | 유형 | 설명 |
|------|------|------|
| `preferred_types` | string[] | 선호 훅 유형(우선순위 순) |
| `strength_baseline` | string | 기본 훅 강도: strong/medium/weak |
| `chapter_end_required` | boolean | 챕터 말미 훅 선호(true=강한 선호, 매 챕터 강제가 아님) |
| `transition_allowance` | number | 전환 챕터 면제 상한(연속 몇 챕터까지 등급 하향 가능) |

### 1.3 쾌감 포인트 설정 (coolpoint_config)

| 필드 | 유형 | 설명 |
|------|------|------|
| `preferred_patterns` | string[] | 선호 쾌감 포인트 패턴(우선순위 순) |
| `density_per_chapter` | string | 챕터당 쾌감 포인트 밀도: high(2+)/medium(1)/low(0-1) |
| `combo_interval` | number | combo 쾌감 포인트 권장 간격(N챕터당 1개 참고) |
| `milestone_interval` | number | 단계적 승리 권장 간격(N챕터당 1개 참고) |

### 1.4 미시 실현 설정 (micropayoff_config)

| 필드 | 유형 | 설명 |
|------|------|------|
| `preferred_types` | string[] | 선호 미시 실현 유형 |
| `min_per_chapter` | number | 챕터당 권장 미시 실현 하한 |
| `transition_min` | number | 전환 챕터 권장 미시 실현 하한 |

### 1.5 리듬 레드라인 (pacing_config)

| 필드 | 유형 | 설명 |
|------|------|------|
| `stagnation_threshold` | number | 리듬 정체 임계값(연속 N챕터 무진행=HARD-003) |
| `strand_quest_max` | number | Quest 메인라인 최대 연속 챕터 수 |
| `strand_fire_gap_max` | number | Fire 감정선 최대 공백 챕터 수 |
| `transition_max_consecutive` | number | 전환 챕터 최대 연속 수 |

### 1.6 제약 면제 (override_config)

| 필드 | 유형 | 설명 |
|------|------|------|
| `allowed_rationale_types` | string[] | 허용되는 Override 사유 유형 |
| `debt_multiplier` | number | 부채 배율(>1은 해당 장르가 더 엄격함을 의미) |
| `payback_window_default` | number | 기본 상환 윈도우(챕터 수) |

---

## 2. 내장 장르 Profiles

### 2.1 쾌감문/시스템류 (shuangwen)

```yaml
id: shuangwen
name: 쾌감문/시스템류
description: 골든핑거 치트, 빠른 템포 레벨업, 허세 응징 원스톱
tags: [shuangwen]

hook_config:
  preferred_types: [갈망 훅, 위기 훅, 감정 훅]
  strength_baseline: medium
  chapter_end_required: true
  transition_allowance: 2

coolpoint_config:
  preferred_patterns: [허세 응징, 돼지 행세 호랑이, 월급 역전, 오해 승격]
  density_per_chapter: high
  combo_interval: 5
  milestone_interval: 10

micropayoff_config:
  preferred_types: [능력 실현, 자원 실현, 인정 실현]
  min_per_chapter: 2
  transition_min: 1

pacing_config:
  stagnation_threshold: 3
  strand_quest_max: 5
  strand_fire_gap_max: 15
  transition_max_consecutive: 2

override_config:
  allowed_rationale_types: [TRANSITIONAL_SETUP, ARC_TIMING]
  debt_multiplier: 1.0
  payback_window_default: 3
```

**장르 특성**:
- 높은 밀도의 쾌감 포인트 추구, 독자가 빠른 템포를 기대
- 챕터 말미에 명확한 기대감 우선 유지(돌파 직전/응징 직전/대박 직전)
- 전환 챕터 허용도가 낮으며, 연속 2챕터를 넘지 않는 것을 권장
- 수치 피드백은 시각화 권장(전투력50→전투력180, 전후 비교)
- 골든핑거는 상한/소모/쿨타임 설정 권장, 무한 사용 방지

---

### 2.2 수선/현환 (xianxia)

```yaml
id: xianxia
name: 수선/현환
description: 운명에 역행, 잔혹한 법칙, 기연과 쟁투가 공존
tags: [xianxia]

hook_config:
  preferred_types: [위기 훅, 갈망 훅, 선택 훅]
  strength_baseline: medium
  chapter_end_required: true
  transition_allowance: 3

coolpoint_config:
  preferred_patterns: [월급 역전, 돼지 행세 호랑이, 정체 폭로, 악역 전복]
  density_per_chapter: high
  combo_interval: 5
  milestone_interval: 15

micropayoff_config:
  preferred_types: [능력 실현, 자원 실현, 정보 실현]
  min_per_chapter: 1
  transition_min: 1

pacing_config:
  stagnation_threshold: 4
  strand_quest_max: 6
  strand_fire_gap_max: 12
  transition_max_consecutive: 3

override_config:
  allowed_rationale_types: [TRANSITIONAL_SETUP, WORLD_RULE_CONSTRAINT, ARC_TIMING]
  debt_multiplier: 0.9
  payback_window_default: 5
```

**장르 특성**:
- 세계관 구축이 필요하여, 더 많은 준비 챕터 허용
- 경지 돌파가 핵심 기대, 계위제 시각화 권장(8-10단계 체계, 전후 수치 비교)
- 자원 화폐화 체계(영석/단약/공법)가 핵심 미시 실현 매개체
- 설정 제약이 합리적 Override 사유로 가능

---

### 2.3 로맨스/달달물 (romance)

```yaml
id: romance
name: 로맨스/달달물
description: 감정 교류, 관계 진전, 설렘과 아픔이 교차
tags: [romance]

hook_config:
  preferred_types: [감정 훅, 갈망 훅, 선택 훅]
  strength_baseline: medium
  chapter_end_required: true
  transition_allowance: 2

coolpoint_config:
  preferred_patterns: [달콤 초과 기대, 정체 폭로, 오해 승격]
  density_per_chapter: medium
  combo_interval: 6
  milestone_interval: 12

micropayoff_config:
  preferred_types: [관계 실현, 감정 실현, 인정 실현]
  min_per_chapter: 1
  transition_min: 1

pacing_config:
  stagnation_threshold: 4
  strand_quest_max: 4
  strand_fire_gap_max: 5
  transition_max_consecutive: 2

override_config:
  allowed_rationale_types: [TRANSITIONAL_SETUP, CHARACTER_CREDIBILITY, ARC_TIMING]
  debt_multiplier: 1.0
  payback_window_default: 4
```

**장르 특성**:
- 감정선이 절대적 핵심이며, 공백 허용도가 극히 낮음
- 감정 훅이 왕패(안쓰러움/설렘/질투)
- 관계 진전이 가장 중요한 미시 실현

---

### 2.4 서스펜스/추리 (mystery)

```yaml
id: mystery
name: 서스펜스/추리
description: 미스터리 구동, 논리 추론, 진실이 한 걸음씩 드러남
tags: [mystery]

hook_config:
  preferred_types: [서스펜스 훅, 위기 훅, 선택 훅]
  strength_baseline: medium
  chapter_end_required: true
  transition_allowance: 2

coolpoint_config:
  preferred_patterns: [악역 전복, 정체 폭로]
  density_per_chapter: low
  combo_interval: 10
  milestone_interval: 20

micropayoff_config:
  preferred_types: [정보 실현, 단서 실현]
  min_per_chapter: 1
  transition_min: 1

pacing_config:
  stagnation_threshold: 3
  strand_quest_max: 8
  strand_fire_gap_max: 20
  transition_max_consecutive: 2

override_config:
  allowed_rationale_types: [LOGIC_INTEGRITY, TRANSITIONAL_SETUP, ARC_TIMING]
  debt_multiplier: 0.8
  payback_window_default: 5
```

**장르 특성**:
- 논리 완결성이 쾌감 포인트 밀도보다 우선
- 정보 실현이 핵심 미시 실현(지속적인 단서 추진 유지 권장)
- LOGIC_INTEGRITY가 훅 강도 하향의 합리적 사유로 가능

---

### 2.5 규칙 괴담 (rules-mystery)

```yaml
id: rules-mystery
name: 규칙 괴담
description: 기괴한 규칙, 생존 추리, 괴담 역전
tags: [rules-mystery, horror]

hook_config:
  preferred_types: [위기 훅, 서스펜스 훅, 선택 훅]
  strength_baseline: strong
  chapter_end_required: true
  transition_allowance: 1

coolpoint_config:
  preferred_patterns: [월급 역전, 악역 전복]
  density_per_chapter: medium
  combo_interval: 5
  milestone_interval: 8

micropayoff_config:
  preferred_types: [정보 실현, 단서 실현, 능력 실현]
  min_per_chapter: 1
  transition_min: 1

pacing_config:
  stagnation_threshold: 2
  strand_quest_max: 4
  strand_fire_gap_max: 15
  transition_max_consecutive: 1

override_config:
  allowed_rationale_types: [LOGIC_INTEGRITY, WORLD_RULE_CONSTRAINT]
  debt_multiplier: 1.2
  payback_window_default: 2
```

**장르 특성**:
- 긴장감이 높은 훅 강도를 요구
- 전환 챕터 허용도가 극히 낮음(1챕터)
- 규칙 제약이 합리적 Override 사유

---

### 2.6 도시 이능 (urban-power)

```yaml
id: urban-power
name: 도시 이능
description: 현대 배경, 숨겨진 초능력, 저자세 허세, 산업 체인 게임
tags: [urban, power, industry]

hook_config:
  preferred_types: [위기 훅, 갈망 훅, 감정 훅]
  strength_baseline: medium
  chapter_end_required: true
  transition_allowance: 2

coolpoint_config:
  preferred_patterns: [돼지 행세 호랑이, 허세 응징, 정체 폭로, 오해 승격]
  density_per_chapter: high
  combo_interval: 3
  milestone_interval: 10

micropayoff_config:
  preferred_types: [인정 실현, 능력 실현, 관계 실현]
  min_per_chapter: 2
  transition_min: 1

pacing_config:
  stagnation_threshold: 3
  strand_quest_max: 5
  strand_fire_gap_max: 8
  transition_max_consecutive: 2

override_config:
  allowed_rationale_types: [TRANSITIONAL_SETUP, ARC_TIMING]
  debt_multiplier: 1.0
  payback_window_default: 3
```

**장르 특성**:
- 허세 응징 시리즈가 핵심 쾌감 포인트
- 현대 배경은 신분 은닉→폭로의 리듬 제어 필요
- 사회적 지위 변화가 중요한 미시 실현
- 연예계/산업 체인 배경이 인기, 감정선 가중치 높음(공백 허용도 8챕터로 하향)
- 3챕터 1피크 리듬: 1챕터 곤경, 2챕터 능력 초반 전개, 3챕터 소승리+새 장애

---

### 2.7 지후 단편 (zhihu-short)

```yaml
id: zhihu-short
name: 지후 단편
description: 짧고 빠르게, 강한 반전, 감정 충격
tags: [short, zhihu]

hook_config:
  preferred_types: [감정 훅, 서스펜스 훅, 선택 훅]
  strength_baseline: strong
  chapter_end_required: true
  transition_allowance: 0

coolpoint_config:
  preferred_patterns: [악역 전복, 정체 폭로, 달콤 초과 기대]
  density_per_chapter: high
  combo_interval: 2
  milestone_interval: 3

micropayoff_config:
  preferred_types: [감정 실현, 정보 실현, 관계 실현]
  min_per_chapter: 2
  transition_min: 2

pacing_config:
  stagnation_threshold: 1
  strand_quest_max: 2
  strand_fire_gap_max: 3
  transition_max_consecutive: 0

override_config:
  allowed_rationale_types: []
  debt_multiplier: 2.0
  payback_window_default: 1
```

**장르 특성**:
- 전환 챕터 윈도우가 극히 좁으며, 매 챕터 최소 한 가지 체감 가능한 수확 권장
- 극히 높은 훅 강도 요구
- 부채 배율이 가장 높음(단편은 장기 부채를 피해야 함)

---

### 2.8 대역물/학대물 (substitute)

```yaml
id: substitute
name: 대역물/학대물
description: 감정 얽힘, 오해와 반전, 아내 쫓아 화장장
tags: [substitute, angst]

hook_config:
  preferred_types: [감정 훅, 선택 훅, 서스펜스 훅]
  strength_baseline: strong
  chapter_end_required: true
  transition_allowance: 2

coolpoint_config:
  preferred_patterns: [정체 폭로, 악역 전복, 달콤 초과 기대]
  density_per_chapter: medium
  combo_interval: 5
  milestone_interval: 10

micropayoff_config:
  preferred_types: [감정 실현, 관계 실현, 인정 실현]
  min_per_chapter: 1
  transition_min: 1

pacing_config:
  stagnation_threshold: 3
  strand_quest_max: 3
  strand_fire_gap_max: 4
  transition_max_consecutive: 2

override_config:
  allowed_rationale_types: [CHARACTER_CREDIBILITY, ARC_TIMING, TRANSITIONAL_SETUP]
  debt_multiplier: 1.0
  payback_window_default: 4
```

**장르 특성**:
- 감정 훅이 절대적 핵심(가슴 아픔→안쓰러움→기대)
- 정체 폭로가 왕패 쾌감 포인트
- 감정선 공백 허용도가 극히 낮음

---

### 2.9 e스포츠 (esports)

```yaml
id: esports
name: e스포츠
description: 경기장 게임, 팀 조율, 역전 드라마와 우승 추격
tags: [esports, competition]

hook_config:
  preferred_types: [위기 훅, 선택 훅, 갈망 훅]
  strength_baseline: strong
  chapter_end_required: true
  transition_allowance: 1

coolpoint_config:
  preferred_patterns: [월급 역전, 악역 전복, 오해 승격]
  density_per_chapter: high
  combo_interval: 4
  milestone_interval: 8

micropayoff_config:
  preferred_types: [정보 실현, 인정 실현, 관계 실현]
  min_per_chapter: 2
  transition_min: 1

pacing_config:
  stagnation_threshold: 2
  strand_quest_max: 4
  strand_fire_gap_max: 8
  transition_max_consecutive: 1

override_config:
  allowed_rationale_types: [TRANSITIONAL_SETUP, ARC_TIMING, LOGIC_INTEGRITY]
  debt_multiplier: 1.1
  payback_window_default: 2
```

**장르 특성**:
- 경기 챕터는 추적 가능한 승패 목표와 의사결정 포인트 권장
- 역경/역전이 핵심 쾌감 포인트 원천
- 전환 챕터 허용도가 낮으며, 실시간 피드백감 유지 필요(스코어/여론/상태)

---

### 2.10 방송물 (livestream)

```yaml
id: livestream
name: 방송물
description: 플랫폼 트래픽 게임, 실시간 피드백 구동, 여론과 비즈니스 양선 병진
tags: [livestream, urban]

hook_config:
  preferred_types: [위기 훅, 감정 훅, 선택 훅]
  strength_baseline: strong
  chapter_end_required: true
  transition_allowance: 1

coolpoint_config:
  preferred_patterns: [허세 응징, 악역 전복, 정체 폭로]
  density_per_chapter: high
  combo_interval: 3
  milestone_interval: 6

micropayoff_config:
  preferred_types: [인정 실현, 자원 실현, 정보 실현]
  min_per_chapter: 2
  transition_min: 1

pacing_config:
  stagnation_threshold: 2
  strand_quest_max: 4
  strand_fire_gap_max: 6
  transition_max_consecutive: 1

override_config:
  allowed_rationale_types: [TRANSITIONAL_SETUP, ARC_TIMING, CHARACTER_CREDIBILITY]
  debt_multiplier: 1.1
  payback_window_default: 2
```

**장르 특성**:
- "외부 피드백→주인공 반응→결과 변화" 순환 형성 우선
- 여론 반전과 비즈니스 게임은 증거 체인에 의존해야 하며, 구호에 의존하지 않음
- 데이터 변화(온라인/순위/전환율)가 고빈도 미시 실현으로 활용 가능

---

### 2.11 크툴루 (cosmic-horror)

```yaml
id: cosmic-horror
name: 크툴루
description: 규칙 오염과 이성 붕괴가 병행, 진실에 가까울수록 대가가 높음
tags: [horror, mystery, cosmic]

hook_config:
  preferred_types: [서스펜스 훅, 위기 훅, 선택 훅]
  strength_baseline: strong
  chapter_end_required: true
  transition_allowance: 1

coolpoint_config:
  preferred_patterns: [악역 전복, 오해 승격, 월급 역전]
  density_per_chapter: medium
  combo_interval: 6
  milestone_interval: 10

micropayoff_config:
  preferred_types: [단서 실현, 정보 실현, 감정 실현]
  min_per_chapter: 1
  transition_min: 1

pacing_config:
  stagnation_threshold: 2
  strand_quest_max: 4
  strand_fire_gap_max: 12
  transition_max_consecutive: 1

override_config:
  allowed_rationale_types: [LOGIC_INTEGRITY, WORLD_RULE_CONSTRAINT, ARC_TIMING]
  debt_multiplier: 1.3
  payback_window_default: 2
```

**장르 특성**:
- 공포감은 규칙과 대가에서 비롯되며, 순수 분위기 쌓기가 아님
- 진실을 추진할 때마다 명확한 손실(이성/관계/자원)을 연계해야 함
- 높은 강도 훅은 "미해결 규칙 문제"를 우선하며, 단순 놀래키기가 아님

### 2.12 역사 전이 (history-travel)

```yaml
id: history-travel
name: 역사 전이
description: 현대 영혼이 고대로 전이, 지식 우위로 역사 변경, 개간 기반 역전
tags: [history, travel, knowledge]

hook_config:
  preferred_types: [선택 훅, 위기 훅, 갈망 훅]
  strength_baseline: medium
  chapter_end_required: true
  transition_allowance: 2

coolpoint_config:
  preferred_patterns: [권위 응징, 돼지 행세 호랑이, 악역 전복, 정체 폭로]
  density_per_chapter: medium
  combo_interval: 3
  milestone_interval: 10

micropayoff_config:
  preferred_types: [정보 실현, 자원 실현, 인정 실현]
  min_per_chapter: 1
  transition_min: 1

pacing_config:
  stagnation_threshold: 3
  strand_quest_max: 5
  strand_fire_gap_max: 10
  transition_max_consecutive: 2

override_config:
  allowed_rationale_types: [WORLD_RULE_CONSTRAINT, CHARACTER_CREDIBILITY, ARC_TIMING]
  debt_multiplier: 0.9
  payback_window_default: 4
```

**장르 특성**:
- 지식 우위 > 무력 우위, 추론 과정을 보여줘야 함(답만 말하면 안 됨)
- 3챕터 1피크 리듬: 1챕터 곤경/전이, 2챕터 지식 초반 전개, 3챕터 소승리+새 장애
- 악역에 합리적 동기 부여(이해충돌), 권위 인물은 쉽게 설득되지 않음(다중 증명 필요)
- 역사에는 관성이 있으며, 하나를 바꾸면 연쇄 반응 발생(비선형 결과)
- 여성 주인공 비율 상승, 개간/기반 구축/업종 개혁 태그가 인기

---

### 2.13 게임물 (game-lit)

```yaml
id: game-lit
name: 게임물
description: 게임화 세계관, 시스템 골든핑거 구동, 수치 피드백 쾌감, 극단적 반차 시작점
tags: [game, system, apocalypse]

hook_config:
  preferred_types: [위기 훅, 갈망 훅, 선택 훅]
  strength_baseline: strong
  chapter_end_required: true
  transition_allowance: 0

coolpoint_config:
  preferred_patterns: [월급 역전, 허세 응징, 돼지 행세 호랑이, 악역 전복]
  density_per_chapter: high
  combo_interval: 3
  milestone_interval: 10

micropayoff_config:
  preferred_types: [능력 실현, 자원 실현, 인정 실현]
  min_per_chapter: 2
  transition_min: 1

pacing_config:
  stagnation_threshold: 2
  strand_quest_max: 5
  strand_fire_gap_max: 15
  transition_max_consecutive: 0

override_config:
  allowed_rationale_types: [WORLD_RULE_CONSTRAINT, ARC_TIMING]
  debt_multiplier: 1.1
  payback_window_default: 2
```

**장르 특성**:
- 초반 챕터에서 골든핑거를 빨리 보여주는 것 권장(보통 1-2챕터 이내)
- 수치 피드백 시각화 권장(전투력50→전투력180, 전후 비교)
- 골든핑거는 상한/소모/쿨타임 설정 권장, 무한 사용 방지
- 전환 챕터 윈도우가 좁으며, "쾌감 포인트 또는 수치 추진" 최소 하나 유지 권장
- IP 융합(LOL/포켓몬 등)이 차별화 태그, 포스트 아포칼립스 생존 장르 부상
- 초반(권장 3챕터 이내) 명확한 적수 출현 필요(환경/규칙/구체적 악역 중 택일)

---

## 3. Profile 로딩 메커니즘

### 3.1 로딩 시점

1. **Step 1.5**: `state.json → project.genre` 기반으로 해당 profile 로딩
2. **Context Agent**: profile 관련 필드를 창작 작업서에 주입
3. **Checkers**: profile에 따라 감지 임계값과 제안 가중치 조정

### 3.2 다중 태그 지원(예약)

현재는 단일 태그 모드입니다. 향후 다중 태그 지원 시:
- `tags` 필드로 중첩
- 충돌 필드는 더 엄격한 값을 취함
- 예: `[romance, mystery]` → 감정선 공백은 min(5, 20) = 5

### 3.3 사용자 정의 Profile

사용자가 `state.json`에서 기본값을 덮어쓸 수 있습니다:

```json
{
  "project": {
    "genre": "xianxia",
    "genre_overrides": {
      "pacing_config": {
        "stagnation_threshold": 5
      }
    }
  }
}
```

---

## 4. Taxonomy와의 관계

| Taxonomy 정의 | Profile 설정 |
|--------------|-------------|
| 훅 유형 목록 | 어떤 유형을 선호하는지 |
| 쾌감 포인트 패턴 목록 | 어떤 패턴을 선호하는지 |
| 미시 실현 유형 목록 | 어떤 유형을 선호하는지 |
| Hard/Soft 기준 | 임계값 조정 |
| Override 사유 유형 | 어떤 사유가 허용되는지 |
