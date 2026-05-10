from __future__ import annotations

from typing import Protocol

from alexa_ticktick_bridge.models import AlexaItemStatus, AlexaListItem, SyncResult, TickTickTask
from alexa_ticktick_bridge.storage.sqlite_store import SQLiteSyncStore


class AlexaListsPort(Protocol):
    async def list_items(self, *, list_type: str = "SHOP") -> list[AlexaListItem]: ...

    async def complete_item(self, item: AlexaListItem) -> None: ...


class TickTickPort(Protocol):
    async def create_task(self, *, title: str, project_id: str | None) -> TickTickTask: ...


class NotifierPort(Protocol):
    async def post(self, text: str) -> None: ...


class SyncService:
    def __init__(
        self,
        *,
        alexa: AlexaListsPort,
        ticktick: TickTickPort,
        store: SQLiteSyncStore,
        notifier: NotifierPort | None = None,
        redact_notification_item_name: bool = False,
        list_type: str = "SHOP",
        project_id: str | None = None,
    ) -> None:
        self.alexa = alexa
        self.ticktick = ticktick
        self.store = store
        self.notifier = notifier
        self.redact_notification_item_name = redact_notification_item_name
        self.list_type = list_type
        self.project_id = project_id

    def _notification_text(self, item: AlexaListItem, task: TickTickTask) -> str:
        item_name = "<redacted>" if self.redact_notification_item_name else item.text
        return f":shopping_trolley: {item_name}"

    async def _notify(self, item: AlexaListItem, task: TickTickTask, result: SyncResult) -> None:
        if self.notifier is None:
            return
        try:
            await self.notifier.post(self._notification_text(item, task))
            result.notified += 1
        except Exception:
            result.notification_failures += 1

    async def sync_once(self) -> SyncResult:
        result = SyncResult()
        items = await self.alexa.list_items(list_type=self.list_type)
        result.scanned = len(items)
        for item in items:
            if item.status != AlexaItemStatus.ACTIVE:
                result.skipped += 1
                continue
            if self.store.has_alexa_item(item.item_id) or self.store.has_item_name(item.text):
                result.skipped += 1
                continue
            try:
                task = await self.ticktick.create_task(title=item.text, project_id=self.project_id)
                inserted = self.store.record_created(
                    alexa_item_id=item.item_id,
                    ticktick_task_id=task.task_id,
                    item_name=item.text,
                )
                if not inserted:
                    result.skipped += 1
                    continue
                result.created += 1
                await self._notify(item, task, result)
                await self.alexa.complete_item(item)
                self.store.mark_completed(item.item_id)
                result.completed += 1
            except Exception:
                result.failures += 1
        return result
