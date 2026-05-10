# Security

Do not commit Amazon credentials, Amazon login data, TickTick tokens, Slack webhook URLs, OTP codes, local databases, or logs.

The default SecretStore uses the OS keyring. Plaintext secret files are disabled unless explicitly requested by the caller.

Logs redact secrets and, by default, shopping item names. Report any leak or near miss as a Careflow incident before continuing implementation.
