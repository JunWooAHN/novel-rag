# preferences.json 설계

사용자 선호와 작성 제약을 저장하는 데 사용됩니다(/webnovel-init 또는 사용자가 수동 편집 가능).

## 예시

```json
{
  "tone": "열혈",
  "pacing": {
    "chapter_words": 2500,
    "cliffhanger": true
  },
  "style": {
    "dialogue_ratio": 0.35,
    "narration_ratio": 0.65
  },
  "avoid": ["과도한 방백", "반복 대사"],
  "focus": ["주인공 성장", "전투 묘사"]
}
```

## 필드 설명
- tone: 전체 감정 기조
- pacing: 리듬 선호
- style: 서술/대화 비율
- avoid: 금기 목록
- focus: 반드시 강조해야 할 방향
