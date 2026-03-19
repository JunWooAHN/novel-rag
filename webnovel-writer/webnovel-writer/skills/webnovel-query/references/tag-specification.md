---
name: tag-specification
purpose: XML 태그 형식 참고
---

<context>
이 파일은 XML 태그 형식 참고용입니다.

**현재 규약**:
- 챕터 집필 시 **더 이상 XML 태그 추가를 요구하지 않음**
- Data Agent가 순수 본문에서 자동으로 엔티티를 추출하여, index.db에 기록
- 태그는 **수동 태깅** 시나리오에만 사용 (예: 중요 엔티티 명시적 표기, 추출 누락 보충)
- 태그를 사용하기로 선택한 경우, 아래 규범을 따르십시오
</context>

<instructions>

## 태그 총람

| 태그 | 용도 | 필수 속성 |
|------|------|----------|
| `<entity>` | 엔티티 신규/자동 업데이트 (캐릭터/장소/아이템/세력/초식) | type, name |
| `<entity-alias>` | 엔티티 별명/칭호 등록 | id/ref, alias |
| `<entity-update>` | 엔티티 속성 업데이트 (set/unset/add/remove/inc + 이력 추적 지원) | id/ref, `<set>` 등 |
| `<skill>` | 금수저 스킬 | name, level, desc, cooldown |
| `<foreshadow>` | 복선 매설 | content, tier |
| `<relationship>` | 캐릭터 관계 | char1, char2, type |
| `<deviation>` | 대강 이탈 표기 | reason |

## 속성 상세

### tier (등급)
- **핵심**: 주선 줄거리에 영향, 반드시 추적
- **지선**: 줄거리를 풍부하게, 추적해야 함
- **장식**: 현실감 증대, 추적 선택

### type (엔티티 유형)
캐릭터 / 장소 / 아이템 / 세력 / 초식

### id / ref (엔티티 참조)
- **id (권장)**: 안정적 고유 식별자 (후속 업데이트/별명 추가에 편리)
- **ref**: 이미 출현한 이름/별명으로 참조 (index.db aliases 테이블을 통해 자동 해석)
- **type (선택)**: ref에 모호성이 있을 때 소거용 (예: 동명이인); 여전히 모호하면 반드시 `id` 사용

### `<entity-update>` 하위 작업
- **set**: `<set key="k" value="v" reason="선택"/>`
- **unset**: `<unset key="k" reason="선택"/>`
- **add**: `<add key="k" value="v" reason="선택"/>` (배열 추가, 자동 중복 제거)
- **remove**: `<remove key="k" value="v" reason="선택"/>` (배열 제거)
- **inc**: `<inc key="k" delta="1" reason="선택"/>` (숫자 증가, 기본 +1)

**최상위 필드 화이트리스트** (current 대신 엔티티 최상위를 직접 업데이트 가능): `tier`, `desc`, `canonical_name`, `importance`, `status`, `parent`

> **권장**: `<entity>`에 `desc`와 `tier`를 보충하는 것을 강력 권장합니다. 그렇지 않으면 후속 검색과 일관성 검사 품질이 저하됩니다.

## 배치 규칙

- **권장**: 챕터 끝에 일괄 배치 (관리 편의)
- **허용**: 엔티티가 처음 출현하는 단락 끝
- **요구**: 태그가 한 줄을 독점, 본문 문장 사이에 끼우지 않음

### 숨김 작법 (권장)

```markdown
본문 내용...

<!--
<entity type="캐릭터" id="luchen" name="육진" desc="주인공, 시공 능력 각성" tier="핵심"/>
<entity-alias id="luchen" alias="육대" context="특근대 가입 후"/>
<entity-update id="luchen"><set key="realm" value="F급-각성자" reason="각성 완료"/></entity-update>
<skill name="시간 역행" level="1" desc="10초 전으로 돌아감" cooldown="24시간"/>
<foreshadow content="신비한 노인의 옥패" tier="핵심" target="50"/>
<relationship char1_id="luchen" char2_id="liwe" type="ally" intensity="60" desc="초기 협력"/>
-->
```

</instructions>

<examples>

<example>
<input>새 캐릭터 태깅</input>
<output>
```xml
<entity type="캐릭터" id="luchen" name="육진" desc="주인공, 시공 능력이 각성된 대학생" tier="핵심"/>
<entity type="캐릭터" id="liwe" name="이미" desc="여주, 신비한 배경의 학교 미녀" tier="핵심"/>
<entity type="캐릭터" name="커피숍 주인" desc="평범해 보이지만 실은 깊이 숨긴 인물" tier="장식"/>
```
</output>
</example>

<example>
<input>새 칭호/별명 등록</input>
<output>
```xml
<entity-alias id="luchen" alias="육대" context="특근대 가입 후"/>
<entity-alias ref="육진" alias="계승자" context="시스템이 신분 확인 후"/>
```
</output>
</example>

<example>
<input>엔티티 속성 업데이트 (경지/위치/상태/소속 등)</input>
<output>
```xml
<entity-update id="luchen">
  <set key="realm" value="E급-지배자" reason="위기 중 돌파"/>
  <set key="location" value="도시 서쪽 폐 실험실"/>
</entity-update>
```
</output>
</example>

<example>
<input>새 스킬 태깅</input>
<output>
```xml
<skill name="시간 역행" level="1" desc="10초 전 상태로 돌아감" cooldown="24시간"/>
<skill name="공간 앵커" level="2" desc="전송 앵커 설정, 순간 이동으로 복귀 가능" cooldown="1시간"/>
<skill name="시간 감지" level="1" desc="패시브 스킬, 3초 내 위험 예지" cooldown="없음"/>
```
</output>
</example>

<example>
<input>복선 매설</input>
<output>
```xml
<foreshadow content="신비한 노인이 남긴 옥패가 빛나기 시작" tier="핵심" target="50" location="폐 실험실"/>
<foreshadow content="이미 손목의 이상한 문신" tier="지선" target="30" characters="이미,육진"/>
<foreshadow content="커피숍 주인의 의미심장한 눈빛" tier="장식"/>
```
</output>
</example>

<example>
<input>대강 이탈 표기</input>
<output>
```xml
<deviation reason="즉흥 영감, 이미와 육진의 감정 상호작용 추가, 후속 감정선 복선을 위해"/>
<deviation reason="원래 이번 장에서 돌파 예정이었으나, 리듬이 너무 빨라 다음 장으로 지연"/>
```
</output>
</example>

</examples>

<errors>
❌ `<entity type='캐릭터' .../>` → ✅ 큰따옴표 사용 `type="캐릭터"`
❌ `<entity type="캐릭터" ...>` → ✅ 자체 닫힘 `.../>` 또는 닫기 태그 `</entity>` 보충
❌ `<Entity type="캐릭터" .../>` → ✅ 소문자 태그명 `<entity`
❌ `[NEW_ENTITY: 캐릭터, 육진, ...]` → ✅ XML 형식 사용
❌ `<entity-update ref="xxx"></entity-update>` → ✅ 최소 하나의 `<set key="..." value="..."/>` 포함
</errors>
