from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from alexa_ticktick_bridge.config import AppConfig, default_config_text
from alexa_ticktick_bridge.constants import DEFAULT_CONFIG_PATH
from alexa_ticktick_bridge.errors import BridgeError

app = typer.Typer(help="Alexa Shopping List to TickTick bridge")
config_app = typer.Typer(help="Configuration commands")
auth_app = typer.Typer(help="Authentication commands")
sync_app = typer.Typer(help="Synchronization commands")
app.add_typer(config_app, name="config")
app.add_typer(auth_app, name="auth")
app.add_typer(sync_app, name="sync")
console = Console()
DEFAULT_CONFIG_FILE = Path(DEFAULT_CONFIG_PATH).expanduser()


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
def auth_amazon() -> None:
    console.print("Amazon auth adapter is scaffolded but not implemented in this MVP foundation.")
    raise typer.Exit(1)


@auth_app.command("ticktick")
def auth_ticktick(
    config: Annotated[Path, typer.Option("--config")] = DEFAULT_CONFIG_FILE,
) -> None:
    from alexa_ticktick_bridge.auth.ticktick_oauth import build_authorization_url

    app_config = AppConfig.load(config)
    url = build_authorization_url(
        client_id=app_config.ticktick.client_id,
        redirect_uri=app_config.ticktick.redirect_uri,
        scope=app_config.ticktick.scope,
        state="manual-local-auth",
    )
    console.print(url)


@sync_app.command("once")
def sync_once(
    config: Annotated[Path, typer.Option("--config")] = DEFAULT_CONFIG_FILE,
) -> None:
    try:
        AppConfig.load(config)
    except BridgeError as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print("sync once requires configured Amazon and TickTick adapters.")
    raise typer.Exit(1)


@sync_app.command("daemon")
def sync_daemon(
    config: Annotated[Path, typer.Option("--config")] = DEFAULT_CONFIG_FILE,
) -> None:
    try:
        AppConfig.load(config)
    except BridgeError as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print("sync daemon requires configured Amazon and TickTick adapters.")
    raise typer.Exit(1)
