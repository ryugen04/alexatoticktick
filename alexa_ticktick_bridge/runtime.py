from __future__ import annotations

from pathlib import Path

from aiohttp import ClientSession

from alexa_ticktick_bridge.auth.amazon_auth import AioAmazonDevicesAuthProvider
from alexa_ticktick_bridge.auth.secret_store import (
    KeyringSecretStore,
    PlainFileSecretStore,
    SecretStore,
)
from alexa_ticktick_bridge.clients.alexa_lists import AlexaListsClient
from alexa_ticktick_bridge.clients.ticktick import TickTickClient
from alexa_ticktick_bridge.config import AppConfig
from alexa_ticktick_bridge.storage.sqlite_store import SQLiteSyncStore
from alexa_ticktick_bridge.sync.service import SyncService


def create_secret_store(
    *,
    plain_secret_file: Path | None = None,
    allow_plain_secret_file: bool = False,
) -> SecretStore:
    if plain_secret_file is not None:
        return PlainFileSecretStore(
            plain_secret_file,
            allow_plain_secret_file=allow_plain_secret_file,
        )
    return KeyringSecretStore()


async def create_sync_service(
    *,
    session: ClientSession,
    config: AppConfig,
    secret_store: SecretStore,
) -> SyncService:
    amazon_auth = AioAmazonDevicesAuthProvider(
        session,
        secret_store,
        domain=config.amazon.domain,
        store_password=config.amazon.store_password,
    )
    amazon_session = await amazon_auth.restore()
    alexa = AlexaListsClient(amazon_session)
    ticktick = TickTickClient(session, secret_store)
    store = SQLiteSyncStore(config.storage.sqlite_path)
    return SyncService(
        alexa=alexa,
        ticktick=ticktick,
        store=store,
        list_type=config.amazon.list_type,
        project_id=config.ticktick.project_id,
    )
