from __future__ import annotations

from http import HTTPMethod, HTTPStatus
from typing import Any, Protocol

from aioamazondevices import CannotAuthenticate, CannotConnect
from aioamazondevices.api import AmazonEchoApi
from aioamazondevices.exceptions import AmazonError, CannotRegisterDevice, CannotRetrieveData
from aiohttp import ClientSession

from alexa_ticktick_bridge.auth.secret_store import SecretStore
from alexa_ticktick_bridge.errors import AuthFailed, RateLimited, ReauthRequired, RemoteServiceError


class AuthenticatedAmazonSession(Protocol):
    @property
    def domain(self) -> str: ...

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


class AioAmazonDevicesSession:
    def __init__(self, amazon_api: AmazonEchoApi) -> None:
        self.amazon_api = amazon_api

    @property
    def domain(self) -> str:
        return self.amazon_api.domain

    async def request_json(
        self,
        method: HTTPMethod,
        url: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            http_wrapper = self.amazon_api._http_wrapper  # noqa: SLF001
            _, response = await http_wrapper.session_request(
                method=method,
                url=url,
                input_data=payload or {},
                json_data=True,
            )
            if response.status == HTTPStatus.TOO_MANY_REQUESTS:
                raise RateLimited("Amazon API rate limited")
            return await http_wrapper.response_to_json(response)
        except CannotAuthenticate as exc:
            raise ReauthRequired("Amazon session expired or unauthorized") from exc
        except CannotConnect as exc:
            raise RemoteServiceError("Amazon API connection failed") from exc
        except CannotRetrieveData as exc:
            raise RemoteServiceError("Amazon API request failed") from exc


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
    ) -> AioAmazonDevicesSession:
        amazon_api = AmazonEchoApi(
            client_session=self.client_session,
            login_email=email,
            login_password=password,
        )
        amazon_api._session_state_data.country_specific_data(  # noqa: SLF001
            f"https://www.amazon.{self.domain}"
        )
        try:
            login_data = await amazon_api.login.login_mode_interactive(otp)
        except (CannotAuthenticate, CannotConnect, CannotRegisterDevice, AmazonError) as exc:
            raise AuthFailed("Amazon interactive login failed") from exc

        self.secret_store.set("amazon.email", email)
        self.secret_store.set_json("amazon.login_data", login_data)
        if self.store_password:
            self.secret_store.set("amazon.password", password)
        return AioAmazonDevicesSession(amazon_api)

    async def restore(self) -> AioAmazonDevicesSession:
        email = self.secret_store.get("amazon.email")
        login_data = self.secret_store.get_json("amazon.login_data")
        if not email or not login_data:
            raise ReauthRequired("Amazon login data is missing")
        password = self.secret_store.get("amazon.password") or ""
        amazon_api = AmazonEchoApi(
            client_session=self.client_session,
            login_email=email,
            login_password=password,
            login_data=login_data,
        )
        try:
            refreshed_login_data = await amazon_api.login.login_mode_stored_data()
        except CannotAuthenticate as exc:
            raise ReauthRequired("Amazon stored login data is invalid") from exc
        except (CannotConnect, CannotRegisterDevice, CannotRetrieveData, AmazonError) as exc:
            raise AuthFailed("Amazon stored login failed") from exc
        self.secret_store.set_json("amazon.login_data", refreshed_login_data)
        return AioAmazonDevicesSession(amazon_api)
