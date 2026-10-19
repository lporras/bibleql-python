"""GraphQL documents and request builders for every BibleQL query.

Each public function returns the JSON body to POST to the API:
``{"query": "...", "variables": {...}}``. No network calls happen here.
"""

from typing import Any

# --- Fragments -------------------------------------------------------------
# A GraphQL document must define every fragment it spreads and no unused ones,
# so each query below is concatenated with exactly the fragments it needs.

VERSE_FIELDS = """
fragment VerseFields on Verse {
  bookId
  bookName
  chapter
  verse
  text
}
"""

PASSAGE_FIELDS = """
fragment PassageFields on Passage {
  reference
  translationId
  translationName
  translationNote
  text
  verses { ...VerseFields }
}
"""

TRANSLATION_FIELDS = """
fragment TranslationFields on Translation {
  identifier
  name
  abbrev
  language
  languageName
  note
}
"""


def _request(document: str, **variables: Any) -> dict[str, Any]:
    """Build a GraphQL request body, dropping variables that are None (like Ruby's .compact)."""
    return {
        "query": document,
        "variables": {name: value for name, value in variables.items() if value is not None},
    }


# --- Translations, books, languages -----------------------------------------

TRANSLATIONS_QUERY = (
    """
query Translations {
  translations { ...TranslationFields }
}
"""
    + TRANSLATION_FIELDS
)


def translations() -> dict[str, Any]:
    return _request(TRANSLATIONS_QUERY)


TRANSLATION_QUERY = (
    """
query Translation($identifier: String!) {
  translation(identifier: $identifier) {
    ...TranslationFields
    books { bookId name testament position chapterCount }
  }
}
"""
    + TRANSLATION_FIELDS
)


def translation(identifier: str) -> dict[str, Any]:
    return _request(TRANSLATION_QUERY, identifier=identifier)


BOOKS_QUERY = """
query Books {
  books { bookId name testament position }
}
"""


def books() -> dict[str, Any]:
    return _request(BOOKS_QUERY)


LANGUAGES_QUERY = (
    """
query Languages {
  languages {
    code
    translationCount
    translations { ...TranslationFields }
  }
}
"""
    + TRANSLATION_FIELDS
)


def languages() -> dict[str, Any]:
    return _request(LANGUAGES_QUERY)


# --- Passages and verses ----------------------------------------------------

PASSAGE_QUERY = (
    """
query Passage($reference: String!, $translation: String) {
  passage(reference: $reference, translation: $translation) { ...PassageFields }
}
"""
    + PASSAGE_FIELDS
    + VERSE_FIELDS
)


def passage(reference: str, *, translation: str | None = None) -> dict[str, Any]:
    return _request(PASSAGE_QUERY, reference=reference, translation=translation)


CHAPTER_QUERY = (
    """
query Chapter($book: String!, $chapter: Int!, $translation: String) {
  chapter(book: $book, chapter: $chapter, translation: $translation) { ...VerseFields }
}
"""
    + VERSE_FIELDS
)


def chapter(book: str, chapter: int, *, translation: str | None = None) -> dict[str, Any]:
    return _request(CHAPTER_QUERY, book=book, chapter=chapter, translation=translation)


VERSE_QUERY = (
    """
query Verse($book: String!, $chapter: Int!, $verse: Int!, $translation: String) {
  verse(book: $book, chapter: $chapter, verse: $verse, translation: $translation) {
    ...VerseFields
  }
}
"""
    + VERSE_FIELDS
)


def verse(book: str, chapter: int, verse: int, *, translation: str | None = None) -> dict[str, Any]:
    return _request(VERSE_QUERY, book=book, chapter=chapter, verse=verse, translation=translation)


RANDOM_VERSE_QUERY = (
    """
query RandomVerse($translation: String, $testament: String, $books: String) {
  randomVerse(translation: $translation, testament: $testament, books: $books) {
    ...VerseFields
  }
}
"""
    + VERSE_FIELDS
)


def random_verse(
    *,
    translation: str | None = None,
    testament: str | None = None,
    books: str | None = None,
) -> dict[str, Any]:
    return _request(RANDOM_VERSE_QUERY, translation=translation, testament=testament, books=books)


VERSE_OF_THE_DAY_QUERY = (
    """
query VerseOfTheDay($translation: String, $date: ISO8601Date) {
  verseOfTheDay(translation: $translation, date: $date) { ...PassageFields }
}
"""
    + PASSAGE_FIELDS
    + VERSE_FIELDS
)


def verse_of_the_day(*, translation: str | None = None, date: str | None = None) -> dict[str, Any]:
    return _request(VERSE_OF_THE_DAY_QUERY, translation=translation, date=date)


BIBLE_INDEX_QUERY = """
query BibleIndex($translation: String) {
  bibleIndex(translation: $translation) {
    bookId
    name
    testament
    position
    chapterCount
    chapters { number verseCount }
  }
}
"""


def bible_index(*, translation: str | None = None) -> dict[str, Any]:
    return _request(BIBLE_INDEX_QUERY, translation=translation)


# --- Search ----------------------------------------------------------------

SEARCH_QUERY = (
    """
query Search($query: String!, $translation: String, $limit: Int) {
  search(query: $query, translation: $translation, limit: $limit) { ...VerseFields }
}
"""
    + VERSE_FIELDS
)


def search(
    query: str, *, translation: str | None = None, limit: int | None = None
) -> dict[str, Any]:
    return _request(SEARCH_QUERY, query=query, translation=translation, limit=limit)


SEMANTIC_SEARCH_QUERY = (
    """
query SemanticSearch($query: String!, $translation: String, $limit: Int) {
  semanticSearch(query: $query, translation: $translation, limit: $limit) {
    verse { ...VerseFields }
    similarity
  }
}
"""
    + VERSE_FIELDS
)


def semantic_search(
    query: str, *, translation: str | None = None, limit: int | None = None
) -> dict[str, Any]:
    return _request(SEMANTIC_SEARCH_QUERY, query=query, translation=translation, limit=limit)


# --- Concordance -----------------------------------------------------------

CONCORDANCE_QUERY = (
    """
query Concordance(
  $translation: String!
  $word: String!
  $book: String
  $testament: Testament
  $first: Int
  $after: String
) {
  concordance(
    translation: $translation
    word: $word
    book: $book
    testament: $testament
    first: $first
    after: $after
  ) {
    totalCount
    entry {
      lemma
      surfaceForms
      totalOccurrences
      verseCount
      occurrencesByBook { bookId bookName count }
      occurrencesByTestament { old new }
    }
    edges {
      cursor
      node {
        context
        strongs { number }
        verse { ...VerseFields }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""
    + VERSE_FIELDS
)


def concordance(
    word: str,
    *,
    translation: str,
    book: str | None = None,
    testament: str | None = None,
    first: int | None = None,
    after: str | None = None,
) -> dict[str, Any]:
    return _request(
        CONCORDANCE_QUERY,
        translation=translation,
        word=word,
        book=book,
        testament=testament,
        first=first,
        after=after,
    )


CONCORDANCE_INDEX_QUERY = """
query ConcordanceIndex(
  $translation: String!
  $prefix: String
  $minOccurrences: Int
  $first: Int
) {
  concordanceIndex(
    translation: $translation
    prefix: $prefix
    minOccurrences: $minOccurrences
    first: $first
  ) {
    lemma
    verseCount
    totalOccurrences
  }
}
"""


def concordance_index(
    *,
    translation: str,
    prefix: str | None = None,
    min_occurrences: int | None = None,
    first: int | None = None,
) -> dict[str, Any]:
    return _request(
        CONCORDANCE_INDEX_QUERY,
        translation=translation,
        prefix=prefix,
        minOccurrences=min_occurrences,
        first=first,
    )
