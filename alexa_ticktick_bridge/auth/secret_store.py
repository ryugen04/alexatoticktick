from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from alexa_ticktick_bridge.constants import SERVICE_NAME
from alexa_ticktick_bridge.errors import SecretStoreError


class SecretStore(ABC):
    @abstractmethod
    def get(self, key: str) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        raise NotImplementedError

    def get_json(self, key: str) -> dict[str, Any] | None:
        raw = self.get(key)
        if raw is None:
            return None
        loaded = json.loads(raw)
        if not isinstance(loaded, dict):
            raise SecretStoreError(f"secret {key} did not contain a JSON object")
        return loaded

    def set_json(self, key: str, value: dict[str, Any]) -> None:
        self.set(key, json.dumps(value, separators=(",", ":"), ensure_ascii=False))


class KeyringSecretStore(SecretStore):
    def __init__(self, service_name: str = SERVICE_NAME) -> None:
        self.service_name = service_name

    def get(self, key: str) -> str | None:
        try:
            import keyring
        except ImportError as exc:
            raise SecretStoreError("keyring is not installed") from exc
        try:
            return keyring.get_password(self.service_name, key)
        except Exception as exc:
            raise SecretStoreError("keyring get failed") from exc

    def set(self, key: str, value: str) -> None:
        try:
            import keyring
        except ImportError as exc:
            raise SecretStoreError("keyring is not installed") from exc
        try:
            keyring.set_password(self.service_name, key, value)
        except Exception as exc:
            raise SecretStoreError("keyring set failed") from exc

    def delete(self, key: str) -> None:
        try:
            import keyring
        except ImportError as exc:
            raise SecretStoreError("keyring is not installed") from exc
        try:
            keyring.delete_password(self.service_name, key)
        except Exception:
            return


class PlainFileSecretStore(SecretStore):
    def __init__(self, path: Path, *, allow_plain_secret_file: bool = False) -> None:
        if not allow_plain_secret_file:
            raise SecretStoreError("plain secret file storage requires explicit opt-in")
        self.path = path.expanduser()

    def _read(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        loaded = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise SecretStoreError("plain secret file must contain a JSON object")
        return {str(key): str(value) for key, value in loaded.items()}

    def _write(self, data: dict[str, str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        self.path.chmod(0o600)

    def get(self, key: str) -> str | None:
        return self._read().get(key)

    def set(self, key: str, value: str) -> None:
        data = self._read()
        data[key] = value
        self._write(data)

    def delete(self, key: str) -> None:
        data = self._read()
        data.pop(key, None)
        self._write(data)
