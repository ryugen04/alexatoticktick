# alexa-ticktick-bridge

Personal bridge from Alexa Shopping List to TickTick.

This project uses an unofficial Alexa mobile-app-derived API boundary for personal local use. It does not depend on or copy `pyalexatodo`; Amazon authentication is isolated behind an adapter so it can be replaced if the current MVP dependency stops working.

## Status

The current CLI can initialize config, store TickTick and Amazon credentials through SecretStore, and run a one-shot sync path that restores Amazon auth, reads the Alexa shopping list, creates TickTick tasks, and marks successfully synced Alexa items complete.

Live Amazon/TickTick verification still depends on user-provided credentials and may expose changes needed for the unofficial Alexa API adapter.

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

## Local Setup

Install dependencies from the repository checkout:

```bash
uv sync --extra dev
```

Create the default config file:

```bash
uv run atb config init
```

The default path is:

```text
~/.config/alexa-ticktick-bridge/config.toml
```

Edit the config and set at least:

```toml
[ticktick]
client_id = "YOUR_TICKTICK_CLIENT_ID"
redirect_uri = "http://127.0.0.1:8765/callback"
scope = "tasks:read tasks:write"
project_id = "YOUR_TICKTICK_PROJECT_ID"

[amazon]
domain = "co.jp"
list_type = "SHOP"
store_password = false

[slack]
enabled = false
redact_item_name = false
```

`store_password = false` is the recommended default. The tool stores Amazon session data after interactive login, not the Amazon password.

## Secret Storage

By default, the CLI uses OS keyring. Use the normal commands without `--plain-secret-file` for real credentials.

For disposable local tests only, you can use a plaintext secret file:

```bash
uv run atb auth ticktick \
  --config /tmp/atb-config.toml \
  --client-secret dummy \
  --plain-secret-file /tmp/atb-secrets.json \
  --allow-plain-secret-file
```

Do not commit config files, secret files, state databases, logs, OAuth codes, passwords, OTP values, or webhook URLs.

## TickTick Auth

First store the TickTick client secret and print the authorization URL:

```bash
uv run atb auth ticktick --client-secret YOUR_TICKTICK_CLIENT_SECRET
```

Open the printed authorization URL in a browser, approve access, and copy the `code` query parameter from the redirect URL.

Then exchange the code for a token:

```bash
uv run atb auth ticktick --code YOUR_AUTHORIZATION_CODE
```

This stores the full TickTick token response under `ticktick.token_response` in SecretStore.

## Amazon Auth

Run interactive Amazon login:

```bash
uv run atb auth amazon
```

The command prompts for:

```text
Amazon email
Amazon password
Current Amazon OTP
```

On success, it stores:

```text
amazon.email
amazon.login_data
```

If `config.amazon.store_password = true`, it also stores `amazon.password`, but this is not recommended.


## Slack Notifications

Slack notifications use an Incoming Webhook URL stored in SecretStore. Create the webhook in Slack, then save it locally:

```bash
uv run atb auth slack --webhook-url YOUR_SLACK_INCOMING_WEBHOOK_URL
```

Enable Slack notifications in the config:

```toml
[slack]
enabled = true
redact_item_name = false
```

With `redact_item_name = false`, Slack messages include the shopping item name. Set it to `true` if item names should not appear in Slack.

Slack posts use a simple `:shopping_trolley: {item name}` message.

Slack notification failures do not block the sync. If TickTick task creation succeeds, the tool still marks the Alexa item complete even when Slack posting fails. The sync summary increments `notification_failures` for those cases.

## One-Shot Sync

After both auth steps succeed, run one sync pass:

```bash
uv run atb sync once
```

Expected behavior:

1. Restore Amazon session from SecretStore.
2. Fetch the Alexa `SHOP` list.
3. Fetch active shopping-list items.
4. Skip items already recorded in SQLite state.
5. Create TickTick tasks in the configured project.
6. Mark Alexa items complete only after TickTick task creation succeeds.
7. Print a `SyncResult` summary.

The default state database is:

```text
~/.local/share/alexa-ticktick-bridge/state.db
```

## Daemon Mode

Run continuous polling:

```bash
uv run atb sync daemon
```

Polling behavior is controlled by:

```toml
[poll]
interval_seconds = 180
jitter_seconds = 15
max_backoff_seconds = 1800
```

The current CLI runs in the foreground. Use your process supervisor of choice if you want it to run continuously after logout.

## Verification Checklist

Run these checks before live sync:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest
uv run --extra dev ruff check
uv run --extra dev mypy alexa_ticktick_bridge
uv run atb --help
```

Smoke-test config and auth URL generation without real secrets:

```bash
uv run atb config init --path /tmp/atb-verify-config.toml --force
uv run atb auth ticktick \
  --config /tmp/atb-verify-config.toml \
  --client-secret dummy \
  --plain-secret-file /tmp/atb-verify-secrets.json \
  --allow-plain-secret-file
```

Smoke-test the missing-auth boundary:

```bash
uv run atb sync once \
  --config /tmp/atb-verify-config.toml \
  --plain-secret-file /tmp/atb-verify-secrets.json \
  --allow-plain-secret-file
```

Without Amazon login data, this should fail cleanly with:

```text
Amazon login data is missing
```

It should not print a Python traceback.

## Troubleshooting

`Amazon login data is missing` means `atb auth amazon` has not completed successfully for the same SecretStore backend.

`ticktick.client_secret is missing` means `atb auth ticktick --client-secret ...` has not stored the client secret, or you are using a different SecretStore backend than the one used for sync.

`TickTick access token is missing` means the authorization URL was generated but the `--code` exchange has not completed.

`slack.webhook_url is missing` means `[slack].enabled = true` but `atb auth slack --webhook-url ...` has not been run for the same SecretStore backend.

Amazon authentication and Alexa list access use unofficial endpoints. If Amazon changes the mobile-app API, login, list fetch, or completion may fail even when TickTick is configured correctly.
