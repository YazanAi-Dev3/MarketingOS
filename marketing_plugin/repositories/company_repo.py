"""Company Repository for Marketing OS."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional
import sqlite3

from schemas.models import Company, FunnelType


class CompanyRepository:
    """Manages Company entities and identity resolution lookups in SQLite."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.conn = connection

    def save_company(self, company: Company) -> None:
        """Insert or update a company entity."""
        sql = """
            INSERT INTO companies (
                company_id, canonical_name, primary_domain, country_code, city,
                sector, public_contacts_json, funnel, entity_confidence,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(company_id) DO UPDATE SET
                canonical_name = excluded.canonical_name,
                primary_domain = excluded.primary_domain,
                country_code = excluded.country_code,
                city = excluded.city,
                sector = excluded.sector,
                public_contacts_json = excluded.public_contacts_json,
                funnel = excluded.funnel,
                entity_confidence = excluded.entity_confidence,
                updated_at = excluded.updated_at;
        """
        self.conn.execute(
            sql,
            (
                company.company_id,
                company.canonical_name,
                company.primary_domain,
                company.country_code,
                company.city,
                company.sector,
                json.dumps(company.public_contacts_json, ensure_ascii=False),
                company.funnel.value,
                company.entity_confidence,
                company.created_at.isoformat(),
                company.updated_at.isoformat(),
            ),
        )
        self.conn.commit()

    def get_company(self, company_id: str) -> Optional[Company]:
        """Fetch a company by ID."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM companies WHERE company_id = ?;", (company_id,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_company(row)

    def find_by_domain(self, domain: str) -> Optional[Company]:
        """Fetch a company by primary domain for deduplication."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM companies WHERE primary_domain = ?;", (domain.lower().strip(),))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_company(row)

    def find_by_name(self, name: str, country_code: Optional[str] = None) -> List[Company]:
        """Fuzzy-search or exact match companies by canonical name."""
        query = "SELECT * FROM companies WHERE canonical_name LIKE ?"
        params: List[Any] = [f"%{name.strip()}%"]
        if country_code:
            query += " AND country_code = ?"
            params.append(country_code)
        query += " ORDER BY entity_confidence DESC;"

        cur = self.conn.cursor()
        cur.execute(query, params)
        return [self._row_to_company(row) for row in cur.fetchall()]

    @staticmethod
    def _row_to_company(row: sqlite3.Row) -> Company:
        return Company(
            company_id=row["company_id"],
            canonical_name=row["canonical_name"],
            primary_domain=row["primary_domain"],
            country_code=row["country_code"],
            city=row["city"],
            sector=row["sector"],
            public_contacts_json=json.loads(row["public_contacts_json"]),
            funnel=FunnelType(row["funnel"]),
            entity_confidence=float(row["entity_confidence"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

