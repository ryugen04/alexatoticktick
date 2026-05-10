from alexa_ticktick_bridge.storage.sqlite_store import SQLiteSyncStore


def test_store_prevents_duplicate_alexa_item(tmp_path) -> None:
    store = SQLiteSyncStore(tmp_path / "state.db")

    assert store.record_created(alexa_item_id="a1", ticktick_task_id="t1", item_name="milk")
    assert not store.record_created(alexa_item_id="a1", ticktick_task_id="t2", item_name="eggs")
    assert store.has_alexa_item("a1")


def test_store_allows_duplicate_item_name_for_new_alexa_item(tmp_path) -> None:
    store = SQLiteSyncStore(tmp_path / "state.db")

    assert store.record_created(alexa_item_id="a1", ticktick_task_id="t1", item_name="milk")
    assert store.record_created(alexa_item_id="a2", ticktick_task_id="t2", item_name="milk")
    assert store.has_item_name("milk")


def test_mark_completed(tmp_path) -> None:
    store = SQLiteSyncStore(tmp_path / "state.db")
    store.record_created(alexa_item_id="a1", ticktick_task_id="t1", item_name="milk")

    store.mark_completed("a1")

    record = store.get("a1")
    assert record is not None
    assert record.completed_at is not None
