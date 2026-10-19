"""Python client for the BibleQL GraphQL API."""

from bibleql._version import __version__
from bibleql.client import Client
from bibleql.errors import (
    APIError,
    AuthenticationError,
    BibleQLError,
    ConfigurationError,
    NetworkError,
    NotFoundError,
    QueryError,
    RateLimitError,
    RequestTimeoutError,
    ServerError,
)
from bibleql.models import (
    Book,
    BookCount,
    Chapter,
    ConcordanceEntry,
    ConcordanceIndexEntry,
    ConcordanceOccurrence,
    ConcordancePage,
    Language,
    LocalizedBook,
    Passage,
    SemanticSearchResult,
    StrongsEntry,
    Testament,
    TestamentCount,
    Translation,
    Verse,
)

__all__ = [
    "__version__",
    "Client",
    # Errors
    "APIError",
    "AuthenticationError",
    "BibleQLError",
    "ConfigurationError",
    "NetworkError",
    "NotFoundError",
    "QueryError",
    "RateLimitError",
    "RequestTimeoutError",
    "ServerError",
    # Models
    "Book",
    "BookCount",
    "Chapter",
    "ConcordanceEntry",
    "ConcordanceIndexEntry",
    "ConcordanceOccurrence",
    "ConcordancePage",
    "Language",
    "LocalizedBook",
    "Passage",
    "SemanticSearchResult",
    "StrongsEntry",
    "Testament",
    "TestamentCount",
    "Translation",
    "Verse",
]
