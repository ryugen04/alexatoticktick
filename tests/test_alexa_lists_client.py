from __future__ import annotations

from http import HTTPMethod
from typing import Any

import pytest

from alexa_ticktick_bridge.clients.alexa_lists import AlexaListsClient
from alexa_ticktick_bridge.errors import RemoteServiceError
from alexa_ticktick_bridge.models import AlexaItemStatus


class FakeAmazonSession:
    domain = "co.jp"

    def __init__(self) -> None:
        self.calls: list[tuple[HTTPMethod, str, dict[str, Any] | None]] = []

    async def request_json(
        self,
        method: HTTPMethod,
        url: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.calls.append((method, url, payload))
        if url.endswith("/lists/fetch"):
            return {
                "listInfoList": [
                    {"listId": "shopping-list-id", "listType": "SHOP", "listName": ""},
                    {"listId": "todo-list-id", "listType": "TODO", "listName": ""},
                ]
            }
        if "items/fetch" in url:
            return {
                "itemInfoList": [
                    {
                        "itemId": "item-1",
                        "itemName": "milk",
                        "itemStatus": "ACTIVE",
                        "version": 3,
                    },
                    {
                        "itemId": "item-2",
                        "itemName": "bread",
                        "itemStatus": "COMPLETE",
                        "version": 4,
                    },
                ]
            }
        return {}


async def test_list_items_detects_shop_list_and_fetches_items() -> None:
    session = FakeAmazonSession()
    client = AlexaListsClient(session)

    items = await client.list_items()

    assert [item.item_id for item in items] == ["item-1", "item-2"]
    assert items[0].list_id == "shopping-list-id"
    assert items[0].status == AlexaItemStatus.ACTIVE
    assert session.calls[0][1].endswith("/alexashoppinglists/api/v2/lists/fetch")
    assert "shopping-list-id/items/fetch?limit=100" in session.calls[1][1]


async def test_complete_item_sends_status_update_with_version() -> None:
    session = FakeAmazonSession()
    client = AlexaListsClient(session)
    item = (await client.list_items())[0]

    await client.complete_item(item)

    method, url, payload = session.calls[-1]
    assert method == HTTPMethod.PUT
    assert "shopping-list-id/items/item-1?version=3" in url
    assert payload == {
        "itemAttributesToUpdate": [{"type": "itemStatus", "value": "COMPLETE"}],
        "itemAttributesToRemove": [],
    }


async def test_complete_item_requires_list_id() -> None:
    client = AlexaListsClient(FakeAmazonSession())
    item = (await client.list_items())[0].model_copy(update={"list_id": None})

    with pytest.raises(RemoteServiceError):
        await client.complete_item(item)
