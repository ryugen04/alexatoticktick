from __future__ import annotations

import asyncio
import secrets
from pathlib import Path
from typing import Annotated

import typer
from aiohttp import ClientSession
from rich.console import Console

from alexa_ticktick_bridge.auth.amazon_auth import AioAmazonDevicesAuthProvider
from alexa_ticktick_bridge.auth.ticktick_oauth import build_authorization_url, exchange_code
from alexa_ticktick_bridge.config import AppConfig, default_config_text
from alexa_ticktick_bridge.constants import DEFAULT_CONFIG_PATH
from alexa_ticktick_bridge.errors import BridgeError
from alexa_ticktick_bridge.runtime import create_secret_store, create_sync_service
from alexa_ticktick_bridge.sync.scheduler import run_forever

app = typer.Typer(help="Alexa Shopping List to TickTick bridge")
config_app = typer.Typer(help="Configuration commands")
auth_app = typer.Typer(help="Authentication commands")
sync_app = typer.Typer(help="Synchronization commands")
app.add_typer(config_app, name="config")
app.add_typer(auth_app, name="auth")
app.add_typer(sync_app, name="sync")
console = Console()
DEFAULT_CONFIG_FILE = Path(DEFAULT_CONFIG_PATH).expanduser()

ConfigOption = Annotated[Path, typer.Option("--config")]
PlainSecretFileOption = Annotated[Path | None, typer.Option("--plain-secret-file")]
AllowPlainSecretFileOption = Annotated[bool, typer.Option("--allow-plain-secret-file")]


@config_app.command("init")
def config_init(
    path: Annotated[Path, typer.Option("--path")] = DEFAULT_CONFIG_FILE,
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    if path.exists() and not force:
        raise typer.BadParameter(f"config already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(default_config_text(), encoding="utf-8")
    console.print(str(path))


@auth_app.command("amazon")
def auth_amazon(
    config: ConfigOption = DEFAULT_CONFIG_FILE,
    email: Annotated[str | None, typer.Option("--email")] = None,
    password: Annotated[str | None, typer.Option("--password", hide_input=True)] = None,
    otp: Annotated[str | None, typer.Option("--otp", hide_input=True)] = None,
    plain_secret_file: PlainSecretFileOption = None,
    allow_plain_secret_file: AllowPlainSecretFileOption = False,
) -> None:
    app_config = AppConfig.load(config)
    secret_store = create_secret_store(
        plain_secret_file=plain_secret_file,
        allow_plain_secret_file=allow_plain_secret_file,
    )
    login_email = email or typer.prompt("Amazon email")
    login_password = password or typer.prompt("Amazon password", hide_input=True)
    login_otp = otp or typer.prompt("Current Amazon OTP", hide_input=True)

    async def _run() -> None:
        async with ClientSession() as session:
            provider = AioAmazonDevicesAuthProvider(
                session,
                secret_store,
                domain=app_config.amazon.domain,
                store_password=app_config.amazon.store_password,
            )
            amazon_session = await provider.login_interactive(
                login_email,
                login_password,
                login_otp,
            )
            console.print(f"Amazon login saved for amazon.{amazon_session.domain}")

    asyncio.run(_run())


@auth_app.command("ticktick")
def auth_ticktick(
    config: ConfigOption = DEFAULT_CONFIG_FILE,
    client_secret: Annotated[str | None, typer.Option("--client-secret", hide_input=True)] = None,
    code: Annotated[str | None, typer.Option("--code")] = None,
    state: Annotated[str | None, typer.Option("--state")] = None,
    plain_secret_file: PlainSecretFileOption = None,
    allow_plain_secret_file: AllowPlainSecretFileOption = False,
) -> None:
    app_config = AppConfig.load(config)
    secret_store = create_secret_store(
        plain_secret_file=plain_secret_file,
        allow_plain_secret_file=allow_plain_secret_file,
    )
    if client_secret:
        secret_store.set("ticktick.client_secret", client_secret)
    oauth_state = state or secrets.token_urlsafe(24)
    url = build_authorization_url(
        client_id=app_config.ticktick.client_id,
        redirect_uri=app_config.ticktick.redirect_uri,
        scope=app_config.ticktick.scope,
        state=oauth_state,
    )
    if not code:
        console.print(url)
        console.print("Run again with --code after approving the authorization URL.")
        console.print(f"Expected state: {oauth_state}")
        return

    async def _run() -> None:
        async with ClientSession() as session:
            await exchange_code(
                session,
                secret_store,
                client_id=app_config.ticktick.client_id,
                redirect_uri=app_config.ticktick.redirect_uri,
                code=code,
                scope=app_config.ticktick.scope,
            )
            console.print("TickTick token saved")

    asyncio.run(_run())


@sync_app.command("once")
def sync_once(
    config: ConfigOption = DEFAULT_CONFIG_FILE,
    plain_secret_file: PlainSecretFileOption = None,
    allow_plain_secret_file: AllowPlainSecretFileOption = False,
) -> None:
    try:
        app_config = AppConfig.load(config)
        secret_store = create_secret_store(
            plain_secret_file=plain_secret_file,
            allow_plain_secret_file=allow_plain_secret_file,
        )
    except BridgeError as exc:
        raise typer.BadParameter(str(exc)) from exc

    async def _run() -> None:
        async with ClientSession() as session:
            service = await create_sync_service(
                session=session,
                config=app_config,
                secret_store=secret_store,
            )
            result = await service.sync_once()
            console.print(result.model_dump())

    asyncio.run(_run())


@sync_app.command("daemon")
def sync_daemon(
    config: ConfigOption = DEFAULT_CONFIG_FILE,
    plain_secret_file: PlainSecretFileOption = None,
    allow_plain_secret_file: AllowPlainSecretFileOption = False,
) -> None:
    try:
        app_config = AppConfig.load(config)
        secret_store = create_secret_store(
            plain_secret_file=plain_secret_file,
            allow_plain_secret_file=allow_plain_secret_file,
        )
    except BridgeError as exc:
        raise typer.BadParameter(str(exc)) from exc

    async def _run() -> None:
        async with ClientSession() as session:
            service = await create_sync_service(
                session=session,
                config=app_config,
                secret_store=secret_store,
            )
            await run_forever(
                service,
                interval_seconds=app_config.poll.interval_seconds,
                jitter_seconds=app_config.poll.jitter_seconds,
                max_backoff_seconds=app_config.poll.max_backoff_seconds,
            )

    asyncio.run(_run())
