class BridgeError(Exception):
    """Base error for bridge failures."""


class ConfigError(BridgeError):
    """Configuration is missing or invalid."""


class SecretStoreError(BridgeError):
    """Secret storage failed or is unavailable."""


class AuthFailed(BridgeError):
    """Authentication failed permanently for the current attempt."""


class ReauthRequired(AuthFailed):
    """Stored credentials are missing or expired."""


class RateLimited(BridgeError):
    """Remote service returned a rate limit response."""


class RemoteServiceError(BridgeError):
    """Remote service returned an unexpected error."""


class NotConfigured(ConfigError):
    """A required feature has not been configured."""
