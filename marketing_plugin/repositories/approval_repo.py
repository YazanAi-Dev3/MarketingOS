"""Human Approval Repository for Marketing OS."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
import sqlite3

from schemas.models import Approval, ApprovalDecision


class ApprovalRepository:
    """Manages Human Approval state machine guarding external actions."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.conn = connection

    def create_request(self, approval: Approval) -> None:
        """Insert a new approval request."""
        sql = """
            INSERT INTO approvals (
                approval_id, action_type, target_type, target_id,
                requested_at, resolved_at, actor_id, decision, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        self.conn.execute(
            sql,
            (
                approval.approval_id,
                approval.action_type,
                approval.target_type,
                approval.target_id,
                approval.requested_at.isoformat(),
                approval.resolved_at.isoformat() if approval.resolved_at else None,
                approval.actor_id,
                approval.decision.value,
                approval.notes,
            ),
        )
        self.conn.commit()

    def get_approval(self, approval_id: str) -> Optional[Approval]:
        """Fetch an approval by ID."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM approvals WHERE approval_id = ?;", (approval_id,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_approval(row)

    def resolve(
        self,
        approval_id: str,
        decision: ApprovalDecision,
        actor_id: str,
        notes: Optional[str] = None,
    ) -> bool:
        """Resolve a pending approval. Returns True if successfully updated."""
        sql = """
            UPDATE approvals
            SET decision = ?, resolved_at = ?, actor_id = ?, notes = ?
            WHERE approval_id = ? AND decision = 'pending';
        """
        cur = self.conn.execute(
            sql,
            (
                decision.value,
                datetime.now(timezone.utc).isoformat(),
                actor_id,
                notes,
                approval_id,
            ),
        )
        updated = cur.rowcount > 0
        if updated:
            self.conn.commit()
        return updated


    def list_pending(self, target_type: Optional[str] = None) -> List[Approval]:
        """List all pending approval requests."""
        query = "SELECT * FROM approvals WHERE decision = 'pending'"
        params: List[str] = []
        if target_type:
            query += " AND target_type = ?"
            params.append(target_type)
        query += " ORDER BY requested_at ASC;"

        cur = self.conn.cursor()
        cur.execute(query, params)
        return [self._row_to_approval(row) for row in cur.fetchall()]

    @staticmethod
    def _row_to_approval(row: sqlite3.Row) -> Approval:
        return Approval(
            approval_id=row["approval_id"],
            action_type=row["action_type"],
            target_type=row["target_type"],
            target_id=row["target_id"],
            requested_at=datetime.fromisoformat(row["requested_at"]),
            resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
            actor_id=row["actor_id"],
            decision=ApprovalDecision(row["decision"]),
            notes=row["notes"],
        )
