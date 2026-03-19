# index.db 테이블 구조 설명

> SQLite로 대규모 데이터 (엔티티/별칭/장면/관계) 저장.
>
> 현재 구조에는 추격력/관측성 관련 테이블이 포함됨.

## 테이블 일람

### 핵심 인덱스 테이블

### chapters
- chapter (INTEGER, PK)
- title (TEXT)
- location (TEXT)
- word_count (INTEGER)
- characters (TEXT)
- summary (TEXT)
- created_at (TIMESTAMP)

### scenes
- id (INTEGER, PK)
- chapter (INTEGER)
- scene_index (INTEGER)
- start_line (INTEGER)
- end_line (INTEGER)
- location (TEXT)
- summary (TEXT)
- characters (TEXT)

### appearances
- id (INTEGER, PK)
- entity_id (TEXT)
- chapter (INTEGER)
- mentions (TEXT)
- confidence (REAL)

### entities
- id (TEXT, PK)
- type (TEXT)
- canonical_name (TEXT)
- tier (TEXT)
- desc (TEXT)
- current_json (TEXT)
- first_appearance (INTEGER)
- last_appearance (INTEGER)
- is_protagonist (INTEGER)
- is_archived (INTEGER)

### aliases
- alias (TEXT)
- entity_id (TEXT)
- entity_type (TEXT)

### state_changes
- id (INTEGER, PK)
- entity_id (TEXT)
- field (TEXT)
- old_value (TEXT)
- new_value (TEXT)
- reason (TEXT)
- chapter (INTEGER)

### relationships
- id (INTEGER, PK)
- from_entity (TEXT)
- to_entity (TEXT)
- type (TEXT)
- description (TEXT)
- chapter (INTEGER)

### 추격력 부채 관련 테이블
- override_contracts
- chase_debt
- debt_events
- chapter_reading_power

### 관측성과 심사 관련 테이블
- invalid_facts
- review_metrics
- rag_query_log
- tool_call_stats
- writing_checklist_scores

> 실제 필드와 제약은 `.claude/scripts/data_modules/index_manager.py`를 기준으로 합니다.
