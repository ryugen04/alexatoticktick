from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

SECRET_KEYS = {
    "password",
    "otp",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "cookie",
    "login_data",
    "webhook_url",
    "client_secret",
}


def mask_email(value: str) -> str:
    if "@" not in value:
        return "<redacted>"
    name, domain = value.split("@", 1)
    return f"{name[:1]}***@{domain}"


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def redact_mapping(data: Mapping[str, Any], *, redact_item_names: bool = True) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in data.items():
        lowered = key.lower()
        if lowered in SECRET_KEYS or any(secret in lowered for secret in SECRET_KEYS):
            redacted[key] = "<redacted>"
        elif lowered in {"email", "amazon.email"} and isinstance(value, str):
            redacted[key] = mask_email(value)
        elif redact_item_names and lowered in {"text", "title", "item_name", "item"}:
            redacted[key] = "<item:redacted>"
        elif isinstance(value, Mapping):
            redacted[key] = redact_mapping(value, redact_item_names=redact_item_names)
        else:
            redacted[key] = value
    return redacted
