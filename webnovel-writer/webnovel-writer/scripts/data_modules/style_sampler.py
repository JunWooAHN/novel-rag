#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Style Sampler - 스타일 샘플 관리 모듈

고품질 챕터 조각을 스타일 참조로 관리:
- 스타일 샘플 스토리지
- 장면 유형별 분류
- 샘플 선택 전략
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from contextlib import contextmanager

from .config import get_config
from .observability import safe_append_perf_timing, safe_log_tool_call


class SceneType(Enum):
    """장면 유형"""
    BATTLE = "전투"
    DIALOGUE = "대화"
    DESCRIPTION = "묘사"
    TRANSITION = "전환"
    EMOTION = "감정"
    TENSION = "긴장"
    COMEDY = "가벼움"


@dataclass
class StyleSample:
    """스타일 샘플"""
    id: str
    chapter: int
    scene_type: str
    content: str
    score: float
    tags: List[str]
    created_at: str = ""


class StyleSampler:
    """스타일 샘플 관리기"""

    def __init__(self, config=None):
        self.config = config or get_config()
        self._init_db()

    def _init_db(self):
        """데이터베이스 초기화"""
        self.config.ensure_dirs()
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS samples (
                    id TEXT PRIMARY KEY,
                    chapter INTEGER,
                    scene_type TEXT,
                    content TEXT,
                    score REAL,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_samples_type ON samples(scene_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_samples_score ON samples(score DESC)")

            conn.commit()

    @contextmanager
    def _get_conn(self):
        """데이터베이스 연결 획득 (닫기 보장, Windows에서 파일 핸들 누수로 임시 디렉토리 정리 불가 방지)"""
        db_path = self.config.webnovel_dir / "style_samples.db"
        conn = sqlite3.connect(str(db_path))
        try:
            yield conn
        finally:
            conn.close()

    # ==================== 샘플 관리 ====================

    def add_sample(self, sample: StyleSample) -> bool:
        """스타일 샘플 추가"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO samples
                    (id, chapter, scene_type, content, score, tags, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    sample.id,
                    sample.chapter,
                    sample.scene_type,
                    sample.content,
                    sample.score,
                    json.dumps(sample.tags, ensure_ascii=False),
                    sample.created_at or datetime.now().isoformat()
                ))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_samples_by_type(
        self,
        scene_type: str,
        limit: int = 5,
        min_score: float = 0.0
    ) -> List[StyleSample]:
        """장면 유형별 샘플 조회"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, chapter, scene_type, content, score, tags, created_at
                FROM samples
                WHERE scene_type = ? AND score >= ?
                ORDER BY score DESC
                LIMIT ?
            """, (scene_type, min_score, limit))

            return [self._row_to_sample(row) for row in cursor.fetchall()]

    def get_best_samples(self, limit: int = 10) -> List[StyleSample]:
        """최고 점수 샘플 조회"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, chapter, scene_type, content, score, tags, created_at
                FROM samples
                ORDER BY score DESC
                LIMIT ?
            """, (limit,))

            return [self._row_to_sample(row) for row in cursor.fetchall()]

    def _row_to_sample(self, row) -> StyleSample:
        """데이터베이스 행을 샘플 객체로 변환"""
        return StyleSample(
            id=row[0],
            chapter=row[1],
            scene_type=row[2],
            content=row[3],
            score=row[4],
            tags=json.loads(row[5]) if row[5] else [],
            created_at=row[6]
        )

    # ==================== 샘플 추출 ====================

    def extract_candidates(
        self,
        chapter: int,
        content: str,
        review_score: float,
        scenes: List[Dict]
    ) -> List[StyleSample]:
        """
        챕터에서 스타일 샘플 후보 추출

        고득점 챕터 (review_score >= 80)만 샘플 추출
        """
        if review_score < 80:
            return []

        candidates = []

        for scene in scenes:
            scene_type = self._classify_scene_type(scene)
            scene_content = scene.get("content", "")

            # 너무 짧은 장면 건너뛰기
            if len(scene_content) < 200:
                continue

            # 샘플 생성
            sample = StyleSample(
                id=f"ch{chapter}_s{scene.get('index', 0)}",
                chapter=chapter,
                scene_type=scene_type,
                content=scene_content[:2000],  # 길이 제한
                score=review_score / 100.0,
                tags=self._extract_tags(scene_content)
            )
            candidates.append(sample)

        return candidates

    def _classify_scene_type(self, scene: Dict) -> str:
        """장면 유형 분류"""
        summary = scene.get("summary", "").lower()
        content = scene.get("content", "").lower()

        # 간단 키워드 분류
        battle_keywords = ["전투", "공격", "출수", "권", "검", "살", "타격", "격투"]
        dialogue_keywords = ["말했다", "물었다", "웃으며", "차갑게", "대화"]
        emotion_keywords = ["마음속", "느낌", "감정", "눈물", "고통", "기쁨"]
        tension_keywords = ["위험", "긴장", "공포", "압박"]

        text = summary + content

        if any(kw in text for kw in battle_keywords):
            return SceneType.BATTLE.value
        elif any(kw in text for kw in tension_keywords):
            return SceneType.TENSION.value
        elif any(kw in text for kw in dialogue_keywords):
            return SceneType.DIALOGUE.value
        elif any(kw in text for kw in emotion_keywords):
            return SceneType.EMOTION.value
        else:
            return SceneType.DESCRIPTION.value

    def _extract_tags(self, content: str) -> List[str]:
        """내용 태그 추출"""
        tags = []

        # 간단 태그 추출
        if "전투" in content or "공격" in content:
            tags.append("전투")
        if "수련" in content or "돌파" in content:
            tags.append("수련")
        if "대화" in content or "말했다" in content:
            tags.append("대화")
        if "묘사" in content or "경치" in content:
            tags.append("묘사")

        return tags[:5]

    # ==================== 샘플 선택 ====================

    def select_samples_for_chapter(
        self,
        chapter_outline: str,
        target_types: List[str] = None,
        max_samples: int = 3
    ) -> List[StyleSample]:
        """
        챕터 집필에 적합한 스타일 샘플 선택

        아웃라인 기반으로 필요한 장면 유형 분석
        """
        if target_types is None:
            # 아웃라인에서 필요한 장면 유형 추론
            target_types = self._infer_scene_types(chapter_outline)

        samples = []
        per_type = max(1, max_samples // len(target_types)) if target_types else max_samples

        for scene_type in target_types:
            type_samples = self.get_samples_by_type(scene_type, limit=per_type, min_score=0.8)
            samples.extend(type_samples)

        return samples[:max_samples]

    def _infer_scene_types(self, outline: str) -> List[str]:
        """아웃라인에서 필요한 장면 유형 추론"""
        types = []

        if any(kw in outline for kw in ["전투", "대결", "비무", "교전"]):
            types.append(SceneType.BATTLE.value)

        if any(kw in outline for kw in ["대화", "담화", "상의", "토론"]):
            types.append(SceneType.DIALOGUE.value)

        if any(kw in outline for kw in ["감정", "심리"]):
            types.append(SceneType.EMOTION.value)

        if not types:
            types = [SceneType.DESCRIPTION.value]

        return types

    # ==================== 통계 ====================

    def get_stats(self) -> Dict[str, Any]:
        """샘플 통계 조회"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM samples")
            total = cursor.fetchone()[0]

            cursor.execute("""
                SELECT scene_type, COUNT(*) as count
                FROM samples
                GROUP BY scene_type
            """)
            by_type = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute("SELECT AVG(score) FROM samples")
            avg_score = cursor.fetchone()[0] or 0

            return {
                "total": total,
                "by_type": by_type,
                "avg_score": round(avg_score, 3)
            }


# ==================== CLI 인터페이스 ====================

def main():
    import argparse
    import sys
    from .cli_output import print_success, print_error
    from .cli_args import normalize_global_project_root, load_json_arg
    from .index_manager import IndexManager

    parser = argparse.ArgumentParser(description="Style Sampler CLI")
    parser.add_argument("--project-root", type=str, help="프로젝트 루트 디렉토리")

    subparsers = parser.add_subparsers(dest="command")

    # 통계 조회
    subparsers.add_parser("stats")

    # 샘플 목록
    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--type", help="유형별 필터링")
    list_parser.add_argument("--limit", type=int, default=10)

    # 샘플 추출
    extract_parser = subparsers.add_parser("extract")
    extract_parser.add_argument("--chapter", type=int, required=True)
    extract_parser.add_argument("--score", type=float, required=True)
    extract_parser.add_argument("--scenes", required=True, help="JSON 형식의 장면 목록")

    # 샘플 선택
    select_parser = subparsers.add_parser("select")
    select_parser.add_argument("--outline", required=True, help="챕터 아웃라인")
    select_parser.add_argument("--max", type=int, default=3)

    argv = normalize_global_project_root(sys.argv[1:])
    args = parser.parse_args(argv)
    command_started_at = time.perf_counter()

    # 초기화
    config = None
    if args.project_root:
        # “작업 영역 루트 디렉토리” 전달 허용, 실제 book project_root로 통일 해석 (.webnovel/state.json 포함 필수)
        from project_locator import resolve_project_root
        from .config import DataModulesConfig

        resolved_root = resolve_project_root(args.project_root)
        config = DataModulesConfig.from_project_root(resolved_root)

    sampler = StyleSampler(config)
    logger = IndexManager(config)
    tool_name = f"style_sampler:{args.command or 'unknown'}"

    def _append_timing(success: bool, *, error_code: str | None = None, error_message: str | None = None, chapter: int | None = None):
        elapsed_ms = int((time.perf_counter() - command_started_at) * 1000)
        safe_append_perf_timing(
            sampler.config.project_root,
            tool_name=tool_name,
            success=success,
            elapsed_ms=elapsed_ms,
            chapter=chapter,
            error_code=error_code,
            error_message=error_message,
        )

    def emit_success(data=None, message: str = "ok", chapter: int | None = None):
        print_success(data, message=message)
        safe_log_tool_call(logger, tool_name=tool_name, success=True)
        _append_timing(True, chapter=chapter)

    def emit_error(code: str, message: str, suggestion: str | None = None, chapter: int | None = None):
        print_error(code, message, suggestion=suggestion)
        safe_log_tool_call(
            logger,
            tool_name=tool_name,
            success=False,
            error_code=code,
            error_message=message,
        )
        _append_timing(False, error_code=code, error_message=message, chapter=chapter)

    if args.command == "stats":
        stats = sampler.get_stats()
        emit_success(stats, message="stats")

    elif args.command == "list":
        if args.type:
            samples = sampler.get_samples_by_type(args.type, args.limit)
        else:
            samples = sampler.get_best_samples(args.limit)
        emit_success([s.__dict__ for s in samples], message="samples")

    elif args.command == "extract":
        scenes = load_json_arg(args.scenes)
        candidates = sampler.extract_candidates(
            chapter=args.chapter,
            content="",
            review_score=args.score,
            scenes=scenes,
        )

        added = []
        skipped = []
        for c in candidates:
            if sampler.add_sample(c):
                added.append(c.id)
            else:
                skipped.append(c.id)
        emit_success({"added": added, "skipped": skipped}, message="extracted", chapter=args.chapter)

    elif args.command == "select":
        samples = sampler.select_samples_for_chapter(args.outline, max_samples=args.max)
        emit_success([s.__dict__ for s in samples], message="selected")

    else:
        emit_error("UNKNOWN_COMMAND", "유효한 명령이 지정되지 않음", suggestion="--help를 참조하세요")


if __name__ == "__main__":
    main()
