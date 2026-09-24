"""Content Repository for Marketing OS.

Manages ContentIdea and ContentAsset entities in SQLite according to
migrations/001_initial_schema.sql (tables content_ideas and content_assets).
"""
from __future__ import annotations

import json
import sqlite3
from typing import List, Optional

from schemas.models import (
    ContentAsset,
    ContentAssetStatus,
    ContentIdea,
    ContentIdeaObjective,
    FunnelType,
)


class ContentRepository:
    """Manages ContentIdea and ContentAsset lifecycle in SQLite."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.conn = connection

    def save_idea(self, idea: ContentIdea) -> None:
        """Insert or update a content idea."""
        sql = """
            INSERT INTO content_ideas (
                content_idea_id, funnel, market_scope, service_key,
                source_signal_ids, topic, objective, score, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(content_idea_id) DO UPDATE SET
                funnel = excluded.funnel,
                market_scope = excluded.market_scope,
                service_key = excluded.service_key,
                source_signal_ids = excluded.source_signal_ids,
                topic = excluded.topic,
                objective = excluded.objective,
                score = excluded.score,
                status = excluded.status;
        """
        self.conn.execute(
            sql,
            (
                idea.content_idea_id,
                idea.funnel.value if hasattr(idea.funnel, "value") else str(idea.funnel),
                json.dumps(idea.market_scope),
                idea.service_key,
                json.dumps(idea.source_signal_ids),
                idea.topic,
                idea.objective.value if hasattr(idea.objective, "value") else str(idea.objective),
                idea.score,
                idea.status,
            ),
        )
        self.conn.commit()

    def get_idea(self, content_idea_id: str) -> Optional[ContentIdea]:
        """Fetch a content idea by ID."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM content_ideas WHERE content_idea_id = ?;", (content_idea_id,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_idea(row)

    def list_ideas(
        self,
        service_key: Optional[str] = None,
        objective: Optional[ContentIdeaObjective] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[ContentIdea]:
        """List content ideas with optional filters."""
        query = "SELECT * FROM content_ideas WHERE 1=1"
        params: list = []

        if service_key:
            query += " AND service_key = ?"
            params.append(service_key)
        if objective:
            query += " AND objective = ?"
            params.append(objective.value if hasattr(objective, "value") else str(objective))
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY score DESC LIMIT ?"
        params.append(limit)

        cur = self.conn.cursor()
        cur.execute(query, params)
        return [self._row_to_idea(row) for row in cur.fetchall()]

    def save_asset(self, asset: ContentAsset) -> None:
        """Insert or update a content asset."""
        sql = """
            INSERT INTO content_assets (
                content_asset_id, idea_id, master_content, platform,
                format, body, media_brief, cta, status, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(content_asset_id) DO UPDATE SET
                master_content = excluded.master_content,
                platform = excluded.platform,
                format = excluded.format,
                body = excluded.body,
                media_brief = excluded.media_brief,
                cta = excluded.cta,
                status = excluded.status,
                version = excluded.version;
        """
        self.conn.execute(
            sql,
            (
                asset.content_asset_id,
                asset.idea_id,
                asset.master_content,
                asset.platform,
                asset.format,
                asset.body,
                asset.media_brief,
                asset.cta,
                asset.status.value if hasattr(asset.status, "value") else str(asset.status),
                asset.version,
            ),
        )
        self.conn.commit()

    def get_asset(self, content_asset_id: str) -> Optional[ContentAsset]:
        """Fetch a content asset by ID."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM content_assets WHERE content_asset_id = ?;", (content_asset_id,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_asset(row)

    def list_assets(
        self,
        idea_id: Optional[str] = None,
        platform: Optional[str] = None,
        status: Optional[ContentAssetStatus] = None,
        limit: int = 50,
    ) -> List[ContentAsset]:
        """List content assets with optional filters."""
        query = "SELECT * FROM content_assets WHERE 1=1"
        params: list = []

        if idea_id:
            query += " AND idea_id = ?"
            params.append(idea_id)
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        if status:
            query += " AND status = ?"
            params.append(status.value if hasattr(status, "value") else str(status))

        query += " ORDER BY version DESC, content_asset_id ASC LIMIT ?"
        params.append(limit)

        cur = self.conn.cursor()
        cur.execute(query, params)
        return [self._row_to_asset(row) for row in cur.fetchall()]

    def update_asset_status(self, content_asset_id: str, status: ContentAssetStatus) -> bool:
        """Update the status of a content asset."""
        sql = "UPDATE content_assets SET status = ? WHERE content_asset_id = ?;"
        cur = self.conn.execute(
            sql,
            (status.value if hasattr(status, "value") else str(status), content_asset_id),
        )
        updated = cur.rowcount > 0
        if updated:
            self.conn.commit()
        return updated

    @staticmethod
    def _row_to_idea(row: sqlite3.Row) -> ContentIdea:
        return ContentIdea(
            content_idea_id=row["content_idea_id"],
            funnel=FunnelType(row["funnel"]),
            market_scope=json.loads(row["market_scope"]) if row["market_scope"] else [],
            service_key=row["service_key"],
            source_signal_ids=json.loads(row["source_signal_ids"]) if row["source_signal_ids"] else [],
            topic=row["topic"],
            objective=ContentIdeaObjective(row["objective"]),
            score=float(row["score"]),
            status=row["status"],
        )

    @staticmethod
    def _row_to_asset(row: sqlite3.Row) -> ContentAsset:
        return ContentAsset(
            content_asset_id=row["content_asset_id"],
            idea_id=row["idea_id"],
            master_content=row["master_content"],
            platform=row["platform"],
            format=row["format"],
            body=row["body"],
            media_brief=row["media_brief"],
            cta=row["cta"],
            status=ContentAssetStatus(row["status"]),
            version=int(row["version"]),
        )

