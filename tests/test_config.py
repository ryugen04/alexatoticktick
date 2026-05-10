from pathlib import Path

import pytest
from pydantic import ValidationError

from alexa_ticktick_bridge.config import AppConfig, default_config_text


def test_load_default_config(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(default_config_text(), encoding="utf-8")

    config = AppConfig.load(path)

    assert config.poll.interval_seconds == 180
    assert config.amazon.domain == "co.jp"
    assert config.ticktick.client_id == "YOUR_TICKTICK_CLIENT_ID"
    assert config.storage.sqlite_path.is_absolute()


def test_poll_interval_is_limited() -> None:
    with pytest.raises(ValidationError):
        AppConfig.model_validate(
            {
                "poll": {"interval_seconds": 30},
                "ticktick": {"client_id": "id"},
            }
        )
