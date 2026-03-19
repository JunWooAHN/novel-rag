---
name: webnovel-learn
description: 현재 세션에서 성공 패턴을 추출하여 project_memory.json에 기록합니다
allowed-tools: Read Write Bash
---

# /webnovel-learn

## Project Root Guard (반드시 먼저 확인)

- 프로젝트 루트 디렉토리에서 실행해야 합니다 (`.webnovel/state.json`이 존재해야 함)
- 현재 디렉토리에 해당 파일이 없으면, 사용자에게 프로젝트 경로를 물어보고 `cd`로 진입
- 진입 후 변수 설정: `$PROJECT_ROOT = (Resolve-Path ".").Path`

## 목표
- 재사용 가능한 집필 패턴 추출 (훅/리듬/대화/미시적 실현 등)
- `.webnovel/project_memory.json`에 추가

## 입력
```bash
/webnovel-learn "이 장의 위기 훅 설계가 매우 효과적이었고, 서스펜스가 최대치였다"
```

## 출력
```json
{
  "status": "success",
  "learned": {
    "pattern_type": "hook",
    "description": "위기 훅 설계: 서스펜스 최대치",
    "source_chapter": 100,
    "learned_at": "2026-02-02T12:00:00Z"
  }
}
```

## 실행 흐름
1. `"$PROJECT_ROOT/.webnovel/state.json"` 읽기, 현재 장 번호 획득 (progress.current_chapter)
2. `"$PROJECT_ROOT/.webnovel/project_memory.json"` 읽기, 존재하지 않으면 `{"patterns": []}` 초기화
3. 사용자 입력 해석, pattern_type 분류 (hook/pacing/dialogue/payoff/emotion)
4. 기록 추가 후 파일에 다시 쓰기

## 제약
- 기존 기록을 삭제하지 않고, 추가만 함
- 완전히 중복되는 description 방지 (중복 제거 가능)
