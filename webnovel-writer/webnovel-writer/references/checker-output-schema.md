# Checker 통합 출력 Schema

모든 검토 Agent는 이 통합 출력 형식을 따라야 하며, 자동화 요약과 추세 분석에 용이합니다.

설명:
- 단일 챕터 작성 시나리오에서는 기본적으로 `chapter` 필드를 사용합니다.
- 구간 통계가 필요한 경우, 집계 레이어에서 `start_chapter/end_chapter`를 보충할 수 있으며, 개별 checker에서 필수 입력을 요구하지 않습니다.
- 확장 필드는 허용되지만, 본 파일에 정의된 필수 필드를 삭제하거나 대체해서는 안 됩니다.

## 표준 JSON Schema

```json
{
  "agent": "checker-name",
  "chapter": 100,
  "overall_score": 85,
  "pass": true,
  "issues": [
    {
      "id": "ISSUE_001",
      "type": "문제 유형",
      "severity": "critical|high|medium|low",
      "location": "위치 설명",
      "description": "문제 설명",
      "suggestion": "수정 제안",
      "can_override": false
    }
  ],
  "metrics": {},
  "summary": "간단한 요약"
}
```

## 필드 설명

| 필드 | 유형 | 필수 | 설명 |
|------|------|------|------|
| `agent` | string | ✅ | Agent 이름 |
| `chapter` | int | ✅ | 챕터 번호 |
| `overall_score` | int | ✅ | 총점 (0-100) |
| `pass` | bool | ✅ | 통과 여부 |
| `issues` | array | ✅ | 문제 목록 |
| `metrics` | object | ✅ | Agent 전용 지표 |
| `summary` | string | ✅ | 간단한 요약 |

확장 필드 규칙(선택):
- checker 전용 필드(예: `hard_violations`, `soft_suggestions`, `override_eligible`)를 추가할 수 있습니다.
- 전용 필드는 설명 강화용이며, `issues`를 대체하는 용도로 사용하지 않습니다.

## 문제 심각도 정의

| severity | 의미 | 처리 방식 |
|----------|------|----------|
| `critical` | 심각한 문제, 반드시 수정 | 윤색 단계에서 반드시 수정 |
| `high` | 높은 우선순위 문제 | 우선 수정 |
| `medium` | 중간 수준 문제 | 수정 권장 |
| `low` | 경미한 문제 | 선택적 수정 |

## 각 Checker 전용 metrics

### reader-pull-checker
```json
{
  "metrics": {
    "hook_present": true,
    "hook_type": "위기 훅",
    "hook_strength": "strong",
    "prev_hook_fulfilled": true,
    "micropayoff_count": 2,
    "micropayoffs": ["능력 실현", "인정 실현"],
    "is_transition": false,
    "debt_balance": 0.0
  }
}
```

### high-point-checker
```json
{
  "metrics": {
    "cool_point_count": 2,
    "cool_point_types": ["허세 응징", "월급 역전"],
    "density_score": 8,
    "type_diversity": 0.8,
    "milestone_present": false
  }
}
```

### consistency-checker
```json
{
  "metrics": {
    "power_violations": 0,
    "location_errors": 1,
    "timeline_issues": 0,
    "entity_conflicts": 0
  }
}
```

### ooc-checker
```json
{
  "metrics": {
    "severe_ooc": 0,
    "moderate_ooc": 1,
    "minor_ooc": 2,
    "speech_violations": 0,
    "character_development_valid": true
  }
}
```

### continuity-checker
```json
{
  "metrics": {
    "transition_grade": "B",
    "active_threads": 3,
    "dormant_threads": 1,
    "forgotten_foreshadowing": 0,
    "logic_holes": 0,
    "outline_deviations": 0
  }
}
```

### pacing-checker
```json
{
  "metrics": {
    "dominant_strand": "quest",
    "quest_ratio": 0.6,
    "fire_ratio": 0.25,
    "constellation_ratio": 0.15,
    "consecutive_quest": 3,
    "fire_gap": 4,
    "constellation_gap": 8,
    "fatigue_risk": "low"
  }
}
```

## 요약 형식

Step 3 완료 후, 요약 JSON을 출력합니다:

```json
{
  "chapter": 100,
  "checkers": {
    "reader-pull-checker": {"score": 85, "pass": true, "critical": 0, "high": 1},
    "high-point-checker": {"score": 80, "pass": true, "critical": 0, "high": 0},
    "consistency-checker": {"score": 90, "pass": true, "critical": 0, "high": 0},
    "ooc-checker": {"score": 75, "pass": true, "critical": 0, "high": 1},
    "continuity-checker": {"score": 85, "pass": true, "critical": 0, "high": 0},
    "pacing-checker": {"score": 80, "pass": true, "critical": 0, "high": 0}
  },
  "overall": {
    "score": 82.5,
    "pass": true,
    "critical_total": 0,
    "high_total": 2,
    "can_proceed": true
  }
}
```
