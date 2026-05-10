from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field, field_validator

from alexa_ticktick_bridge.constants import DEFAULT_CONFIG_PATH, DEFAULT_SQLITE_PATH
from alexa_ticktick_bridge.errors import ConfigError


class PollConfig(BaseModel):
    interval_seconds: int = Field(default=180)
    jitter_seconds: int = Field(default=15)
    max_backoff_seconds: int = Field(default=1800)

    @field_validator("interval_seconds")
    @classmethod
    def validate_interval(cls, value: int) -> int:
        if not 60 <= value <= 180:
            raise ValueError("poll.interval_seconds must be between 60 and 180")
        return value


class AmazonConfig(BaseModel):
    domain: str = "co.jp"
    list_type: str = "SHOP"
    store_password: bool = False


class TickTickConfig(BaseModel):
    client_id: str
    redirect_uri: str = "http://127.0.0.1:8765/callback"
    scope: str = "tasks:read tasks:write"
    project_id: str | None = None


class SlackConfig(BaseModel):
    enabled: bool = False
    redact_item_name: bool = False


class StorageConfig(BaseModel):
    sqlite_path: Path = Path(DEFAULT_SQLITE_PATH)
    store_plain_item_names: bool = True

    @field_validator("sqlite_path")
    @classmethod
    def expand_sqlite_path(cls, value: Path) -> Path:
        return value.expanduser()


class LoggingConfig(BaseModel):
    level: str = "INFO"
    redact_item_names: bool = True


class AppConfig(BaseModel):
    poll: PollConfig = Field(default_factory=PollConfig)
    amazon: AmazonConfig = Field(default_factory=AmazonConfig)
    ticktick: TickTickConfig
    slack: SlackConfig = Field(default_factory=SlackConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def load(cls, path: Path | str | None = None) -> Self:
        config_path = Path(path or DEFAULT_CONFIG_PATH).expanduser()
        if not config_path.exists():
            raise ConfigError(f"config file not found: {config_path}")
        with config_path.open("rb") as handle:
            data = tomllib.load(handle)
        return cls.model_validate(data)


def default_config_text() -> str:
    return """[poll]
interval_seconds = 180
jitter_seconds = 15
max_backoff_seconds = 1800

[amazon]
domain = "co.jp"
list_type = "SHOP"
store_password = false

[ticktick]
client_id = "YOUR_TICKTICK_CLIENT_ID"
redirect_uri = "http://127.0.0.1:8765/callback"
scope = "tasks:read tasks:write"
project_id = "YOUR_TICKTICK_PROJECT_ID"

[slack]
enabled = false
redact_item_name = false

[storage]
sqlite_path = "~/.local/share/alexa-ticktick-bridge/state.db"
store_plain_item_names = true

[logging]
level = "INFO"
redact_item_names = true
"""
