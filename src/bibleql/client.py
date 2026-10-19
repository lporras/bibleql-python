"""HTTP client for the BibleQL GraphQL API."""

from __future__ import annotations

import datetime
import os
from collections.abc import Iterator, Sequence
from types import TracebackType
from typing import Any

import httpx

from bibleql import queries
from bibleql._version import __version__
from bibleql.errors import (
    APIError,
    AuthenticationError,
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
    ConcordanceIndexEntry,
    ConcordanceOccurrence,
    ConcordancePage,
    Language,
    LocalizedBook,
    Passage,
    SemanticSearchResult,
    Testament,
    Translation,
    Verse,
)

DEFAULT_API_URL = "https://bibleql.org/graphql"
DEFAULT_TRANSLATION = "eng-web"
DEFAULT_TIMEOUT = 30.0
API_KEY_ENV_VAR = "BIBLEQL_API_KEY"

# The API limits query complexity to 300, and a concordance page costs about first × 28 / 5,
# so 53 is the largest page that fits. Measured against the live API on 2026-10-18.
MAX_CONCORDANCE_PAGE_SIZE = 50

# Phrases the API uses in GraphQL error messages for missing records:
# "Book 'XYZ' not found" (PassageLookup) and "Couldn't find Translation" (Rails RecordNotFound).
_NOT_FOUND_MARKERS = ("not found", "couldn't find")


class Client:
    """Client for the BibleQL GraphQL API.

    Example::

        import bibleql

        with bibleql.Client(api_key="bql_live_...") as client:
            passage = client.passage("John 3:16")
            print(passage.text)

    If ``api_key`` is omitted, it is read from the ``BIBLEQL_API_KEY`` environment variable.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        default_translation: str = DEFAULT_TRANSLATION,
        api_url: str = DEFAULT_API_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        api_key = api_key or os.environ.get(API_KEY_ENV_VAR)
        if not api_key:
            raise ConfigurationError(
                f"api_key is required. Pass it to Client(api_key=...) or set {API_KEY_ENV_VAR}."
            )

        self.default_translation = default_translation
        self.api_url = api_url
        self._http = httpx.Client(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": f"bibleql-python/{__version__}",
            },
        )

    def __repr__(self) -> str:
        # Never include the API key here: reprs end up in logs and tracebacks.
        return f"Client(api_url={self.api_url!r}, default_translation={self.default_translation!r})"

    # --- Lifecycle -------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # --- Translations, books, languages ----------------------------------------

    def translations(self) -> list[Translation]:
        """List all available Bible translations."""
        data = self._execute(queries.translations())
        return [Translation.from_api(t) for t in data["translations"]]

    def translation(self, identifier: str) -> Translation:
        """Get one translation, including its books with localized names."""
        data = self._execute(queries.translation(identifier))
        return Translation.from_api(data["translation"])

    def books(self) -> list[Book]:
        """List the 66 canonical books in order."""
        data = self._execute(queries.books())
        return [Book.from_api(b) for b in data["books"]]

    def languages(self) -> list[Language]:
        """List every language that has at least one translation."""
        data = self._execute(queries.languages())
        return [Language.from_api(lang) for lang in data["languages"]]

    # --- Passages and verses ---------------------------------------------------

    def passage(self, reference: str, *, translation: str | None = None) -> Passage:
        """Look up a passage such as ``"John 3:16"``, ``"John 3:16-18"`` or ``"Mateo 28:18-20"``."""
        body = queries.passage(reference, translation=self._translation(translation))
        return Passage.from_api(self._execute(body)["passage"])

    def chapter(self, book: str, chapter: int, *, translation: str | None = None) -> list[Verse]:
        """Get every verse in a chapter. ``book`` is a book id (``"MAT"``) or localized name."""
        body = queries.chapter(book, chapter, translation=self._translation(translation))
        return [Verse.from_api(v) for v in self._execute(body)["chapter"]]

    def verse(
        self, book: str, chapter: int, verse: int, *, translation: str | None = None
    ) -> Verse:
        """Get a single verse."""
        body = queries.verse(book, chapter, verse, translation=self._translation(translation))
        return Verse.from_api(self._execute(body)["verse"])

    def random_verse(
        self,
        *,
        translation: str | None = None,
        testament: str | None = None,
        books: str | Sequence[str] | None = None,
    ) -> Verse:
        """Get a random verse.

        ``testament`` is ``"OT"`` or ``"NT"``. ``books`` is a list of book ids or
        localized names (``["PSA", "PRO"]``) or a comma-separated string (``"PSA,PRO"``).
        """
        if books is not None and not isinstance(books, str):
            books = ",".join(books)
        body = queries.random_verse(
            translation=self._translation(translation), testament=testament, books=books
        )
        return Verse.from_api(self._execute(body)["randomVerse"])

    def verse_of_the_day(
        self,
        *,
        translation: str | None = None,
        date: datetime.date | str | None = None,
    ) -> Passage:
        """Get the verse of the day. ``date`` defaults to today (server time)."""
        if isinstance(date, datetime.date):
            date = date.isoformat()
        body = queries.verse_of_the_day(translation=self._translation(translation), date=date)
        return Passage.from_api(self._execute(body)["verseOfTheDay"])

    def bible_index(self, *, translation: str | None = None) -> list[LocalizedBook]:
        """Get every book with its chapters and verse counts."""
        body = queries.bible_index(translation=self._translation(translation))
        return [LocalizedBook.from_api(b) for b in self._execute(body)["bibleIndex"]]

    # --- Search ----------------------------------------------------------------

    def search(
        self, query: str, *, translation: str | None = None, limit: int | None = None
    ) -> list[Verse]:
        """Case-insensitive substring search (no stemming). The API caps ``limit`` at 100."""
        body = queries.search(query, translation=self._translation(translation), limit=limit)
        return [Verse.from_api(v) for v in self._execute(body)["search"]]

    def semantic_search(
        self, query: str, *, translation: str | None = None, limit: int | None = None
    ) -> list[SemanticSearchResult]:
        """Search by meaning using AI embeddings. The API caps ``limit`` at 50.

        Unlike the other methods, this does **not** fall back to ``default_translation``:
        only some translations have embeddings, so when ``translation`` is omitted the
        API's own default (currently ``spa-rv1909``) is used.
        """
        body = queries.semantic_search(query, translation=translation, limit=limit)
        return [SemanticSearchResult.from_api(r) for r in self._execute(body)["semanticSearch"]]

    # --- Concordance -----------------------------------------------------------

    def concordance(
        self,
        word: str,
        *,
        translation: str | None = None,
        book: str | None = None,
        testament: Testament | str | None = None,
        first: int | None = None,
        after: str | None = None,
    ) -> ConcordancePage:
        """Get one page of every occurrence of ``word``, in canonical order.

        Pass ``after=page.end_cursor`` to fetch the next page, or use
        :meth:`iter_concordance` to walk all pages. ``first`` defaults to 25 on the API.
        Keep it at or below :data:`MAX_CONCORDANCE_PAGE_SIZE`: larger pages exceed the
        API's query complexity limit and raise :class:`QueryError`.
        """
        body = queries.concordance(
            word,
            translation=self._translation(translation),
            book=book,
            testament=_testament_value(testament),
            first=first,
            after=after,
        )
        return ConcordancePage.from_api(self._execute(body)["concordance"])

    def iter_concordance(
        self,
        word: str,
        *,
        translation: str | None = None,
        book: str | None = None,
        testament: Testament | str | None = None,
        page_size: int = MAX_CONCORDANCE_PAGE_SIZE,
    ) -> Iterator[ConcordanceOccurrence]:
        """Yield every occurrence of ``word``, fetching further pages lazily as needed."""
        after: str | None = None
        while True:
            page = self.concordance(
                word,
                translation=translation,
                book=book,
                testament=testament,
                first=page_size,
                after=after,
            )
            yield from page.occurrences
            if not page.has_next_page or page.end_cursor is None:
                return
            after = page.end_cursor

    def concordance_index(
        self,
        *,
        translation: str | None = None,
        prefix: str | None = None,
        min_occurrences: int | None = None,
        first: int | None = None,
    ) -> list[ConcordanceIndexEntry]:
        """Alphabetical word-frequency index. ``first`` is clamped by the API to 1..200."""
        body = queries.concordance_index(
            translation=self._translation(translation),
            prefix=prefix,
            min_occurrences=min_occurrences,
            first=first,
        )
        return [ConcordanceIndexEntry.from_api(e) for e in self._execute(body)["concordanceIndex"]]

    # --- Internals -------------------------------------------------------------

    def _translation(self, translation: str | None) -> str:
        return translation or self.default_translation

    def _execute(self, body: dict[str, Any]) -> dict[str, Any]:
        """POST a GraphQL request and return its ``data``, raising a BibleQLError on failure."""
        try:
            response = self._http.post(self.api_url, json=body)
        except httpx.TimeoutException as e:
            raise RequestTimeoutError(f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise NetworkError(f"Connection failed: {e}") from e

        _raise_for_status(response)

        try:
            payload = response.json()
        except ValueError as e:
            raise APIError(
                "Response was not valid JSON", status=response.status_code, body=response.text
            ) from e

        errors = payload.get("errors")
        if errors:
            _raise_for_graphql_errors(errors)

        return payload["data"]


def _raise_for_status(response: httpx.Response) -> None:
    status = response.status_code
    if 200 <= status < 300:
        return

    error_class: type[APIError]
    if status == 401:
        error_class = AuthenticationError
    elif status == 429:
        error_class = RateLimitError
    elif status >= 500:
        error_class = ServerError
    else:
        error_class = APIError

    # The API explains HTTP errors in a GraphQL-style body, e.g.
    # 401 → {"errors": [{"message": "Invalid or missing API key"}]}. Surface it when present.
    message = f"HTTP {status}"
    try:
        detail = _join_messages(response.json().get("errors") or [])
    except (ValueError, AttributeError):
        detail = ""
    if detail:
        message = f"{message}: {detail}"
    raise error_class(message, status=status, body=response.text)


def _join_messages(errors: list[dict[str, Any]]) -> str:
    return "; ".join(str(error.get("message", "")) for error in errors)


def _raise_for_graphql_errors(errors: list[dict[str, Any]]) -> None:
    message = _join_messages(errors)
    if any(marker in message.lower() for marker in _NOT_FOUND_MARKERS):
        raise NotFoundError(message, errors=errors)
    raise QueryError(message, errors=errors)


def _testament_value(testament: Testament | str | None) -> str | None:
    """Accept ``Testament.OLD``, ``"OLD"`` or ``"old"`` and return the enum value to send."""
    if testament is None:
        return None
    if isinstance(testament, Testament):
        return testament.value
    return Testament(testament.upper()).value
