"""Lead and Assessment Repository for Marketing OS."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional
import sqlite3

from schemas.models import FunnelType, Lead, LeadAssessment, LeadStatus


class LeadRepository:
    """Manages Leads and their append-only LeadAssessments in SQLite."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.conn = connection

    def save_lead(self, lead: Lead) -> None:
        """Insert or update a lead."""
        sql = """
            INSERT INTO leads (
                lead_id, company_id, funnel, status, priority_bucket,
                recommended_service_key, owner, next_action,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(lead_id) DO UPDATE SET
                status = excluded.status,
                priority_bucket = excluded.priority_bucket,
                recommended_service_key = excluded.recommended_service_key,
                owner = excluded.owner,
                next_action = excluded.next_action,
                updated_at = excluded.updated_at;
        """
        self.conn.execute(
            sql,
            (
                lead.lead_id,
                lead.company_id,
                lead.funnel.value,
                lead.status.value,
                lead.priority_bucket,
                lead.recommended_service_key,
                lead.owner,
                lead.next_action,
                lead.created_at.isoformat(),
                lead.updated_at.isoformat(),
            ),
        )
        self.conn.commit()

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Fetch a lead by ID."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM leads WHERE lead_id = ?;", (lead_id,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_lead(row)

    def list_leads(
        self,
        funnel: Optional[FunnelType] = None,
        status: Optional[LeadStatus] = None,
        max_priority_bucket: Optional[int] = None,
        company_id: Optional[str] = None,
    ) -> List[Lead]:
        """List leads matching criteria, ordered by priority bucket (1 is highest)."""
        query = "SELECT * FROM leads WHERE 1=1"
        params: List[Any] = []
        if company_id:
            query += " AND company_id = ?"
            params.append(company_id)
        if funnel:
            query += " AND funnel = ?"
            params.append(funnel.value)
        if status:
            query += " AND status = ?"
            params.append(status.value)
        if max_priority_bucket is not None:
            query += " AND priority_bucket <= ?"
            params.append(max_priority_bucket)
        query += " ORDER BY priority_bucket ASC, updated_at DESC;"

        cur = self.conn.cursor()
        cur.execute(query, params)
        return [self._row_to_lead(row) for row in cur.fetchall()]

    def get_lead_by_company(self, company_id: str) -> Optional[Lead]:
        """Fetch the most relevant lead for a company."""
        leads = self.list_leads(company_id=company_id)
        return leads[0] if leads else None

    def save_assessment(self, assessment: LeadAssessment) -> None:
        """Append a new assessment snapshot for a lead."""
        sql = """
            INSERT INTO lead_assessments (
                assessment_id, lead_id, assessment_version, fit_score,
                pain_score, urgency_score, reachability_score, final_score,
                confidence, recommended_service_key, evidence_ids,
                reasoning_summary, provider_identity, prompt_contract_version,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        self.conn.execute(
            sql,
            (
                assessment.assessment_id,
                assessment.lead_id,
                assessment.assessment_version,
                assessment.fit_score,
                assessment.pain_score,
                assessment.urgency_score,
                assessment.reachability_score,
                assessment.final_score,
                assessment.confidence,
                assessment.recommended_service_key,
                json.dumps(assessment.evidence_ids, ensure_ascii=False),
                assessment.reasoning_summary,
                assessment.provider_identity,
                assessment.prompt_contract_version,
                assessment.created_at.isoformat(),
            ),
        )
        self.conn.commit()

    def get_latest_assessment(self, lead_id: str) -> Optional[LeadAssessment]:
        """Fetch the most recent assessment for a lead."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM lead_assessments WHERE lead_id = ? ORDER BY created_at DESC, rowid DESC LIMIT 1;",
            (lead_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_assessment(row)

    @staticmethod
    def _row_to_lead(row: sqlite3.Row) -> Lead:
        return Lead(
            lead_id=row["lead_id"],
            company_id=row["company_id"],
            funnel=FunnelType(row["funnel"]),
            status=LeadStatus(row["status"]),
            priority_bucket=int(row["priority_bucket"]),
            recommended_service_key=row["recommended_service_key"],
            owner=row["owner"],
            next_action=row["next_action"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_assessment(row: sqlite3.Row) -> LeadAssessment:
        return LeadAssessment(
            assessment_id=row["assessment_id"],
            lead_id=row["lead_id"],
            assessment_version=row["assessment_version"],
            fit_score=float(row["fit_score"]),
            pain_score=float(row["pain_score"]),
            urgency_score=float(row["urgency_score"]),
            reachability_score=float(row["reachability_score"]),
            final_score=float(row["final_score"]),
            confidence=float(row["confidence"]),
            recommended_service_key=row["recommended_service_key"],
            evidence_ids=json.loads(row["evidence_ids"]),
            reasoning_summary=row["reasoning_summary"],
            provider_identity=row["provider_identity"],
            prompt_contract_version=row["prompt_contract_version"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

