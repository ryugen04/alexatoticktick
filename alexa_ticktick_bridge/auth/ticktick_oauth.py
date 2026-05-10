from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from aiohttp import BasicAuth, ClientSession

from alexa_ticktick_bridge.auth.secret_store import SecretStore
from alexa_ticktick_bridge.errors import AuthFailed

AUTH_URL = "https://ticktick.com/oauth/authorize"
TOKEN_URL = "https://ticktick.com/oauth/token"


def build_authorization_url(*, client_id: str, redirect_uri: str, scope: str, state: str) -> str:
    query = urlencode(
        {
            "client_id": client_id,
            "scope": scope,
            "state": state,
            "redirect_uri": redirect_uri,
            "response_type": "code",
        }
    )
    return f"{AUTH_URL}?{query}"


async def exchange_code(
    session: ClientSession,
    secret_store: SecretStore,
    *,
    client_id: str,
    redirect_uri: str,
    code: str,
    scope: str = "tasks:read tasks:write",
) -> dict[str, Any]:
    client_secret = secret_store.get("ticktick.client_secret")
    if not client_secret:
        raise AuthFailed("ticktick.client_secret is missing")
    async with session.post(
        TOKEN_URL,
        auth=BasicAuth(client_id, client_secret),
        data={
            "code": code,
            "grant_type": "authorization_code",
            "scope": scope,
            "redirect_uri": redirect_uri,
        },
    ) as response:
        if response.status < 200 or response.status >= 300:
            raise AuthFailed(f"TickTick token exchange failed: status={response.status}")
        payload = await response.json()
    if not isinstance(payload, dict):
        raise AuthFailed("TickTick token response was not a JSON object")
    secret_store.set_json("ticktick.token_response", payload)
    return payload
