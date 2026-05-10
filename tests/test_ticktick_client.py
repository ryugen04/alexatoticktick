from __future__ import annotations

from typing import Any

import pytest

from alexa_ticktick_bridge.auth.secret_store import PlainFileSecretStore
from alexa_ticktick_bridge.clients.ticktick import TickTickClient
from alexa_ticktick_bridge.errors import RemoteServiceError


class FakeResponse:
    def __init__(self, *, status: int = 200, payload: Any = None) -> None:
        self.status = status
        self.payload = payload

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def json(self) -> Any:
        return self.payload


class FakeSession:
    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.calls: list[tuple[str, str]] = []

    def request(self, method: str, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append((method, url))
        return FakeResponse(payload=self.payload)


def make_store(tmp_path) -> PlainFileSecretStore:
    store = PlainFileSecretStore(tmp_path / "secrets.json", allow_plain_secret_file=True)
    store.set_json("ticktick.token_response", {"access_token": "token"})
    return store


async def test_find_open_task_by_title_returns_matching_open_task(tmp_path) -> None:
    session = FakeSession(
        {
            "tasks": [
                {"id": "done", "title": "milk", "projectId": "p1", "status": 2},
                {"id": "open", "title": "milk", "projectId": "p1", "status": 0},
            ]
        }
    )
    client = TickTickClient(session, make_store(tmp_path), api_base="https://example.test")  # type: ignore[arg-type]

    task = await client.find_open_task_by_title(title="milk", project_id="p1")

    assert task is not None
    assert task.task_id == "open"
    assert session.calls == [("GET", "https://example.test/project/p1/data")]


async def test_find_open_task_by_title_ignores_completed_time(tmp_path) -> None:
    session = FakeSession(
        {
            "tasks": [
                {
                    "id": "done",
                    "title": "milk",
                    "projectId": "p1",
                    "status": 0,
                    "completedTime": "2026-05-10T00:00:00+0000",
                }
            ]
        }
    )
    client = TickTickClient(session, make_store(tmp_path), api_base="https://example.test")  # type: ignore[arg-type]

    task = await client.find_open_task_by_title(title="milk", project_id="p1")

    assert task is None


async def test_find_open_task_by_title_requires_tasks_list(tmp_path) -> None:
    client = TickTickClient(
        FakeSession({"tasks": {}}),  # type: ignore[arg-type]
        make_store(tmp_path),
        api_base="https://example.test",
    )

    with pytest.raises(RemoteServiceError):
        await client.find_open_task_by_title(title="milk", project_id="p1")
