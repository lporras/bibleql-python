"""Data models returned by the BibleQL client."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Testament(str, Enum):
    """Testament filter for concordance queries.

    Note: ``random_verse`` takes the plain strings ``"OT"``/``"NT"`` instead,
    because that is what the API's ``randomVerse`` field expects.
    """

    OLD = "OLD"
    NEW = "NEW"


@dataclass(frozen=True)
class Verse:
    """A single Bible verse."""

    book_id: str
    book_name: str
    chapter: int
    verse: int
    text: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Verse:
        return cls(
            book_id=data["bookId"],
            book_name=data["bookName"],
            chapter=data["chapter"],
            verse=data["verse"],
            text=data["text"],
        )


@dataclass(frozen=True)
class Passage:
    """A passage such as "John 3:16-18", with its full text and its verses."""

    reference: str
    translation_id: str
    translation_name: str
    text: str
    translation_note: str | None = None
    verses: list[Verse] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Passage:
        return cls(
            reference=data["reference"],
            translation_id=data["translationId"],
            translation_name=data["translationName"],
            text=data["text"],
            translation_note=data.get("translationNote"),
            verses=[Verse.from_api(v) for v in data.get("verses") or []],
        )


@dataclass(frozen=True)
class Book:
    """A canonical book of the Bible (e.g. GEN, Genesis)."""

    book_id: str
    name: str
    testament: str
    position: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Book:
        return cls(
            book_id=data["bookId"],
            name=data["name"],
            testament=data["testament"],
            position=data["position"],
        )


@dataclass(frozen=True)
class Chapter:
    """A chapter in the Bible index, with how many verses it has."""

    number: int
    verse_count: int
    verses: list[Verse] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Chapter:
        return cls(
            number=data["number"],
            verse_count=data["verseCount"],
            verses=[Verse.from_api(v) for v in data.get("verses") or []],
        )


@dataclass(frozen=True)
class LocalizedBook:
    """A book as named in a given translation (e.g. "Mateo" in Spanish)."""

    book_id: str
    name: str
    testament: str
    position: int
    chapter_count: int
    chapters: list[Chapter] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> LocalizedBook:
        return cls(
            book_id=data["bookId"],
            name=data["name"],
            testament=data["testament"],
            position=data["position"],
            chapter_count=data["chapterCount"],
            chapters=[Chapter.from_api(c) for c in data.get("chapters") or []],
        )


@dataclass(frozen=True)
class Translation:
    """A Bible translation (e.g. eng-web, World English Bible)."""

    identifier: str
    name: str
    language: str
    abbrev: str | None = None
    language_name: str | None = None
    note: str | None = None
    books: list[LocalizedBook] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Translation:
        return cls(
            identifier=data["identifier"],
            name=data["name"],
            language=data["language"],
            abbrev=data.get("abbrev"),
            language_name=data.get("languageName"),
            note=data.get("note"),
            books=[LocalizedBook.from_api(b) for b in data.get("books") or []],
        )


@dataclass(frozen=True)
class Language:
    """A language and the translations available in it."""

    code: str
    translation_count: int
    translations: list[Translation] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Language:
        return cls(
            code=data["code"],
            translation_count=data["translationCount"],
            translations=[Translation.from_api(t) for t in data.get("translations") or []],
        )


@dataclass(frozen=True)
class SemanticSearchResult:
    """A verse found by semantic (meaning-based) search, with its similarity score."""

    verse: Verse
    similarity: float

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> SemanticSearchResult:
        return cls(
            verse=Verse.from_api(data["verse"]),
            similarity=data["similarity"],
        )


# --- Concordance -----------------------------------------------------------


@dataclass(frozen=True)
class BookCount:
    """How many verses in one book contain a concordance word."""

    book_id: str
    book_name: str
    count: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> BookCount:
        return cls(book_id=data["bookId"], book_name=data["bookName"], count=data["count"])


@dataclass(frozen=True)
class TestamentCount:
    """How many verses in each testament contain a concordance word."""

    old: int
    new: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> TestamentCount:
        return cls(old=data["old"], new=data["new"])


@dataclass(frozen=True)
class ConcordanceEntry:
    """Aggregate statistics for a word across the whole translation."""

    lemma: str
    surface_forms: list[str]
    total_occurrences: int
    verse_count: int
    occurrences_by_book: list[BookCount]
    occurrences_by_testament: TestamentCount

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ConcordanceEntry:
        return cls(
            lemma=data["lemma"],
            surface_forms=list(data["surfaceForms"]),
            total_occurrences=data["totalOccurrences"],
            verse_count=data["verseCount"],
            occurrences_by_book=[BookCount.from_api(b) for b in data["occurrencesByBook"]],
            occurrences_by_testament=TestamentCount.from_api(data["occurrencesByTestament"]),
        )


@dataclass(frozen=True)
class StrongsEntry:
    """A Strong's concordance number (e.g. H2617, G26)."""

    number: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> StrongsEntry:
        return cls(number=data["number"])


@dataclass(frozen=True)
class ConcordanceOccurrence:
    """One verse containing the word.

    ``context`` is a keyword-in-context snippet with ``<mark>`` tags around the
    match; sanitize it before rendering as HTML. ``cursor`` can be passed as
    ``after=`` to resume pagination right after this occurrence.
    """

    verse: Verse
    context: str
    cursor: str
    strongs: StrongsEntry | None = None

    @classmethod
    def from_api(cls, edge: dict[str, Any]) -> ConcordanceOccurrence:
        node = edge["node"]
        strongs = node.get("strongs")
        return cls(
            verse=Verse.from_api(node["verse"]),
            context=node["context"],
            cursor=edge["cursor"],
            strongs=StrongsEntry.from_api(strongs) if strongs else None,
        )


@dataclass(frozen=True)
class ConcordancePage:
    """One page of concordance results.

    The GraphQL connection (``edges``/``node``/``pageInfo``) is flattened into
    ``occurrences``, ``has_next_page`` and ``end_cursor``.
    """

    entry: ConcordanceEntry
    total_count: int
    occurrences: list[ConcordanceOccurrence]
    has_next_page: bool
    end_cursor: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ConcordancePage:
        page_info = data["pageInfo"]
        return cls(
            entry=ConcordanceEntry.from_api(data["entry"]),
            total_count=data["totalCount"],
            occurrences=[ConcordanceOccurrence.from_api(edge) for edge in data["edges"]],
            has_next_page=page_info["hasNextPage"],
            end_cursor=page_info.get("endCursor"),
        )


@dataclass(frozen=True)
class ConcordanceIndexEntry:
    """A word in the alphabetical concordance index."""

    lemma: str
    verse_count: int
    total_occurrences: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ConcordanceIndexEntry:
        return cls(
            lemma=data["lemma"],
            verse_count=data["verseCount"],
            total_occurrences=data["totalOccurrences"],
        )
