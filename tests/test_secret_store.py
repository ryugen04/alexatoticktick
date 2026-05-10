from pathlib import Path

import pytest

from alexa_ticktick_bridge.auth.secret_store import PlainFileSecretStore
from alexa_ticktick_bridge.errors import SecretStoreError


def test_plain_file_store_requires_opt_in(tmp_path: Path) -> None:
    with pytest.raises(SecretStoreError):
        PlainFileSecretStore(tmp_path / "secrets.json")


def test_plain_file_store_json_roundtrip(tmp_path: Path) -> None:
    store = PlainFileSecretStore(tmp_path / "secrets.json", allow_plain_secret_file=True)

    store.set_json("ticktick.token_response", {"access_token": "abc"})

    assert store.get_json("ticktick.token_response") == {"access_token": "abc"}
