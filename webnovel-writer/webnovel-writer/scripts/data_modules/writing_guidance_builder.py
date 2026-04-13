#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Writing guidance and checklist builders.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .genre_aliases import to_profile_key


GENRE_GUIDANCE_TEXT: dict[str, str] = {
    “xianxia”: “장르 가중: 업그레이드/대항 결과의 가시적 피드백 강화, 용어 설명 후치.”,
    “shuangwen”: “장르 가중: 높은 카타르시스 밀도 유지, 주요 쾌감포인트 외에 부축 반전 추가.”,
    “urban-power”: “장르 가중: 사회 피드백 체인 우선 (타인 반응→자원 변화→지위 변화).”,
    “romance”: “장르 가중: 매 챕터 관계 위치 변화 추진, 감정 제자리 회전 방지.”,
    “mystery”: “장르 가중: 단서는 반드시 회수 가능, 규칙 충돌로 서스펜스 생성 우선.”,
    “rules-mystery”: “장르 가중: 규칙이 설명보다 먼저, 대가가 승리보다 먼저.”,
    “zhihu-short”: “장르 가중: 복선 압축, 반전과 고강도 결미 훅 우선.”,
    “substitute”: “장르 가중: 오해-밀당-결단 체인 강화, 반복 학대 포인트 방지.”,
    “esports”: “장르 가중: 매 대전마다 최소 한 가지 전술 결정 포인트와 그 결과 명확히 서술.”,
    “livestream”: “장르 가중: '외부 피드백→주인공 대응→데이터 변화' 즉시 폐쇄 루프 강화.”,
    “cosmic-horror”: “장르 가중: 공포는 규칙과 대가에서 비롯, 막연한 공포 묘사에 의존하지 않음.”,
}


GENRE_METHOD_ANCHORS: dict[str, dict[str, str]] = {
    "xianxia": {
        "pressure_source": "자원 쟁탈/경지 압제",
        "release_target": "주인공이 주도적으로 돌파하여 가시적 수익 획득",
    },
    "urban-power": {
        "pressure_source": "계층 포지션/권력 압제",
        "release_target": "주인공이 자원 게임을 통해 지위와 보상 획득",
    },
    "romance": {
        "pressure_source": "관계 오해/감정 밀당",
        "release_target": "관계 위치 변화 착지 후 다음 단계 약속 형성",
    },
    "mystery": {
        "pressure_source": "단서 결핍/규칙 충돌",
        "release_target": "검증 가능한 새 단서 제시 후 미지 영역 유지",
    },
    "rules-mystery": {
        "pressure_source": "규칙 반작용/대가 증가",
        "release_target": "대가로 돌파 후 더 높은 규칙 문제 남김",
    },
    "zhihu-short": {
        "pressure_source": "정보 격차/입장 충돌",
        "release_target": "반전 실현 후 고강도 결미 훅 형성",
    },
    "substitute": {
        "pressure_source": "신분 오독/감정 대치",
        "release_target": "오해 체인이 명확한 결단으로 진행",
    },
    "esports": {
        "pressure_source": "전술 압제/리듬 불균형",
        "release_target": "핵심 결정이 효력 발휘하여 전세 우위로 전환",
    },
    "livestream": {
        "pressure_source": "여론 변동/데이터 하락",
        "release_target": "현장 대응으로 가시적 데이터 반등 형성",
    },
    "cosmic-horror": {
        "pressure_source": "인지 왜곡/규칙 침식",
        "release_target": "명확한 대가로 단계적 생존 창구 확보",
    },
    "history-travel": {
        "pressure_source": "역사 관성/예교 저항",
        "release_target": "지식 우위 실현 후 새로운 연쇄 반응 유발",
    },
    "game-lit": {
        "pressure_source": "시스템 규칙 제한/자원 희소",
        "release_target": "수치 돌파 후 더 높은 층급 위협 노출",
    },
}


def build_methodology_strategy_card(
    *,
    chapter: int,
    reader_signal: Dict[str, Any],
    genre_profile: Dict[str, Any],
    label: str = "digital-serial-v1",
) -> Dict[str, Any]:
    genre = str(genre_profile.get("genre") or "").strip()
    profile_key = to_profile_key(genre) or "general"

    hook_usage = reader_signal.get("hook_type_usage") or {}
    pattern_usage = reader_signal.get("pattern_usage") or {}
    review_trend = reader_signal.get("review_trend") or {}
    low_ranges = reader_signal.get("low_score_ranges") or []

    dominant_hook = ""
    if isinstance(hook_usage, dict) and hook_usage:
        dominant_hook = max(hook_usage.items(), key=lambda kv: kv[1])[0]

    dominant_pattern = ""
    if isinstance(pattern_usage, dict) and pattern_usage:
        dominant_pattern = max(pattern_usage.items(), key=lambda kv: kv[1])[0]

    overall_avg = float(review_trend.get("overall_avg") or 0.0)
    has_low_range = bool(low_ranges)
    hook_variety = len(hook_usage) if isinstance(hook_usage, dict) else 0
    pattern_variety = len(pattern_usage) if isinstance(pattern_usage, dict) else 0

    next_reason_clarity = 70.0 + (4.0 if has_low_range else 8.0)
    anchor_effectiveness = 68.0 + (6.0 if dominant_hook else 0.0) + (4.0 if overall_avg >= 75 else -4.0)
    rhythm_naturalness = 65.0 + min(10.0, float(hook_variety + pattern_variety) * 2.0)

    risk_flags: List[str] = []
    if has_low_range:
        risk_flags.append("low_score_recency")
    if dominant_pattern:
        risk_flags.append("pattern_overuse_watch")
    if overall_avg > 0 and overall_avg < 75:
        risk_flags.append("readability_guard")

    stage_mod = chapter % 5
    if stage_mod in {1, 2}:
        stage = "build_up"
    elif stage_mod in {3, 4}:
        stage = "confront"
    else:
        stage = "release"

    anchor_preset = GENRE_METHOD_ANCHORS.get(
        profile_key,
        {
            "pressure_source": "생존 목표/자원 경쟁",
            "release_target": "주인공이 단계 목표를 완료하고 새로운 행동 이유를 남김",
        },
    )

    return {
        "enabled": True,
        "framework": label,
        "pilot": profile_key,
        "genre_profile_key": profile_key,
        "chapter_stage": stage,
        "emotion_anchor": {
            "pressure_source": anchor_preset["pressure_source"],
            "release_target": anchor_preset["release_target"],
            "position_hint": "전반부에 압력 설정, 중후반부에 해소, 고정 위치 배치 지양",
        },
        "long_arc_controls": {
            "map_transition": "단계 전환 시 기존 자산과 관계 장부를 승계, 능력과 수익 초기화 방지",
            "power_guard": "핵심 승리에는 반드시 메커니즘 근거 제시 (정보/자원/대가/전략)",
            "antagonist_model": "악역은 목표-수단-대가 3요소를 갖춰야 하며, 도구적 추진 지양",
        },
        "serialization_ops": {
            "next_reason": "챕터 말미 또는 후반부에 복술 가능한 다음 챕터 동기 문장 제시",
            "interaction_note": "논의 가능한 분기점 하나를 남겨 연재 상호작용 피드백 유도",
        },
        "observability": {
            "next_reason_clarity": round(max(0.0, min(100.0, next_reason_clarity)), 2),
            "anchor_effectiveness": round(max(0.0, min(100.0, anchor_effectiveness)), 2),
            "rhythm_naturalness": round(max(0.0, min(100.0, rhythm_naturalness)), 2),
        },
        "signals": {
            "dominant_hook": dominant_hook,
            "dominant_pattern": dominant_pattern,
            "risk_flags": risk_flags,
        },
    }


def build_methodology_guidance_items(strategy_card: Dict[str, Any]) -> List[str]:
    if not isinstance(strategy_card, dict) or not strategy_card.get("enabled"):
        return []

    observability = strategy_card.get("observability") or {}
    signals = strategy_card.get("signals") or {}
    risk_flags = list(signals.get("risk_flags") or [])
    stage = str(strategy_card.get("chapter_stage") or "build_up")
    genre_key = str(strategy_card.get("genre_profile_key") or strategy_card.get("pilot") or "general")

    stage_text = {
        "build_up": "이번 챕터는 복선 압력 위주로, 위협과 대가의 체감 가능한 복선을 우선 배치.",
        "confront": "이번 챕터는 정면 대항 위주로, 돌파 경로가 명확하고 복기 가능하도록 확보.",
        "release": "이번 챕터는 해소와 여파 위주로, 실질 수익을 제시하고 다음 문제를 유도.",
    }.get(stage, "이번 챕터는 압력-돌파-여파의 완전한 체인을 유지.")

    items = [
        f"방법론 전략 (범용/{genre_key}): {stage_text}",
        "장기선 제어: 맵 전환 시 기존 자산 승계, 주인공이 새 맵 진입 후 능력과 자원 초기화 방지.",
        "메커니즘 제어: 핵심 승리에는 반드시 메커니즘 근거와 대가를 서술, 순수 광환 압도 지양.",
        (
            "연재 상호작용: 논의 가능한 분기점 하나를 남겨 다음 챕터 추독 동기 강화."
            f" (next_reason={observability.get('next_reason_clarity')})"
        ),
    ]

    if "pattern_overuse_watch" in risk_flags:
        dominant_pattern = str(signals.get("dominant_pattern") or "").strip()
        if dominant_pattern:
            items.append(f”리스크 보정: 최근 \”{dominant_pattern}\” 빈도 과다, 이번 챕터에 이질적 부축 하나를 추가하여 피로 방지.”)
    if "readability_guard" in risk_flags:
        items.append("리스크 보정: 최근 검토 평균점 낮음, 이번 챕터는 우선 단락 동작-결과 폐쇄루프와 가독성 확보.")

    return items


def build_guidance_items(
    *,
    chapter: int,
    reader_signal: Dict[str, Any],
    genre_profile: Dict[str, Any],
    low_score_threshold: float,
    hook_diversify_enabled: bool,
) -> Dict[str, Any]:
    guidance: List[str] = []

    low_ranges = reader_signal.get("low_score_ranges") or []
    if low_ranges:
        worst = min(
            low_ranges,
            key=lambda row: float(row.get("overall_score", 9999)),
        )
        guidance.append(
            f"제{chapter}장 우선 수정 최근 저점 구간 문제: {worst.get('start_chapter')}-{worst.get('end_chapter')}장 참고, 충돌 추진과 결미 훅 강화."
        )

    hook_usage = reader_signal.get("hook_type_usage") or {}
    if hook_usage and hook_diversify_enabled:
        dominant_hook = max(hook_usage.items(), key=lambda kv: kv[1])[0]
        guidance.append(
            f”최근 훅 유형 \”{dominant_hook}\” 사용 과다, 이번 챕터는 훅 차별화 제안, 연속 동일 구조 지양.”
        )

    pattern_usage = reader_signal.get("pattern_usage") or {}
    if pattern_usage:
        top_pattern = max(pattern_usage.items(), key=lambda kv: kv[1])[0]
        guidance.append(
            f”쾌감포인트 모드 \”{top_pattern}\” 최근 고빈도, 이번 챕터는 주 쾌감포인트를 유지하되 새 쾌감포인트 부축 추가.”
        )

    review_trend = reader_signal.get("review_trend") or {}
    overall_avg = review_trend.get("overall_avg")
    if isinstance(overall_avg, (int, float)) and float(overall_avg) < low_score_threshold:
        guidance.append(
            f"최근 검토 평균점 {overall_avg:.1f}이 임계값 {low_score_threshold:.1f} 미만, 안정 우선 제안: 장면 전환 줄이고 매 단락마다 동작-결과 폐쇄루프 보완."
        )

    genre = str(genre_profile.get("genre") or "").strip()
    refs = genre_profile.get("reference_hints") or []
    if genre:
        guidance.append(f”장르 앵커링: \”{genre}\” 서사 메인 스토리에 따라 추진, 장르 독자 기대의 안정적 실현 유지.”)
    if refs:
        guidance.append(f"장르 전략 실행 팁: {refs[0]}")

    guidance.append("웹소설 리듬 기준선: 챕터 서두 300자 이내에 목표와 저항 제시, 챕터 말미에 미해결 문제 남김.")
    guidance.append("실현 밀도 기준선: 600-900자마다 소규모 실현 1회, 이번 챕터에 최소 1곳 정량화 가능한 변화 확보.")

    normalized_genre = to_profile_key(genre)
    genre_hint = GENRE_GUIDANCE_TEXT.get(normalized_genre)
    if genre_hint:
        guidance.append(genre_hint)

    composite_hints = genre_profile.get("composite_hints") or []
    if composite_hints:
        guidance.append(f"복합 장르 시너지: {composite_hints[0]}")

    if not guidance:
        guidance.append("이번 챕터는 기본값 고가독성 전략 실행: 충돌 전치, 정보 후치, 단락 말미 훅 남김.")

    return {
        "guidance": guidance,
        "low_ranges": low_ranges,
        "hook_usage": hook_usage,
        "pattern_usage": pattern_usage,
        "genre": genre,
    }


def build_writing_checklist(
    *,
    guidance_items: List[str],
    reader_signal: Dict[str, Any],
    genre_profile: Dict[str, Any],
    strategy_card: Dict[str, Any] | None = None,
    min_items: int,
    max_items: int,
    default_weight: float,
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    def _add_item(
        item_id: str,
        label: str,
        *,
        weight: float | None = None,
        required: bool = False,
        source: str = "writing_guidance",
        verify_hint: str = "",
    ) -> None:
        if len(items) >= max_items:
            return
        if any(row.get("id") == item_id for row in items):
            return

        item_weight = float(weight if weight is not None else default_weight)
        if item_weight <= 0:
            item_weight = default_weight

        items.append(
            {
                "id": item_id,
                "label": label,
                "weight": round(item_weight, 2),
                "required": bool(required),
                "source": source,
                "verify_hint": verify_hint,
            }
        )

    low_ranges = reader_signal.get("low_score_ranges") or []
    if low_ranges:
        worst = min(low_ranges, key=lambda row: float(row.get("overall_score", 9999)))
        span = f"{worst.get('start_chapter')}-{worst.get('end_chapter')}"
        _add_item(
            "fix_low_score_range",
            f"저점 구간 문제 수정 (제{span}장 참고)",
            weight=max(default_weight, 1.4),
            required=True,
            source="reader_signal.low_score_ranges",
            verify_hint="최소 1곳 충돌 업그레이드 완료하고, 단락 말미에 훅 남김.",
        )

    hook_usage = reader_signal.get("hook_type_usage") or {}
    if hook_usage:
        dominant_hook = max(hook_usage.items(), key=lambda kv: kv[1])[0]
        _add_item(
            "hook_diversification",
            f”훅 차별화 (단일 \”{dominant_hook}\” 연속 사용 지양)”,
            weight=max(default_weight, 1.2),
            required=True,
            source=”reader_signal.hook_type_usage”,
            verify_hint=”결미 훅 유형이 최근 20장 주요 유형과 최소 1곳 차이 필요.”,
        )

    pattern_usage = reader_signal.get("pattern_usage") or {}
    if pattern_usage:
        top_pattern = max(pattern_usage.items(), key=lambda kv: kv[1])[0]
        _add_item(
            "coolpoint_combo",
            f"주 쾌감포인트 + 부 쾌감포인트 조합 (주 쾌감포인트: {top_pattern})",
            weight=default_weight,
            required=False,
            source="reader_signal.pattern_usage",
            verify_hint="신규 부 쾌감포인트 최소 1개, 주 쾌감포인트와 인과 체인 형성.",
        )

    review_trend = reader_signal.get("review_trend") or {}
    overall_avg = review_trend.get("overall_avg")
    if isinstance(overall_avg, (int, float)):
        _add_item(
            "readability_loop",
            "단락 가독성 폐쇄루프 (동작→결과→감정)",
            weight=max(default_weight, 1.1),
            required=True,
            source="reader_signal.review_trend",
            verify_hint="3개 단락 표본 검사, 모두 동작-결과 폐쇄루프 포함.",
        )

    genre = str(genre_profile.get("genre") or "").strip()
    if genre:
        _add_item(
            "genre_anchor_consistency",
            f"장르 앵커링 일관성 ({genre})",
            weight=max(default_weight, 1.1),
            required=True,
            source="genre_profile.genre",
            verify_hint="주 충돌과 장르 핵심 약속이 일관성 유지.",
        )

    if isinstance(strategy_card, dict) and strategy_card.get("enabled"):
        _add_item(
            “methodology_next_reason”,
            “방법론: 다음 챕터 동기가 복술 가능해야 함 (챕터 말미 또는 후반부 모두 가능)”,
            weight=default_weight,
            required=False,
            source=”methodology.next_reason”,
            verify_hint=”'왜 다음 챕터를 클릭해야 하는가'의 동기 문장 한 줄 추출.”,
        )
        _add_item(
            "methodology_power_guard",
            "방법론: 월급(레벨 초월)과 돌파에 메커니즘 근거와 대가 제시",
            weight=default_weight,
            required=False,
            source="methodology.power_guard",
            verify_hint="최소 1개 메커니즘 근거와 1개 대가를 명확히 서술."
        )
        _add_item(
            "methodology_antagonist_pressure",
            "방법론: 악역 행동에 목표-수단-대가 구비",
            weight=default_weight,
            required=False,
            source="methodology.antagonist",
            verify_hint="악역이 도구적 추진이 아닌, 설명 가능한 행동 논리를 갖춰야 함.",
        )

    for idx, text in enumerate(guidance_items, start=1):
        if len(items) >= max_items:
            break
        label = str(text).strip()
        if not label:
            continue
        _add_item(
            f"guidance_item_{idx}",
            label,
            weight=default_weight,
            required=False,
            source="writing_guidance.guidance_items",
            verify_hint="완료 후 본문(chapters)에서 해당 단락 위치 확인 가능.",
        )

    fallback_items = [
        (
            "opening_conflict",
            "서두 300자 이내에 충돌 트리거 제시",
            "첫 단락에 명확한 목표와 저항 등장.",
        ),
        (
            "scene_goal_block",
            "장면 목표와 저항 명확화",
            "각 장면에 최소 1개 검증 가능한 목표.",
        ),
        (
            "ending_hook",
            "단락 말미에 훅을 남기고 다음 문제 유도",
            "결미에 미해결 문제 또는 다음 행동 등장.",
        ),
    ]
    for item_id, label, verify_hint in fallback_items:
        if len(items) >= min_items or len(items) >= max_items:
            break
        _add_item(
            item_id,
            label,
            weight=default_weight,
            required=False,
            source="fallback",
            verify_hint=verify_hint,
        )

    return items[:max_items]


def is_checklist_item_completed(item: Dict[str, Any], reader_signal: Dict[str, Any]) -> bool:
    item_id = str(item.get("id") or "")
    if item_id in {"fix_low_score_range", "readability_loop"}:
        review_trend = reader_signal.get("review_trend") or {}
        overall = review_trend.get("overall_avg")
        return isinstance(overall, (int, float)) and float(overall) >= 75.0

    if item_id == "hook_diversification":
        hook_usage = reader_signal.get("hook_type_usage") or {}
        return len(hook_usage) >= 2

    if item_id == "coolpoint_combo":
        pattern_usage = reader_signal.get("pattern_usage") or {}
        return len(pattern_usage) >= 2

    if item_id == "genre_anchor_consistency":
        return True

    source = str(item.get("source") or "")
    if source.startswith("fallback"):
        return True

    if source.startswith("methodology."):
        # 방법론 항목은 현재 소프트 팁으로, 관찰과 유도만 수행하며 감점에 참여하지 않음.
        return True

    return False
