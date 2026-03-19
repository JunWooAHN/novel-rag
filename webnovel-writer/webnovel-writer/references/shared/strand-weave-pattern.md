---
name: strand-weave-pattern
purpose: 챕터 기획 시 3선 균형 점검, 리듬 단조로움 방지
---

<context>
이 파일은 스토리 라인 균형 제어에 사용됩니다. Claude는 다중 라인 서사 기법을 알고 있으므로, 여기서는 웹소설 특유의 3선 교직 메커니즘과 state.json 내 추적기 구조만 보충합니다.
참고: 이 파일은 shared 단일 진실 소스입니다; 각 Skill의 references에서 복사 수정하는 것을 금합니다. 업데이트가 필요하면, 본 파일을 수정하세요.
</context>

<instructions>

## 세 줄기 정의와 비율

| 줄기 | 비율 | 정의 | 전형적 스토리 |
|------|------|------|----------|
| **Quest(메인라인)** | 55-65% | 핵심 임무, 레벨업, 전투, 보물 쟁탈 | 종문 대비, 비경, 경지 돌파, 복수 응징 |
| **Fire(감정선)** | 20-30% | 감정 관계 발전(연애/우정/사제) | 만남 썸, 영웅구미, 관계 확인 |
| **Constellation(세계관선)** | 10-20% | 설정 확장, 새 세력/장소 전시, 세력 관계, 사교 네트워크 | 숨겨진 세력 공개, 새 대륙 소개, 주인공 출생의 비밀 |

## 교직 규칙 (낮은 자유도 - 반드시 실행)

| 규칙 | 경고 조건 | 권장 조치 |
|------|----------|----------|
| Quest 연속 5챕터 초과 금지 | chapters_since_switch >= 5 | Fire 또는 Constellation로 전환 |
| Fire 10챕터 초과 미등장 금지 | current - last_fire > 10 | 감정씬 배치(달달/질투) |
| Constellation 15챕터 초과 미등장 금지 | current - last_constellation > 15 | 새 설정/세력/복선 전시 |

## state.json 내 strand_tracker 구조

```json
{
  "strand_tracker": {
    "last_quest_chapter": 45,
    "last_fire_chapter": 43,
    "last_constellation_chapter": 40,
    "current_dominant": "quest",
    "chapters_since_switch": 3,
    "history": [{"chapter": 46, "dominant": "quest"}, ...]
  }
}
```

호환 설명:
- `history[].dominant`가 현재 표준 필드(update_state.py가 기록)
- 프로젝트에 기존 데이터 `history[].strand`가 있으면, 읽기 시 dominant로 호환 매핑해야 함

## 첫 30챕터 교직 템플릿

```
1-5화:   Quest ×5(초반 빠른 메인라인 추진)
6화:     Fire(첫 여주 만남)
7-10화:  Quest ×4(종문 대비)
11화:    Fire(영웅구미)
12-14화: Quest ×3(비경 보물 쟁탈)
15화:    Constellation("성지" 존재 공개)
16-19화: Quest ×4(강적 격파)
20화:    Fire(관계 확인)
21-24화: Quest ×4(경지 돌파)
25화:    Constellation(주인공 출생 단서 발견)
26-30화: Quest ×5(권말 클라이맥스)
```

</instructions>

<examples>

<example>
<input>현재 46화, last_quest=45, last_fire=43, last_constellation=40, current_dominant="quest", chapters_since_switch=3</input>
<output>
**경고 판단**:
- Quest 연속 3챕터 < 5챕터 → 경고 없음
- Fire까지 3챕터 < 10챕터 → 경고 없음
- Constellation까지 6챕터 < 15챕터 → 경고 없음

**본 챕터 권장**: Quest 계속 가능, 하지만 향후 1-2챕터 내 Fire 배치하여 리듬 조절 권장
</output>
</example>

<example>
<input>현재 55화, last_fire=42, 연속 13챕터 감정선 없음</input>
<output>
⚠️ **경고**: 마지막 감정선 이후 > 10챕터!

**권장**: 본 챕터에 Fire선 배치
- 옵션 A: 여주 등장, 작은 달달 인터랙션
- 옵션 B: 영웅구미 장면
- 옵션 C: 질투/오해 소극
</output>
</example>

<example type="edge_case">
<input>초반 10챕터는 메인라인을 빠르게 구축해야 하는데, 감정선을 좀 줄여도 되나요?</input>
<output>
✅ 가능합니다. 첫 10챕터 비율 조정 가능:
- Quest: 70-80%
- Fire: 10-15%
- Constellation: 5-10%

하지만 6-8화에 반드시 최소 1회 Fire 배치(첫 만남/인상 수립)
</output>
</example>

</examples>

<errors>
❌ 연속 10챕터 순수 Quest → ✅ 최대 5챕터 후 전환
❌ 감정선 10챕터 넘게 미등장 → ✅ 5-10챕터마다 한 번 배치
❌ 세계관선 15챕터 넘게 미등장 → ✅ 10-15챕터마다 새 설정 전시
❌ Strand 전환 후 strand_tracker 업데이트 잊음 → ✅ 매 챕터 종료 후 자동 업데이트
</errors>
