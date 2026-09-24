"""Interaction Repository for Marketing OS.

Manages conversational interactions across channels (WhatsApp, Telegram, Email, Web)
in SQLite according to migrations/001_initial_schema.sql (table interactions).
"""
from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
from typing import List, Optional

from schemas.models import (
    ActorType,
    Interaction,
    InteractionDirection,
    utc_now,
)


class InteractionRepository:
    """Manages Interaction entity lifecycle in SQLite."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.conn = connection

    def save_interaction(self, interaction: Interaction) -> None:
        """Insert or update an interaction record."""
        sql = """
            INSERT INTO interactions (
                interaction_id, lead_id, channel, external_party_ref,
                direction, actor, content_summary, outcome_tag,
                raw_content_path, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(interaction_id) DO UPDATE SET
                lead_id = excluded.lead_id,
                channel = excluded.channel,
                external_party_ref = excluded.external_party_ref,
                direction = excluded.direction,
                actor = excluded.actor,
                content_summary = excluded.content_summary,
                outcome_tag = excluded.outcome_tag,
                raw_content_path = excluded.raw_content_path,
                occurred_at = excluded.occurred_at;
        """
        self.conn.execute(
            sql,
            (
                interaction.interaction_id,
                interaction.lead_id,
                interaction.channel,
                interaction.external_party_ref,
                interaction.direction.value if hasattr(interaction.direction, "value") else str(interaction.direction),
                interaction.actor.value if hasattr(interaction.actor, "value") else str(interaction.actor),
                interaction.content_summary,
                interaction.outcome_tag,
                interaction.raw_content_path,
                interaction.occurred_at.isoformat() if interaction.occurred_at else utc_now().isoformat(),
            ),
        )
        self.conn.commit()

    def get_interaction(self, interaction_id: str) -> Optional[Interaction]:
        """Fetch an interaction by ID."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM interactions WHERE interaction_id = ?;", (interaction_id,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_interaction(row)

    def list_interactions(
        self,
        lead_id: Optional[str] = None,
        channel: Optional[str] = None,
        actor: Optional[ActorType] = None,
        direction: Optional[InteractionDirection] = None,
        limit: int = 50,
    ) -> List[Interaction]:
        """List interactions with optional filters."""
        query = "SELECT * FROM interactions WHERE 1=1"
        params: list = []

        if lead_id:
            query += " AND lead_id = ?"
            params.append(lead_id)
        if channel:
            query += " AND channel = ?"
            params.append(channel.lower().strip())
        if actor:
            query += " AND actor = ?"
            params.append(actor.value if hasattr(actor, "value") else str(actor))
        if direction:
            query += " AND direction = ?"
            params.append(direction.value if hasattr(direction, "value") else str(direction))

        query += " ORDER BY occurred_at DESC, rowid DESC LIMIT ?"
        params.append(limit)

        cur = self.conn.cursor()
        cur.execute(query, params)
        return [self._row_to_interaction(row) for row in cur.fetchall()]

    def update_outcome(self, interaction_id: str, outcome_tag: str) -> bool:
        """Updates the outcome_tag of an interaction."""
        sql = "UPDATE interactions SET outcome_tag = ? WHERE interaction_id = ?;"
        cur = self.conn.execute(sql, (outcome_tag.strip(), interaction_id))
        updated = cur.rowcount > 0
        if updated:
            self.conn.commit()
        return updated

    @staticmethod
    def _row_to_interaction(row: sqlite3.Row) -> Interaction:
        occ_dt = datetime.fromisoformat(row["occurred_at"]) if row["occurred_at"] else utc_now()
        return Interaction(
            interaction_id=row["interaction_id"],
            lead_id=row["lead_id"],
            channel=row["channel"],
            external_party_ref=row["external_party_ref"],
            direction=InteractionDirection(row["direction"]),
            actor=ActorType(row["actor"]),
            content_summary=row["content_summary"],
            outcome_tag=row["outcome_tag"],
            raw_content_path=row["raw_content_path"],
            occurred_at=occ_dt,
        )
