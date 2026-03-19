# RAG 와 설정 설명

## RAG 검색 아키텍처

```text
쿼리 → QueryRouter(auto) → vector / bm25 / hybrid / graph_hybrid
                     └→ RRF 융합 + Rerank → Top-K
```

기본 모델：

- Embedding：`Qwen/Qwen3-Embedding-8B`
- Reranker：`jina-reranker-v3`

## 환경 변수 로딩 순서

1. 프로세스 환경 변수（최고 우선순위）
2. 소설 프로젝트 루트 디렉토리의 `.env`
3. 사용자 레벨 전역：`~/.claude/webnovel-writer/.env`

## `.env` 최소 설정

```bash
EMBED_BASE_URL=https://api-inference.modelscope.cn/v1
EMBED_MODEL=Qwen/Qwen3-Embedding-8B
EMBED_API_KEY=your_embed_api_key

RERANK_BASE_URL=https://api.jina.ai/v1
RERANK_MODEL=jina-reranker-v3
RERANK_API_KEY=your_rerank_api_key
```

설명：

- Embedding Key가 설정되지 않은 경우, 시맨틱 검색은 BM25로 폴백됩니다.
- 각 소설별로 `${PROJECT_ROOT}/.env`를 개별 설정하는 것을 권장하며, 다중 프로젝트 간 설정 혼선을 방지합니다.
