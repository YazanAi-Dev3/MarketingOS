"""SQLite Database Connection and Migration Manager for Marketing OS.

Handles SQLite connection lifecycle, enforces WAL mode and foreign keys,
and runs migrations in migrations/*.sql.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


class Database:
    """SQLite Database manager with connection lifecycle and automatic migrations."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self._connection: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """Open or return existing SQLite connection with required pragmas."""
        if self._connection is None:
            if self.db_path != ":memory:":
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
            )
            self._connection.row_factory = sqlite3.Row
            # Enforce foreign key constraints
            self._connection.execute("PRAGMA foreign_keys = ON;")
            # Enable WAL mode for disk files
            if self.db_path != ":memory:":
                self._connection.execute("PRAGMA journal_mode = WAL;")
                self._connection.execute("PRAGMA busy_timeout = 5000;")
        return self._connection

    def close(self) -> None:
        """Close connection if open."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def run_migrations(self, migrations_dir: Optional[Path] = None) -> List[int]:
        """Apply all pending .sql migrations in numerical order."""
        conn = self.connect()
        target_dir = migrations_dir or MIGRATIONS_DIR

        # Ensure schema_migrations table exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

        # Find applied migrations
        cur = conn.cursor()
        cur.execute("SELECT version FROM schema_migrations ORDER BY version;")
        applied = {row[0] for row in cur.fetchall()}

        applied_versions: List[int] = []
        sql_files = sorted(target_dir.glob("*.sql"))

        for file_path in sql_files:
            # File convention: 001_initial_schema.sql -> version 1
            prefix = file_path.name.split("_")[0]
            if not prefix.isdigit():
                continue
            version = int(prefix)
            if version not in applied:
                logger.info("Applying migration %d: %s", version, file_path.name)
                # Take backup snapshot if on disk before applying migration
                if self.db_path != ":memory:" and Path(self.db_path).is_file():
                    import shutil
                    shutil.copy2(self.db_path, f"{self.db_path}.bak")
                script = file_path.read_text(encoding="utf-8")
                with conn:
                    conn.executescript(script)
                    conn.execute(
                        "INSERT INTO schema_migrations (version, name) VALUES (?, ?);",
                        (version, file_path.name),
                    )
                applied_versions.append(version)


        return applied_versions

    def __enter__(self) -> sqlite3.Connection:
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._connection:
            if exc_type is None:
                self._connection.commit()
            else:
                self._connection.rollback()
