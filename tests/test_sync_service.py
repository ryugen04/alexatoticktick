from alexa_ticktick_bridge.models import AlexaItemStatus, AlexaListItem, TickTickTask
from alexa_ticktick_bridge.storage.sqlite_store import SQLiteSyncStore
from alexa_ticktick_bridge.sync.service import SyncService


class FakeAlexa:
    def __init__(self) -> None:
        self.completed: list[str] = []

    async def list_items(self, *, list_type: str = "SHOP") -> list[AlexaListItem]:
        return [
            AlexaListItem(item_id="a1", text="milk"),
            AlexaListItem(item_id="a2", text="done", status=AlexaItemStatus.COMPLETE),
        ]

    async def complete_item(self, item: AlexaListItem) -> None:
        self.completed.append(item.item_id)


class FakeTickTick:
    async def create_task(self, *, title: str, project_id: str | None) -> TickTickTask:
        return TickTickTask(task_id=f"task-{title}", project_id=project_id, title=title)


async def test_sync_creates_task_then_completes_alexa_item(tmp_path) -> None:
    alexa = FakeAlexa()
    store = SQLiteSyncStore(tmp_path / "state.db")
    service = SyncService(alexa=alexa, ticktick=FakeTickTick(), store=store, project_id="p1")

    result = await service.sync_once()

    assert result.scanned == 2
    assert result.created == 1
    assert result.completed == 1
    assert result.skipped == 1
    assert alexa.completed == ["a1"]
    record = store.get("a1")
    assert record is not None
    assert record.ticktick_task_id == "task-milk"


async def test_sync_is_idempotent(tmp_path) -> None:
    alexa = FakeAlexa()
    store = SQLiteSyncStore(tmp_path / "state.db")
    service = SyncService(alexa=alexa, ticktick=FakeTickTick(), store=store)

    await service.sync_once()
    second = await service.sync_once()

    assert second.created == 0
    assert second.skipped == 2
