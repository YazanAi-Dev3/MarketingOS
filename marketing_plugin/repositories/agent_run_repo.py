"""Agent Run Repository for Marketing OS.

Tracks agent execution, provider usage, and token accounting in SQLite.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional
import sqlite3

from schemas.models import AgentRun


class AgentRunRepository:
    """Manages AgentRun records in SQLite with explicit commits."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.conn = connection

    def save_agent_run(self, run: AgentRun) -> None:
        """Insert or update an agent run record."""
        sql = """
            INSERT INTO agent_runs (
                agent_run_id, task_type, provider_path, model_identity,
                input_refs, input_size_estimate, output_contract_version,
                started_at, finished_at, status, error_class, approval_required
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_run_id) DO UPDATE SET
                task_type = excluded.task_type,
                provider_path = excluded.provider_path,
                model_identity = excluded.model_identity,
                input_refs = excluded.input_refs,
                input_size_estimate = excluded.input_size_estimate,
                output_contract_version = excluded.output_contract_version,
                finished_at = excluded.finished_at,
                status = excluded.status,
                error_class = excluded.error_class,
                approval_required = excluded.approval_required;
        """
        self.conn.execute(
            sql,
            (
                run.agent_run_id,
                run.task_type,
                run.provider_path,
                run.model_identity,
                json.dumps(run.input_refs, ensure_ascii=False),
                run.input_size_estimate,
                run.output_contract_version,
                run.started_at.isoformat(),
                run.finished_at.isoformat() if run.finished_at else None,
                run.status,
                run.error_class,
                1 if run.approval_required else 0,
            ),
        )
        self.conn.commit()

    def get_agent_run(self, agent_run_id: str) -> Optional[AgentRun]:
        """Fetch an agent run record by ID."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM agent_runs WHERE agent_run_id = ?;", (agent_run_id,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_agent_run(row)

    def list_by_task(self, task_type: str, limit: int = 50) -> List[AgentRun]:
        """Fetch recent runs for a given task type."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM agent_runs WHERE task_type = ? ORDER BY started_at DESC LIMIT ?;",
            (task_type, limit),
        )
        return [self._row_to_agent_run(row) for row in cur.fetchall()]

    def list_recent(self, limit: int = 50) -> List[AgentRun]:
        """Fetch recent runs across all tasks."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM agent_runs ORDER BY started_at DESC LIMIT ?;", (limit,))
        return [self._row_to_agent_run(row) for row in cur.fetchall()]

    @staticmethod
    def _row_to_agent_run(row: sqlite3.Row) -> AgentRun:
        return AgentRun(
            agent_run_id=row["agent_run_id"],
            task_type=row["task_type"],
            provider_path=row["provider_path"],
            model_identity=row["model_identity"],
            input_refs=json.loads(row["input_refs"]),
            input_size_estimate=int(row["input_size_estimate"]),
            output_contract_version=row["output_contract_version"],
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            status=row["status"],
            error_class=row["error_class"],
            approval_required=bool(row["approval_required"]),
        )

