# Step 5 Debt Switch

## 기본 전략

- 채무 이자는 기본적으로 비활성.
- 다음 두 가지 상황에서만 활성화 허용:
  - 사용자가 명확히 활성화 요청;
  - 프로젝트에서 명시적으로 채무 추적 활성화.

## 실행 명령

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index accrue-interest --current-chapter {chapter_num}
```

## 실행 후 요구사항

- Step 5 출력에 이번에 이자 계산을 실행했는지 표기.
- 실행한 경우, 결과 요약 출력: 처리 채무 수, 누적 이자, 연체 발생 여부.
- 미실행 시, 명확히 `debt_interest: skipped (default off)` 표기.
