from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from alexa_ticktick_bridge.cli import app
from alexa_ticktick_bridge.config import default_config_text


def test_ticktick_auth_prints_authorization_url_and_stores_secret(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    secrets = tmp_path / "secrets.json"
    config.write_text(default_config_text(), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "auth",
            "ticktick",
            "--config",
            str(config),
            "--client-secret",
            "secret-value",
            "--plain-secret-file",
            str(secrets),
            "--allow-plain-secret-file",
        ],
    )

    assert result.exit_code == 0
    assert "https://ticktick.com/oauth/authorize?" in result.stdout
    assert "Expected state:" in result.stdout
    assert "secret-value" in secrets.read_text(encoding="utf-8")


def test_sync_once_rejects_plain_secret_file_without_opt_in(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    secrets = tmp_path / "secrets.json"
    config.write_text(default_config_text(), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["sync", "once", "--config", str(config), "--plain-secret-file", str(secrets)],
    )

    assert result.exit_code != 0
    assert "plain secret file storage requires explicit opt-in" in result.stderr


def test_sync_once_reports_missing_amazon_auth_without_traceback(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    secrets = tmp_path / "secrets.json"
    config.write_text(default_config_text(), encoding="utf-8")
    secrets.write_text('{"ticktick.client_secret":"dummy"}', encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "sync",
            "once",
            "--config",
            str(config),
            "--plain-secret-file",
            str(secrets),
            "--allow-plain-secret-file",
        ],
    )

    assert result.exit_code != 0
    assert "Amazon login data is missing" in result.stderr
    assert "Traceback" not in result.stderr
