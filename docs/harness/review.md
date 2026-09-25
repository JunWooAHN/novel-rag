# Codex 프로젝트 하네스 독립 검토

검토일: 2026-09-24. **판정: 문서·정적 설정 수락.** 이 판정은 새 작업의 배정·재개 지침과 로컬 설정 파일의 구조에 한정한다. 실제 Sol/Luna 역할 선택, 지정 모델 접근, 유료 모델 호출이나 350화 분석 실행을 수락한 것은 아니다. 구현 담당 Sol이 아닌 별도 Sol이 이 문서만 작성했고, 하네스 본문·설정·위키는 수정하지 않았다.

| 검토 항목 | 결과와 근거 |
|---|---|
| 역할과 권한 | [루트 지침](../../AGENTS.md), [하네스 안내](README.md), [세션 결정](session-decisions.md)을 대조했다. Astra 루트는 배정·취합, Sol은 설계·구현·작가 검토, Luna는 작품 한 편 분석·기계적 점검으로 분리된다. 별도 승인 게이트를 만들지 않고 계획만 요청한 일과 이미 승인된 가역 작업을 구별한다. 역사표 잠금·정사·취향·외부 게시의 기존 결정 권한을 유지한다. |
| 분석과 완료 상태 | [코퍼스 독립 검토](../research/chapter-ingestion/review.md)의 7편·61,533,769 bytes·현재 3,292구간, 첫 50화 249 mapped·100 unmapped·1 conflict를 [체크포인트](current-checkpoint.md) 및 세션 결정과 대조했다. [통합 계획](../plans/20260924-first-50-analysis-and-ingestion-plan.md)의 350화 개별 분석은 미실행으로 유지된다. 경계 미확정 화는 보류하며, 학습·운영 캐논 실행도 완료로 표기하지 않는다. |
| 배정과 재개 | [작업 카드](task-template.md)에 입력 revision/hash, 문맥 제한, 산출물, 파일 소유권, 완료·검증 조건이 있다. 작품별 새 문맥과 t화 이하 입력, 3~5화 체크포인트, 작가별 Sol 검토, 단일 DB writer, 중단 후 근거 재확인을 안내한다. |
| 설정 구조 | `.codex/config.toml`과 두 역할 TOML은 Python `tomllib` 파싱을 통과했다. 기본 모델은 `gpt-6-astra`, CLI 0.144.4 호환 하위 스레드 한도는 `agents.max_threads = 3`, 역할별 `config_file`은 존재하는 파일을 가리킨다. 두 역할 파일에 `name`, `description`, `developer_instructions`, 지정 모델이 있다. |
| 탐색 링크 | 루트 지침, 하네스 5문서, 위키 `index.md`·`sources.md`·`log.md`의 상대링크 대상 존재를 검사해 누락 0건을 확인했다. 위키 출처 색인의 83개는 최초 목록의 시점과 범위로 설명하고, 새 하네스 5문서를 별도 절에 등록한다. |

검토 중 처음의 `agents.max_concurrent_threads_per_session = 3`은 로컬 `codex-cli 0.144.4` 설정 로더에서 `expected struct AgentRoleToml` 오류를 냈다. 구현 담당이 `agents.max_threads = 3` 및 명시적인 `agents.sol/luna.config_file`로 바꾼 뒤, 담당자의 읽기 전용 `codex debug prompt-input` 확인은 종료 코드 0이었다. 이 호출은 프로젝트 지침 로딩의 증거이며 역할 선택·모델 접근의 직접 증거는 아니다. 공식 [Subagents 문서](https://learn.chatgpt.com/docs/agent-configuration/subagents)는 현행 한도 키와 레거시 `agents.max_threads` 별칭을 설명한다.

현재 대화의 모델이 설정 변경으로 소급 교체되지는 않는다. 새 작업에서 프로젝트 신뢰·역할 선택·계정의 모델 사용 가능 여부는 실제 실행 시 확인해야 한다. 이 검토에서는 모델 호출·분석·DB 쓰기·원문 재독을 하지 않았다.
