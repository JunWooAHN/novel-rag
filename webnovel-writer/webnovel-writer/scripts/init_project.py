#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
웹소설 프로젝트 초기화 스크립트

목표：
- 실행 가능한 프로젝트 구조 생성（webnovel-project）
- 생성/업데이트 .webnovel/state.json（런타임 소스 오브 트루스）
- 기본 설정집 및 개요 템플릿 파일 생성（/webnovel-plan 및 /webnovel-write 사용을 위해）

설명：
- 이 스크립트는 /webnovel-init 명령의 "유일한 파일 생성 진입점"입니다（명령 문서와 일관성 유지）.
- 생성되는 콘텐츠는 "템플릿 골격" 위주이며, AI/작가의 후속 보완을 위해 모든 핵심 파일의 존재를 보장합니다.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from runtime_compat import enable_windows_utf8_stdio
from typing import Any, Dict, List
import re

# 보안 수정: 보안 유틸리티 함수 임포트
from security_utils import sanitize_commit_message, atomic_write_json, is_git_available
from project_locator import write_current_project_pointer


# Windows 인코딩 호환성 수정
if sys.platform == "win32":
    enable_windows_utf8_stdio()


def _read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _write_text_if_missing(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    path.write_text(content, encoding="utf-8")


def _split_genre_keys(genre: str) -> list[str]:
    raw = (genre or "").strip()
    if not raw:
        return []
    # 복합 장르 지원：A+B / A+B / A、B / A와B
    raw = re.sub(r"[＋/、]", "+", raw)
    raw = raw.replace("와", "+")
    parts = [p.strip() for p in raw.split("+") if p.strip()]
    return parts or [raw]


def _normalize_genre_key(key: str) -> str:
    aliases = {
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
    return aliases.get(key, key)


def _apply_label_replacements(text: str, replacements: Dict[str, str]) -> str:
    if not text or not replacements:
        return text
    lines = text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        for label, value in replacements.items():
            if not value:
                continue
            prefix = f"- {label}："
            if stripped.startswith(prefix):
                leading = line[: len(line) - len(stripped)]
                lines[i] = f"{leading}{prefix}{value}"
    return "\n".join(lines)


def _parse_tier_map(raw: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if not raw:
        return result
    for part in raw.split(";"):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            key, val = part.split(":", 1)
            result[key.strip()] = val.strip()
    return result


def _render_team_rows(names: List[str], roles: List[str]) -> List[str]:
    rows = []
    for idx, name in enumerate(names):
        role = roles[idx] if idx < len(roles) else ""
        rows.append(f"| {name} | {role or '메인 스토리/서브 라인'} | | | |")
    return rows


def _ensure_state_schema(state: Dict[str, Any]) -> Dict[str, Any]:
    """state.json이 v5.1 아키텍처에 필요한 필드 집합을 갖추도록 보장（v5.4 유지）.

    v5.1 변경:
    - entities_v3 및 alias_index가 index.db로 마이그레이션됨, state.json에 더 이상 저장하지 않음
    - structured_relationships가 index.db relationships 테이블로 마이그레이션됨
    - state.json 간결하게 유지 (< 5KB)
    """
    state.setdefault("project_info", {})
    state.setdefault("progress", {})
    state.setdefault("protagonist_state", {})
    state.setdefault("relationships", {})  # update_state.py에서 이 필드 필요
    state.setdefault("disambiguation_warnings", [])
    state.setdefault("disambiguation_pending", [])
    state.setdefault("world_settings", {"power_system": [], "factions": [], "locations": []})
    state.setdefault("plot_threads", {"active_threads": [], "foreshadowing": []})
    state.setdefault("review_checkpoints", [])
    state.setdefault("chapter_meta", {})
    state.setdefault(
        "strand_tracker",
        {
            "last_quest_chapter": 0,
            "last_fire_chapter": 0,
            "last_constellation_chapter": 0,
            "current_dominant": "quest",
            "chapters_since_switch": 0,
            "history": [],
        },
    )
    # v5.1: entities_v3, alias_index, structured_relationships는 index.db로 마이그레이션 완료
    # 더 이상 state.json에서 이 필드들을 초기화하지 않음

    # progress schema evolution
    state["progress"].setdefault("current_chapter", 0)
    state["progress"].setdefault("total_words", 0)
    state["progress"].setdefault("last_updated", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    state["progress"].setdefault("volumes_completed", [])
    state["progress"].setdefault("current_volume", 1)
    state["progress"].setdefault("volumes_planned", [])

    # protagonist schema evolution
    ps = state["protagonist_state"]
    ps.setdefault("name", "")
    ps.setdefault("power", {"realm": "", "layer": 1, "bottleneck": ""})
    ps.setdefault("location", {"current": "", "last_chapter": 0})
    ps.setdefault("golden_finger", {"name": "", "level": 1, "cooldown": 0, "skills": []})
    ps.setdefault("attributes", {})

    return state


def _build_master_outline(target_chapters: int, *, chapters_per_volume: int = 50) -> str:
    volumes = (target_chapters - 1) // chapters_per_volume + 1 if target_chapters > 0 else 1
    lines: list[str] = [
        "# Master Outline",
        "",
        "> 이 파일은 총강 골격이며, /webnovel-plan으로 권별 개요와 장별 개요로 세분화합니다.",
        "",
        "## Volume Structure",
        "",
    ]

    for v in range(1, volumes + 1):
        start = (v - 1) * chapters_per_volume + 1
        end = min(v * chapters_per_volume, target_chapters)
        lines.extend(
            [
                f"### Vol {v} (chapter {start}-{end})",
                "- 핵심충돌:",
                "- 핵심 쾌감포인트:",
                "- 권말 클라이맥스:",
                "- 주요 등장 캐릭터:",
                "- 핵심 복선 (매설/회수):",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def _inject_volume_rows(template_text: str, target_chapters: int, *, chapters_per_volume: int = 50) -> str:
    """총강 템플릿의 권 테이블에 권 행을 주입."""
    lines = template_text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("| Vol") or line.strip().startswith("| 권번호"):
            header_idx = i
            break
    if header_idx is None:
        return template_text

    insert_idx = header_idx + 2 if header_idx + 1 < len(lines) else len(lines)
    volumes = (target_chapters - 1) // chapters_per_volume + 1 if target_chapters > 0 else 1
    rows = []
    for v in range(1, volumes + 1):
        start = (v - 1) * chapters_per_volume + 1
        end = min(v * chapters_per_volume, target_chapters)
        rows.append(f"| {v} | | chapter {start}-{end} | | |")

    # 중복 삽입 방지 (템플릿에 이미 데이터 행이 있는 경우)
    existing = {line.strip() for line in lines}
    rows = [r for r in rows if r.strip() not in existing]
    return "\n".join(lines[:insert_idx] + rows + lines[insert_idx:])


def init_project(
    project_dir: str,
    title: str,
    genre: str,
    *,
    protagonist_name: str = "",
    target_words: int = 2_000_000,
    target_chapters: int = 600,
    golden_finger_name: str = "",
    golden_finger_type: str = "",
    golden_finger_style: str = "",
    core_selling_points: str = "",
    protagonist_structure: str = "",
    heroine_config: str = "",
    heroine_names: str = "",
    heroine_role: str = "",
    co_protagonists: str = "",
    co_protagonist_roles: str = "",
    antagonist_tiers: str = "",
    world_scale: str = "",
    factions: str = "",
    power_system_type: str = "",
    social_class: str = "",
    resource_distribution: str = "",
    gf_visibility: str = "",
    gf_irreversible_cost: str = "",
    protagonist_desire: str = "",
    protagonist_flaw: str = "",
    protagonist_archetype: str = "",
    antagonist_level: str = "",
    target_reader: str = "",
    platform: str = "",
    currency_system: str = "",
    currency_exchange: str = "",
    sect_hierarchy: str = "",
    cultivation_chain: str = "",
    cultivation_subtiers: str = "",
) -> None:
    project_path = Path(project_dir).expanduser().resolve()
    if ".claude" in project_path.parts:
        raise SystemExit("Refusing to initialize a project inside .claude. Choose a different directory.")
    project_path.mkdir(parents=True, exist_ok=True)

    # Directory structure (supports volume layout and future extensions)
    directories = [
        ".webnovel/backups",
        ".webnovel/archive",
        ".webnovel/summaries",
        "settings/characters/main",
        "settings/characters/minor",
        "settings/characters/villain",
        "settings/items",
        "settings/misc",
        "outline",
        "chapters/vol_1",
        "reviews",
    ]
    for dir_path in directories:
        (project_path / dir_path).mkdir(parents=True, exist_ok=True)

    # state.json（생성 또는 증분 보충）
    state_path = project_path / ".webnovel" / "state.json"
    if state_path.exists():
        try:
            state: Dict[str, Any] = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}
    else:
        state = {}

    state = _ensure_state_schema(state)
    created_at = state.get("project_info", {}).get("created_at") or datetime.now().strftime("%Y-%m-%d")

    state["project_info"].update(
        {
            "title": title,
            "genre": genre,
            "created_at": created_at,
            "target_words": int(target_words),
            "target_chapters": int(target_chapters),
            # 아래 필드는 "초기화 메타 정보"로, 런타임 스크립트에 영향 없음
            "golden_finger_name": golden_finger_name,
            "golden_finger_type": golden_finger_type,
            "golden_finger_style": golden_finger_style,
            "core_selling_points": core_selling_points,
            "protagonist_structure": protagonist_structure,
            "heroine_config": heroine_config,
            "heroine_names": heroine_names,
            "heroine_role": heroine_role,
            "co_protagonists": co_protagonists,
            "co_protagonist_roles": co_protagonist_roles,
            "antagonist_tiers": antagonist_tiers,
            "world_scale": world_scale,
            "factions": factions,
            "power_system_type": power_system_type,
            "social_class": social_class,
            "resource_distribution": resource_distribution,
            "gf_visibility": gf_visibility,
            "gf_irreversible_cost": gf_irreversible_cost,
            "target_reader": target_reader,
            "platform": platform,
            "currency_system": currency_system,
            "currency_exchange": currency_exchange,
            "sect_hierarchy": sect_hierarchy,
            "cultivation_chain": cultivation_chain,
            "cultivation_subtiers": cultivation_subtiers,
        }
    )

    if protagonist_name:
        state["protagonist_state"]["name"] = protagonist_name

    gf_type_norm = (golden_finger_type or "").strip()
    if gf_type_norm in {"없음", "골든핑거 없음", "none"}:
        state["protagonist_state"]["golden_finger"]["name"] = "골든핑거 없음"
        state["protagonist_state"]["golden_finger"]["level"] = 0
        state["protagonist_state"]["golden_finger"]["cooldown"] = 0
    elif golden_finger_name:
        state["protagonist_state"]["golden_finger"]["name"] = golden_finger_name

    # golden_finger 필드가 존재하고 편집 가능하도록 보장
    if not state["protagonist_state"]["golden_finger"].get("name"):
        state["protagonist_state"]["golden_finger"]["name"] = "이름 없는 골든핑거"

    state["progress"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    # 원자적 쓰기 사용(초기화 시 이전 파일 백업 불필요)
    atomic_write_json(state_path, state, use_lock=True, backup=False)

    # 내장 템플릿 읽기(선택사항)
    script_dir = Path(__file__).resolve().parent
    templates_dir = script_dir.parent / "templates"
    output_templates_dir = templates_dir / "output"
    genre_key = (genre or "").strip()
    genre_keys = [_normalize_genre_key(k) for k in _split_genre_keys(genre_key)]
    genre_templates = []
    seen = set()
    for key in genre_keys:
        if not key or key in seen:
            continue
        seen.add(key)
        template_text = _read_text_if_exists(templates_dir / "genres" / f"{key}.md")
        if template_text:
            genre_templates.append(template_text.strip())
    genre_template = "\n\n---\n\n".join(genre_templates)
    golden_finger_templates = _read_text_if_exists(templates_dir / "golden-finger-templates.md")
    output_worldview = _read_text_if_exists(output_templates_dir / "settings-worldview.md")
    output_power = _read_text_if_exists(output_templates_dir / "settings-power-system.md")
    output_protagonist = _read_text_if_exists(output_templates_dir / "settings-protagonist.md")
    output_heroine = _read_text_if_exists(output_templates_dir / "settings-heroine.md")
    output_team = _read_text_if_exists(output_templates_dir / "settings-team.md")
    output_golden_finger = _read_text_if_exists(output_templates_dir / "settings-golden-finger.md")
    output_outline = _read_text_if_exists(output_templates_dir / "outline-master.md")
    output_fusion = _read_text_if_exists(output_templates_dir / "settings-genre-fusion.md")
    output_antagonist = _read_text_if_exists(output_templates_dir / "settings-antagonist.md")

    # 기본 파일(결여 시에만 생성, 기존 내용 덮어쓰기 방지)
    now = datetime.now().strftime("%Y-%m-%d")

    worldview_content = output_worldview.strip() if output_worldview else ""
    if not worldview_content:
        worldview_content = "\n".join(
            [
                "# 세계관",
                "",
                f"> 프로젝트：{title}｜장르：{genre}｜생성：{now}",
                "",
                "## 한 줄 세계관",
                "- （한 줄로 세계의 핵심 규칙과 셀링포인트를 설명）",
                "",
                "## 핵심 규칙（설정이 곧 물리）",
                "- 규칙1：",
                "- 규칙2：",
                "- 규칙3：",
                "",
                "## 세력과 지리（간략판）",
                "- 주요 세력：",
                "- 핵심 장소：",
                "",
                "## 참고 장르 템플릿（삭제/수정 가능）",
                "",
                (genre_template.strip() + "\n") if genre_template else "（해당 장르 템플릿을 찾을 수 없음, 직접 보충 가능）\n",
            ]
        ).rstrip() + "\n"
    else:
        worldview_content = _apply_label_replacements(
            worldview_content,
            {
                "대륙/차원 수량": world_scale,
                "핵심세력": factions,
                "사회 계층": social_class,
                "자원 분배 규칙": resource_distribution,
                "문파/조직 계층": sect_hierarchy,
                "화폐 체계": currency_system,
                "환전 규칙": currency_exchange,
            },
        )
    _write_text_if_missing(
        project_path / "settings" / "worldview.md",
        worldview_content,
    )

    power_content = output_power.strip() if output_power else ""
    if not power_content:
        power_content = "\n".join(
            [
                "# 능력 체계",
                "",
                f"> 프로젝트：{title}｜장르：{genre}｜생성：{now}",
                "",
                "## 등급/경지 구분",
                "- （약한 것부터 강한 것까지 등급을 나열하고, 돌파 조건과 대가를 포함）",
                "",
                "## 기술/초식 규칙",
                "- 획득 방식：",
                "- 비용과 부작용：",
                "- 승급과 조합：",
                "",
                "## 금지 사항（설정 붕괴 방지）",
                "- 등급 미달 시 고급 능력 사용 불가（설정이 곧 물리）",
                "- 신규 능력은 반드시 신고 후 등록（발명 시 신고 필요）",
                "",
            ]
        ).rstrip() + "\n"
    else:
        power_content = _apply_label_replacements(
            power_content,
            {
                "체계 유형": power_system_type,
                "전형적인 경지 체인（선택）": cultivation_chain,
                "소경지 구분": cultivation_subtiers,
            },
        )
    _write_text_if_missing(
        project_path / "settings" / "power-system.md",
        power_content,
    )

    protagonist_content = output_protagonist.strip() if output_protagonist else ""
    if not protagonist_content:
        protagonist_content = "\n".join(
            [
                "# 주인공 카드",
                "",
                f"> 주인공：{protagonist_name or '（작성 예정）'}｜프로젝트：{title}｜생성：{now}",
                "",
                "## 3요소",
                f"- 욕망：{protagonist_desire or '（작성 예정）'}",
                f"- 결함：{protagonist_flaw or '（작성 예정）'}",
                f"- 캐릭터 유형：{protagonist_archetype or '（작성 예정）'}",
                "",
                "## 초기 상태（오프닝）",
                "- 신분：",
                "- 자원：",
                "- 제약：",
                "",
                "## 골든핑거 개요",
                f"- 호칭：{golden_finger_name or '（작성 예정）'}",
                f"- 유형：{golden_finger_type or '（작성 예정）'}",
                f"- 스타일：{golden_finger_style or '（작성 예정）'}",
                "- 성장 곡선：",
                "",
            ]
        ).rstrip() + "\n"
    else:
        protagonist_content = _apply_label_replacements(
            protagonist_content,
            {
                "이름": protagonist_name,
                "진정한 갈망（본인이 모를 수 있음）": protagonist_desire,
                "성격 결함": protagonist_flaw,
            },
        )
    _write_text_if_missing(
        project_path / "settings" / "protagonist.md",
        protagonist_content,
    )

    heroine_content = output_heroine.strip() if output_heroine else ""
    if heroine_content:
        heroine_content = _apply_label_replacements(
            heroine_content,
            {
                "이름": heroine_names,
                "주인공과의 관계 포지션（라이벌/동맹/공모/견제）": heroine_role,
            },
        )
        _write_text_if_missing(project_path / "settings" / "heroine.md", heroine_content)

    team_content = output_team.strip() if output_team else ""
    if team_content:
        names = [n.strip() for n in co_protagonists.split(",") if n.strip()] if co_protagonists else []
        roles = [r.strip() for r in co_protagonist_roles.split(",") if r.strip()] if co_protagonist_roles else []
        if names:
            lines = team_content.splitlines()
            new_rows = _render_team_rows(names, roles)
            replaced = False
            out_lines: List[str] = []
            for line in lines:
                if line.strip().startswith("| 주인공A"):
                    out_lines.extend(new_rows)
                    replaced = True
                    continue
                if replaced and line.strip().startswith("| 주인공"):
                    continue
                out_lines.append(line)
            team_content = "\n".join(out_lines)
        _write_text_if_missing(
            project_path / "settings" / "team.md",
            team_content,
        )

    golden_finger_content = output_golden_finger.strip() if output_golden_finger else ""
    if not golden_finger_content:
        golden_finger_content = "\n".join(
            [
                "# 골든핑거 설계",
                "",
                f"> 프로젝트：{title}｜장르：{genre}｜생성：{now}",
                "",
                "## 선택",
                f"- 호칭：{golden_finger_name or '（작성 예정）'}",
                f"- 유형：{golden_finger_type or '（작성 예정）'}",
                f"- 스타일：{golden_finger_style or '（작성 예정）'}",
                "",
                "## 규칙（반드시 명시）",
                "- 발동 조건：",
                "- 쿨다운/대가：",
                "- 상한：",
                "- 반작용/리스크：",
                "",
                "## 성장 곡선（챕터 계획）",
                "- Lv1：",
                "- Lv2：",
                "- Lv3：",
                "",
                "## 템플릿 참고（삭제/수정 가능）",
                "",
                (golden_finger_templates.strip() + "\n") if golden_finger_templates else "（골든핑거 템플릿 라이브러리를 찾을 수 없음）\n",
            ]
        ).rstrip() + "\n"
    else:
        golden_finger_content = _apply_label_replacements(
            golden_finger_content,
            {
                "유형": golden_finger_type,
                "독자 가시성": gf_visibility,
                "불가역적 대가": gf_irreversible_cost,
            },
        )
    _write_text_if_missing(
        project_path / "settings" / "golden-finger.md",
        golden_finger_content,
    )

    fusion_content = output_fusion.strip() if output_fusion else ""
    if fusion_content:
        _write_text_if_missing(
            project_path / "settings" / "genre-fusion.md",
            fusion_content,
        )

    antagonist_content = output_antagonist.strip() if output_antagonist else ""
    if not antagonist_content:
        antagonist_content = "\n".join(
            [
                "# 악역 설계",
                "",
                f"> 프로젝트：{title}｜생성：{now}",
                "",
                f"- 악역 등급：{antagonist_level or '（작성 예정）'}",
                "- 동기：",
                "- 자원/세력：",
                "- 주인공과의 거울상 관계：",
                "- 결말：",
                "",
            ]
        ).rstrip() + "\n"
    else:
        tier_map = _parse_tier_map(antagonist_tiers)
        if tier_map:
            lines = antagonist_content.splitlines()
            out_lines = []
            for line in lines:
                if line.strip().startswith("| 소반파"):
                    name = tier_map.get("소반파", "")
                    out_lines.append(f"| 소반파 | {name} | 전기 | | |")
                    continue
                if line.strip().startswith("| 중반파"):
                    name = tier_map.get("중반파", "")
                    out_lines.append(f"| 중반파 | {name} | 중기 | | |")
                    continue
                if line.strip().startswith("| 대반파"):
                    name = tier_map.get("대반파", "")
                    out_lines.append(f"| 대반파 | {name} | 후기 | | |")
                    continue
                out_lines.append(line)
            antagonist_content = "\n".join(out_lines)
    _write_text_if_missing(project_path / "settings" / "antagonist.md", antagonist_content)

    outline_content = output_outline.strip() if output_outline else ""
    if outline_content:
        outline_content = _inject_volume_rows(outline_content, int(target_chapters)).rstrip() + "\n"
    else:
        outline_content = _build_master_outline(int(target_chapters))
    _write_text_if_missing(project_path / "outline" / "master.md", outline_content)

    _write_text_if_missing(
        project_path / "outline" / "highlights.md",
        "\n".join(
            [
                "# 쾌감포인트 계획",
                "",
                f"> 프로젝트：{title}｜장르：{genre}｜생성：{now}",
                "",
                "## 핵심 셀링포인트（초기화 입력에서 가져옴）",
                f"- {core_selling_points or '（작성 예정, 1-3건 제안, 쉼표로 구분）'}",
                "",
                "## 밀도 목표（제안）",
                "- 매 챕터 최소 1개 소 쾌감포인트",
                "- 매 5챕터 최소 1개 대 쾌감포인트",
                "",
                "## 분포표（예시, 수정 가능）",
                "",
                "| 챕터 범위 | 주도 쾌감포인트 유형 | 비고 |",
                "|---|---|---|",
                "| 1-5 | 골든핑거/체면 구기기/반전 | 오프닝 훅 + 캐릭터 확립 |",
                "| 6-10 | 레벨업/보상 | 메인 스토리 리듬 진입 |",
                "",
            ]
        ),
    )

    # 환경 변수 템플릿 생성(실제 키 미기록)
    _write_text_if_missing(
        project_path / ".env.example",
        "\n".join(
            [
                "# Webnovel Writer 설정예시（.env로 복사 후 작성）",
                "# 주의: 실제 API_KEY가 포함된 .env를 저장소에 커밋하지 마세요.",
                "",
                "# Embedding",
                "EMBED_BASE_URL=https://api-inference.modelscope.cn/v1",
                "EMBED_MODEL=Qwen/Qwen3-Embedding-8B",
                "EMBED_API_KEY=",
                "",
                "# Rerank",
                "RERANK_BASE_URL=https://api.jina.ai/v1",
                "RERANK_MODEL=jina-reranker-v3",
                "RERANK_API_KEY=",
                "",
            ]
        )
        + "\n",
    )

    # Git 초기화(프로젝트 디렉토리에 .git이 없고 Git이 사용 가능한 경우에만)
    git_dir = project_path / ".git"
    if not git_dir.exists():
        if not is_git_available():
            print("\n⚠️  Git 사용 불가, 버전 관리 초기화 건너뜀")
            print("💡 Git 버전 관리를 사용하려면 Git을 설치하세요: https://git-scm.com/")
        else:
            print("\nInitializing Git repository...")
            try:
                subprocess.run(["git", "init"], cwd=project_path, check=True, capture_output=True, text=True)

                gitignore_file = project_path / ".gitignore"
                if not gitignore_file.exists():
                    gitignore_file.write_text(
                        """# Python
__pycache__/
*.py[cod]
*.so

# Env (keep .env.example)
.env
.env.*
!.env.example

# Temporary files
*.tmp
*.bak
.DS_Store

# IDE
.vscode/
.idea/

# Don't ignore .webnovel (we need to track state.json)
# But ignore cache files
.webnovel/context_cache.json
.webnovel/*.lock
.webnovel/*.bak
""",
                        encoding="utf-8",
                    )

                subprocess.run(["git", "add", "."], cwd=project_path, check=True, capture_output=True)
                # 보안 수정: title 정리로 명령 주입 방지
                safe_title = sanitize_commit_message(title)
                subprocess.run(
                    ["git", "commit", "-m", f"웹소설 프로젝트 초기화：{safe_title}"],
                    cwd=project_path,
                    check=True,
                    capture_output=True,
                )
                print("Git initialized.")
            except subprocess.CalledProcessError as e:
                print(f"Git init failed (non-fatal): {e}")

    # 워크스페이스 기본 프로젝트 포인터 기록(비차단)
    try:
        pointer_file = write_current_project_pointer(project_path)
        if pointer_file is not None:
            print(f"Default project pointer updated: {pointer_file}")
    except Exception as e:
        print(f"Default project pointer update failed (non-fatal): {e}")

    print(f"\nProject initialized at: {project_path}")
    print("Key files:")
    print(" - .webnovel/state.json")
    print(" - settings/worldview.md")
    print(" - settings/power-system.md")
    print(" - settings/protagonist.md")
    print(" - settings/golden-finger.md")
    print(" - outline/master.md")
    print(" - outline/highlights.md")


def main() -> None:
    parser = argparse.ArgumentParser(description="웹소설 프로젝트 초기화 스크립트(프로젝트 구조 + state.json + 기본 템플릿 생성)")
    parser.add_argument("project_dir", help="프로젝트 디렉토리(./webnovel-project 권장)")
    parser.add_argument("title", help="소설 제목")
    parser.add_argument(
        "genre",
        help="장르 유형（'+'로 조합 가능, 예: 도시기발+규칙괴담; 예시: 수선/시스템류/도시이능/고대로맨스/현실장르）",
    )

    parser.add_argument("--protagonist-name", default="", help="주인공 이름")
    parser.add_argument("--target-words", type=int, default=2_000_000, help="목표 총 글자 수（기본값 2000000）")
    parser.add_argument("--target-chapters", type=int, default=600, help="목표 총 챕터 수（기본값 600）")

    parser.add_argument("--golden-finger-name", default="", help="골든핑거 호칭/시스템명(독자에게 보이는 코드명 권장)")
    parser.add_argument("--golden-finger-type", default="", help="골든핑거 유형（예: 시스템류/감정류/출석류）")
    parser.add_argument("--golden-finger-style", default="", help="골든핑거 스타일（예: 냉담 도구형/독설 츳코미형）")
    parser.add_argument("--core-selling-points", default="", help="핵심 셀링포인트(쉼표 구분)")
    parser.add_argument("--protagonist-structure", default="", help="주인공 구조(단일 주인공/다중 주인공)")
    parser.add_argument("--heroine-config", default="", help="여주인공 설정(여주 없음/단일 여주/다중 여주)")
    parser.add_argument("--heroine-names", default="", help="여주인공 이름(여러 명은 쉼표 구분)")
    parser.add_argument("--heroine-role", default="", help="여주인공 포지션(커리어 라인/감정 라인/대립 라인)")
    parser.add_argument("--co-protagonists", default="", help="다중 주인공 이름(쉼표 구분)")
    parser.add_argument("--co-protagonist-roles", default="", help="다중 주인공 포지션(쉼표 구분)")
    parser.add_argument("--antagonist-tiers", default="", help="악역 계층화（예: 소반파:홍길동;중반파:이몽룡;대반파:변학도）")
    parser.add_argument("--world-scale", default="", help="세계 규모")
    parser.add_argument("--factions", default="", help="세력 구도/핵심 세력")
    parser.add_argument("--power-system-type", default="", help="전투력 체계 유형")
    parser.add_argument("--social-class", default="", help="사회 계층")
    parser.add_argument("--resource-distribution", default="", help="자원 분배")
    parser.add_argument("--gf-visibility", default="", help="골든핑거 가시성(공개/반공개/비공개)")
    parser.add_argument("--gf-irreversible-cost", default="", help="골든핑거 불가역적 대가")
    parser.add_argument("--currency-system", default="", help="화폐 체계")
    parser.add_argument("--currency-exchange", default="", help="화폐 환전/액면가 규칙")
    parser.add_argument("--sect-hierarchy", default="", help="문파/조직 계층")
    parser.add_argument("--cultivation-chain", default="", help="전형적인 경지 체인")
    parser.add_argument("--cultivation-subtiers", default="", help="소경지 구분（초/중/후/정점 등）")

    # 심층 모드 선택 매개변수（템플릿 사전 입력용）
    parser.add_argument("--protagonist-desire", default="", help="주인공 핵심 욕망(심층 모드)")
    parser.add_argument("--protagonist-flaw", default="", help="주인공 성격 약점(심층 모드)")
    parser.add_argument("--protagonist-archetype", default="", help="주인공 캐릭터 유형(심층 모드)")
    parser.add_argument("--antagonist-level", default="", help="악역 등급(심층 모드)")
    parser.add_argument("--target-reader", default="", help="대상 독자(심층 모드)")
    parser.add_argument("--platform", default="", help="출판 플랫폼(심층 모드)")

    args = parser.parse_args()

    init_project(
        args.project_dir,
        args.title,
        args.genre,
        protagonist_name=args.protagonist_name,
        target_words=args.target_words,
        target_chapters=args.target_chapters,
        golden_finger_name=args.golden_finger_name,
        golden_finger_type=args.golden_finger_type,
        golden_finger_style=args.golden_finger_style,
        core_selling_points=args.core_selling_points,
        protagonist_structure=args.protagonist_structure,
        heroine_config=args.heroine_config,
        heroine_names=args.heroine_names,
        heroine_role=args.heroine_role,
        co_protagonists=args.co_protagonists,
        co_protagonist_roles=args.co_protagonist_roles,
        antagonist_tiers=args.antagonist_tiers,
        world_scale=args.world_scale,
        factions=args.factions,
        power_system_type=args.power_system_type,
        social_class=args.social_class,
        resource_distribution=args.resource_distribution,
        gf_visibility=args.gf_visibility,
        gf_irreversible_cost=args.gf_irreversible_cost,
        protagonist_desire=args.protagonist_desire,
        protagonist_flaw=args.protagonist_flaw,
        protagonist_archetype=args.protagonist_archetype,
        antagonist_level=args.antagonist_level,
        target_reader=args.target_reader,
        platform=args.platform,
        currency_system=args.currency_system,
        currency_exchange=args.currency_exchange,
        sect_hierarchy=args.sect_hierarchy,
        cultivation_chain=args.cultivation_chain,
        cultivation_subtiers=args.cultivation_subtiers,
    )


if __name__ == "__main__":
    main()
