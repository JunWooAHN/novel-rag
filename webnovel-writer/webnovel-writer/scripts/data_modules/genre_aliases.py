#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genre alias normalization and profile key mapping.
"""

from __future__ import annotations


GENRE_INPUT_ALIASES: dict[str, str] = {
    "수선/현판타지": "수선",
    "현판타지수선": "수선",
    "현판타지": "수선",
    "수진": "수선",
    "도시수진": "도시이능",
    "도시고무": "고무",
    "도시기문": "도시기발",
    "고대기발": "고대로맨스",
    "게임e스포츠": "e스포츠",
    "e스포츠문": "e스포츠",
    "방송": "방송문",
    "라방": "방송문",
    "스트리머": "방송문",
    "크계": "크툴루",
    "크계서스펜스": "크툴루",
}


GENRE_PROFILE_KEY_ALIASES: dict[str, str] = {
    "수선": "xianxia",
    "수선/현판타지": "xianxia",
    "현판타지": "xianxia",
    "쾌감문/시스템류": "shuangwen",
    "고무": "xianxia",
    "서판타지": "xianxia",
    "도시이능": "urban-power",
    "도시기발": "urban-power",
    "도시일상": "urban-power",
    "막장로맨스": "romance",
    "고대로맨스": "romance",
    "청춘달콤": "romance",
    "대역문": "substitute",
    "규칙괴담": "rules-mystery",
    "서스펜스기발": "mystery",
    "서스펜스심령": "mystery",
    "지후단편": "zhihu-short",
    "e스포츠": "esports",
    "방송문": "livestream",
    "크툴루": "cosmic-horror",
    "역사기발": "history-travel",
}


def normalize_genre_token(token: str) -> str:
    value = str(token or "").strip()
    if not value:
        return ""
    return GENRE_INPUT_ALIASES.get(value, value)


def to_profile_key(genre: str) -> str:
    value = str(genre or "").strip()
    if not value:
        return ""
    normalized = normalize_genre_token(value)
    return GENRE_PROFILE_KEY_ALIASES.get(normalized, normalized.lower())
