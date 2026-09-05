"""Evidence Repository for Marketing OS."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import sqlite3

from schemas.models import Evidence, ExtractorType


class EvidenceRepository:
    """Manages immutable evidence records anchored by content hash."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.conn = connection

    def save_evidence(self, evidence: Evidence) -> None:
        """Insert or update an evidence record."""
        sql = """
            INSERT INTO evidence (
                evidence_id, company_id, source_id, url, artifact_path,
                observed_at, published_at, fact_type, fact_text, extractor,
                content_hash, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(evidence_id) DO UPDATE SET
                company_id = excluded.company_id,
                artifact_path = excluded.artifact_path,
                published_at = excluded.published_at,
                confidence = excluded.confidence;
        """
        self.conn.execute(
            sql,
            (
                evidence.evidence_id,
                evidence.company_id,
                evidence.source_id,
                evidence.url,
                evidence.artifact_path,
                evidence.observed_at.isoformat(),
                evidence.published_at.isoformat() if evidence.published_at else None,
                evidence.fact_type,
                evidence.fact_text,
                evidence.extractor.value,
                evidence.content_hash,
                evidence.confidence,
            ),
        )
        self.conn.commit()

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        """Fetch an evidence record by ID."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM evidence WHERE evidence_id = ?;", (evidence_id,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_evidence(row)

    def find_by_hash(self, content_hash: str) -> Optional[Evidence]:
        """Fetch primary evidence by its cryptographic content hash."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM evidence WHERE content_hash = ?;", (content_hash,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_evidence(row)

    def list_by_hash(self, content_hash: str) -> List[Evidence]:
        """Fetch all evidence records sharing the same cryptographic content hash."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM evidence WHERE content_hash = ? ORDER BY observed_at DESC;",
            (content_hash,),
        )
        return [self._row_to_evidence(row) for row in cur.fetchall()]


    def list_for_company(self, company_id: str) -> List[Evidence]:
        """Fetch all evidence items linked to a company."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM evidence WHERE company_id = ? ORDER BY observed_at DESC;",
            (company_id,),
        )
        return [self._row_to_evidence(row) for row in cur.fetchall()]

    @staticmethod
    def _row_to_evidence(row: sqlite3.Row) -> Evidence:
        return Evidence(
            evidence_id=row["evidence_id"],
            company_id=row["company_id"],
            source_id=row["source_id"],
            url=row["url"],
            artifact_path=row["artifact_path"],
            observed_at=datetime.fromisoformat(row["observed_at"]),
            published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
            fact_type=row["fact_type"],
            fact_text=row["fact_text"],
            extractor=ExtractorType(row["extractor"]),
            content_hash=row["content_hash"],
            confidence=float(row["confidence"]),
        )
