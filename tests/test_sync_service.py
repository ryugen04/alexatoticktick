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
    def __init__(self, *, open_tasks: list[TickTickTask] | None = None) -> None:
        self.open_tasks = open_tasks or []
        self.created_titles: list[str] = []

    async def create_task(self, *, title: str, project_id: str | None) -> TickTickTask:
        self.created_titles.append(title)
        return TickTickTask(task_id=f"task-{title}", project_id=project_id, title=title)

    async def find_open_task_by_title(
        self,
        *,
        title: str,
        project_id: str | None,
    ) -> TickTickTask | None:
        for task in self.open_tasks:
            if task.title == title and task.project_id == project_id:
                return task
        return None


class FakeNotifier:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.messages: list[str] = []

    async def post(self, text: str) -> None:
        self.messages.append(text)
        if self.fail:
            raise RuntimeError("slack failed")


async def test_sync_creates_task_then_completes_alexa_item(tmp_path) -> None:
    alexa = FakeAlexa()
    store = SQLiteSyncStore(tmp_path / "state.db")
    service = SyncService(alexa=alexa, ticktick=FakeTickTick(), store=store, project_id="p1")

    result = await service.sync_once()

    assert result.scanned == 2
    assert result.created == 1
    assert result.completed == 1
    assert result.skipped == 1
    assert result.notified == 0
    assert result.notification_failures == 0
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


async def test_sync_posts_slack_notification_after_task_create(tmp_path) -> None:
    alexa = FakeAlexa()
    notifier = FakeNotifier()
    store = SQLiteSyncStore(tmp_path / "state.db")
    service = SyncService(
        alexa=alexa,
        ticktick=FakeTickTick(),
        store=store,
        notifier=notifier,
    )

    result = await service.sync_once()

    assert result.notified == 1
    assert result.notification_failures == 0
    assert notifier.messages == [":shopping_trolley: milk"]
    assert alexa.completed == ["a1"]


async def test_sync_redacts_slack_item_name_when_configured(tmp_path) -> None:
    notifier = FakeNotifier()
    service = SyncService(
        alexa=FakeAlexa(),
        ticktick=FakeTickTick(),
        store=SQLiteSyncStore(tmp_path / "state.db"),
        notifier=notifier,
        redact_notification_item_name=True,
    )

    result = await service.sync_once()

    assert result.notified == 1
    assert "milk" not in notifier.messages[0]
    assert "<redacted>" in notifier.messages[0]


async def test_sync_continues_when_slack_notification_fails(tmp_path) -> None:
    alexa = FakeAlexa()
    notifier = FakeNotifier(fail=True)
    service = SyncService(
        alexa=alexa,
        ticktick=FakeTickTick(),
        store=SQLiteSyncStore(tmp_path / "state.db"),
        notifier=notifier,
    )

    result = await service.sync_once()

    assert result.created == 1
    assert result.notified == 0
    assert result.notification_failures == 1
    assert result.completed == 1
    assert result.failures == 0
    assert alexa.completed == ["a1"]


async def test_same_name_can_sync_again_when_no_open_ticktick_task(tmp_path) -> None:
    alexa = FakeAlexa()
    store = SQLiteSyncStore(tmp_path / "state.db")
    store.record_created(
        alexa_item_id="old-alexa-id",
        ticktick_task_id="old-task-milk",
        item_name="milk",
    )
    store.mark_completed("old-alexa-id")
    ticktick = FakeTickTick()
    service = SyncService(alexa=alexa, ticktick=ticktick, store=store)

    result = await service.sync_once()

    assert result.created == 1
    assert result.completed == 1
    assert ticktick.created_titles == ["milk"]
    assert alexa.completed == ["a1"]


async def test_open_ticktick_duplicate_completes_alexa_without_creating_task(tmp_path) -> None:
    alexa = FakeAlexa()
    ticktick = FakeTickTick(
        open_tasks=[TickTickTask(task_id="existing-task", project_id="p1", title="milk")]
    )
    store = SQLiteSyncStore(tmp_path / "state.db")
    service = SyncService(alexa=alexa, ticktick=ticktick, store=store, project_id="p1")

    result = await service.sync_once()

    assert result.created == 0
    assert result.completed == 1
    assert result.failures == 0
    assert ticktick.created_titles == []
    assert alexa.completed == ["a1"]
    record = store.get("a1")
    assert record is not None
    assert record.ticktick_task_id == "existing-task"
