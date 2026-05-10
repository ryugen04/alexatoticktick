from __future__ import annotations

from typing import Any

from aiohttp import ClientSession

from alexa_ticktick_bridge.auth.secret_store import SecretStore
from alexa_ticktick_bridge.errors import AuthFailed, RateLimited, RemoteServiceError
from alexa_ticktick_bridge.models import TickTickTask

API_BASE = "https://api.ticktick.com/open/v1"


class TickTickClient:
    def __init__(
        self,
        session: ClientSession,
        secret_store: SecretStore,
        *,
        api_base: str = API_BASE,
    ) -> None:
        self.session = session
        self.secret_store = secret_store
        self.api_base = api_base.rstrip("/")

    def _access_token(self) -> str:
        token_response = self.secret_store.get_json("ticktick.token_response")
        token = token_response.get("access_token") if token_response else None
        if not isinstance(token, str) or not token:
            raise AuthFailed("TickTick access token is missing")
        return token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> Any:
        headers = {"Authorization": f"Bearer {self._access_token()}"}
        url = f"{self.api_base}{path}"
        async with self.session.request(method, url, headers=headers, json=json) as response:
            if response.status == 401:
                raise AuthFailed("TickTick token is unauthorized")
            if response.status == 429:
                raise RateLimited("TickTick rate limited")
            if response.status < 200 or response.status >= 300:
                raise RemoteServiceError(f"TickTick API error: status={response.status}")
            if response.status == 204:
                return None
            return await response.json()

    async def create_task(self, *, title: str, project_id: str | None) -> TickTickTask:
        payload: dict[str, Any] = {"title": title}
        if project_id:
            payload["projectId"] = project_id
        data = await self._request("POST", "/task", json=payload)
        if not isinstance(data, dict):
            raise RemoteServiceError("TickTick create task response was not an object")
        task_id = data.get("id")
        if not isinstance(task_id, str):
            raise RemoteServiceError("TickTick create task response omitted id")
        project = data.get("projectId")
        return TickTickTask(
            task_id=task_id,
            project_id=project if isinstance(project, str) else None,
            title=title,
            raw=data,
        )
