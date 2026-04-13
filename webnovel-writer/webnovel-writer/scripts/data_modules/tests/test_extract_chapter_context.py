#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from pathlib import Path


def test_extract_state_summary_accepts_dominant_key(tmp_path):
    scripts_dir = Path(__file__).resolve().parents[2]
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from extract_chapter_context import extract_state_summary

    state = {
        "progress": {"current_chapter": 12, "total_words": 12345},
        "protagonist_state": {
            "power": {"realm": "축기", "layer": 2},
            "location": "종문",
            "golden_finger": {"name": "시스템", "level": 1},
        },
        "strand_tracker": {
            "history": [
                {"chapter": 10, "dominant": "quest"},
                {"chapter": 11, "dominant": "fire"},
            ]
        },
    }

    webnovel_dir = tmp_path / ".webnovel"
    webnovel_dir.mkdir(parents=True, exist_ok=True)
    (webnovel_dir / "state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    text = extract_state_summary(tmp_path)
    assert "Ch10:quest" in text
    assert "Ch11:fire" in text


def test_extract_chapter_outline_supports_hyphen_filename(tmp_path):
    scripts_dir = Path(__file__).resolve().parents[2]
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from extract_chapter_context import extract_chapter_outline

    outline_dir = tmp_path / "outline"
    outline_dir.mkdir(parents=True, exist_ok=True)
    (outline_dir / "vol_1-detailed.md").write_text("### chapter 1: 테스트 제목\n테스트 개요", encoding="utf-8")

    outline = extract_chapter_outline(tmp_path, 1)
    assert "### chapter 1: 테스트 제목" in outline
    assert "테스트 개요" in outline


def test_extract_chapter_outline_prefers_state_volume_mapping(tmp_path):
    scripts_dir = Path(__file__).resolve().parents[2]
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from extract_chapter_context import extract_chapter_outline

    webnovel_dir = tmp_path / ".webnovel"
    webnovel_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "progress": {
            "volumes_planned": [
                {"volume": 1, "chapters_range": "1-10"},
                {"volume": 2, "chapters_range": "11-20"},
            ]
        }
    }
    (webnovel_dir / "state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    outline_dir = tmp_path / "outline"
    outline_dir.mkdir(parents=True, exist_ok=True)
    (outline_dir / "vol_2-detailed.md").write_text("### chapter 12: V2제목\nV2개요", encoding="utf-8")

    outline = extract_chapter_outline(tmp_path, 12)
    assert "### chapter 12: V2제목" in outline
    assert "V2개요" in outline


def test_extract_chapter_outline_falls_back_when_state_has_no_match(tmp_path):
    scripts_dir = Path(__file__).resolve().parents[2]
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from extract_chapter_context import extract_chapter_outline

    webnovel_dir = tmp_path / ".webnovel"
    webnovel_dir.mkdir(parents=True, exist_ok=True)
    state = {"progress": {"volumes_planned": [{"volume": 1, "chapters_range": "1-10"}]}}
    (webnovel_dir / "state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    outline_dir = tmp_path / "outline"
    outline_dir.mkdir(parents=True, exist_ok=True)
    (outline_dir / "vol_2-detailed.md").write_text("### chapter 60: V2제목\nV2개요", encoding="utf-8")

    outline = extract_chapter_outline(tmp_path, 60)
    assert "### chapter 60: V2제목" in outline
    assert "V2개요" in outline


def test_build_chapter_context_payload_includes_contract_sections(tmp_path):
    scripts_dir = Path(__file__).resolve().parents[2]
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from extract_chapter_context import build_chapter_context_payload
    from data_modules.config import DataModulesConfig
    from data_modules.index_manager import IndexManager, ChapterReadingPowerMeta, ReviewMetrics

    cfg = DataModulesConfig.from_project_root(tmp_path)
    cfg.ensure_dirs()

    state = {
        "project": {"genre": "xuanhuan"},
        "progress": {"current_chapter": 3, "total_words": 9000},
        "protagonist_state": {
            "power": {"realm": "축기", "layer": 2},
            "location": "종문",
            "golden_finger": {"name": "시스템", "level": 1},
        },
        "strand_tracker": {"history": [{"chapter": 2, "dominant": "quest"}]},
        "chapter_meta": {},
        "disambiguation_warnings": [],
        "disambiguation_pending": [],
    }
    (cfg.webnovel_dir / "state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    summaries_dir = cfg.webnovel_dir / "summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)
    (summaries_dir / "ch0002.md").write_text("## 줄거리 요약\n이전 챕터 요약", encoding="utf-8")

    outline_dir = tmp_path / "outline"
    outline_dir.mkdir(parents=True, exist_ok=True)
    (outline_dir / "vol_1 detailed.md").write_text("### chapter 3: 테스트 제목\n테스트 개요", encoding="utf-8")

    refs_dir = tmp_path / ".claude" / "references"
    refs_dir.mkdir(parents=True, exist_ok=True)
    (refs_dir / "genre-profiles.md").write_text("## xuanhuan\n- 성장 라인 명확", encoding="utf-8")
    (refs_dir / "reading-power-taxonomy.md").write_text("## xuanhuan\n- 서스펜스훅우선", encoding="utf-8")

    idx = IndexManager(cfg)
    idx.save_chapter_reading_power(
        ChapterReadingPowerMeta(chapter=2, hook_type="서스펜스훅", hook_strength="strong", coolpoint_patterns=["신분정체폭로"])
    )
    idx.save_review_metrics(
        ReviewMetrics(start_chapter=1, end_chapter=2, overall_score=71, dimension_scores={"plot": 71})
    )

    payload = build_chapter_context_payload(tmp_path, 3)
    assert payload["context_contract_version"] == "v2"
    assert payload.get("context_weight_stage") in {"early", "mid", "late"}
    assert "writing_guidance" in payload
    assert isinstance(payload["writing_guidance"].get("guidance_items"), list)
    assert isinstance(payload["writing_guidance"].get("checklist"), list)
    assert isinstance(payload["writing_guidance"].get("checklist_score"), dict)
    assert payload["genre_profile"].get("genre") == "xuanhuan"
    assert "rag_assist" in payload
    assert isinstance(payload["rag_assist"], dict)
    assert payload["rag_assist"].get("invoked") is False


def test_render_text_contains_writing_guidance_section(tmp_path):
    scripts_dir = Path(__file__).resolve().parents[2]
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from extract_chapter_context import _render_text

    payload = {
        "chapter": 10,
        "outline": "테스트 개요",
        "previous_summaries": ["### 제9챕터 요약\n이전 장"],
        "state_summary": "상태",
        "context_contract_version": "v2",
        "context_weight_stage": "early",
        "reader_signal": {"review_trend": {"overall_avg": 72}, "low_score_ranges": [{"start_chapter": 8, "end_chapter": 9}]},
        "genre_profile": {
            "genre": "xuanhuan",
            "genres": ["xuanhuan", "realistic"],
            "composite_hints": ["현환으로 메인 스토리 추진, 현실 이슈 표현 유지"],
            "reference_hints": ["성장 라인 명확"],
        },
        "writing_guidance": {
            "guidance_items": ["낮은 점수 먼저 수정", "훅 차별화"],
            "checklist": [
                {
                    "id": "fix_low_score_range",
                    "label": "낮은 점수 구간 문제 수정",
                    "weight": 1.4,
                    "required": True,
                    "source": "reader_signal.low_score_ranges",
                    "verify_hint": "최소 1곳 충돌 업그레이드 완료",
                }
            ],
            "checklist_score": {
                "score": 81.5,
                "completion_rate": 0.66,
                "required_completion_rate": 0.75,
            },
            "methodology": {
                "enabled": True,
                "framework": "digital-serial-v1",
                "pilot": "xianxia",
                "genre_profile_key": "xianxia",
                "chapter_stage": "confront",
                "observability": {
                    "next_reason_clarity": 78.0,
                    "anchor_effectiveness": 74.0,
                    "rhythm_naturalness": 72.0,
                },
                "signals": {"risk_flags": ["pattern_overuse_watch"]},
            },
        },
    }

    text = _render_text(payload)
    assert "## 작성 실행 제안" in text
    assert "낮은 점수 먼저 수정" in text
    assert "## Contract (v2)" in text
    assert "- 컨텍스트 단계 가중치: early" in text
    assert "### 실행 체크리스트(평가 가능)" in text
    assert "- 총 가중치: 1.40" in text
    assert "[필수][w=1.4] 낮은 점수 구간 문제 수정" in text
    assert "### 실행 점수" in text
    assert "- 점수: 81.5" in text
    assert "- 복합 장르: xuanhuan + realistic" in text
    assert "## 장편 방법론 전략" in text
    assert "- 적용 장르: xianxia" in text
    assert "next_reason=78.0" in text


def test_render_text_contains_rag_assist_section_when_hits_exist(tmp_path):
    scripts_dir = Path(__file__).resolve().parents[2]
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from extract_chapter_context import _render_text

    payload = {
        "chapter": 12,
        "outline": "테스트 개요",
        "previous_summaries": [],
        "state_summary": "상태",
        "context_contract_version": "v2",
        "reader_signal": {},
        "genre_profile": {},
        "writing_guidance": {},
        "rag_assist": {
            "invoked": True,
            "mode": "auto",
            "intent": "relationship",
            "query": "제12장 인물 관계와 동기：소염와약로발생충돌",
            "hits": [
                {
                    "chapter": 9,
                    "scene_index": 2,
                    "source": "graph_hybrid",
                    "score": 0.91,
                    "content": "소염와약로수련 방향에서발생이견。",
                }
            ],
        },
    }

    text = _render_text(payload)
    assert "## RAG 검색단서" in text
    assert "- 모드: auto" in text
    assert "[graph_hybrid]" in text
    assert "소염와약로" in text
