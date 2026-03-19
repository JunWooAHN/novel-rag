# project_memory.json 설계

장기적으로 재사용 가능한 작성 패턴을 저장하며, `/webnovel-learn`이 기록합니다.

## 예시

```json
{
  "patterns": [
    {
      "pattern_type": "hook",
      "description": "위기 훅 설계: 서스펜스 극대화",
      "source_chapter": 100,
      "learned_at": "2026-02-02T12:00:00Z"
    }
  ]
}
```

## 필드 설명
- patterns: 검증된 작성 패턴 목록
  - pattern_type: hook / pacing / dialogue / payoff / emotion
  - description: 재사용 가능한 설명
  - source_chapter: 출처 챕터
  - learned_at: 기록 시간
