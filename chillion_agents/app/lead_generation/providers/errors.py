"""Provider-level errors for people search integrations."""

from typing import Optional


class PeopleProviderError(Exception):
    """Base error for people search providers."""


class ProspeoError(PeopleProviderError):
    """Base error for Prospeo-specific failures."""


class ProspeoNotConfiguredError(ProspeoError):
    """PROSPEO_API_KEY is missing or empty."""


class ProspeoDomainRequiredError(ProspeoError):
    """Prospeo people search requires a real organization domain."""


class ProspeoAuthenticationError(ProspeoError):
    """Prospeo rejected the API key."""

    def __init__(self, message: str = "Prospeo authentication failed", status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class ProspeoRateLimitError(ProspeoError):
    """Prospeo rate limit exceeded (429)."""


class ProspeoInsufficientCreditsError(ProspeoError):
    """Prospeo credits are exhausted."""


class ProspeoPlanRequiredError(ProspeoError):
    """The requested Prospeo filters require a higher plan."""


class ProspeoAPIError(ProspeoError):
    """Unexpected Prospeo API, timeout, or network failure."""

    def __init__(self, message: str = "Prospeo request failed", status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
