#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query router for RAG requests."""
from __future__ import annotations

import re
from typing import Any, Dict, List


class QueryRouter:
    def __init__(self):
        self.intent_patterns = {
            "relationship": [r"관계", r"도표", r"타임라인", r"누구와누구", r"적대", r"동맹"],
            "entity": [r"인물", r"캐릭터", r"누구", r"신분", r"별칭"],
            "scene": [r"장소", r"장면", r"어디", r"위치"],
            "setting": [r"설정", r"규칙", r"체계", r"세계관"],
            "plot": [r"스토리", r"발생", r"사건", r"경과"],
        }
        self.patterns = {
            "entity": list(self.intent_patterns["entity"]),
            "scene": list(self.intent_patterns["scene"]),
            "setting": list(self.intent_patterns["setting"]),
            "plot": list(self.intent_patterns["plot"]),
        }

    def _extract_entities(self, query: str) -> List[str]:
        # 경량 휴리스틱 추출: 길이 2-6의 한중 구문 추출, 일반 쿼리 단어 필터링
        candidates = re.findall(r"[\u4e00-\u9fff가-힣]{2,6}", query)
        stopwords = {
            "관계",
            "도표",
            "타임라인",
            "스토리",
            "발생",
            "사건",
            "캐릭터",
            "인물",
            "설정",
            "세계관",
            "장소",
            "장면",
        }
        entities: List[str] = []
        for c in candidates:
            if c in stopwords:
                continue
            if c not in entities:
                entities.append(c)
        return entities[:4]

    def _extract_time_scope(self, query: str) -> Dict[str, Any]:
        m_range = re.search(r"(?:제?\s*)?(\d+)\s*[-~부터에서]\s*(\d+)\s*(?:장|화)", query)
        if m_range:
            start = int(m_range.group(1))
            end = int(m_range.group(2))
            if start > end:
                start, end = end, start
            return {"from_chapter": start, "to_chapter": end}

        m_single = re.search(r"(?:제?\s*)?(\d+)\s*(?:장|화)", query)
        if m_single:
            chapter = int(m_single.group(1))
            return {"from_chapter": chapter, "to_chapter": chapter}

        return {}

    def route_intent(self, query: str) -> Dict[str, Any]:
        query = str(query or "")
        intent = "plot"
        for intent_name, patterns in self.intent_patterns.items():
            if any(re.search(pat, query) for pat in patterns):
                intent = intent_name
                break

        time_scope = self._extract_time_scope(query)
        entities = self._extract_entities(query)
        needs_graph = intent == "relationship" or "관계" in query or "도표" in query
        return {
            "intent": intent,
            "entities": entities,
            "time_scope": time_scope,
            "needs_graph": needs_graph,
            "raw_query": query,
        }

    def plan_subqueries(self, intent_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        intent = str((intent_payload or {}).get("intent") or "plot")
        entities = list((intent_payload or {}).get("entities") or [])
        time_scope = dict((intent_payload or {}).get("time_scope") or {})
        needs_graph = bool((intent_payload or {}).get("needs_graph"))

        steps: List[Dict[str, Any]] = []
        if intent == "relationship":
            steps.append(
                {
                    "name": "relationship_graph",
                    "strategy": "graph_lookup",
                    "entities": entities,
                    "time_scope": time_scope,
                }
            )
            steps.append(
                {
                    "name": "relationship_evidence",
                    "strategy": "graph_hybrid",
                    "entities": entities,
                    "time_scope": time_scope,
                }
            )
            return steps

        if needs_graph and entities:
            steps.append(
                {
                    "name": "graph_enhanced_retrieval",
                    "strategy": "graph_hybrid",
                    "entities": entities,
                    "time_scope": time_scope,
                }
            )
            return steps

        strategy_map = {
            "entity": "hybrid",
            "scene": "bm25",
            "setting": "bm25",
            "plot": "hybrid",
        }
        steps.append(
            {
                "name": "default_retrieval",
                "strategy": strategy_map.get(intent, "hybrid"),
                "entities": entities,
                "time_scope": time_scope,
            }
        )
        return steps

    def route(self, query: str) -> str:
        return str(self.route_intent(query).get("intent") or "plot")

    def split(self, query: str) -> List[str]:
        parts = re.split(r"[，,；;및과]\s*", query)
        return [p.strip() for p in parts if p.strip()]
