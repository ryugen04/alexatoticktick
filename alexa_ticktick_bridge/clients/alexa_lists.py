from __future__ import annotations

from http import HTTPMethod
from typing import Any

from alexa_ticktick_bridge.auth.amazon_auth import AuthenticatedAmazonSession
from alexa_ticktick_bridge.errors import RemoteServiceError
from alexa_ticktick_bridge.models import AlexaItemStatus, AlexaListItem


class AlexaListsClient:
    def __init__(self, session: AuthenticatedAmazonSession) -> None:
        self.session = session

    async def list_items(self, *, list_type: str = "SHOP") -> list[AlexaListItem]:
        data = await self.session.request_json(
            HTTPMethod.POST,
            f"https://alexa.amazon.{self.session.domain}/api/namedLists/{list_type}/items",
            payload={},
        )
        raw_items = data.get("items", [])
        if not isinstance(raw_items, list):
            raise RemoteServiceError("Alexa list response items was not a list")
        items: list[AlexaListItem] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            item_id = raw.get("id") or raw.get("itemId")
            text = raw.get("text") or raw.get("value")
            if isinstance(item_id, str) and isinstance(text, str):
                items.append(
                    AlexaListItem(
                        item_id=item_id,
                        version=raw.get("version") if isinstance(raw.get("version"), int) else None,
                        text=text,
                        status=AlexaItemStatus(raw.get("status", "ACTIVE")),
                        raw=raw,
                    )
                )
        return items

    async def complete_item(self, item: AlexaListItem) -> None:
        payload: dict[str, Any] = {"status": AlexaItemStatus.COMPLETE.value}
        if item.version is not None:
            payload["version"] = item.version
        await self.session.request_json(
            HTTPMethod.PUT,
            f"https://alexa.amazon.{self.session.domain}/api/namedLists/items/{item.item_id}",
            payload=payload,
        )
