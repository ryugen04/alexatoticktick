from __future__ import annotations

from aiohttp import ClientSession

from alexa_ticktick_bridge.auth.secret_store import SecretStore
from alexa_ticktick_bridge.errors import NotConfigured, RemoteServiceError


class SlackNotifier:
    def __init__(self, session: ClientSession, secret_store: SecretStore) -> None:
        self.session = session
        self.secret_store = secret_store

    async def post(self, text: str) -> None:
        webhook_url = self.secret_store.get("slack.webhook_url")
        if not webhook_url:
            raise NotConfigured("slack.webhook_url is missing")
        async with self.session.post(webhook_url, json={"text": text}) as response:
            if response.status < 200 or response.status >= 300:
                raise RemoteServiceError(f"Slack webhook failed: status={response.status}")
