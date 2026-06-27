"""Ops backup registry — Postgres when configured, SQLite fallback for tests."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class OpsStore:
    def __init__(self, db_path: Path | None = None) -> None:
        from raphael_contracts import db as rdb

        self._postgres = rdb.is_postgres()
        if self._postgres:
            rdb.ensure_migrations()
        else:
            self._db = db_path or Path(os.environ.get("RAPHAEL_OPS_DB", "/tmp/raphael-ops.db"))
            self._db.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._db, check_same_thread=False)
            self._init_sqlite()

    def _init_sqlite(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS ops_backups (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL DEFAULT 'manual',
                location TEXT NOT NULL,
                services TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ops_replay_log (
                event_id TEXT PRIMARY KEY,
                replayed_at TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def add_backup(self, entry: dict[str, Any]) -> dict[str, Any]:
        services = entry.get("services", [])
        services_json = json.dumps(services)
        if self._postgres:
            from raphael_contracts import db as rdb

            rdb.pg_execute(
                "INSERT INTO ops_backups (id, label, location, services, created_at) "
                "VALUES (%s, %s, %s, %s::jsonb, %s)",
                (entry["id"], entry["label"], entry["location"], services_json, entry["created_at"]),
            )
        else:
            self._conn.execute(
                "INSERT INTO ops_backups (id, label, location, services, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (entry["id"], entry["label"], entry["location"], services_json, entry["created_at"]),
            )
            self._conn.commit()
        return entry

    def list_backups(self) -> list[dict[str, Any]]:
        if self._postgres:
            from raphael_contracts import db as rdb

            rows = rdb.pg_fetchall(
                "SELECT id, label, location, services, created_at FROM ops_backups ORDER BY created_at DESC"
            )
        else:
            rows = self._conn.execute(
                "SELECT id, label, location, services, created_at FROM ops_backups ORDER BY created_at DESC"
            ).fetchall()
        return [self._backup_row(r) for r in rows]

    def backup_count(self) -> int:
        if self._postgres:
            from raphael_contracts import db as rdb

            row = rdb.pg_fetchone("SELECT COUNT(*) AS n FROM ops_backups")
            return int(row["n"]) if row else 0
        row = self._conn.execute("SELECT COUNT(*) FROM ops_backups").fetchone()
        return int(row[0]) if row else 0

    def was_replayed(self, event_id: str) -> bool:
        if self._postgres:
            from raphael_contracts import db as rdb

            row = rdb.pg_fetchone("SELECT 1 FROM ops_replay_log WHERE event_id = %s", (event_id,))
        else:
            row = self._conn.execute(
                "SELECT 1 FROM ops_replay_log WHERE event_id = ?", (event_id,)
            ).fetchone()
        return row is not None

    def mark_replayed(self, event_id: str) -> None:
        now = self._now()
        if self._postgres:
            from raphael_contracts import db as rdb

            rdb.pg_execute(
                "INSERT INTO ops_replay_log (event_id, replayed_at) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (event_id, now),
            )
        else:
            self._conn.execute(
                "INSERT OR IGNORE INTO ops_replay_log (event_id, replayed_at) VALUES (?, ?)",
                (event_id, now),
            )
            self._conn.commit()

    @staticmethod
    def _backup_row(row: Any) -> dict[str, Any]:
        if isinstance(row, dict):
            services = row.get("services")
            if isinstance(services, str):
                services = json.loads(services or "[]")
            return {
                "id": row["id"],
                "label": row["label"],
                "location": row["location"],
                "services": services or [],
                "created_at": str(row.get("created_at") or ""),
            }
        services = json.loads(row[3] or "[]")
        return {
            "id": row[0],
            "label": row[1],
            "location": row[2],
            "services": services,
            "created_at": row[4],
        }
