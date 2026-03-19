# Webnovel Writer

[![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Compatible-purple.svg)](https://claude.ai/claude-code)

<a href="https://trendshift.io/repositories/22487" target="_blank"><img src="https://trendshift.io/api/badge/repositories/22487" alt="lingfengQAQ%2Fwebnovel-writer | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>
## 프로젝트 소개

`Webnovel Writer`는 Claude Code 기반의 장편 웹소설 창작 시스템으로, AI 글쓰기에서 발생하는 "망각"과 "환각" 문제를 줄이고, 장기 연재 창작을 지원하는 것을 목표로 합니다.

상세 문서는 `docs/`에 분리되어 있습니다:

- 아키텍처 및 모듈: `docs/architecture.md`
- 명령어 상세: `docs/commands.md`
- RAG 및 설정: `docs/rag-and-config.md`
- 장르 템플릿: `docs/genres.md`
- 운영 및 복구: `docs/operations.md`
- 문서 네비게이션: `docs/README.md`

## 빠른 시작

### 1) 플러그인 설치 (공식 Marketplace)

```bash
claude plugin marketplace add lingfengQAQ/webnovel-writer --scope user
claude plugin install webnovel-writer@webnovel-writer-marketplace --scope user
```

> 현재 프로젝트에서만 적용하려면 `--scope user`를 `--scope project`로 변경하세요.

### 2) Python 의존성 설치

```bash
python -m pip install -r https://raw.githubusercontent.com/lingfengQAQ/webnovel-writer/HEAD/requirements.txt
```

설명: 이 명령어로 핵심 글쓰기 체인과 Dashboard 의존성을 함께 설치합니다.

### 3) 소설 프로젝트 초기화

Claude Code에서 실행:

```bash
/webnovel-init
```

설명: `/webnovel-init`은 현재 워크스페이스 하위에 책 제목으로 `PROJECT_ROOT`(하위 디렉토리)를 생성하고, `workspace/.claude/.webnovel-current-project`에 현재 프로젝트 포인터를 기록합니다.

### 4) RAG 환경 설정 (필수)

초기화 후 책 프로젝트 루트 디렉토리로 이동하여 `.env`를 생성합니다:

```bash
cp .env.example .env
```

최소 설정 예시:

```bash
EMBED_BASE_URL=https://api-inference.modelscope.cn/v1
EMBED_MODEL=Qwen/Qwen3-Embedding-8B
EMBED_API_KEY=your_embed_api_key

RERANK_BASE_URL=https://api.jina.ai/v1
RERANK_MODEL=jina-reranker-v3
RERANK_API_KEY=your_rerank_api_key
```

### 5) 사용 시작

```bash
/webnovel-plan 1
/webnovel-write 1
/webnovel-review 1-5
```

로컬 CLI / 플러그인 디렉토리 / 프로젝트 루트 해석 문제를 확인하려면 통합 사전 점검을 직접 실행할 수 있습니다:

```bash
python -X utf8 "<CLAUDE_PLUGIN_ROOT>/scripts/webnovel.py" --project-root "<WORKSPACE_ROOT>" preflight
```

### 6) 시각화 패널 시작 (선택사항)

```bash
/webnovel-dashboard
```

설명:
- Dashboard는 읽기 전용 패널입니다 (프로젝트 상태, 엔티티 그래프, 챕터/아웃라인 탐색, 추독력 확인).
- 프론트엔드 빌드 산출물은 플러그인과 함께 배포되므로, 사용자가 로컬에서 `npm build`할 필요가 없습니다.

### 7) Agent 모델 설정 (선택사항)

본 프로젝트의 모든 내장 Agent는 기본적으로 다음과 같이 설정되어 있습니다:

```yaml
model: inherit
```

이는 하위 Agent가 현재 Claude 세션에서 사용하는 모델을 상속한다는 의미입니다.

특정 Agent에 별도 모델을 지정하려면 해당 파일(`webnovel-writer/agents/*.md`)의 frontmatter를 편집하세요. 예시:

```yaml
---
name: context-agent
description: ...
tools: Read, Grep, Bash
model: sonnet
---
```

사용 가능한 값: `inherit` / `sonnet` / `opus` / `haiku` (Claude Code의 현재 지원 사항에 따름).

## 업데이트 요약

| 버전 | 설명 |
|------|------|
| **v5.5.4 (현재)** | 글쓰기 체인 프롬프트 강제 제약 보완 (프로세스 하드 제약, 중국어 사고 글쓰기 제약, Step 책임 경계); 중국어 통일 심사/윤색/Agent 보고 문구; 문서 내부 버전 번호 및 버전 이력 정리, 플러그인 배포 버전과의 혼동 감소. |
| **v5.5.3** | 통합 `preflight` 사전 점검 명령 추가; 글쓰기 체인 CLI 예시를 UTF-8 실행 방식으로 통일, 문서의 긴 shell 사전 점검 스니펫 수렴 및 Windows 터미널 깨짐 위험 감소. |
| **v5.5.2** | 상세 아웃라인의 챕터 이름을 본문 파일명에 동기화하는 기능 지원; workflow_manager의 무인자 find_project_root monkeypatch 호환성 문제 수정. |
| **v5.5.1** | 권별 단일 파일 아웃라인의 컨텍스트 스냅샷에서 챕터 추출 문제 수정; 명령어 문서에서 누락된 `/webnovel-dashboard`와 `/webnovel-learn` 보완. |
| **v5.5.0** | 읽기 전용 시각화 Dashboard Skill(`/webnovel-dashboard`) 및 실시간 새로고침 기능 추가; 플러그인 디렉토리 시작 및 사전 빌드 프론트엔드 배포 지원 |
| **v5.4.4** | 공식 Plugin Marketplace 설치 메커니즘 도입; Skills/Agents/References의 CLI 호출 통합 수정 (`CLAUDE_PLUGIN_ROOT` 단일 경로, 투과 명령 `--` 통일) |
| **v5.4.3** | 스마트 RAG 컨텍스트 보조 강화 (`auto/graph_hybrid` 폴백 BM25) |
| **v5.3** | 추독력 시스템 도입 (훅 / 쿨포인트 / 마이크로 실현 / 부채 추적) |

## 플러그인 배포

GitHub Actions의 `Plugin Release` 워크플로를 사용한 통합 배포를 권장합니다:

1. 먼저 로컬에서 버전 정보를 동기화합니다:
   ```bash
   python -X utf8 webnovel-writer/scripts/sync_plugin_version.py --version 5.5.4 --release-notes "이번 버전 설명"
   ```
2. 버전 변경 사항을 커밋하고 푸시합니다 (`README.md`, `plugin.json`, `marketplace.json`).
3. 저장소의 Actions 페이지를 열고 `Plugin Release`를 선택합니다.
4. 현재 저장소 메타데이터와 일치하는 `version` (예: `5.5.4`)과 GitHub Release용 `release_notes`를 입력합니다.
5. 워크플로가 다음 동작을 수행합니다:
   - `plugin.json`, `marketplace.json`과 README의 현재 버전이 일치하는지 검증
   - 현재 버전과 입력한 `version`이 일치하는지 검증
   - `vX.Y.Z` Tag 생성 및 푸시
   - 동일 이름의 GitHub Release 생성

일상 개발에서 `Plugin Version Check`는 Push / PR 시 자동으로 버전 정보의 일관성을 검증합니다.

## 오픈소스 라이선스
본 프로젝트는 `GPL v3` 라이선스를 사용합니다. 자세한 내용은 `LICENSE`를 참조하세요.

## Star 히스토리

[![Star History Chart](https://api.star-history.com/svg?repos=lingfengQAQ/webnovel-writer&type=Date)](https://star-history.com/#lingfengQAQ/webnovel-writer&Date)

## 감사의 말

본 프로젝트는 **Claude Code + Gemini CLI + Codex**를 활용한 Vibe Coding 방식으로 개발되었습니다.
영감 출처: [Linux.do 게시글](https://linux.do/t/topic/1397944/49)

## 기여

Issue와 PR을 환영합니다:

```bash
git checkout -b feature/your-feature
git commit -m "feat: add your feature"
git push origin feature/your-feature
```
