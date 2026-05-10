from __future__ import annotations

from http import HTTPMethod
from typing import Any, Protocol

from aiohttp import ClientSession

from alexa_ticktick_bridge.auth.secret_store import SecretStore
from alexa_ticktick_bridge.errors import AuthFailed, ReauthRequired


class AuthenticatedAmazonSession(Protocol):
    domain: str

    async def request_json(
        self,
        method: HTTPMethod,
        url: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


class AmazonAuthProvider(Protocol):
    async def login_interactive(
        self,
        email: str,
        password: str,
        otp: str,
    ) -> AuthenticatedAmazonSession: ...

    async def restore(self) -> AuthenticatedAmazonSession: ...


class AioAmazonDevicesAuthProvider:
    def __init__(
        self,
        client_session: ClientSession,
        secret_store: SecretStore,
        *,
        domain: str = "co.jp",
        store_password: bool = False,
    ) -> None:
        self.client_session = client_session
        self.secret_store = secret_store
        self.domain = domain
        self.store_password = store_password

    async def login_interactive(
        self,
        email: str,
        password: str,
        otp: str,
    ) -> AuthenticatedAmazonSession:
        raise NotImplementedError(
            "Amazon login adapter is scaffolded until aioamazondevices behavior is verified"
        )

    async def restore(self) -> AuthenticatedAmazonSession:
        has_email = self.secret_store.get("amazon.email")
        has_login_data = self.secret_store.get("amazon.login_data")
        if not has_email or not has_login_data:
            raise ReauthRequired("Amazon login data is missing")
        raise AuthFailed("Amazon restore adapter is not implemented yet")
