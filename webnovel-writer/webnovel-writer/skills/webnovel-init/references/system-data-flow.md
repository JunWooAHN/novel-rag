---
name: system-data-flow-redirect
purpose: 권위 버전으로 리디렉션
---

<context>
이 파일은 통합 위치로 이전되었으며, 다중 버전 비동기 문제를 방지합니다.
</context>

<instructions>

## 권위 버전 위치

`${CLAUDE_PLUGIN_ROOT}/skills/webnovel-query/references/system-data-flow.md`

## 로딩 방법

```bash
cat "${CLAUDE_PLUGIN_ROOT}/skills/webnovel-query/references/system-data-flow.md"
```

## 빠른 참조

### 디렉토리 구조
```
프로젝트 루트/
├── 正文/           # 장 파일
├── 大纲/           # 권별 개요/장별 개요
├── 设定集/         # 세계관/능력체계/캐릭터카드
└── .webnovel/
    ├── state.json          # 권위 상태
    ├── workflow_state.json # 워크플로 브레이크포인트
    ├── index.db            # SQLite 인덱스
    └── archive/            # 아카이브 데이터
```

### 현재 구조의 핵심 변경
- **듀얼 Agent 아키텍처**: Context Agent (읽기) + Data Agent (쓰기)
- **XML 태그 없음**: 순수 본문 집필, Data Agent AI가 엔티티 자동 추출
- **SQLite 저장**: entities/aliases/state_changes를 index.db로 이전
- **state.json 경량화**: < 5KB 유지, 주로 progress/protagonist_state/strand_tracker/disambiguation 포함

</instructions>
