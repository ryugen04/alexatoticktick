# alexa-ticktick-bridge

Personal bridge from Alexa Shopping List to TickTick.

This project uses an unofficial Alexa mobile-app-derived API boundary for personal local use. It does not depend on or copy `pyalexatodo`; Amazon authentication is isolated behind an adapter so it can be replaced if the current MVP dependency stops working.

## Status

MVP foundation is in progress. The package currently provides configuration loading, secret storage abstractions, redaction, API client boundaries, SQLite idempotency state, a sync service skeleton, and the `atb` CLI.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check
uv run mypy alexa_ticktick_bridge
```

## CLI

```bash
atb config init
atb auth amazon
atb auth ticktick
atb sync once
atb sync daemon
```

Secrets are stored through OS keyring by default. Plain secret files require an explicit opt-in and are intended only for constrained local environments.
