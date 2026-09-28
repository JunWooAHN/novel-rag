"""Small localhost-only vLLM completion client for the fixed benchmark."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import aiohttp


@dataclass(frozen=True)
class Completion:
    text: str
    prompt_tokens: int | None
    completion_tokens: int | None


@dataclass(frozen=True)
class RawCompletion:
    status: int
    body: bytes
    elapsed_seconds: float


class CompletionHTTPError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"vLLM HTTP {status}")
        self.status = status
        self.body = body


def local_base(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or not parsed.port:
        raise ValueError("Benchmark endpoint must be localhost HTTP with an explicit port")
    if parsed.path.rstrip("/") not in {"", "/v1"} or parsed.query or parsed.fragment:
        raise ValueError("Benchmark endpoint must be a bare localhost origin or /v1")
    return f"http://127.0.0.1:{parsed.port}/v1"


async def completion(session: aiohttp.ClientSession, url: str, model: str,
                     prompt_ids: list[int], max_tokens: int) -> RawCompletion:
    # The client supplies the verified token IDs; the server must not add BOS.
    if not model or not prompt_ids or any(not isinstance(x, int) or x < 0 for x in prompt_ids) or not 1 <= max_tokens <= 4096:
        raise ValueError("Missing model/prompt or invalid output cap")
    body = {"model": model, "prompt": prompt_ids, "max_tokens": max_tokens,
            "temperature": 0, "top_p": 1, "n": 1, "stream": False}
    start = time.perf_counter()
    async with session.post(local_base(url) + "/completions", json=body) as response:
        raw = await response.read()
        status = response.status
    elapsed = time.perf_counter() - start
    return RawCompletion(status, raw, elapsed)


def parse_completion(response: RawCompletion) -> Completion:
    if response.status != 200:
        raise CompletionHTTPError(response.status, response.body[:2000].decode("utf-8", "replace"))
    if len(response.body) > 2_000_000:
        raise ValueError("vLLM response exceeds bounded JSON size; full body was retained")
    decoded = json.loads(response.body)
    choices = decoded.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0].get("text"), str):
        raise ValueError("vLLM completion response lacks one text choice")
    usage = decoded.get("usage") or {}
    return Completion(choices[0]["text"], usage.get("prompt_tokens"), usage.get("completion_tokens"))
