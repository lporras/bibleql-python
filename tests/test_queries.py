from pathlib import Path

import pytest
from graphql import OperationDefinitionNode, build_schema, parse, validate
from graphql.execution.values import get_variable_values

from bibleql import queries

# Snapshot of the API schema (bibleql repo: docs/generated/schema.graphql).
SCHEMA = build_schema((Path(__file__).parent / "fixtures" / "schema.graphql").read_text())

REQUESTS = {
    "translations": queries.translations(),
    "translation": queries.translation("eng-web"),
    "books": queries.books(),
    "languages": queries.languages(),
    "passage": queries.passage("John 3:16", translation="eng-web"),
    "chapter": queries.chapter("GEN", 1, translation="eng-web"),
    "verse": queries.verse("GEN", 1, 1, translation="eng-web"),
    "random_verse": queries.random_verse(translation="eng-web", testament="NT", books="PSA,PRO"),
    "verse_of_the_day": queries.verse_of_the_day(translation="eng-web", date="2026-01-01"),
    "bible_index": queries.bible_index(translation="eng-web"),
    "search": queries.search("love", translation="eng-web", limit=5),
    "semantic_search": queries.semantic_search("faith", translation="spa-rv1909", limit=5),
    "concordance": queries.concordance(
        "misericordia", translation="spa-rv1909", book="PSA", testament="OLD", first=10, after="x"
    ),
    "concordance_index": queries.concordance_index(
        translation="spa-rv1909", prefix="mis", min_occurrences=2, first=20
    ),
}


@pytest.mark.parametrize("body", REQUESTS.values(), ids=list(REQUESTS))
def test_query_is_valid_against_schema(body):
    """Catches typos in field names, wrong argument types and missing/unused fragments."""
    errors = validate(SCHEMA, parse(body["query"]))

    assert errors == []


@pytest.mark.parametrize("body", REQUESTS.values(), ids=list(REQUESTS))
def test_variables_match_the_query_definition(body):
    """Every variable we send has the name and type the query declares."""
    document = parse(body["query"])
    operation = next(d for d in document.definitions if isinstance(d, OperationDefinitionNode))
    definitions = operation.variable_definitions or []
    declared = {v.variable.name.value for v in definitions}

    coerced = get_variable_values(SCHEMA, definitions, body["variables"])

    assert not isinstance(coerced, list), coerced  # a list means coercion errors
    assert set(body["variables"]) <= declared


def test_request_drops_none_variables():
    body = queries._request("query { x }", a=1, b=None, c="x")

    assert body == {"query": "query { x }", "variables": {"a": 1, "c": "x"}}


def test_request_keeps_falsy_but_not_none_values():
    body = queries._request("query { x }", limit=0, text="")

    assert body["variables"] == {"limit": 0, "text": ""}


def test_translations_has_no_variables():
    assert queries.translations()["variables"] == {}


def test_passage_variables():
    body = queries.passage("John 3:16", translation="spa-bes")

    assert body["variables"] == {"reference": "John 3:16", "translation": "spa-bes"}


def test_random_verse_only_sends_given_filters():
    body = queries.random_verse(translation="eng-web", testament="NT")

    assert body["variables"] == {"translation": "eng-web", "testament": "NT"}


def test_search_without_limit_omits_it():
    body = queries.search("love", translation="eng-web")

    assert body["variables"] == {"query": "love", "translation": "eng-web"}


def test_concordance_index_uses_camel_case_variable():
    body = queries.concordance_index(translation="spa-rv1909", min_occurrences=3)

    assert body["variables"] == {"translation": "spa-rv1909", "minOccurrences": 3}
