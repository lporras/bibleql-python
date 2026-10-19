import datetime

import httpx
import pytest

import bibleql
from bibleql import (
    APIError,
    AuthenticationError,
    Book,
    Client,
    ConcordanceIndexEntry,
    ConcordancePage,
    ConfigurationError,
    Language,
    LocalizedBook,
    NetworkError,
    NotFoundError,
    Passage,
    QueryError,
    RateLimitError,
    RequestTimeoutError,
    SemanticSearchResult,
    ServerError,
    Translation,
    Verse,
)
from tests.conftest import API_URL, sent_body

VERSE = {"bookId": "JHN", "bookName": "John", "chapter": 3, "verse": 16, "text": "For God..."}
PASSAGE = {
    "reference": "John 3:16",
    "translationId": "eng-web",
    "translationName": "World English Bible",
    "translationNote": "Public Domain",
    "text": "For God...",
    "verses": [VERSE],
}
TRANSLATION = {"identifier": "eng-web", "name": "World English Bible", "language": "eng"}


def concordance_page(*, cursor, has_next_page, end_cursor):
    return {
        "totalCount": 2,
        "entry": {
            "lemma": "misericordia",
            "surfaceForms": ["misericordia", "misericordias"],
            "totalOccurrences": 2,
            "verseCount": 2,
            "occurrencesByBook": [{"bookId": "PSA", "bookName": "Salmos", "count": 2}],
            "occurrencesByTestament": {"old": 2, "new": 0},
        },
        "edges": [
            {
                "cursor": cursor,
                "node": {
                    "context": "su <mark>misericordia</mark>",
                    "strongs": None,
                    "verse": VERSE,
                },
            }
        ],
        "pageInfo": {"hasNextPage": has_next_page, "endCursor": end_cursor},
    }


# --- Configuration -----------------------------------------------------------


def test_requires_an_api_key(monkeypatch):
    monkeypatch.delenv("BIBLEQL_API_KEY", raising=False)

    with pytest.raises(ConfigurationError, match="api_key is required"):
        Client()


def test_reads_api_key_from_environment(monkeypatch, mock_graphql):
    monkeypatch.setenv("BIBLEQL_API_KEY", "env-key")
    route = mock_graphql({"books": []})

    with Client(api_url=API_URL) as client:
        client.books()

    assert route.calls.last.request.headers["Authorization"] == "Bearer env-key"


def test_defaults():
    client = Client(api_key="k")

    assert client.api_url == "https://bibleql.org/graphql"
    assert client.default_translation == "eng-web"
    client.close()


def test_sends_auth_and_user_agent_headers(client, mock_graphql):
    route = mock_graphql({"books": []})

    client.books()

    headers = route.calls.last.request.headers
    assert headers["Authorization"] == "Bearer test-key"
    assert headers["Content-Type"] == "application/json"
    assert headers["User-Agent"] == f"bibleql-python/{bibleql.__version__}"


def test_repr_does_not_leak_api_key():
    with Client(api_key="secret-key") as client:
        assert "secret-key" not in repr(client)


def test_context_manager_closes_http_client():
    with Client(api_key="k") as client:
        pass

    assert client._http.is_closed


# --- Query methods -----------------------------------------------------------


def test_translations(client, mock_graphql):
    mock_graphql({"translations": [{**TRANSLATION, "abbrev": "WEB"}]})

    result = client.translations()

    assert result == [Translation.from_api({**TRANSLATION, "abbrev": "WEB"})]


def test_translation(client, mock_graphql):
    route = mock_graphql({"translation": {**TRANSLATION, "books": []}})

    result = client.translation("eng-web")

    assert isinstance(result, Translation)
    assert sent_body(route)["variables"] == {"identifier": "eng-web"}


def test_books(client, mock_graphql):
    mock_graphql(
        {"books": [{"bookId": "GEN", "name": "Genesis", "testament": "OT", "position": 1}]}
    )

    assert client.books() == [Book(book_id="GEN", name="Genesis", testament="OT", position=1)]


def test_languages(client, mock_graphql):
    mock_graphql(
        {"languages": [{"code": "eng", "translationCount": 1, "translations": [TRANSLATION]}]}
    )

    result = client.languages()

    assert isinstance(result[0], Language)
    assert result[0].translations[0].identifier == "eng-web"


def test_passage_uses_default_translation(client, mock_graphql):
    route = mock_graphql({"passage": PASSAGE})

    result = client.passage("John 3:16")

    assert isinstance(result, Passage)
    assert result.verses[0].text == "For God..."
    assert sent_body(route)["variables"] == {"reference": "John 3:16", "translation": "eng-web"}


def test_passage_with_explicit_translation(client, mock_graphql):
    route = mock_graphql({"passage": {**PASSAGE, "translationId": "spa-bes"}})

    client.passage("Juan 3:16", translation="spa-bes")

    assert sent_body(route)["variables"]["translation"] == "spa-bes"


def test_custom_default_translation(mock_graphql):
    route = mock_graphql({"passage": PASSAGE})

    with Client(api_key="k", api_url=API_URL, default_translation="spa-bes") as client:
        client.passage("Juan 3:16")

    assert sent_body(route)["variables"]["translation"] == "spa-bes"


def test_chapter(client, mock_graphql):
    route = mock_graphql({"chapter": [VERSE, {**VERSE, "verse": 17}]})

    result = client.chapter("JHN", 3)

    assert [v.verse for v in result] == [16, 17]
    assert sent_body(route)["variables"] == {"book": "JHN", "chapter": 3, "translation": "eng-web"}


def test_verse(client, mock_graphql):
    mock_graphql({"verse": VERSE})

    assert client.verse("JHN", 3, 16) == Verse.from_api(VERSE)


def test_random_verse_with_testament(client, mock_graphql):
    route = mock_graphql({"randomVerse": VERSE})

    client.random_verse(testament="NT")

    assert sent_body(route)["variables"] == {"translation": "eng-web", "testament": "NT"}


@pytest.mark.parametrize("books", [["PSA", "PRO"], ("PSA", "PRO"), "PSA,PRO"])
def test_random_verse_accepts_books_as_list_or_string(client, mock_graphql, books):
    route = mock_graphql({"randomVerse": VERSE})

    client.random_verse(books=books)

    assert sent_body(route)["variables"]["books"] == "PSA,PRO"


def test_verse_of_the_day_accepts_a_date_object(client, mock_graphql):
    route = mock_graphql({"verseOfTheDay": PASSAGE})

    result = client.verse_of_the_day(date=datetime.date(2026, 1, 1))

    assert isinstance(result, Passage)
    assert sent_body(route)["variables"]["date"] == "2026-01-01"


def test_verse_of_the_day_without_date_omits_it(client, mock_graphql):
    route = mock_graphql({"verseOfTheDay": PASSAGE})

    client.verse_of_the_day()

    assert "date" not in sent_body(route)["variables"]


def test_bible_index(client, mock_graphql):
    mock_graphql(
        {
            "bibleIndex": [
                {
                    "bookId": "GEN",
                    "name": "Genesis",
                    "testament": "OT",
                    "position": 1,
                    "chapterCount": 50,
                    "chapters": [{"number": 1, "verseCount": 31}],
                }
            ]
        }
    )

    result = client.bible_index()

    assert isinstance(result[0], LocalizedBook)
    assert result[0].chapters[0].verse_count == 31


def test_search(client, mock_graphql):
    route = mock_graphql({"search": [VERSE]})

    result = client.search("love", limit=10)

    assert result == [Verse.from_api(VERSE)]
    assert sent_body(route)["variables"] == {
        "query": "love",
        "translation": "eng-web",
        "limit": 10,
    }


def test_semantic_search_lets_the_api_pick_the_translation(client, mock_graphql):
    route = mock_graphql({"semanticSearch": [{"verse": VERSE, "similarity": 0.95}]})

    result = client.semantic_search("love and forgiveness", limit=5)

    assert isinstance(result[0], SemanticSearchResult)
    assert result[0].similarity == 0.95
    assert sent_body(route)["variables"] == {"query": "love and forgiveness", "limit": 5}


def test_semantic_search_with_translation(client, mock_graphql):
    route = mock_graphql({"semanticSearch": []})

    client.semantic_search("amor", translation="spa-rv1909")

    assert sent_body(route)["variables"]["translation"] == "spa-rv1909"


# --- Concordance ---------------------------------------------------------------


def test_concordance_returns_a_page(client, mock_graphql):
    route = mock_graphql(
        {"concordance": concordance_page(cursor="c1", has_next_page=True, end_cursor="c1")}
    )

    page = client.concordance("misericordia", translation="spa-rv1909", book="Salmos", first=1)

    assert isinstance(page, ConcordancePage)
    assert page.total_count == 2
    assert page.entry.surface_forms == ["misericordia", "misericordias"]
    assert page.entry.occurrences_by_testament.old == 2
    assert page.entry.occurrences_by_book[0].book_name == "Salmos"
    assert page.occurrences[0].verse.book_id == "JHN"
    assert page.occurrences[0].cursor == "c1"
    assert page.occurrences[0].strongs is None
    assert page.has_next_page is True
    assert page.end_cursor == "c1"
    assert sent_body(route)["variables"] == {
        "translation": "spa-rv1909",
        "word": "misericordia",
        "book": "Salmos",
        "first": 1,
    }


# bibleql.Testament (not a bare import): pytest would try to collect a class named Test* as tests.
@pytest.mark.parametrize("testament", [bibleql.Testament.OLD, "OLD", "old"])
def test_concordance_normalizes_testament(client, mock_graphql, testament):
    route = mock_graphql(
        {"concordance": concordance_page(cursor="c1", has_next_page=False, end_cursor=None)}
    )

    client.concordance("misericordia", testament=testament)

    assert sent_body(route)["variables"]["testament"] == "OLD"


def test_concordance_rejects_unknown_testament(client):
    with pytest.raises(ValueError):
        client.concordance("misericordia", testament="OT")


def test_iter_concordance_follows_cursors_across_pages(client, api):
    route = api.post(API_URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "data": {
                        "concordance": concordance_page(
                            cursor="c1", has_next_page=True, end_cursor="c1"
                        )
                    }
                },
            ),
            httpx.Response(
                200,
                json={
                    "data": {
                        "concordance": concordance_page(
                            cursor="c2", has_next_page=False, end_cursor="c2"
                        )
                    }
                },
            ),
        ]
    )

    occurrences = list(client.iter_concordance("misericordia", translation="spa-rv1909"))

    assert [o.cursor for o in occurrences] == ["c1", "c2"]
    assert route.call_count == 2
    assert "after" not in sent_body(route, 0)["variables"]
    assert sent_body(route, 1)["variables"]["after"] == "c1"


def test_iter_concordance_is_lazy(client, api):
    route = api.post(API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "concordance": concordance_page(
                        cursor="c1", has_next_page=True, end_cursor="c1"
                    )
                }
            },
        )
    )

    iterator = client.iter_concordance("misericordia")
    assert route.call_count == 0  # nothing fetched until we start iterating

    next(iterator)
    assert route.call_count == 1


def test_concordance_index(client, mock_graphql):
    route = mock_graphql(
        {"concordanceIndex": [{"lemma": "misericordia", "verseCount": 10, "totalOccurrences": 12}]}
    )

    result = client.concordance_index(translation="spa-rv1909", prefix="mis", min_occurrences=2)

    assert result == [
        ConcordanceIndexEntry(lemma="misericordia", verse_count=10, total_occurrences=12)
    ]
    assert sent_body(route)["variables"] == {
        "translation": "spa-rv1909",
        "prefix": "mis",
        "minOccurrences": 2,
    }


# --- Errors --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "error_class"),
    [
        (401, AuthenticationError),
        (429, RateLimitError),
        (500, ServerError),
        (503, ServerError),
        (404, APIError),
        (400, APIError),
    ],
)
def test_http_errors(client, api, status, error_class):
    api.post(API_URL).mock(return_value=httpx.Response(status, text="nope"))

    with pytest.raises(error_class) as exc_info:
        client.books()

    assert exc_info.value.status == status
    assert exc_info.value.body == "nope"
    assert str(exc_info.value) == f"HTTP {status}"


def test_http_error_includes_server_message(client, api):
    # This is the real body the API returns for a bad key.
    api.post(API_URL).mock(
        return_value=httpx.Response(
            401, json={"errors": [{"message": "Invalid or missing API key"}]}
        )
    )

    with pytest.raises(AuthenticationError, match=r"^HTTP 401: Invalid or missing API key$"):
        client.books()


@pytest.mark.parametrize(
    "message",
    [
        "Book 'XYZ' not found for translation 'eng-web'",
        "Translation 'xxx' not found",
        "Couldn't find Translation",
    ],
)
def test_graphql_not_found_errors(client, api, message):
    errors = [{"message": message, "path": ["passage"]}]
    api.post(API_URL).mock(return_value=httpx.Response(200, json={"data": None, "errors": errors}))

    with pytest.raises(NotFoundError) as exc_info:
        client.passage("XYZ 1:1")

    assert str(exc_info.value) == message
    assert exc_info.value.errors == errors


def test_other_graphql_errors_raise_query_error(client, api):
    errors = [{"message": "Testament must be 'OT' or 'NT'"}, {"message": "second problem"}]
    api.post(API_URL).mock(return_value=httpx.Response(200, json={"data": None, "errors": errors}))

    with pytest.raises(QueryError) as exc_info:
        client.random_verse(testament="ZZ")

    assert not isinstance(exc_info.value, NotFoundError)
    assert str(exc_info.value) == "Testament must be 'OT' or 'NT'; second problem"


def test_timeout_raises_request_timeout_error(client, api):
    api.post(API_URL).mock(side_effect=httpx.ReadTimeout("too slow"))

    with pytest.raises(RequestTimeoutError) as exc_info:
        client.books()

    assert isinstance(exc_info.value.__cause__, httpx.ReadTimeout)


def test_connection_failure_raises_network_error(client, api):
    api.post(API_URL).mock(side_effect=httpx.ConnectError("no route to host"))

    with pytest.raises(NetworkError) as exc_info:
        client.books()

    assert not isinstance(exc_info.value, RequestTimeoutError)


def test_invalid_json_raises_api_error(client, api):
    api.post(API_URL).mock(return_value=httpx.Response(200, text="<html>oops</html>"))

    with pytest.raises(APIError, match="not valid JSON"):
        client.books()
