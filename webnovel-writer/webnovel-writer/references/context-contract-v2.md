# Context Contract

## 목적
- `Context Agent`, `Writer`, `Review`에 통합적이고, 정렬 가능하며, 추적 가능한 컨텍스트 계약을 제공합니다.
- 기존 호출자를 깨뜨리지 않으면서, 컨텍스트 안정성과 적중률을 향상시킵니다.

## 출력 구조
- 루트 필드 호환 유지: `meta`, `sections`, `template`, `weights`.
- `meta` 신규 추가:
  - `context_contract_version`: `v2`로 고정
  - `ranker`: 현재 정렬기 설정 스냅샷(재현용)

## Section 정렬 규칙
- `core.recent_summaries`
  - 주로 챕터 최신성 순으로 정렬(최신이 높음)
  - "훅/서스펜스/반전/갈등" 힌트가 포함된 경우 추가 가산점
- `core.recent_meta`
  - 주로 챕터 최신성 순으로 정렬
  - `hook`이 있는 항목 우선
- `scene.appearing_characters`
  - 최신성 + 등장 빈도 종합 정렬
  - `warning`(예: pending invalid) 포함 시 감점
- `story_skeleton`
  - 최신성 우선, 요약 정보 밀도 겸비
- `alerts`
  - `critical/high` 또는 핵심 위험 키워드가 포함된 항목 우선

## Phase B 확장 섹션
- `reader_signal`
  - 최근 챕터 추독력 메타데이터 집계(훅/쾌감 포인트/미시 실현)
  - 최근 윈도우의 패턴 사용 통계 집계(`pattern_usage` / `hook_type_usage`)
  - 검토 추세 및 저점수 구간 집계(`review_trend` / `low_score_ranges`)
- `genre_profile`
  - `state.json -> project.genre` 기반으로 장르 전략 조각 자동 선택
  - `${CLAUDE_PLUGIN_ROOT}/references/genre-profiles.md` 및 `${CLAUDE_PLUGIN_ROOT}/references/reading-power-taxonomy.md` 참조
  - Writer가 빠르게 실행할 수 있도록 `reference_hints` 출력

## Phase C 확장 섹션
- `writing_guidance`
  - `reader_signal` + `genre_profile` 기반으로 챕터 수준 실행 제안 생성
  - 저점수 구간 수정, 훅 차별화, 쾌감 포인트 패턴 최적화, 장르 고정을 우선 안내
  - `guidance_items` 및 `signals_used` 출력

## 압축 텍스트 전략
- section이 예산을 초과할 때, 텍스트는 압축 절단(헤드 + 절단 표시 + 테일)을 사용
- 절단 표시는 `…[TRUNCATED]`로 고정
- `content` 원본 구조를 유지하고, `text`는 모델 컨텍스트에 빠르게 주입하는 데 사용

## 호환성 제약
- 기존 key 이름과 필드 의미를 변경하지 않습니다.
- 목록 순서만 재배열하며; 내용은 삭제/수정하지 않습니다(기존 필터링 로직 제외).
- 호출자가 `meta.context_contract_version`을 무시하면, v1과 동일하게 동작합니다.

## 권장 호출 시점
- `Context Agent`가 Step 1에서 컨텍스트를 집계할 때 호출합니다.
- `webnovel-write`, `webnovel-review` 시작 단계에서 호출합니다.
- 복구 프로세스(`webnovel-resume`)에서 `detect` 후 컨텍스트를 재구축할 때 호출합니다.

## 설정 항목 (DataModulesConfig)
- `context_ranker_enabled`
- `context_ranker_recency_weight`
- `context_ranker_frequency_weight`
- `context_ranker_hook_bonus`
- `context_ranker_length_bonus_cap`
- `context_ranker_alert_critical_keywords`
- `context_ranker_debug`

Phase B:
- `context_reader_signal_enabled`
- `context_reader_signal_recent_limit`
- `context_reader_signal_window_chapters`
- `context_reader_signal_review_window`
- `context_reader_signal_include_debt`
- `context_genre_profile_enabled`
- `context_genre_profile_max_refs`
- `context_genre_profile_fallback`

Phase C:
- `context_compact_text_enabled`
- `context_compact_min_budget`
- `context_compact_head_ratio`
- `context_writing_guidance_enabled`
- `context_writing_guidance_max_items`
- `context_writing_guidance_low_score_threshold`
- `context_writing_guidance_hook_diversify`

Phase E:
- `context_writing_checklist_enabled`
- `context_writing_checklist_min_items`
- `context_writing_checklist_max_items`
- `context_writing_checklist_default_weight`

Phase F:
- `context_writing_score_persist_enabled`
- `context_writing_score_include_reader_trend`
- `context_writing_score_trend_window`
- `writing_guidance.checklist_score` 를 `index.db -> writing_checklist_scores`에 기록

Phase H:
- `context_dynamic_budget_enabled`
- `context_dynamic_budget_early_chapter`
- `context_dynamic_budget_late_chapter`
- 신규 `meta.context_weight_stage` (early/mid/late)

Phase I:
- `context_genre_profile_support_composite`
- `context_genre_profile_max_genres`
- `context_genre_profile_separators`
- 신규 `genre_profile.genres/composite/composite_hints`
