from __future__ import annotations

from urllib.parse import urlencode

from aiohttp import ClientSession

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
) -> dict[str, object]:
    client_secret = secret_store.get("ticktick.client_secret")
    if not client_secret:
        raise AuthFailed("ticktick.client_secret is missing")
    async with session.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
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
