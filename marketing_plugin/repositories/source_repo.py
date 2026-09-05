"""Source Registry Repository for Marketing OS."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import sqlite3

from schemas.models import AccessMode, Source, SourceCapabilityScore, SourceStatus


class SourceRepository:
    """Manages sources and their capability scores in SQLite."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.conn = connection

    def save_source(self, source: Source) -> None:
        """Insert or update a source record."""
        sql = """
            INSERT INTO sources (
                source_id, domain_or_platform_key, country_scope, source_family,
                languages, status, first_seen_at, last_seen_at, last_success_at,
                access_mode, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                domain_or_platform_key = excluded.domain_or_platform_key,
                country_scope = excluded.country_scope,
                source_family = excluded.source_family,
                languages = excluded.languages,
                status = excluded.status,
                last_seen_at = excluded.last_seen_at,
                last_success_at = excluded.last_success_at,
                access_mode = excluded.access_mode,
                metadata_json = excluded.metadata_json;
        """
        self.conn.execute(
            sql,
            (
                source.source_id,
                source.domain_or_platform_key,
                json.dumps(source.country_scope, ensure_ascii=False),
                source.source_family,
                json.dumps(source.languages, ensure_ascii=False),
                source.status.value,
                source.first_seen_at.isoformat(),
                source.last_seen_at.isoformat(),
                source.last_success_at.isoformat() if source.last_success_at else None,
                source.access_mode.value,
                json.dumps(source.metadata_json, ensure_ascii=False),
            ),
        )
        self.conn.commit()

    def get_source(self, source_id: str) -> Optional[Source]:
        """Fetch a source by its primary key."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM sources WHERE source_id = ?;", (source_id,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_source(row)

    def find_by_domain(self, domain: str) -> Optional[Source]:
        """Fetch a source by its domain/platform key."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM sources WHERE domain_or_platform_key = ?;", (domain,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_source(row)

    def list_sources(
        self,
        status: Optional[SourceStatus] = None,
        source_family: Optional[str] = None,
    ) -> List[Source]:
        """List sources matching filters."""
        query = "SELECT * FROM sources WHERE 1=1"
        params: List[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status.value)
        if source_family:
            query += " AND source_family = ?"
            params.append(source_family)
        query += " ORDER BY last_seen_at DESC;"

        cur = self.conn.cursor()
        cur.execute(query, params)
        return [self._row_to_source(row) for row in cur.fetchall()]

    def set_capability_score(
        self,
        source_id: str,
        capability: str,
        score: float,
        sample_count_increment: int = 1,
    ) -> None:
        """Insert or update capability score for a source."""
        sql = """
            INSERT INTO source_capability_scores (
                source_id, capability, score, sample_count, last_updated_at, score_version
            ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, '1.0')
            ON CONFLICT(source_id, capability) DO UPDATE SET
                score = excluded.score,
                sample_count = source_capability_scores.sample_count + excluded.sample_count,
                last_updated_at = CURRENT_TIMESTAMP;
        """
        self.conn.execute(sql, (source_id, capability, score, sample_count_increment))
        self.conn.commit()

    def get_capability_scores(self, source_id: str) -> Dict[str, float]:
        """Return a mapping of capability name to score."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT capability, score FROM source_capability_scores WHERE source_id = ?;",
            (source_id,),
        )
        return {row[0]: row[1] for row in cur.fetchall()}

    @staticmethod
    def _row_to_source(row: sqlite3.Row) -> Source:
        return Source(
            source_id=row["source_id"],
            domain_or_platform_key=row["domain_or_platform_key"],
            country_scope=json.loads(row["country_scope"]),
            source_family=row["source_family"],
            languages=json.loads(row["languages"]),
            status=SourceStatus(row["status"]),
            first_seen_at=datetime.fromisoformat(row["first_seen_at"]),
            last_seen_at=datetime.fromisoformat(row["last_seen_at"]),
            last_success_at=datetime.fromisoformat(row["last_success_at"]) if row["last_success_at"] else None,
            access_mode=AccessMode(row["access_mode"]),
            metadata_json=json.loads(row["metadata_json"]),
        )

