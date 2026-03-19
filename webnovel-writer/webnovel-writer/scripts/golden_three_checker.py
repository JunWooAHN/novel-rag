# -*- coding: utf-8 -*-
"""
골든 3챕터 검사 도구 v2.0 (LLM-Driven)

기능: 소설 처음 3챕터가 "골든 3챕터" 기준에 부합하는지 검사

v2.0 주요 업그레이드：
- 키워드 사전 검사를 빠른 모드로 유지
- LLM 심층 평가 모드 추가（AI Native）
- 구조화된 평가 Prompt 생성, XML 평가 결과 파싱

핵심 체크포인트：
- 第 1 章：300 자 이내 주인공 등장 + 골든핑거 단서 + 강한 갈등 오프닝
- 第 2 章：골든핑거 시연 + 첫 번째 소규모 승리 + 즉시 카타르시스
- 第 3 章：서스펜스 후크 + 다음 단계 예고 + 카타르시스 밀도 >= 1

사용법：
python golden_three_checker.py --auto                    # 빠른 키워드 모드
python golden_three_checker.py --auto --mode llm         # LLM 심층 평가(권장)
python golden_three_checker.py --auto --generate-prompt  # 평가 Prompt만 생성
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path

from runtime_compat import enable_windows_utf8_stdio
from typing import Dict, List, Optional, Any

# 프로젝트 위치 및 챕터 경로 모듈 임포트
from project_locator import resolve_project_root
from chapter_paths import find_chapter_file

# Windows UTF-8 출력 수정
if sys.platform == "win32":
    enable_windows_utf8_stdio()


# ============================================================================
# LLM 평가 Prompt 템플릿
# ============================================================================

LLM_EVALUATION_PROMPT = """당신은 웹소설 편집자로, 소설 오프닝의 "골든 3챕터" 품질을 평가하는 전문가입니다.

다음 기준에 따라 이 세 챕터의 내용을 전문적으로 평가해 주세요:

## 골든 3챕터 기준

### 제1챕터 핵심 체크포인트：
1. **주인공 300자 이내 등장**：주인공이 처음 300자 이내에 등장하는가? 신분이 명확한가?
2. **골든핑거 단서**：골든핑거/치트의 암시나 단서가 있는가?
3. **강한 갈등 오프닝**：오프닝에 충분히 강한 갈등/위기/모순이 있는가?

### 제2챕터 핵심 체크포인트：
1. **골든핑거 시연**：골든핑거가 명확히 시연되었는가? 독자가 그 능력을 이해할 수 있는가?
2. **첫 번째 소규모 승리**：주인공이 첫 번째 소규모 승리/성공을 거두었는가?
3. **즉시 카타르시스**：독자가 통쾌함/만족감을 느끼는 장면이 있는가?

### 제3챕터 핵심 체크포인트：
1. **서스펜스 후크**：챕터 끝에 서스펜스가 있는가? 독자의 계속 읽기를 유도할 수 있는가?
2. **다음 단계 예고**：다음 스토리 방향/새로운 도전이 암시되었는가?
3. **카타르시스 밀도**：이번 챕터에 최소 1개의 명확한 카타르시스 장면이 있는가?

---

## 평가 대상 내용

### 第 1 章
```
{chapter1_content}
```

### 第 2 章
```
{chapter2_content}
```

### 第 3 章
```
{chapter3_content}
```

---

## 출력 요구사항

다음 XML 형식으로 평가 결과를 출력하세요(형식을 엄격히 준수)：

```xml
<golden_three_assessment>
  <chapter num="1">
    <check name="主角300자内出场" passed="true|false" score="0-100">
      <evidence>구체적 증거/원문 인용</evidence>
      <suggestion>미통과 시, 개선 제안 제시</suggestion>
    </check>
    <check name="골든핑거 단서" passed="true|false" score="0-100">
      <evidence>구체적 증거</evidence>
      <suggestion>개선 제안</suggestion>
    </check>
    <check name="강한 갈등 오프닝" passed="true|false" score="0-100">
      <evidence>구체적 증거</evidence>
      <suggestion>개선 제안</suggestion>
    </check>
  </chapter>

  <chapter num="2">
    <check name="골든핑거 시연" passed="true|false" score="0-100">
      <evidence>구체적 증거</evidence>
      <suggestion>개선 제안</suggestion>
    </check>
    <check name="첫 번째 소규모 승리" passed="true|false" score="0-100">
      <evidence>구체적 증거</evidence>
      <suggestion>개선 제안</suggestion>
    </check>
    <check name="즉시 카타르시스" passed="true|false" score="0-100">
      <evidence>구체적 증거</evidence>
      <suggestion>개선 제안</suggestion>
    </check>
  </chapter>

  <chapter num="3">
    <check name="서스펜스 후크" passed="true|false" score="0-100">
      <evidence>구체적 증거</evidence>
      <suggestion>개선 제안</suggestion>
    </check>
    <check name="다음 단계 예고" passed="true|false" score="0-100">
      <evidence>구체적 증거</evidence>
      <suggestion>개선 제안</suggestion>
    </check>
    <check name="카타르시스 밀도>=1" passed="true|false" score="0-100">
      <evidence>구체적 증거</evidence>
      <suggestion>개선 제안</suggestion>
    </check>
  </chapter>

  <overall_score>0-100</overall_score>
  <verdict>우수|양호|需改进|严重不足</verdict>
  <top_issues>
    <issue priority="1">가장 개선이 필요한 문제</issue>
    <issue priority="2">부차적 문제</issue>
  </top_issues>
</golden_three_assessment>
```

지금 평가를 시작합니다：
"""


class GoldenThreeChecker:
    """골든 3챕터 검사기 v2.0"""

    def __init__(self, chapter_files: List[str], mode: str = "keyword"):
        """
        검사기 초기화

        Args:
            chapter_files: 챕터 파일 경로 목록(반드시 처음 3챕터)
            mode: 검사 모드 ("keyword" 빠른 모드, "llm" LLM평가 모드)
        """
        if len(chapter_files) != 3:
            raise ValueError("처음 3챕터의 파일 경로를 제공해야 합니다")

        self.chapter_files = chapter_files
        self.mode = mode
        self.chapters: List[Dict[str, Any]] = []
        self.results: Dict[str, Any] = {
            "mode": mode,
            "ch1": {"主角300자内出场": False, "골든핑거 단서": False, "강한 갈등 오프닝": False, "상세": {}},
            "ch2": {"골든핑거 시연": False, "첫 번째 소규모 승리": False, "즉시 카타르시스": False, "상세": {}},
            "ch3": {"서스펜스 후크": False, "다음 단계 예고": False, "카타르시스 밀도>=1": False, "상세": {}},
        }

    def load_chapters(self) -> None:
        """챕터 내용 로드"""
        for i, file_path in enumerate(self.chapter_files):
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"파일이 존재하지 않음: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.chapters.append({
                    "number": i + 1,
                    "path": file_path,
                    "content": content,
                    "word_count": len(re.sub(r'\s+', '', content))
                })

    # ============================================================================
    # 빠른 키워드 모드(기존 로직 유지)
    # ============================================================================

    def check_chapter1_keywords(self) -> None:
        """제1챕터 검사(키워드 모드)"""
        content = self.chapters[0]["content"]
        first_300_chars = content[:300]

        # 检查1: 주인공 300자 이내 등장
        protagonist_keywords = ["林天", "我", "主角", "少年", "他", "叶凡", "萧炎", "楚枫"]
        for keyword in protagonist_keywords:
            if keyword in first_300_chars:
                self.results["ch1"]["主角300자内出场"] = True
                self.results["ch1"]["상세"]["주인공 등장 키워드"] = keyword
                break

        # 检查2: 골든핑거 단서
        golden_finger_keywords = [
            "系统", "空间", "重生", "穿越", "戒指", "老爷爷",
            "器灵", "传承", "血脉", "觉醒", "签到", "퀘스트", "面板", "属性"
        ]
        found = [kw for kw in golden_finger_keywords if kw in content]
        self.results["ch1"]["골든핑거 단서"] = len(found) > 0
        self.results["ch1"]["상세"]["골든핑거 키워드"] = found

        # 检查3: 강한 갈등 오프닝
        conflict_keywords = [
            "退婚", "羞辱", "嘲讽", "废物", "落魄", "危机",
            "追杀", "绝境", "被困", "重伤", "濒死", "灭族"
        ]
        found = [kw for kw in conflict_keywords if kw in content]
        self.results["ch1"]["강한 갈등 오프닝"] = len(found) > 0
        self.results["ch1"]["상세"]["갈등 키워드"] = found

    def check_chapter2_keywords(self) -> None:
        """제2챕터 검사(키워드 모드)"""
        content = self.chapters[1]["content"]

        system_display_keywords = ["【", "╔", "姓名", "경지", "力量", "属性", "获得", "奖励", "升级"]
        found = [kw for kw in system_display_keywords if kw in content]
        self.results["ch2"]["골든핑거 시연"] = len(found) >= 2
        self.results["ch2"]["상세"]["시연 키워드"] = found

        victory_keywords = ["击败", "胜利", "获胜", "成功", "통과", "突破", "秒杀", "碾压"]
        found = [kw for kw in victory_keywords if kw in content]
        self.results["ch2"]["첫 번째 소규모 승리"] = len(found) > 0
        self.results["ch2"]["상세"]["승리 키워드"] = found

        cool_keywords = ["震惊", "不可能", "怎么会", "全场哗然", "目瞪口呆", "难以置信"]
        found = [kw for kw in cool_keywords if kw in content]
        self.results["ch2"]["즉시 카타르시스"] = len(found) >= 2
        self.results["ch2"]["상세"]["카타르시스 키워드"] = found

    def check_chapter3_keywords(self) -> None:
        """제3챕터 검사(키워드 모드)"""
        content = self.chapters[2]["content"]
        last_300_chars = content[-300:]

        suspense_keywords = ["？", "！", "危机", "即将", "突然", "就在这时", "阴影", "杀机"]
        found = [kw for kw in suspense_keywords if kw in last_300_chars]
        self.results["ch3"]["서스펜스 후크"] = len(found) >= 2
        self.results["ch3"]["상세"]["서스펜스 키워드"] = found

        preview_keywords = ["秘境", "大比", "选拔", "试炼", "퀘스트", "挑战", "前往", "即将"]
        found = [kw for kw in preview_keywords if kw in content]
        self.results["ch3"]["다음 단계 예고"] = len(found) > 0
        self.results["ch3"]["상세"]["예고 키워드"] = found

        cool_count = sum(content.count(kw) for kw in ["震惊", "不可能", "全场哗然", "天才", "击败", "获得"])
        self.results["ch3"]["카타르시스 밀도>=1"] = cool_count >= 1
        self.results["ch3"]["상세"]["카타르시스 통계"] = cool_count

    # ============================================================================
    # LLM 평가 모드
    # ============================================================================

    def generate_llm_prompt(self) -> str:
        """LLM 평가 Prompt 생성"""
        # 각 챕터 내용 발췌(너무 길지 않도록)
        max_chars_per_chapter = 6000

        ch1 = self.chapters[0]["content"][:max_chars_per_chapter]
        ch2 = self.chapters[1]["content"][:max_chars_per_chapter]
        ch3 = self.chapters[2]["content"][:max_chars_per_chapter]

        prompt = LLM_EVALUATION_PROMPT.format(
            chapter1_content=ch1,
            chapter2_content=ch2,
            chapter3_content=ch3
        )
        return prompt

    def parse_llm_response(self, xml_response: str) -> Dict[str, Any]:
        """LLM이 반환한 XML 평가 결과 파싱"""
        results: Dict[str, Any] = {
            "mode": "llm",
            "ch1": {"상세": {}},
            "ch2": {"상세": {}},
            "ch3": {"상세": {}},
            "overall_score": 0,
            "verdict": "",
            "top_issues": []
        }

        # 추출 overall_score
        score_match = re.search(r'<overall_score>(\d+)</overall_score>', xml_response)
        if score_match:
            results["overall_score"] = int(score_match.group(1))

        # 추출 verdict
        verdict_match = re.search(r'<verdict>([^<]+)</verdict>', xml_response)
        if verdict_match:
            results["verdict"] = verdict_match.group(1).strip()

        # 각 챕터의 체크포인트 추출
        chapter_pattern = re.compile(
            r'<chapter num="(\d)">(.*?)</chapter>',
            re.DOTALL
        )
        check_pattern = re.compile(
            r'<check name="([^"]+)" passed="(true|false)" score="(\d+)">\s*'
            r'<evidence>([^<]*)</evidence>\s*'
            r'<suggestion>([^<]*)</suggestion>\s*'
            r'</check>',
            re.DOTALL
        )

        for chapter_match in chapter_pattern.finditer(xml_response):
            chapter_num = chapter_match.group(1)
            chapter_content = chapter_match.group(2)
            chapter_key = f"ch{chapter_num}"

            for check_match in check_pattern.finditer(chapter_content):
                check_name = check_match.group(1)
                passed = check_match.group(2) == "true"
                score = int(check_match.group(3))
                evidence = check_match.group(4).strip()
                suggestion = check_match.group(5).strip()

                results[chapter_key][check_name] = passed
                results[chapter_key]["상세"][check_name] = {
                    "score": score,
                    "evidence": evidence,
                    "suggestion": suggestion
                }

        # 추출 top_issues
        issue_pattern = re.compile(r'<issue priority="(\d)">([^<]+)</issue>')
        for issue_match in issue_pattern.finditer(xml_response):
            priority = int(issue_match.group(1))
            issue_text = issue_match.group(2).strip()
            results["top_issues"].append({"priority": priority, "issue": issue_text})

        return results

    # ============================================================================
    # 보고서 생성
    # ============================================================================

    def calculate_score(self) -> tuple:
        """전체 점수 계산"""
        total_checks = 0
        passed_checks = 0

        for chapter_key in ["ch1", "ch2", "ch3"]:
            for check_key, check_value in self.results[chapter_key].items():
                if check_key != "상세" and isinstance(check_value, bool):
                    total_checks += 1
                    if check_value:
                        passed_checks += 1

        score = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        return score, passed_checks, total_checks

    def generate_report(self) -> str:
        """검사 보고서 생성"""
        score, passed, total = self.calculate_score()

        report = []
        report.append("=" * 60)
        report.append(f"골든 3챕터 진단 보고서 (모드: {self.mode})")
        report.append("=" * 60)
        report.append(f"\n전체 점수: {score:.1f}% ({passed}/{total} 항목 통과)\n")

        # 第 1 章
        report.append("-" * 60)
        report.append("【第 1 章】검사 결과")
        report.append("-" * 60)
        for check_name in ["主角300자内出场", "골든핑거 단서", "강한 갈등 오프닝"]:
            passed = self.results["ch1"].get(check_name, False)
            icon = "✅" if passed else "❌"
            report.append(f"{icon} {check_name}: {'통과' if passed else '미통과'}")

            # 显示상세信息
            detail = self.results["ch1"]["상세"].get(check_name)
            if isinstance(detail, dict):
                if detail.get("evidence"):
                    report.append(f"   └─ 증거: {detail['evidence'][:100]}...")
                if not passed and detail.get("suggestion"):
                    report.append(f"   └─ 제안: {detail['suggestion']}")
            elif isinstance(detail, list) and detail:
                report.append(f"   └─ 키워드: {', '.join(detail[:5])}")

        # 第 2 章
        report.append("\n" + "-" * 60)
        report.append("【第 2 章】검사 결과")
        report.append("-" * 60)
        for check_name in ["골든핑거 시연", "첫 번째 소규모 승리", "즉시 카타르시스"]:
            passed = self.results["ch2"].get(check_name, False)
            icon = "✅" if passed else "❌"
            report.append(f"{icon} {check_name}: {'통과' if passed else '미통과'}")
            detail = self.results["ch2"]["상세"].get(check_name)
            if isinstance(detail, dict) and detail.get("evidence"):
                report.append(f"   └─ 증거: {detail['evidence'][:100]}...")
            elif isinstance(detail, list) and detail:
                report.append(f"   └─ 키워드: {', '.join(detail[:5])}")

        # 第 3 章
        report.append("\n" + "-" * 60)
        report.append("【第 3 章】검사 결과")
        report.append("-" * 60)
        for check_name in ["서스펜스 후크", "다음 단계 예고", "카타르시스 밀도>=1"]:
            passed = self.results["ch3"].get(check_name, False)
            icon = "✅" if passed else "❌"
            report.append(f"{icon} {check_name}: {'통과' if passed else '미통과'}")
            detail = self.results["ch3"]["상세"].get(check_name)
            if isinstance(detail, dict) and detail.get("evidence"):
                report.append(f"   └─ 증거: {detail['evidence'][:100]}...")

        # 개선 제안
        report.append("\n" + "=" * 60)
        report.append("【개선 제안】")
        report.append("=" * 60)

        if score < 60:
            report.append("\n🔴 경고: 오프닝 매력 부족, 독자 유지율에 심각한 영향!")
        elif score < 80:
            report.append("\n🟡 주의: 오프닝에 개선 여지 있음")
        else:
            report.append("\n✅ 좋습니다! 오프닝이 골든 3챕터 기준에 부합")

        # LLM 모드的额外信息
        if self.mode == "llm" and self.results.get("top_issues"):
            report.append("\n우선 수정：")
            for issue in self.results["top_issues"]:
                report.append(f"  {issue['priority']}. {issue['issue']}")

        report.append("\n" + "=" * 60)
        return "\n".join(report)

    def run(self) -> None:
        """검사 실행"""
        print("챕터 로딩 중...")
        self.load_chapters()

        print(f"✅ 로드 완료 {len(self.chapters)} 章")
        for ch in self.chapters:
            print(f"   - 第 {ch['number']} 章: {ch['word_count']} 자")
        print(f"\n검사 실행 중 (모드: {self.mode})...\n")

        if self.mode == "keyword":
            self.check_chapter1_keywords()
            self.check_chapter2_keywords()
            self.check_chapter3_keywords()
            report = self.generate_report()
            print(report)

        elif self.mode == "llm":
            prompt = self.generate_llm_prompt()
            print("=" * 60)
            print("LLM 평가 모드: 다음 Prompt를 Claude/GPT에 전송하세요")
            print("=" * 60)
            print("\n--- PROMPT START ---\n")
            print(prompt[:2000] + "\n...[내용이 잘림, 전체 버전은 출력 파일 참조]...")
            print("\n--- PROMPT END ---\n")

            # 저장完整 prompt
            output_dir = Path(".webnovel")
            output_dir.mkdir(exist_ok=True)
            prompt_file = output_dir / "golden_three_prompt.md"
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            print(f"📄 전체 Prompt 저장 위치: {prompt_file}")
            print("\n💡 사용법：")
            print("   1. Prompt를 Claude/GPT에 전송")
            print("   2. XML 형식의 평가 결과 획득")
            print("   3. 실행: python golden_three_checker.py --parse-response <response.xml>")

        # 결과 저장
        output_dir = Path(".webnovel")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "golden_three_report.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"\n📄 상세 결과 저장 위치: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="골든 3챕터 검사 도구 v2.0 (LLM-Driven)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시：
  # 빠른 키워드 모드(기본값)
  python golden_three_checker.py --auto

  # LLM 심층 평가 모드(권장)
  python golden_three_checker.py --auto --mode llm

  # LLM이 반환한 평가 결과 파싱
  python golden_three_checker.py --parse-response response.xml
""".strip(),
    )

    parser.add_argument("chapter_files", nargs="*", help="처음 3챕터 파일 경로")
    parser.add_argument("--auto", action="store_true", help="처음 3챕터 파일 자동 탐지")
    parser.add_argument("--mode", choices=["keyword", "llm"], default="keyword",
                        help="검사 모드: keyword(빠름) / llm(심층)")
    parser.add_argument("--project-root", default=None, help="프로젝트 루트 디렉토리")
    parser.add_argument("--parse-response", metavar="FILE", help="LLM이 반환한 XML 파일 파싱")

    args = parser.parse_args()

    # LLM 응답 모드 파싱
    if args.parse_response:
        if not os.path.exists(args.parse_response):
            print(f"❌ 파일이 존재하지 않음: {args.parse_response}")
            sys.exit(1)

        with open(args.parse_response, 'r', encoding='utf-8') as f:
            xml_content = f.read()

        checker = GoldenThreeChecker(["dummy"] * 3, mode="llm")
        checker.results = checker.parse_llm_response(xml_content)

        print("=" * 60)
        print("LLM 평가 결과 파싱")
        print("=" * 60)
        print(json.dumps(checker.results, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 일반 검사 모드
    chapter_files = []

    if args.auto or not args.chapter_files:
        try:
            project_root = resolve_project_root(args.project_root)
        except FileNotFoundError as e:
            print(f"❌ {e}")
            sys.exit(1)

        for i in range(1, 4):
            chapter_path = find_chapter_file(project_root, i)
            if chapter_path:
                chapter_files.append(str(chapter_path))
            else:
                print(f"❌ 찾을 수 없음: 제 {i} 챕터 파일 삭제")
                sys.exit(1)

        print(f"📂 프로젝트 루트 디렉토리: {project_root}")
        print(f"📄 처음 3챕터 감지 완료: {', '.join(Path(f).name for f in chapter_files)}\n")
    else:
        if len(args.chapter_files) < 3:
            print("사용법: python golden_three_checker.py <第1章路径> <第2章路径> <第3章路径>")
            sys.exit(1)
        chapter_files = args.chapter_files[:3]

    try:
        checker = GoldenThreeChecker(chapter_files, mode=args.mode)
        checker.run()
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
