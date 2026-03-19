#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Modules - API 客户端 (v5.4，v5.0 OpenAI 兼容인터페이스유지)

지원两种 API 类型：
1. openai: OpenAI 兼容的 /v1/embeddings 和 /v1/rerank 인터페이스
   - 适用于: OpenAI, Jina, Cohere, vLLM, Ollama 等
2. modal: Modal 自定义인터페이스格式
   - 适用于: 自部署的 Modal 服务

설정예시 (config.py):
    embed_api_type = "openai"
    embed_base_url = "https://api.openai.com/v1"
    embed_model = "text-embedding-3-small"
    embed_api_key = "sk-xxx"

    rerank_api_type = "openai"  # Jina/Cohere 也使用此类型
    rerank_base_url = "https://api.jina.ai/v1"
    rerank_model = "jina-reranker-v2-base-multilingual"
    rerank_api_key = "jina_xxx"
"""

import asyncio
import aiohttp
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .config import get_config


@dataclass
class APIStats:
    """API 호출 통계"""
    total_calls: int = 0
    total_time: float = 0.0
    errors: int = 0


class EmbeddingAPIClient:
    """
    범용 Embedding API 클라이언트

    OpenAI 호환 인터페이스 지원 (/v1/embeddings) 및 Modal 커스텀 인터페이스
    """

    def __init__(self, config=None):
        self.config = config or get_config()
        self.sem = asyncio.Semaphore(self.config.embed_concurrency)
        self.stats = APIStats()
        self._warmed_up = False
        self._session: Optional[aiohttp.ClientSession] = None
        self.last_error_status: Optional[int] = None
        self.last_error_message: str = ""

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=200, limit_per_host=100)
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _build_headers(self) -> Dict[str, str]:
        """요청 헤더 구성"""
        headers = {"Content-Type": "application/json"}
        if self.config.embed_api_key:
            headers["Authorization"] = f"Bearer {self.config.embed_api_key}"
        return headers

    def _build_url(self) -> str:
        """요청 URL 구성"""
        base_url = self.config.embed_base_url.rstrip("/")
        if self.config.embed_api_type == "openai":
            # OpenAI 兼容: /v1/embeddings
            if not base_url.endswith("/embeddings"):
                if base_url.endswith("/v1"):
                    return f"{base_url}/embeddings"
                return f"{base_url}/v1/embeddings"
            return base_url
        else:
            # Modal 自定义인터페이스: 설정된 URL 직접 사용
            return base_url

    def _build_payload(self, texts: List[str]) -> Dict[str, Any]:
        """요청 본문 구성"""
        if self.config.embed_api_type == "openai":
            return {
                "input": texts,
                "model": self.config.embed_model,
                "encoding_format": "float"
            }
        else:
            # Modal 格式
            return {
                "input": texts,
                "model": self.config.embed_model
            }

    def _parse_response(self, data: Dict[str, Any]) -> Optional[List[List[float]]]:
        """응답 파싱"""
        if self.config.embed_api_type == "openai":
            # OpenAI 格式: {"data": [{"embedding": [...], "index": 0}, ...]}
            if "data" in data:
                # index로 정렬하여 순서 보장
                sorted_data = sorted(data["data"], key=lambda x: x.get("index", 0))
                return [item["embedding"] for item in sorted_data]
            return None
        else:
            # Modal 格式: {"data": [{"embedding": [...]}, ...]}
            if "data" in data:
                return [item["embedding"] for item in data["data"]]
            return None

    async def embed(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Embedding 서비스 호출(재시도 메커니즘 포함)"""
        if not texts:
            return []

        timeout = self.config.cold_start_timeout if not self._warmed_up else self.config.normal_timeout
        max_retries = getattr(self.config, 'api_max_retries', 3)
        base_delay = getattr(self.config, 'api_retry_delay', 1.0)

        async with self.sem:
            start = time.time()
            session = await self._get_session()

            for attempt in range(max_retries):
                try:
                    url = self._build_url()
                    headers = self._build_headers()
                    payload = self._build_payload(texts)

                    async with session.post(
                        url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            import json as json_module
                            data = json_module.loads(text)
                            embeddings = self._parse_response(data)

                            if embeddings:
                                self.stats.total_calls += 1
                                self.stats.total_time += time.time() - start
                                self._warmed_up = True
                                self.last_error_status = None
                                self.last_error_message = ""
                                return embeddings

                        # 재시도 가능한 상태 코드: 429 (속도 제한), 500, 502, 503, 504
                        if resp.status in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)  # 지수 백오프
                            print(f"[WARN] Embed {resp.status}, retrying in {delay:.1f}s ({attempt + 1}/{max_retries})")
                            await asyncio.sleep(delay)
                            continue

                        self.stats.errors += 1
                        err_text = await resp.text()
                        self.last_error_status = int(resp.status)
                        self.last_error_message = str(err_text[:200])
                        print(f"[ERR] Embed {resp.status}: {err_text[:200]}")
                        return None

                except asyncio.TimeoutError:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"[WARN] Embed timeout, retrying in {delay:.1f}s ({attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    self.stats.errors += 1
                    self.last_error_status = None
                    self.last_error_message = f"Timeout after {max_retries} attempts"
                    print(f"[ERR] Embed: Timeout after {max_retries} attempts")
                    return None

                except Exception as e:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"[WARN] Embed error: {e}, retrying in {delay:.1f}s ({attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    self.stats.errors += 1
                    self.last_error_status = None
                    self.last_error_message = str(e)
                    print(f"[ERR] Embed: {e}")
                    return None

            return None

    async def embed_batch(
        self, texts: List[str], *, skip_failures: bool = True
    ) -> List[Optional[List[float]]]:
        """
        배치 Embedding

        Args:
            texts: 임베딩할 텍스트 목록
            skip_failures: True 실패한 텍스트는 None 반환；False 하나라도 실패하면 전체 빈 목록 반환

        Returns:
            texts와 같은 길이의 목록, 성공 위치는 벡터, 실패 위치는 None
        """
        if not texts:
            return []

        all_embeddings: List[Optional[List[float]]] = []
        batch_size = self.config.embed_batch_size

        batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
        tasks = [self.embed(batch) for batch in batches]
        results = await asyncio.gather(*tasks)

        for batch_idx, result in enumerate(results):
            actual_batch_size = len(batches[batch_idx])
            if result and len(result) == actual_batch_size:
                all_embeddings.extend(result)
            else:
                if not skip_failures:
                    print(f"[WARN] Embed batch {batch_idx} failed, aborting all")
                    return []
                print(f"[WARN] Embed batch {batch_idx} failed, marking {actual_batch_size} items as None")
                all_embeddings.extend([None] * actual_batch_size)

        return all_embeddings[:len(texts)]

    async def warmup(self):
        """서비스 워밍업"""
        await self.embed(["test"])
        self._warmed_up = True


class RerankAPIClient:
    """
    범용 Rerank API 클라이언트

    OpenAI 호환 인터페이스 지원 (Jina/Cohere 格式) 및 Modal 커스텀 인터페이스
    """

    def __init__(self, config=None):
        self.config = config or get_config()
        self.sem = asyncio.Semaphore(self.config.rerank_concurrency)
        self.stats = APIStats()
        self._warmed_up = False
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=200, limit_per_host=100)
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _build_headers(self) -> Dict[str, str]:
        """요청 헤더 구성"""
        headers = {"Content-Type": "application/json"}
        if self.config.rerank_api_key:
            headers["Authorization"] = f"Bearer {self.config.rerank_api_key}"
        return headers

    def _build_url(self) -> str:
        """요청 URL 구성"""
        base_url = self.config.rerank_base_url.rstrip("/")
        if self.config.rerank_api_type == "openai":
            # Jina/Cohere 兼容: /v1/rerank
            if not base_url.endswith("/rerank"):
                if base_url.endswith("/v1"):
                    return f"{base_url}/rerank"
                return f"{base_url}/v1/rerank"
            return base_url
        else:
            # Modal 自定义인터페이스
            return base_url

    def _build_payload(self, query: str, documents: List[str], top_n: Optional[int]) -> Dict[str, Any]:
        """요청 본문 구성"""
        if self.config.rerank_api_type == "openai":
            # Jina/Cohere 格式
            payload: Dict[str, Any] = {
                "query": query,
                "documents": documents,
                "model": self.config.rerank_model
            }
            if top_n:
                payload["top_n"] = top_n
            return payload
        else:
            # Modal 格式
            payload = {"query": query, "documents": documents}
            if top_n:
                payload["top_n"] = top_n
            return payload

    def _parse_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """응답 파싱"""
        if self.config.rerank_api_type == "openai":
            # Jina/Cohere 格式: {"results": [{"index": 0, "relevance_score": 0.9}, ...]}
            return data.get("results", [])
        else:
            # Modal 格式: {"results": [...]}
            return data.get("results", [])

    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: Optional[int] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Rerank 서비스 호출(재시도 메커니즘 포함)"""
        if not documents:
            return []

        timeout = self.config.cold_start_timeout if not self._warmed_up else self.config.normal_timeout
        max_retries = getattr(self.config, 'api_max_retries', 3)
        base_delay = getattr(self.config, 'api_retry_delay', 1.0)

        async with self.sem:
            start = time.time()
            session = await self._get_session()

            for attempt in range(max_retries):
                try:
                    url = self._build_url()
                    headers = self._build_headers()
                    payload = self._build_payload(query, documents, top_n)

                    async with session.post(
                        url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()

                            self.stats.total_calls += 1
                            self.stats.total_time += time.time() - start
                            self._warmed_up = True

                            return self._parse_response(data)

                        # 재시도 가능한 상태 코드
                        if resp.status in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            print(f"[WARN] Rerank {resp.status}, retrying in {delay:.1f}s ({attempt + 1}/{max_retries})")
                            await asyncio.sleep(delay)
                            continue

                        self.stats.errors += 1
                        err_text = await resp.text()
                        print(f"[ERR] Rerank {resp.status}: {err_text[:200]}")
                        return None

                except asyncio.TimeoutError:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"[WARN] Rerank timeout, retrying in {delay:.1f}s ({attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    self.stats.errors += 1
                    print(f"[ERR] Rerank: Timeout after {max_retries} attempts")
                    return None

                except Exception as e:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"[WARN] Rerank error: {e}, retrying in {delay:.1f}s ({attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    self.stats.errors += 1
                    print(f"[ERR] Rerank: {e}")
                    return None

            return None

    async def warmup(self):
        """서비스 워밍업"""
        await self.rerank("test", ["doc1", "doc2"])
        self._warmed_up = True


class ModalAPIClient:
    """
    통합 API 클라이언트(이전 인터페이스 호환)

    Embedding + Rerank 클라이언트 통합, 하위 호환 유지
    """

    def __init__(self, config=None):
        self.config = config or get_config()
        self._embed_client = EmbeddingAPIClient(self.config)
        self._rerank_client = RerankAPIClient(self.config)

        # 이전 코드 호환 세마포어
        self.sem_embed = self._embed_client.sem
        self.sem_rerank = self._rerank_client.sem

        self._warmed_up = {"embed": False, "rerank": False}
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def stats(self) -> Dict[str, APIStats]:
        return {
            "embed": self._embed_client.stats,
            "rerank": self._rerank_client.stats
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        # 复用 embed client 的 session
        return await self._embed_client._get_session()

    async def close(self):
        await self._embed_client.close()
        await self._rerank_client.close()

    # ==================== 워밍업 ====================

    async def warmup(self):
        """Embedding 및 Rerank 서비스 워밍업"""
        print("[WARMUP] Warming up Embed + Rerank...")
        start = time.time()

        tasks = [self._warmup_embed(), self._warmup_rerank()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for name, result in zip(["Embed", "Rerank"], results):
            if isinstance(result, Exception):
                print(f"  [FAIL] {name}: {result}")
            else:
                print(f"  [OK] {name} ready")

        print(f"[WARMUP] Done in {time.time() - start:.1f}s")

    async def _warmup_embed(self):
        await self._embed_client.warmup()
        self._warmed_up["embed"] = True

    async def _warmup_rerank(self):
        await self._rerank_client.warmup()
        self._warmed_up["rerank"] = True

    # ==================== Embedding API ====================

    async def embed(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Embedding 서비스 호출"""
        return await self._embed_client.embed(texts)

    async def embed_batch(
        self, texts: List[str], *, skip_failures: bool = True
    ) -> List[Optional[List[float]]]:
        """배치 Embedding"""
        return await self._embed_client.embed_batch(texts, skip_failures=skip_failures)

    # ==================== Rerank API ====================

    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: Optional[int] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Rerank 서비스 호출"""
        return await self._rerank_client.rerank(query, documents, top_n)

    # ==================== 통계 ====================

    def print_stats(self):
        print("\n[API STATS]")
        for name, stats in self.stats.items():
            if stats.total_calls > 0:
                avg_time = stats.total_time / stats.total_calls
                print(f"  {name.upper()}: {stats.total_calls} calls, "
                      f"{stats.total_time:.1f}s total, "
                      f"{avg_time:.2f}s avg, "
                      f"{stats.errors} errors")


# 전역 클라이언트
_client: Optional[ModalAPIClient] = None


def get_client(config=None) -> ModalAPIClient:
    global _client
    if _client is None or config is not None:
        _client = ModalAPIClient(config)
    return _client
