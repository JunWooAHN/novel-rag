#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quality_trend_report.py - 챕터 품질 트렌드 보고서 생성(오프라인)

데이터 출처：
- index.db.review_metrics
- index.db.writing_checklist_scores
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from runtime_compat import enable_windows_utf8_stdio

try:
    from project_locator import resolve_project_root
except ImportError:  # pragma: no cover
    from scripts.project_locator import resolve_project_root

try:
    from data_modules.config import DataModulesConfig
    from data_modules.index_manager import IndexManager
except ImportError:  # pragma: no cover
    from scripts.data_modules.config import DataModulesConfig
    from scripts.data_modules.index_manager import IndexManager


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _build_review_rows(records: List[Dict[str, Any]]) -> List[str]:
    if not records:
        return ["| - | - | - | - | - | - |", "| - | - | - | - | - | - |"]

    rows: List[str] = []
    sorted_records = sorted(
        records,
        key=lambda x: (_to_int(x.get("end_chapter")), _to_int(x.get("start_chapter"))),
    )
    for row in sorted_records:
        severities = row.get("severity_counts") or {}
        critical = _to_int(severities.get("critical"))
        high = _to_int(severities.get("high"))
        medium = _to_int(severities.get("medium"))
        low = _to_int(severities.get("low"))
        range_text = f"{_to_int(row.get('start_chapter'))}-{_to_int(row.get('end_chapter'))}"
        score = _to_float(row.get("overall_score"))
        rows.append(
            f"| {range_text} | {score:.1f} | {critical} | {high} | {medium} | {low} |"
        )
    return rows


def _build_checklist_rows(records: List[Dict[str, Any]]) -> List[str]:
    if not records:
        return ["| - | - | - | - |"]

    rows: List[str] = []
    sorted_records = sorted(records, key=lambda x: _to_int(x.get("chapter")))
    for row in sorted_records:
        chapter = _to_int(row.get("chapter"))
        score = _to_float(row.get("score"))
        completion = _to_float(row.get("completion_rate"))
        required_items = _to_int(row.get("required_items"))
        completed_required = _to_int(row.get("completed_required"))
        if required_items > 0:
            required_rate = completed_required / required_items
        else:
            required_rate = 1.0
        rows.append(
            f"| {chapter} | {score:.1f} | {_percent(completion)} | {_percent(required_rate)} |"
        )
    return rows


def _build_risk_flags(
    review_trend: Dict[str, Any],
    checklist_trend: Dict[str, Any],
) -> List[str]:
    flags: List[str] = []

    overall_avg = _to_float(review_trend.get("overall_avg"))
    if overall_avg < 75 and review_trend.get("count", 0) > 0:
        flags.append(f"검토 평균점 낮음（{overall_avg:.1f}），저점수 구간 우선 재검토 권장.")

    severity_totals = review_trend.get("severity_totals") or {}
    critical_total = _to_int(severity_totals.get("critical"))
    high_total = _to_int(severity_totals.get("high"))
    if critical_total > 0:
        flags.append(f"{critical_total}개 critical 문제 존재, 최우선 수정 우선순위로 설정 권장.")
    elif high_total >= 5:
        flags.append(f"high 문제 누적 {high_total} 개, 일괄 수정 전담 권장.")

    score_avg = _to_float(checklist_trend.get("score_avg"))
    if checklist_trend.get("count", 0) > 0 and score_avg < 80:
        flags.append(f"작성 체크리스트 평균점 낮음（{score_avg:.1f}），실행 체크리스트 이행 강화 권장.")

    completion_avg = _to_float(checklist_trend.get("completion_avg"))
    if checklist_trend.get("count", 0) > 0 and completion_avg < 0.7:
        flags.append(f"작성 체크리스트 완료율 단 {_percent(completion_avg)}，각 챕터 선택 항목 수 줄이기 권장.")

    if not flags:
        flags.append("최근 품질 지표 전반적으로 안정, 고우선순위 위험 없음.")

    return flags


def build_quality_report(
    project_root: Path,
    manager: IndexManager,
    *,
    limit: int,
) -> str:
    review_records = manager.get_recent_review_metrics(limit=limit)
    review_trend = manager.get_review_trend_stats(last_n=limit)
    checklist_records = manager.get_recent_writing_checklist_scores(limit=limit)
    checklist_trend = manager.get_writing_checklist_score_trend(last_n=limit)

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    overall_avg = _to_float(review_trend.get("overall_avg"))
    review_count = _to_int(review_trend.get("count"))
    checklist_count = _to_int(checklist_trend.get("count"))
    checklist_score_avg = _to_float(checklist_trend.get("score_avg"))
    checklist_completion_avg = _to_float(checklist_trend.get("completion_avg"))

    dimension_avg = review_trend.get("dimension_avg") or {}
    severity_totals = review_trend.get("severity_totals") or {}
    risk_flags = _build_risk_flags(review_trend, checklist_trend)

    lines: List[str] = []
    lines.append("# 품질 트렌드 보고서")
    lines.append("")
    lines.append(f"- 생성 시간: {now_text}")
    lines.append(f"- 프로젝트 경로: `{project_root}`")
    lines.append(f"- 통계 구간: 최근 {limit} 건 기록")
    lines.append("")
    lines.append("## 개요")
    lines.append("")
    lines.append(f"- 검토 기록 수: {review_count}")
    lines.append(f"- 검토 평균점: {overall_avg:.1f}")
    lines.append(f"- 체크리스트 평가 기록 수: {checklist_count}")
    lines.append(f"- 체크리스트 평균점: {checklist_score_avg:.1f}")
    lines.append(f"- 체크리스트 평균 완료율: {_percent(checklist_completion_avg)}")
    lines.append("")

    lines.append("## 검토 구간 트렌드")
    lines.append("")
    lines.append("| 구간 | 총점 | Critical | High | Medium | Low |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    lines.extend(_build_review_rows(review_records))
    lines.append("")

    lines.append("## 차원 평균점")
    lines.append("")
    lines.append("| 차원 | 평균점 |")
    lines.append("|---|---:|")
    if dimension_avg:
        for key in sorted(dimension_avg.keys()):
            lines.append(f"| {key} | {_to_float(dimension_avg.get(key)):.1f} |")
    else:
        lines.append("| - | - |")
    lines.append("")

    lines.append("## 심각도 수준 요약")
    lines.append("")
    lines.append("| 등급 | 수량 |")
    lines.append("|---|---:|")
    for level in ("critical", "high", "medium", "low"):
        lines.append(f"| {level} | {_to_int(severity_totals.get(level))} |")
    lines.append("")

    lines.append("## 작성 체크리스트 트렌드")
    lines.append("")
    lines.append("| 챕터 | 점수 | 완료율 | 필수 완료율 |")
    lines.append("|---:|---:|---:|---:|")
    lines.extend(_build_checklist_rows(checklist_records))
    lines.append("")

    lines.append("## 위험 경고")
    lines.append("")
    for item in risk_flags:
        lines.append(f"- {item}")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="오프라인 품질 트렌드 보고서 생성(index.db 기반)")
    parser.add_argument("--project-root", type=str, help="프로젝트 루트 디렉토리(선택사항, 미전달 시 자동 탐지)")
    parser.add_argument("--limit", type=int, default=20, help="최근 N건 기록 통계（기본값 20）")
    parser.add_argument("--output", type=str, help="출력 파일 경로（기본값 .webnovel/reports/quality-trend.md）")
    args = parser.parse_args()

    if args.project_root:
        # “워크스페이스 루트 디렉토리” 전달 허용, 실제 book project_root로 통합 해석
        project_root = resolve_project_root(args.project_root)
    else:
        project_root = resolve_project_root()

    cfg = DataModulesConfig.from_project_root(project_root)
    manager = IndexManager(cfg)

    limit = max(1, int(args.limit))
    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else (cfg.webnovel_dir / "reports" / "quality-trend.md")
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = build_quality_report(project_root, manager, limit=limit)
    output_path.write_text(report, encoding="utf-8")
    print(f"✅ 품질 트렌드 보고서 생성 완료: {output_path}")


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        enable_windows_utf8_stdio()
    main()
