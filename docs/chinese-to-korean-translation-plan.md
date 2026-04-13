# webnovel-writer 중국어→영어/한국어 번역 플랜

## 결정 사항

- **디렉토리명**: 영어 (`chapters`, `settings`, `outline`, `reviews`)
- **챕터 파일명**: `chapter_N` (예: `chapter_0001.md`, `chapter_0001-title.md`)
- **하위 호환성**: 나중에 처리 (지금은 신규 규칙만 적용)

## 변경 범위 요약

| 범위 | Python 파일 | Skill/MD 파일 | Template 파일 | 총 변경점 |
|------|-----------|-------------|-------------|----------|
| 디렉토리명 (chapters/settings/outline/reviews) | ~12 | ~15 | 13 | ~300+ |
| 챕터 패턴 (chapter_N/vol_N) | ~15 | ~10 | - | ~150+ |
| 설정 파일명 (power-system 등) | ~3 | ~8 | 7 | ~50+ |
| 엔티티 타입 (물품/초식) | ~4 | ~2 | - | ~20+ |
| 비즈니스 로직 상수 | ~6 | - | - | ~80+ |
| 주석/독스트링 | ~40 | - | - | ~1600+ |

---

## Phase 1: 디렉토리 구조 (핵심 — 연쇄 영향 최대)

### 1.1 디렉토리명 변환 테이블

| 현재 (중국어) | 변경 (영어) | 용도 |
|-------------|-----------|------|
| `정문/` → | `chapters/` | 챕터 본문 |
| `설정집/` → | `settings/` | 세계관/캐릭터카드 |
| `대강/` → | `outline/` | 총강/권별 개요 |
| `심사보고/` → | `reviews/` | 리뷰 보고서 |
| `설정집/캐릭터库/주요캐릭터/` → | `settings/characters/main/` | 주요 캐릭터 |
| `설정집/캐릭터库/보조캐릭터/` → | `settings/characters/minor/` | 보조 캐릭터 |
| `설정집/캐릭터库/악역캐릭터/` → | `settings/characters/villain/` | 악역 캐릭터 |
| `설정집/물품库/` → | `settings/items/` | 물품 |
| `설정집/기타설정/` → | `settings/misc/` | 기타 설정 |

### 1.2 챕터/권 파일명 패턴 변환

| 현재 (중국어) | 변경 (영어) | 비고 |
|-------------|-----------|------|
| `제0001장.md` → | `chapter_0001.md` | flat layout |
| `제0001장-제목.md` → | `chapter_0001-title.md` | 제목 포함 |
| `제1권/` → | `vol_1/` | volume 디렉토리 |
| `제1권/제001장-제목.md` → | `vol_1/chapter_001-title.md` | volume layout |

### 1.3 개요 파일명 변환

| 현재 (중국어) | 변경 (영어) | 비고 |
|-------------|-----------|------|
| `outline/총강.md` → | `outline/master.md` | 마스터 개요 |
| `outline/쾌감포인트기획.md` → | `outline/highlights.md` | 쾌감포인트 기획 |
| `outline/제1권-비트시트.md` → | `outline/vol_1-beats.md` | 비트시트 |
| `outline/제1권-타임라인.md` → | `outline/vol_1-timeline.md` | 타임라인 |
| `outline/제1권-상세개요.md` → | `outline/vol_1-detailed.md` | 상세 개요 |
| `제1장*.md` (split outline) → | `chapter_1*.md` | 분할 개요 |

### 1.4 설정 파일명 변환

| 현재 (중국어/혼합) | 변경 (영어/한국어) | 비고 |
|----------------|---------------|------|
| `세계관.md` → | `worldview.md` | 세계관 |
| `능력체계.md` → | `power-system.md` | 능력체계 |
| `주인공카드.md` → | `protagonist.md` | 주인공 카드 |
| `여주카드.md` → | `heroine.md` | 여주 카드 |
| `주인공팀.md` → | `team.md` | 주인공 팀 |
| `골든핑거설계.md` → | `golden-finger.md` | 골든핑거 |
| `악역설계.md` → | `antagonist.md` | 악역 설계 |
| `복합장르-융합로직.md` → | `genre-fusion.md` | 복합장르 |
| `문체계약` (context_manager 참조) → | `style-contract` | 문체계약 |

### 1.5 리뷰 보고서 파일명

| 현재 | 변경 |
|-----|------|
| `reviews/제1-1장심사보고.md` → | `reviews/review_ch1-1.md` |
| `reviews/제1-10장심사보고.md` → | `reviews/review_ch1-10.md` |

### 1.6 RAG source_file 참조

| 현재 | 변경 |
|-----|------|
| `chapters/chapter_0001.md#scene_1` | `chapters/chapter_0001.md#scene_1` |

---

## Phase 1 영향받는 파일 상세

### Python 파일 (기능 코드)

| 파일 | 변경 내용 | 라인 수 |
|-----|---------|--------|
| `scripts/data_modules/config.py` | `"chapters"`, `"settings"`, `"outline"` 디렉토리 상수 | 3 |
| `scripts/chapter_paths.py` | 정규식 3개 + 파일명 생성 함수 + 경로 구성 전체 | ~20 |
| `scripts/chapter_outline_loader.py` | 개요 디렉토리 + 파일 glob 패턴 + 에러 메시지 | ~15 |
| `scripts/init_project.py` | 디렉토리 구조 + 파일 생성 + 템플릿 로딩 + 출력 메시지 | ~40 |
| `scripts/status_reporter.py` | `"chapters"` 경로 + 보고서 출력 포맷 | ~10 |
| `scripts/backup_manager.py` | `"chapters"` glob 패턴 + 메시지 | ~3 |
| `scripts/golden_three_checker.py` | 보고서 헤더/포맷 (chapter_N) | ~15 |
| `scripts/extract_chapter_context.py` | 진행 표시 + 결과 포맷 | ~3 |
| `scripts/update_state.py` | 상태 업데이트 출력 | ~5 |
| `scripts/archive_manager.py` | 챕터 범위 정규식 | ~2 |
| `dashboard/app.py` | 디렉토리명 상수 + 에러 메시지 | ~6 |
| `scripts/data_modules/rag_adapter.py` | source_file 경로 참조 | ~3 |
| `scripts/data_modules/context_manager.py` | 설정 파일명 (`power-system`, `style-contract`) | ~2 |
| `scripts/data_modules/query_router.py` | chapter_N 정규식 | ~2 |
| `scripts/data_modules/writing_guidance_builder.py` | verify_hint 메시지 | ~2 |
| `scripts/data_modules/index_debt_mixin.py` | chapter_N 메시지 | ~1 |
| `scripts/data_modules/index_manager.py` | chapter_N 에러 메시지 | ~2 |

### Template 파일 (output/)

| 파일 | 변경 내용 |
|-----|---------|
| `templates/output/settings-worldview.md` | 파일명 변경 완료 |
| `templates/output/settings-power-system.md` | 파일명 변경 완료 |
| `templates/output/settings-protagonist.md` | 파일명 변경 완료 |
| `templates/output/settings-heroine.md` | 파일명 변경 완료 |
| `templates/output/settings-team.md` | 파일명 변경 완료 |
| `templates/output/settings-golden-finger.md` | 파일명 변경 완료 |
| `templates/output/settings-antagonist.md` | 파일명 변경 완료 |
| `templates/output/genre-fusion.md` | 파일명 변경 완료 |
| `templates/output/outline-master.md` | 파일명 변경 완료 |
| `templates/output/outline-volume-beats.md` | 파일명 변경 완료 |
| `templates/output/outline-volume-timeline.md` | 파일명 변경 완료 |

### Skill 마크다운 파일

| 파일 | chapters | settings | outline | chapter_N | reviews |
|-----|----------|----------|---------|-----------|---------|
| `skills/webnovel-init/SKILL.md` | - | 2 | 2 | - | - |
| `skills/webnovel-plan/SKILL.md` | - | 11 | 20+ | 10+ | - |
| `skills/webnovel-write/SKILL.md` | 7 | - | 1 | 10+ | 1 |
| `skills/webnovel-review/SKILL.md` | - | - | - | 3 | 3 |
| `skills/webnovel-resume/references/workflow-resume.md` | 2 | - | - | 2 | - |
| `skills/webnovel-write/references/polish-guide.md` | 2 | - | - | 2 | - |
| `skills/webnovel-write/references/step-3-review-gate.md` | 2 | - | 1 | 1 | 1 |
| `skills/webnovel-write/references/step-1.5-contract.md` | - | - | 2 | - | - |
| `skills/webnovel-plan/references/outlining/outline-structure.md` | - | 6 | 40+ | 10+ | - |
| `skills/webnovel-plan/references/outlining/chapter-planning.md` | - | 1 | 1 | 20+ | - |
| `skills/webnovel-init/references/system-data-flow.md` | 1 | 1 | 1 | - | - |
| `skills/webnovel-resume/references/system-data-flow.md` | 1 | 1 | 1 | - | - |
| `skills/webnovel-query/references/system-data-flow.md` | 1 | 1 | 1 | 1 | - |
| `skills/webnovel-init/references/worldbuilding/setting-consistency.md` | - | 1 | - | - | - |
| `skills/webnovel-init/references/worldbuilding/character-design.md` | - | 1 | - | - | - |

### 테스트 파일

| 파일 | 주요 변경 |
|-----|---------|
| `tests/test_chapter_paths.py` | `"chapters"`, `"outline"`, `"chapter_N"` 전부 |
| `tests/test_extract_chapter_context.py` | `"outline"`, `"vol_N"`, `"chapter_N"` 전부 |
| `tests/test_context_manager.py` | `"vol_N"`, `"outline"` |
| `tests/test_rag_adapter.py` | `"chapters/chapter_N"` source_file |
| `tests/test_data_modules.py` | `"reviews/chapter_N"` report_file |
| `tests/test_state_validator.py` | `"chapter_N"` |

---

## Phase 2: 비즈니스 로직 상수

### 2.1 엔티티 타입 (3개 파일 동시 변경 필수)

| 파일 | 라인 | 변경 |
|-----|-----|------|
| `state_manager.py:94` | `ENTITY_TYPES` | `"물품"`, `"초식"` |
| `sql_state_manager.py:95` | `ENTITY_TYPES` | 동일 |
| `index_manager.py:85,693` | 타입 주석 + help 텍스트 | 동일 |
| `dashboard/frontend/src/App.jsx:361` | UI 컬러 매핑 | `'초식'` 등 |

**위험**: 기존 index.db에 이전 타입으로 저장된 엔티티가 있으면 마이그레이션 필요.

### 2.2 장르 별칭 (`genre_aliases.py`)

전체 재작성. 중국어 키 → 한국어 키로 변환. 영어 프로파일 키는 유지.

### 2.3 가이던스 텍스트 (`writing_guidance_builder.py`)

- `GENRE_GUIDANCE_TEXT`: 11개 항목 전체 한국어 번역
- `GENRE_METHOD_ANCHORS`: 12개 장르 × 2 필드 = 24개 문자열 전체 한국어 번역
- 기타 쾌감포인트 관련 문자열 ~5개

### 2.4 SceneType enum (`style_sampler.py`)

6개 중국어 값 → 한국어 변환. 이 값이 DB나 JSON에 저장되는 경우 주의.

### 2.5 쿼리 라우터 (`query_router.py`)

- `intent_patterns`: 중국어 키워드 ~15개 → 한국어
- `stopwords`: 중국어 불용어 ~8개 → 한국어
- chapter_N 정규식

### 2.6 컨텍스트 랭커 (`context_ranker.py`)

- `SUMMARY_HOOK_HINTS`: `"서스펜스"`, `"훅"`, `"반전"`

---

## Phase 3: 주석/독스트링

~40개 파일, ~1600개 중국어 문자열. 기능에 영향 없음.
Phase 1-2 작업 시 해당 파일 주석도 함께 번역하는 방식으로 점진적 처리.

---

## Phase 4: 테스트 데이터

~15개 테스트 파일의 중국어 테스트 픽스처.
Phase 1-2에서 변경한 상수/패턴에 의존하는 테스트는 반드시 동시 수정.
순수 데이터(인명/지명)는 선택적.

---

## 위험 분석

### HIGH RISK

1. **연쇄 참조 불일치**: 디렉토리명은 Python 코드, Skill MD, Template 파일, 테스트 4곳에서 동시에 참조됨. 하나라도 빠지면 런타임 에러.
2. **정규식 변경**: `chapter_(\d+)` 변환 시, 기존 개요 파일 내부의 마크다운 헤딩도 함께 변경해야 outline 파싱이 작동.
3. **RAG source_file 키**: `rag_adapter.py`에서 생성하는 `source_file` 값이 변경되면, 기존 벡터 DB 인덱스와 불일치.
4. **init_project.py 템플릿 로딩**: `templates/output/settings-power-system.md` 같은 파일명을 하드코딩으로 참조. 파일명 변경과 코드 변경이 동시에 이루어져야 함.

### MEDIUM RISK

5. **SceneType enum 값 변경**: 이 값이 state.json이나 index.db에 기록되는 경우, 기존 데이터와 불일치.
6. **ENTITY_TYPES 변경**: index.db의 entities 테이블에 이미 이전 타입으로 저장된 레코드 존재 시 문제.
7. **Skill 파일 내 bash 명령**: `test -f "${PROJECT_ROOT}/chapters/..."` 같은 셸 명령이 실제 실행되므로 반드시 변경.

### LOW RISK

8. **주석/독스트링 번역 누락**: 기능에 영향 없음. 나중에 처리 가능.
9. **테스트 데이터 중국어 인명**: 테스트 로직에 영향 없는 한 무방.

---

## 작업 순서 권장

```
1. templates/output/ 파일명 변경 (mv)
2. scripts/data_modules/config.py (3개 디렉토리 상수)
3. scripts/chapter_paths.py (정규식 + 파일명 생성)
4. scripts/chapter_outline_loader.py (개요 파일 탐색)
5. scripts/init_project.py (디렉토리 생성 + 파일 생성 + 템플릿 참조)
6. scripts/status_reporter.py (보고서 출력)
7. scripts/golden_three_checker.py (보고서 포맷)
8. scripts/backup_manager.py (glob 패턴)
9. scripts/archive_manager.py (정규식)
10. scripts/extract_chapter_context.py (출력 포맷)
11. scripts/update_state.py (출력 포맷)
12. dashboard/app.py (디렉토리 상수 + 에러 메시지)
13. scripts/data_modules/rag_adapter.py (source_file)
14. scripts/data_modules/context_manager.py (설정 파일명)
15. scripts/data_modules/writing_guidance_builder.py (verify_hint)
16. scripts/data_modules/index_debt_mixin.py (메시지)
17. scripts/data_modules/index_manager.py (에러 메시지)
18. scripts/data_modules/query_router.py (정규식)
--- Phase 1 완료, 테스트 실행 ---
19. scripts/data_modules/genre_aliases.py (장르 매핑)
20. scripts/data_modules/state_manager.py (ENTITY_TYPES)
21. scripts/data_modules/sql_state_manager.py (ENTITY_TYPES)
22. scripts/data_modules/style_sampler.py (SceneType)
23. scripts/data_modules/context_ranker.py (HOOK_HINTS)
24. scripts/data_modules/query_router.py (intent_patterns)
25. scripts/data_modules/writing_guidance_builder.py (가이던스 전체)
--- Phase 2 완료, 테스트 실행 ---
26. Skill MD 파일 전체 (15개+)
27. 테스트 파일 (Phase 1-2 의존성 있는 것만)
--- Phase 3-4 (주석/테스트 데이터) 점진적 ---
```

---

## 기존 프로젝트 (철갑-단종) 처리

현재 `철갑-단종` 프로젝트는 아직 챕터가 없고 (current_chapter: 0), 디렉토리만 생성된 상태.
코드 변경 후 디렉토리명만 수동으로 rename하면 됨:

```bash
cd /Users/ahnjunwoo/dev/novel/철갑-단종
mv 正文 chapters
mv 设定集 settings
mv 大纲 outline
# reviews는 아직 없음
```

설정집 내 파일명도 변경:
```bash
cd settings
mv 세계관.md worldview.md
mv 力量体系.md power-system.md
mv 主角卡.md protagonist.md
mv 女主卡.md heroine.md
mv 主角组.md team.md
mv "골든핑거设计.md" golden-finger.md
mv 反派设计.md antagonist.md
```
