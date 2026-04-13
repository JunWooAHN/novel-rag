#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IndexDebtMixin extracted from IndexManager.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional


class IndexDebtMixin:
    def create_override_contract(self, contract: OverrideContractMeta) -> int:
        """
        Override Contract 생성 또는 수정

        SQLite의 INSERT ... ON CONFLICT ... DO UPDATE로 원자적 UPSERT 구현:
        - 동시성 안전, 명시적 잠금 불필요
        - id 유지, chase_debt.override_contract_id 미아 방지
        - 종료 상태 완전 동결: 이미 fulfilled/cancelled된 계약의 모든 필드는 수정되지 않음

        호환성: SQLite 3.24+ 지원 (ON CONFLICT 문법), RETURNING(3.35+)에 의존하지 않음

        반환: 계약 ID
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()

            # ON CONFLICT로 원자적 UPSERT 구현 (SQLite 3.24+)
            # 종료 상태 완전 동결: fulfilled/cancelled 상태에서는 모든 필드 변경 불가
            cursor.execute(
                """
                INSERT INTO override_contracts
                (chapter, constraint_type, constraint_id, rationale_type,
                 rationale_text, payback_plan, due_chapter, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chapter, constraint_type, constraint_id) DO UPDATE SET
                    rationale_type = CASE
                        WHEN override_contracts.status IN ('fulfilled', 'cancelled')
                        THEN override_contracts.rationale_type
                        ELSE excluded.rationale_type
                    END,
                    rationale_text = CASE
                        WHEN override_contracts.status IN ('fulfilled', 'cancelled')
                        THEN override_contracts.rationale_text
                        ELSE excluded.rationale_text
                    END,
                    payback_plan = CASE
                        WHEN override_contracts.status IN ('fulfilled', 'cancelled')
                        THEN override_contracts.payback_plan
                        ELSE excluded.payback_plan
                    END,
                    due_chapter = CASE
                        WHEN override_contracts.status IN ('fulfilled', 'cancelled')
                        THEN override_contracts.due_chapter
                        ELSE excluded.due_chapter
                    END,
                    status = CASE
                        WHEN override_contracts.status IN ('fulfilled', 'cancelled')
                        THEN override_contracts.status
                        ELSE excluded.status
                    END
            """,
                (
                    contract.chapter,
                    contract.constraint_type,
                    contract.constraint_id,
                    contract.rationale_type,
                    contract.rationale_text,
                    contract.payback_plan,
                    contract.due_chapter,
                    contract.status,
                ),
            )

            # RETURNING 미사용 (SQLite 3.35+ 필요), 대신 쿼리로 id 조회
            cursor.execute(
                """
                SELECT id FROM override_contracts
                WHERE chapter = ? AND constraint_type = ? AND constraint_id = ?
            """,
                (contract.chapter, contract.constraint_type, contract.constraint_id),
            )
            row = cursor.fetchone()
            if not row:
                # UPSERT 후 기록을 찾지 못하는 것은 비정상 상황, 발생해서는 안 됨
                raise RuntimeError(
                    f"Override Contract UPSERT 후 id 조회 불가: "
                    f"chapter={contract.chapter}, type={contract.constraint_type}, "
                    f"id={contract.constraint_id}"
                )
            contract_id = row[0]

            conn.commit()
            return contract_id

    def get_pending_overrides(self, before_chapter: int = None) -> List[Dict]:
        """상환 대기 중인 Override Contracts 조회"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            if before_chapter:
                cursor.execute(
                    """
                    SELECT * FROM override_contracts
                    WHERE status = 'pending' AND due_chapter <= ?
                    ORDER BY due_chapter ASC
                """,
                    (before_chapter,),
                )
            else:
                cursor.execute("""
                    SELECT * FROM override_contracts
                    WHERE status = 'pending'
                    ORDER BY due_chapter ASC
                """)
            return [dict(row) for row in cursor.fetchall()]

    def get_overdue_overrides(self, current_chapter: int) -> List[Dict]:
        """이미 연체된 Override Contracts 조회"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM override_contracts
                WHERE status = 'pending' AND due_chapter < ?
                ORDER BY due_chapter ASC
            """,
                (current_chapter,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def fulfill_override(self, contract_id: int) -> bool:
        """Override Contract를 상환 완료로 표시"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE override_contracts SET
                    status = 'fulfilled',
                    fulfilled_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (contract_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_chapter_overrides(self, chapter: int) -> List[Dict]:
        """특정 챕터에서 생성된 Override Contracts 조회"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM override_contracts WHERE chapter = ?
            """,
                (chapter,),
            )
            return [dict(row) for row in cursor.fetchall()]

    # ==================== v5.3 추독력 부채 관리 ====================

    def create_debt(self, debt: ChaseDebtMeta) -> int:
        """
        추독력 부채 생성

        반환: 부채 ID
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO chase_debt
                (debt_type, original_amount, current_amount, interest_rate,
                 source_chapter, due_chapter, override_contract_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    debt.debt_type,
                    debt.original_amount,
                    debt.current_amount,
                    debt.interest_rate,
                    debt.source_chapter,
                    debt.due_chapter,
                    debt.override_contract_id if debt.override_contract_id else None,
                    debt.status,
                ),
            )
            conn.commit()
            debt_id = cursor.lastrowid

            # 생성 이벤트 기록
            self._record_debt_event(
                cursor,
                debt_id,
                "created",
                debt.original_amount,
                debt.source_chapter,
                f"부채 생성: {debt.debt_type}",
            )
            conn.commit()
            return debt_id

    def get_active_debts(self) -> List[Dict]:
        """모든 활성 부채 조회"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM chase_debt
                WHERE status = 'active'
                ORDER BY due_chapter ASC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_overdue_debts(self, current_chapter: int) -> List[Dict]:
        """이미 연체된 부채 조회 (active이지만 이미 만료된 것과 overdue로 표시된 것 포함)"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM chase_debt
                WHERE (status = 'overdue')
                   OR (status = 'active' AND due_chapter < ?)
                ORDER BY due_chapter ASC
            """,
                (current_chapter,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_total_debt_balance(self) -> float:
        """총 부채 잔액 조회 (active와 overdue 포함)"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(SUM(current_amount), 0) FROM chase_debt
                WHERE status IN ('active', 'overdue')
            """)
            return cursor.fetchone()[0]

    def accrue_interest(self, current_chapter: int) -> Dict[str, Any]:
        """
        이자 계산 (챕터당 한 번 호출)

        - active와 overdue 부채 모두 이자 부과 (연체 부채도 계속 이자 누적)
        - debt_events 테이블로 동일 챕터 중복 이자 부과 방지
        - 연체 여부 확인 및 상태 수정

        반환: {debts_processed, total_interest, new_overdues, skipped_already_processed}
        """
        result = {
            "debts_processed": 0,
            "total_interest": 0.0,
            "new_overdues": 0,
            "skipped_already_processed": 0,
        }

        with self._get_conn() as conn:
            cursor = conn.cursor()

            # 모든 미상환 부채 조회 (active + overdue 모두 계속 이자 부과)
            cursor.execute("""
                SELECT * FROM chase_debt WHERE status IN ('active', 'overdue')
            """)
            debts = cursor.fetchall()

            for debt in debts:
                debt_id = debt["id"]
                current_amount = debt["current_amount"]
                interest_rate = debt["interest_rate"]
                due_chapter = debt["due_chapter"]
                debt_status = debt["status"]

                # 이번 챕터에서 이미 이자 부과 완료 여부 확인 (중복 호출 방지)
                cursor.execute(
                    """
                    SELECT 1 FROM debt_events
                    WHERE debt_id = ? AND chapter = ? AND event_type = 'interest_accrued'
                """,
                    (debt_id, current_chapter),
                )
                if cursor.fetchone():
                    result["skipped_already_processed"] += 1
                    continue

                # 이자 계산
                interest = current_amount * interest_rate
                new_amount = current_amount + interest

                # 부채 수정
                cursor.execute(
                    """
                    UPDATE chase_debt SET
                        current_amount = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    (new_amount, debt_id),
                )

                # 이자 이벤트 기록
                self._record_debt_event(
                    cursor,
                    debt_id,
                    "interest_accrued",
                    interest,
                    current_chapter,
                    f"이자: {interest:.2f} (이율: {interest_rate * 100:.0f}%)",
                )

                result["debts_processed"] += 1
                result["total_interest"] += interest

                # 연체 여부 확인 (active 상태의 부채에만 해당)
                if debt_status == "active" and current_chapter > due_chapter:
                    cursor.execute(
                        """
                        UPDATE chase_debt SET status = 'overdue'
                        WHERE id = ? AND status = 'active'
                    """,
                        (debt_id,),
                    )
                    if cursor.rowcount > 0:
                        result["new_overdues"] += 1
                        self._record_debt_event(
                            cursor,
                            debt_id,
                            "overdue",
                            new_amount,
                            current_chapter,
                            f"부채 연체 (마감: 제{due_chapter}장)",
                        )

            conn.commit()

        return result

    def pay_debt(self, debt_id: int, amount: float, chapter: int) -> Dict[str, Any]:
        """
        부채 상환

        - amount > 0 검증
        - 완전 상환 시, 원자적 UPDATE로 연관 Override를 fulfilled로 표시
          (동시성 안전: NOT EXISTS 서브쿼리로 모든 부채가 이미 정리되었는지 확인)

        반환: {remaining, fully_paid, override_fulfilled}
        """
        # 상환 금액 검증
        if amount <= 0:
            return {
                "remaining": 0,
                "fully_paid": False,
                "error": "상환 금액은 0보다 커야 합니다",
            }

        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT current_amount, override_contract_id FROM chase_debt WHERE id = ?",
                (debt_id,),
            )
            row = cursor.fetchone()
            if not row:
                return {"remaining": 0, "fully_paid": False, "error": "부채가 존재하지 않음"}

            current = row["current_amount"]
            override_contract_id = row["override_contract_id"]
            remaining = max(0, current - amount)
            override_fulfilled = False

            if remaining == 0:
                # 완전 상환
                cursor.execute(
                    """
                    UPDATE chase_debt SET
                        current_amount = 0,
                        status = 'paid',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    (debt_id,),
                )
                self._record_debt_event(
                    cursor, debt_id, "full_payment", amount, chapter, "부채 완전 상환 완료"
                )

                # 원자적으로 확인 후 Override를 fulfilled로 표시
                # NOT EXISTS 서브쿼리로 동시성 안전 보장: 미정산 부채가 없을 때만 수정
                if override_contract_id:
                    cursor.execute(
                        """
                        UPDATE override_contracts SET
                            status = 'fulfilled',
                            fulfilled_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                          AND status = 'pending'
                          AND NOT EXISTS (
                              SELECT 1 FROM chase_debt
                              WHERE override_contract_id = ?
                                AND status IN ('active', 'overdue')
                          )
                    """,
                        (override_contract_id, override_contract_id),
                    )
                    if cursor.rowcount > 0:
                        override_fulfilled = True
            else:
                # 부분 상환
                cursor.execute(
                    """
                    UPDATE chase_debt SET
                        current_amount = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    (remaining, debt_id),
                )
                self._record_debt_event(
                    cursor,
                    debt_id,
                    "partial_payment",
                    amount,
                    chapter,
                    f"부분 상환, 잔액: {remaining:.2f}",
                )

            conn.commit()
            return {
                "remaining": remaining,
                "fully_paid": remaining == 0,
                "override_fulfilled": override_fulfilled,
            }

    def _record_debt_event(
        self,
        cursor,
        debt_id: int,
        event_type: str,
        amount: float,
        chapter: int,
        note: str = "",
    ):
        """부채 이벤트 기록 (내부 메서드)"""
        cursor.execute(
            """
            INSERT INTO debt_events (debt_id, event_type, amount, chapter, note)
            VALUES (?, ?, ?, ?, ?)
        """,
            (debt_id, event_type, amount, chapter, note),
        )

    def get_debt_history(self, debt_id: int) -> List[Dict]:
        """부채의 이벤트 이력 조회"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM debt_events
                WHERE debt_id = ?
                ORDER BY created_at ASC
            """,
                (debt_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    # ==================== v5.3 챕터 추독력 메타데이터 관리 ====================

    def get_debt_summary(self) -> Dict[str, Any]:
        """부채 요약 정보 조회"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            # 활성 부채
            cursor.execute("""
                SELECT COUNT(*) as count, COALESCE(SUM(current_amount), 0) as total
                FROM chase_debt WHERE status = 'active'
            """)
            active = cursor.fetchone()

            # 연체 부채
            cursor.execute("""
                SELECT COUNT(*) as count, COALESCE(SUM(current_amount), 0) as total
                FROM chase_debt WHERE status = 'overdue'
            """)
            overdue = cursor.fetchone()

            # 상환 대기 Override
            cursor.execute("""
                SELECT COUNT(*) FROM override_contracts WHERE status = 'pending'
            """)
            pending_overrides = cursor.fetchone()[0]

            return {
                "active_debts": active["count"],
                "active_total": active["total"],
                "overdue_debts": overdue["count"],
                "overdue_total": overdue["total"],
                "pending_overrides": pending_overrides,
                "total_balance": active["total"] + overdue["total"],
            }

    # ==================== 일괄 관리 ====================

