# state.json 구조 설명

> 이 파일은 런타임 간소화 상태이며, 용량 팽창을 방지합니다. 엔티티 등 대량 데이터는 index.db에 저장됩니다.
>
> 아래 예시는 `update_state.py` 현재 검증 필드와 일치합니다.

```json
{
  "project_info": {
    "title": "",
    "genre": "",
    "target_words": 0,
    "target_chapters": 0
  },
  "progress": {
    "current_chapter": 0,
    "total_words": 0,
    "last_updated": "",
    "volumes_completed": [],
    "current_volume": 1,
    "volumes_planned": [
      {"volume": 1, "chapters_range": "1-100", "planned_at": "2026-02-01"}
    ]
  },
  "protagonist_state": {
    "name": "",
    "power": {"realm": "", "layer": 0, "bottleneck": ""},
    "location": {"current": "", "last_chapter": 0},
    "golden_finger": {"name": "", "level": 0, "cooldown": 0}
  },
  "relationships": {},
  "world_settings": {
    "power_system": [],
    "factions": [],
    "locations": []
  },
  "review_checkpoints": [
    {"chapters": "1-5", "report": "심사보고/제1-5장심사보고.md", "reviewed_at": "2026-02-26 20:00:00"}
  ],
  "strand_tracker": {
    "last_quest_chapter": 0,
    "last_fire_chapter": 0,
    "last_constellation_chapter": 0,
    "current_dominant": "quest",
    "chapters_since_switch": 0,
    "history": []
  },
  "plot_threads": {
    "active_threads": [],
    "foreshadowing": []
  },
  "disambiguation_warnings": [],
  "disambiguation_pending": [],
  "chapter_meta": {
    "0001": {
      "hook": {"type": "위기 훅", "content": "...", "strength": "strong"},
      "pattern": {
        "opening": "갈등 오프닝",
        "hook": "위기 훅",
        "emotion_rhythm": "저→고",
        "info_density": "medium"
      },
      "ending": {"time": "밤", "location": "종문 대전", "emotion": "긴장"}
    }
  }
}
```
