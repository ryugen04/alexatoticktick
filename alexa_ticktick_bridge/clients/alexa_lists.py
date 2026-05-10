from __future__ import annotations

from http import HTTPMethod
from typing import Any

from alexa_ticktick_bridge.auth.amazon_auth import AuthenticatedAmazonSession
from alexa_ticktick_bridge.errors import RemoteServiceError
from alexa_ticktick_bridge.models import AlexaItemStatus, AlexaList, AlexaListItem, AlexaListType


class AlexaListsClient:
    def __init__(self, session: AuthenticatedAmazonSession) -> None:
        self.session = session
        self.base_url = f"https://www.amazon.{session.domain}"

    async def get_lists(self) -> list[AlexaList]:
        data = await self.session.request_json(
            HTTPMethod.POST,
            f"{self.base_url}/alexashoppinglists/api/v2/lists/fetch",
            payload={},
        )
        raw_lists = data.get("listInfoList", [])
        if not isinstance(raw_lists, list):
            raise RemoteServiceError("Alexa list response listInfoList was not a list")
        return [AlexaList.model_validate(raw) for raw in raw_lists if isinstance(raw, dict)]

    async def get_shop_list(self) -> AlexaList:
        for alexa_list in await self.get_lists():
            if alexa_list.list_type == AlexaListType.SHOP:
                return alexa_list
        raise RemoteServiceError("Alexa SHOP list not found")

    async def get_items(self, list_id: str) -> list[AlexaListItem]:
        data = await self.session.request_json(
            HTTPMethod.POST,
            f"{self.base_url}/alexashoppinglists/api/v2/lists/{list_id}/items/fetch?limit=100",
            payload={},
        )
        raw_items = data.get("itemInfoList", [])
        if not isinstance(raw_items, list):
            raise RemoteServiceError("Alexa items response itemInfoList was not a list")
        items: list[AlexaListItem] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            item_id = raw.get("itemId")
            text = raw.get("itemName")
            version = raw.get("version")
            if isinstance(item_id, str) and isinstance(text, str) and isinstance(version, int):
                items.append(
                    AlexaListItem(
                        item_id=item_id,
                        list_id=list_id,
                        text=text,
                        version=version,
                        status=AlexaItemStatus(raw.get("itemStatus", "ACTIVE")),
                        raw=raw,
                    )
                )
        return items

    async def list_items(self, *, list_type: str = "SHOP") -> list[AlexaListItem]:
        if list_type != AlexaListType.SHOP.value:
            raise RemoteServiceError(f"Unsupported Alexa list_type for MVP: {list_type}")
        shop_list = await self.get_shop_list()
        return await self.get_items(shop_list.list_id)

    async def complete_item(self, item: AlexaListItem) -> None:
        if not item.list_id:
            raise RemoteServiceError("Alexa item is missing list_id")
        payload: dict[str, Any] = {
            "itemAttributesToUpdate": [
                {
                    "type": "itemStatus",
                    "value": AlexaItemStatus.COMPLETE.value,
                }
            ],
            "itemAttributesToRemove": [],
        }
        await self.session.request_json(
            HTTPMethod.PUT,
            f"{self.base_url}/alexashoppinglists/api/v2/lists/"
            f"{item.list_id}/items/{item.item_id}?version={item.version}",
            payload=payload,
        )
