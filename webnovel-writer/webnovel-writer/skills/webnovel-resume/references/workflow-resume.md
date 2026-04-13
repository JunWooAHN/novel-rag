---
name: workflow-resume
purpose: 작업 복구 시 로드, 중단 복구 흐름 안내
---

<context>
이 파일은 중단 작업 복구에 사용됩니다. Claude는 오류 처리 흐름을 이미 알고 있으며, 여기서는 웹소설 창작 워크플로우에 특화된 Step 난이도 등급과 복구 전략만 보충합니다.
</context>

<instructions>

## Step 중단 난이도 등급

| Step | 이름 | 영향 | 난이도 | 기본 전략 |
|------|------|------|------|----------|
| Step 1 | Context Agent | 부작용 없음 (읽기만) | ⭐ | 직접 재실행 |
| Step 1.5 | 챕터 설계 | 구조 미확정 | ⭐ | 재설계 |
| Step 2A | 초고 생성 | 반제품 챕터 파일 | ⭐⭐ | **반제품 삭제**, Step 1부터 다시 시작 |
| Step 2B | 스타일 적응 | 부분 개작 내용 | ⭐⭐ | 적응 계속 또는 2A로 복귀 |
| Step 3 | 심사 | 심사 미완료 | ⭐⭐⭐ | 사용자 결정: 재심사 또는 건너뛰기 |
| Step 4 | 웹소설화 윤색 | 부분 윤색된 파일 | ⭐⭐ | 윤색 계속 또는 삭제 후 재작성 |
| Step 5 | Data Agent | 엔티티 미추출 완료 | ⭐⭐ | 재실행 (멱등) |
| Step 6 | Git 백업 | 미커밋 | ⭐⭐⭐ | 스테이징 영역 확인, 커밋/롤백 결정 |

## 복구 흐름

### Phase 1: 중단 상태 감지

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" workflow detect
```

### Phase 2: 사용자에게 확인

**반드시 표시**:
- 작업 명령과 매개변수
- 중단 시간과 위치
- 완료된 단계
- 복구 옵션과 리스크 등급

### Phase 3: 복구 실행

**옵션 A (권장)**: 반제품 삭제 후 처음부터 다시 시작
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" workflow cleanup --chapter {N} --confirm
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" workflow clear
/webnovel-write {N}
```

**옵션 B**: 이전 챕터로 롤백
```bash
git reset --hard ch{N-1:04d}
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" workflow clear
```

## 왜 이어쓰기가 아닌 삭제인가?

1. **품질 보장**: 반제품은 미완성 문장, 논리 단절을 포함할 수 있음
2. **컨텍스트 손실**: 새 세션은 이전 창작 사고를 기억할 수 없음
3. **환각 방지**: 이어쓰기는 전후 모순을 쉽게 발생시킴
4. **비용 통제**: 재생성 < 반제품 수정 + 심사

## 특수 시나리오

| 시나리오 | 전략 |
|------|------|
| 24시간 초과 | 롤백 권장 (컨텍스트 완전 손실) |
| 1시간 초과 | 처음부터 다시 시작 권장 |
| 복수 반제품 | 모두 삭제, 안정 상태에서 다시 시작 |
| workflow_state.json 부재 | 휴리스틱 감지: state.json vs 파일 비교 |

</instructions>

<examples>

<example>
<input>Step 2A 중단 (가장 흔함)</input>
<output>
🔴 중단된 작업 감지:

작업: /webnovel-write 7
중단 위치: Step 2A - 챕터 내용 생성 중

완료됨:
  ✅ Step 1: Context Agent 컨텍스트 수집

미완료:
  ⏸️ Step 2A: 챕터 내용 생성 (이미 1500자 작성)
  ⏹️ Step 3-6: 미시작

복구 옵션:
A) 반제품 삭제, Step 1부터 다시 시작 (권장) ⭐
B) Ch6으로 롤백, Ch7 모든 진행 포기

선택해 주세요 (A/B):
</output>
</example>

<example>
<input>Step 3 중단 (심사)</input>
<output>
복구 옵션:
A) 심사 재실행 ⚠️
   - 6명의 심사원 호출
   - 심사 보고서 생성
   - Step 4 윤색 계속

B) 심사 건너뛰기, 바로 윤색 (권장)
   - 심사 보고서 미생성
   - 추후 /webnovel-review로 보충 심사 가능

선택해 주세요 (A/B):
</output>
</example>

<example>
<input>Step 4 중단 (윤색)</input>
<output>
복구 옵션:
A) 윤색 계속 (권장) ⭐
   - 실제 챕터 파일을 열어 윤색 계속 (우선 `chapters/chapter_0007-챕터제목.md`)
   - 파일 저장
   - Step 5 (Data Agent) 계속

B) 윤색 원고 삭제, Step 2A부터 재작성
   - 실제 챕터 파일 삭제 (우선 `chapters/chapter_0007-챕터제목.md`)
   - 챕터 내용 재생성

선택해 주세요 (A/B):
</output>
</example>

</examples>

<errors>
❌ 반제품 지능 이어쓰기 → ✅ 삭제 후 재생성
❌ 자동으로 복구 전략 결정 → ✅ 반드시 사용자 확인
❌ 중단 감지 건너뛰기 → ✅ 먼저 workflow_manager.py detect 실행
❌ state.json 수정 후 검증 안 함 → ✅ 필드별 일관성 점검
</errors>
