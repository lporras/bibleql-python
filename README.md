# BibleQL Python

[![CI](https://github.com/lporras/bibleql-python/actions/workflows/ci.yml/badge.svg)](https://github.com/lporras/bibleql-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/bibleql.svg)](https://pypi.org/project/bibleql/)
[![Python versions](https://img.shields.io/pypi/pyversions/bibleql.svg)](https://pypi.org/project/bibleql/)

A typed Python client for the [BibleQL](https://bibleql.org) GraphQL API. Query Bible verses, passages, translations, search and concordance across 47 translations in 31 languages, without writing GraphQL.

## Installation

```bash
pip install bibleql
```

Requires Python 3.10+.

## Quick start

```python
import bibleql

with bibleql.Client(api_key="bql_live_...") as client:
    passage = client.passage("John 3:16")
    print(passage.reference)  # John 3:16
    print(passage.text)  # For God so loved the world...
```

Get an API key at [bibleql.org](https://bibleql.org), and try queries in the [playground](https://bibleql.org/playground).

## Configuration

```python
client = bibleql.Client(
    api_key="bql_live_...",  # or set the BIBLEQL_API_KEY environment variable
    default_translation="spa-bes",  # optional, defaults to "eng-web"
    api_url="https://custom-host.com/graphql",  # optional, defaults to https://bibleql.org/graphql
    timeout=60,  # optional, seconds, defaults to 30
)
```

If `api_key` is omitted, the client reads `BIBLEQL_API_KEY`:

```bash
export BIBLEQL_API_KEY=bql_live_...
```

```python
client = bibleql.Client()
```

Use the client as a context manager (`with ... as client:`) or call `client.close()` when done, so its connection pool is released.

Every method that takes `translation=` falls back to `default_translation` when it's omitted. The exception is `semantic_search`, which lets the API pick a translation that has embeddings.

## Usage

### Passages

```python
passage = client.passage("John 3:16")
passage.reference  # "John 3:16"
passage.text  # "For God so loved the world..."
passage.translation_id  # "eng-web"
passage.verses  # [Verse(book_id='JHN', book_name='John', chapter=3, verse=16, text='...')]

client.passage("John 3:16-18")
client.passage("Matthew 25:31-33,46")
client.passage("Genesis 1")
client.passage("Mateo 28:18-20", translation="spa-bes")
```

### Verses and chapters

```python
verse = client.verse("MAT", 5, 3)
verse.book_name  # "Matthew"
verse.text  # "Blessed are the poor in spirit..."

verses = client.chapter("GEN", 1)  # list[Verse]
```

### Random verse

```python
client.random_verse()
client.random_verse(testament="NT")  # "OT" or "NT"
client.random_verse(books=["PSA", "PRO"])  # or books="PSA,PRO"
```

### Verse of the day

```python
import datetime

client.verse_of_the_day()
client.verse_of_the_day(date=datetime.date(2026, 1, 1))  # or date="2026-01-01"
```

### Search

Case-insensitive substring search, with no stemming ("love" won't match "loved"):

```python
for verse in client.search("love", limit=5):
    print(verse.book_name, verse.chapter, verse.verse, verse.text)
```

Semantic search finds verses by meaning, using AI embeddings:

```python
for result in client.semantic_search("fe y esperanza", limit=5):
    print(f"{result.similarity:.2f}", result.verse.text)
```

### Concordance

Exhaustive, canonically ordered occurrences of a word, with per-book and per-testament totals:

```python
page = client.concordance("misericordia", translation="spa-rv1909", first=10)
page.total_count  # total occurrences
page.entry.surface_forms  # ["misericordia", "misericordias", ...]
page.entry.occurrences_by_testament.old  # verses in the Old Testament
for occurrence in page.occurrences:
    print(occurrence.verse.book_name, occurrence.context)  # context has <mark> tags

# Next page
if page.has_next_page:
    page = client.concordance("misericordia", translation="spa-rv1909", after=page.end_cursor)

# Or let the client paginate for you (pages are fetched lazily)
for occurrence in client.iter_concordance("misericordia", translation="spa-rv1909"):
    ...

# Filters
client.concordance("misericordia", translation="spa-rv1909", book="Salmos")
client.concordance("misericordia", translation="spa-rv1909", testament=bibleql.Testament.NEW)

# Alphabetical word-frequency index
client.concordance_index(translation="spa-rv1909", prefix="mis", min_occurrences=5)
```

The `context` field contains `<mark>` HTML tags around the match, so sanitize it before rendering it as HTML.

### Translations, languages, books

```python
client.translations()  # list[Translation]
t = client.translation("eng-web")
t.name, t.abbrev  # "World English Bible", "WEB"
t.books  # list[LocalizedBook]

client.languages()  # list[Language], each with .translations
client.books()  # list[Book], the 66 canonical books
```

### Bible index

```python
index = client.bible_index()
index[0].name  # "Genesis"
index[0].chapters[0].verse_count  # 31
```

### Models

All results are immutable dataclasses with snake_case attributes. To convert one to a dict:

```python
import dataclasses

dataclasses.asdict(client.verse("JHN", 3, 16))
```

## Error handling

Every error inherits from `bibleql.BibleQLError`:

```
BibleQLError
├── ConfigurationError        no API key
├── NetworkError              no response (DNS, connection refused, ...)
│   └── RequestTimeoutError
├── APIError (.status, .body) non-2xx HTTP response
│   ├── AuthenticationError     401
│   ├── RateLimitError          429
│   └── ServerError             5xx
└── QueryError (.errors)      GraphQL errors in the response
    └── NotFoundError
```

```python
try:
    client.passage("Hezekiah 1:1")
except bibleql.NotFoundError as e:
    print(f"Not found: {e}")
except bibleql.AuthenticationError:
    print("Invalid API key")
except bibleql.RateLimitError:
    print("Too many requests")
except bibleql.RequestTimeoutError:
    print("Request timed out")
except bibleql.NetworkError:
    print("Connection failed")
except bibleql.QueryError as e:
    print(f"GraphQL error: {e}")
    print(e.errors)  # raw error list from the API
```

## Development

```bash
asdf install                      # Python version from .tool-versions
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"

pytest                            # run tests (HTTP is mocked with respx, no network needed)
ruff check . && ruff format .     # lint and format
```

`tests/fixtures/schema.graphql` is a snapshot of the API schema, and every query is validated against it. Refresh it from the API repo (`docs/generated/schema.graphql`) when the schema changes.

### Testing against the live API

The test suite never touches the network. To check the client against the real API, put your key in a `.env` file (gitignored) and run the smoke test, which loads it with [python-dotenv](https://pypi.org/project/python-dotenv/):

```bash
cp .env.example .env              # then set BIBLEQL_API_KEY in .env
python scripts/smoke_test.py      # calls every method and prints the results
```

The library itself never reads `.env` files. In your own app, load them yourself (for example with `dotenv.load_dotenv()`) before creating a `Client()`.

## License

Released under the [MIT License](LICENSE).
