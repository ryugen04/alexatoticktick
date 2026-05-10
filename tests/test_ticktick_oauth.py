from __future__ import annotations

from aiohttp import BasicAuth

from alexa_ticktick_bridge.auth.secret_store import PlainFileSecretStore
from alexa_ticktick_bridge.auth.ticktick_oauth import build_authorization_url, exchange_code


class FakeResponse:
    status = 200

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def json(self) -> dict[str, object]:
        return {"access_token": "token-value", "token_type": "bearer"}


class FakeSession:
    def __init__(self) -> None:
        self.auth: BasicAuth | None = None
        self.data: dict[str, str] | None = None

    def post(self, url: str, *, auth: BasicAuth, data: dict[str, str]) -> FakeResponse:
        self.auth = auth
        self.data = data
        return FakeResponse()


def test_build_authorization_url_contains_required_parameters() -> None:
    url = build_authorization_url(
        client_id="client-id",
        redirect_uri="http://127.0.0.1:8765/callback",
        scope="tasks:read tasks:write",
        state="state-value",
    )

    assert "https://ticktick.com/oauth/authorize?" in url
    assert "client_id=client-id" in url
    assert "response_type=code" in url
    assert "state=state-value" in url
    assert "tasks%3Aread+tasks%3Awrite" in url


async def test_exchange_code_uses_basic_auth_and_stores_token(tmp_path) -> None:
    store = PlainFileSecretStore(tmp_path / "secrets.json", allow_plain_secret_file=True)
    store.set("ticktick.client_secret", "secret-value")
    session = FakeSession()

    payload = await exchange_code(
        session,  # type: ignore[arg-type]
        store,
        client_id="client-id",
        redirect_uri="http://127.0.0.1:8765/callback",
        code="code-value",
    )

    assert payload["access_token"] == "token-value"
    assert session.auth == BasicAuth("client-id", "secret-value")
    assert session.data is not None
    assert session.data["grant_type"] == "authorization_code"
    assert "client_secret" not in session.data
    assert store.get_json("ticktick.token_response") == payload
