# Changelog

## [Unreleased]

## [0.1.0] - 2026-10-18

- Initial release.
- `Client` with API key from argument or `BIBLEQL_API_KEY`, configurable default translation, API URL and timeout; usable as a context manager.
- Queries: `translations`, `translation`, `books`, `languages`, `passage`, `chapter`, `verse`, `random_verse`, `verse_of_the_day`, `bible_index`, `search`, `semantic_search`.
- Concordance: `concordance` (one page), `iter_concordance` (lazy auto-pagination), `concordance_index`, and the `Testament` enum.
- Immutable, typed dataclass models (`py.typed` included).
- Error hierarchy rooted at `BibleQLError`. HTTP errors include the server's message, and "Couldn't find ..." GraphQL errors raise `NotFoundError`.
