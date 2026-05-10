from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AlexaItemStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETE = "COMPLETE"


class AlexaListItem(BaseModel):
    item_id: str
    version: int | None = None
    text: str
    status: AlexaItemStatus = AlexaItemStatus.ACTIVE
    raw: dict[str, Any] = Field(default_factory=dict)


class TickTickTask(BaseModel):
    task_id: str
    project_id: str | None = None
    title: str
    raw: dict[str, Any] = Field(default_factory=dict)


class SyncRecord(BaseModel):
    alexa_item_id: str
    ticktick_task_id: str
    item_name_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class SyncResult(BaseModel):
    scanned: int = 0
    created: int = 0
    skipped: int = 0
    completed: int = 0
    failures: int = 0
