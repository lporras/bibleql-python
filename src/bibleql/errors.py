"""Exceptions raised by the BibleQL client."""

from typing import Any


class BibleQLError(Exception):
    """Base class for every error raised by this library."""


class ConfigurationError(BibleQLError):
    """The client is misconfigured (e.g. missing API key)."""


class NetworkError(BibleQLError):
    """The request never got a response (DNS failure, connection refused, ...)."""


class RequestTimeoutError(NetworkError):
    """The request took longer than the configured timeout."""


class APIError(BibleQLError):
    """The server answered with a non-2xx HTTP status."""

    def __init__(self, message: str, *, status: int | None = None, body: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


class AuthenticationError(APIError):
    """HTTP 401: the API key is missing or invalid."""


class RateLimitError(APIError):
    """HTTP 429: too many requests."""


class ServerError(APIError):
    """HTTP 5xx: something went wrong on the server."""


class QueryError(BibleQLError):
    """The GraphQL response contained an ``errors`` array."""

    def __init__(self, message: str, *, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


class NotFoundError(QueryError):
    """A GraphQL error said the requested resource was not found."""
