# 칸글 소설 프로젝트 작업 플랜
> 작성일: 2026-03-20
> 최종 업데이트: 2026-03-20

## Context
webnovel-writer 프로젝트가 `한글-창제를-훔친-몽골-카간/`에 초기화 완료. 기존 소설 데이터(`한글 창제를 훔친 몽골 카간/`)를 마이그레이션하고, 설정 파일을 완성하여 200화 완결 목표 연속 집필이 가능한 상태를 만든다.

---

## Phase 0: 중국어 경로/파일명 → 영어 변환 ✅ 완료

### 0-1. 프로젝트 디렉토리 ✅
심링크 방식으로 변환 완료:
- `正文/` → `text/`, `设定集/` → `settings/`, `大纲/` → `outline/`, `审查报告/` → `reviews/`
- 하위 디렉토리 및 파일명도 영어로 변환 + 중국어 심링크 유지

### 0-2. webnovel-writer 시스템 스크립트 ✅
플러그인 경로: `~/.claude/plugins/cache/webnovel-writer-marketplace/webnovel-writer/5.5.4/`

**수정 완료 항목:**

| 분류 | 파일 | 변경 내용 |
|------|------|----------|
| 핵심 경로 | `scripts/data_modules/config.py` | `正文`→`text`, `设定集`→`settings`, `大纲`→`outline` |
| 챕터 패턴 | `scripts/chapter_paths.py` | `第NNN章`→`ch-NNN`, `第N卷`→`vol-N`, 레거시 fallback 유지 |
| 초기화 | `scripts/init_project.py` | 디렉토리 생성 경로 전체 영어화 |
| 아웃라인 | `scripts/chapter_outline_loader.py` | `大纲`→`outline`, 볼륨 파일명 영어화 |
| 상태 보고 | `scripts/status_reporter.py` | `正文`→`text`, 글로브 패턴 이중 지원 |
| 백업 | `scripts/backup_manager.py` | 주석 내 경로 업데이트 |
| 컨텍스트 | `scripts/extract_chapter_context.py` | 섹션 제목 영어화 |
| 대시보드 | `dashboard/app.py` | 디렉토리 참조 3곳 영어화 |
| RAG | `scripts/data_modules/rag_adapter.py` | 소스 파일 참조 영어화 |
| 템플릿 | `templates/output/` 11개 파일 | 파일명 영어로 리네임 (예: `大纲-总纲.md`→`outline-master.md`) |
| 스킬 | `skills/` 내 SKILL.md 파일들 | 경로 참조 텍스트 영어화 |
| 에이전트 | `agents/` 내 8개 .md | 경로 참조 텍스트 영어화 |
| 테스트 | `scripts/data_modules/tests/` | 테스트 내 경로/패턴 업데이트 |

**주의:** 플러그인 업데이트 시 덮어씌워질 수 있음. 재적용 필요 시 이 문서 참조.

---

## Phase 1: 기존 데이터 마이그레이션 ✅ 완료

### 1-1. 챕터 파일 이전 ✅
- **출발**: `한글 창제를 훔친 몽골 카간/series/volume1/chapter01/`
- **도착**: `한글-창제를-훔친-몽골-카간/text/vol-1/`

| 원본 | 변환 후 | 비고 |
|------|---------|------|
| `001.md` ~ `023.md` | `ch-001.md` ~ `ch-023.md` | 23개 챕터 |
| `000-abstract.md` | `abstract.md` | 전체 챕터 요약 |
| `998.md` | `side-998.md` | 외전 (칸글 창제 회상) |
| `999.md` | `side-999.md` | 외전 (첫 만남 회상) |
| `019시놉.md`, `022_plot.md`, `014 copy.md` | — | 스킵 (초안/중복) |

### 1-2. 캐릭터/세계관 이전 ✅

| 원본 | 변환 후 | 위치 |
|------|---------|------|
| `mains/윤기령.md` | `yun-giryeong.md` | `settings/characters/main/` |
| `mains/소르칵타니.md` | `sorghaghtani.md` | `settings/characters/main/` |
| `mains/툴루이.md` | `tolui.md` | `settings/characters/main/` |
| `mains/수부타이.md` | `subutai.md` | `settings/characters/main/` |
| `mains/아륵.md` | `aruq.md` | `settings/characters/main/` |
| `mains/바하우딘.md` | `bahauddin.md` | `settings/characters/main/` |
| `sub/타타통아.md` | `tata-tonga.md` | `settings/characters/supporting/` |
| `commons/몽골병사.md` | `mongol-soldier.md` | `settings/characters/supporting/` |
| `commons/몽골케식.md` | `mongol-keshik.md` | `settings/characters/supporting/` |
| `명칭 등.md` | `terminology.md` | `settings/misc/` |
| `history/몽골 제국...연표.md` | `war-timeline.md` | `settings/misc/` |

### 1-3. state.json 업데이트 ✅

| 필드 | 이전 | 이후 |
|------|------|------|
| `current_chapter` | 0 | 23 |
| `total_words` | 0 | 165,490 |
| `current_volume` | 1 | 1 |
| `volumes_planned` | [] | 4권 등록 (칸글의 탄생/제국의 확장/세계의 문/칸글의 시대) |
| `protagonist_state.location` | "" | 우하이(Wuhai) 제철소 |
| `protagonist_state.power.realm` | "" | 병참총책임자 |

---

## Phase 2: 빈 설정 파일 완성 ✅ 완료

### 2-1. settings/heroine.md ✅
- 소르칵타니 베키 전체 카드 완성 (3,685 bytes)
- 기본 정보, 성격, 동기, 결함, 관계, 외모, 행동 패턴, 성장 호선, OOC 경계

### 2-2. settings/antagonist.md ✅
- 3층 반파 설계 완성 (5,752 bytes)
- 소반파: 차가타이/오고타이 (형제 권력투쟁) — 핵심 구동, 미러 대항, 극점
- 중반파: 서하/금나라/호라즘 — 기능, 도덕 딜레마, 쾌감 생성
- 대반파: 아륵 (불멸의 설계자) — 미스터리, 복선 회수 로드맵

### 2-3. settings/protagonist-group.md ✅
- 진리회 5사도 + 툴루이 체계 (3,973 bytes)
- 구성원 역할표, 공동 목표, 역할 분담, POV 배분, 내부 갈등, 성장 곡선

### 2-4. settings/genre-fusion.md ✅
- 대체역사(7) + 착각계 개그(3) 융합 논리 (3,032 bytes)
- 융합 메커니즘, 혼용 금지 규칙, 위험 목록, 회피 방법

### 2-5. outline/highlight-plan.md ✅
- 200화 전체 쾌감 포인트 분포표 (6,336 bytes)
- 기집필 1~23화 쾌감 맵, 24~50화 계획, 2~4권 개략, 복선 회수 이정표

---

## Phase 3: RAG 환경 설정 ⏸ 보류

### 3-1. .env 파일 ✅ (빈 키)
- `.env.example` → `.env` 복사 완료
- Embedding/Rerank API 키는 **사용자가 나중에 직접 설정** 예정
- 키 없이도 기본 집필 워크플로는 동작함

---

## Phase 4: 상세 아웃라인 작성 ⬜ 미시작

### 4-1. /webnovel-plan 실행 필요
- 1권(1~50화) 상세 아웃라인
  - 기존 1~23화: 이미 집필 완료 → 요약만 기록
  - 24~50화: 상세 챕터별 플롯 작성 필요
- 2~4권: 권별 개략 아웃라인

---

## Phase 5: 집필 재개 ⬜ 미시작

### 5-1. 24화부터 /webnovel-write로 집필
- 23화 시점: 툴루이가 우하이 제철소로 이동, 컨테이너 박스 물류 혁신 확립
- 24화 예상: 금나라 침공 준비, 병참 체계 시운전
- 시간대: 1211년, 금나라 침공 직전

---

## 현재 프로젝트 파일 구조

```
한글-창제를-훔친-몽골-카간/
├── .env                          # API 키 (빈 키, 나중에 설정)
├── .env.example
├── .webnovel/
│   ├── state.json                # current_chapter=23, total_words=165,490
│   ├── idea_bank.json
│   ├── archive/
│   ├── backups/
│   └── summaries/
├── text/
│   └── vol-1/
│       ├── ch-001.md ~ ch-023.md # 23개 챕터
│       ├── abstract.md           # 전체 요약
│       ├── side-998.md           # 외전
│       └── side-999.md           # 외전
├── settings/
│   ├── protagonist.md            # 툴루이 카드 ✅
│   ├── heroine.md                # 소르칵타니 카드 ✅
│   ├── antagonist.md             # 3층 반파 설계 ✅
│   ├── protagonist-group.md      # 진리회 5사도 ✅
│   ├── golden-finger.md          # 금손가락 설계 ✅
│   ├── genre-fusion.md           # 장르 융합 ✅
│   ├── worldview.md              # 세계관
│   ├── power-system.md           # 역량체계
│   ├── characters/
│   │   ├── main/                 # 주요 캐릭터 6명 ✅
│   │   ├── supporting/           # 보조 캐릭터 3명 ✅
│   │   └── villain/
│   ├── items/
│   └── misc/
│       ├── terminology.md        # 명칭 정리 ✅
│       └── war-timeline.md       # 전쟁 연표 ✅
├── outline/
│   ├── master-outline.md         # 총강 (4권 200화 구조) ✅
│   └── highlight-plan.md         # 200화 쾌감 분포표 ✅
├── reviews/
├── 正文 → text/                  # 심링크
├── 设定集 → settings/            # 심링크
├── 大纲 → outline/               # 심링크
└── 审查报告 → reviews/           # 심링크
```

---

## 작업 진행 요약

| 순서 | 작업 | 상태 | 비고 |
|------|------|------|------|
| 0 | Phase 0: 시스템 스크립트 중국어→영어 | ✅ 완료 | 플러그인 캐시 수정 완료 |
| 1 | Phase 1-1: 챕터 마이그레이션 | ✅ 완료 | 23개 + 부록 3개 |
| 2 | Phase 1-2: 캐릭터/세계관 이전 | ✅ 완료 | 11개 파일 |
| 3 | Phase 1-3: state.json 업데이트 | ✅ 완료 | ch=23, words=165,490 |
| 4 | Phase 2: 빈 설정 파일 완성 | ✅ 완료 | 5개 파일 작성 |
| 5 | Phase 3: RAG .env 설정 | ⏸ 보류 | 빈 키로 생성, 나중에 설정 |
| 6 | **Phase 4: 상세 아웃라인** | **⬜ 다음** | `/webnovel-plan` 실행 필요 |
| 7 | Phase 5: 집필 재개 (24화~) | ⬜ 대기 | 아웃라인 완료 후 |

---

## 다음 작업

1. `/webnovel-plan` 실행 → 1권 24~50화 상세 아웃라인 + 2~4권 개략 아웃라인
2. `/webnovel-write` 실행 → 24화부터 집필 재개
3. (선택) RAG API 키 설정 → `.env`에 Embedding/Rerank 키 입력

---

## 검증 체크리스트

- [x] `text/vol-1/` 에 23개 챕터 파일 존재
- [x] `state.json`의 `current_chapter == 23`
- [x] `settings/` 내 모든 핵심 .md 파일에 실제 내용 존재
- [x] 플러그인 스크립트가 `text/`, `ch-NNN`, `vol-N` 패턴 사용
- [ ] `/webnovel-plan` 실행 시 에러 없이 아웃라인 생성
- [ ] `/webnovel-write` 실행 시 24화 집필 가능
