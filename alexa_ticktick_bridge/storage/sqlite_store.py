from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from alexa_ticktick_bridge.logging import stable_hash
from alexa_ticktick_bridge.models import SyncRecord
from alexa_ticktick_bridge.storage.migrations import SCHEMA


class SQLiteSyncStore:
    def __init__(self, path: Path) -> None:
        self.path = path.expanduser()

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.executescript(SCHEMA)
        return connection

    def has_alexa_item(self, alexa_item_id: str) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM sync_records WHERE alexa_item_id = ?", (alexa_item_id,)
            ).fetchone()
        return row is not None

    def has_item_name(self, item_name: str) -> bool:
        item_hash = stable_hash(item_name)
        with self.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM sync_records WHERE item_name_hash = ?", (item_hash,)
            ).fetchone()
        return row is not None

    def record_created(self, *, alexa_item_id: str, ticktick_task_id: str, item_name: str) -> bool:
        now = datetime.now(UTC).isoformat()
        try:
            with self.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO sync_records(
                        alexa_item_id,
                        ticktick_task_id,
                        item_name_hash,
                        created_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (alexa_item_id, ticktick_task_id, stable_hash(item_name), now),
                )
        except sqlite3.IntegrityError:
            return False
        return True

    def mark_completed(self, alexa_item_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        with self.connect() as connection:
            connection.execute(
                "UPDATE sync_records SET completed_at = ? WHERE alexa_item_id = ?",
                (now, alexa_item_id),
            )

    def get(self, alexa_item_id: str) -> SyncRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM sync_records WHERE alexa_item_id = ?", (alexa_item_id,)
            ).fetchone()
        if row is None:
            return None
        completed_at = None
        if row["completed_at"]:
            completed_at = datetime.fromisoformat(row["completed_at"])
        return SyncRecord(
            alexa_item_id=row["alexa_item_id"],
            ticktick_task_id=row["ticktick_task_id"],
            item_name_hash=row["item_name_hash"],
            created_at=datetime.fromisoformat(row["created_at"]),
            completed_at=completed_at,
        )
