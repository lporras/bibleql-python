import pytest

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


@pytest.mark.parametrize(
    "error_class",
    [
        ConfigurationError,
        NetworkError,
        RequestTimeoutError,
        APIError,
        AuthenticationError,
        RateLimitError,
        ServerError,
        QueryError,
        NotFoundError,
    ],
)
def test_every_error_is_a_bibleql_error(error_class):
    assert issubclass(error_class, BibleQLError)


def test_timeout_is_a_network_error():
    assert issubclass(RequestTimeoutError, NetworkError)


def test_api_error_stores_status_and_body():
    error = AuthenticationError("HTTP 401", status=401, body="Unauthorized")

    assert str(error) == "HTTP 401"
    assert error.status == 401
    assert error.body == "Unauthorized"


def test_api_error_requires_keyword_arguments():
    with pytest.raises(TypeError):
        APIError("HTTP 401", 401)


def test_query_error_defaults_to_empty_errors():
    assert QueryError("boom").errors == []


def test_not_found_can_be_caught_as_query_error():
    raw = [{"message": "Book 'XYZ' not found"}]

    with pytest.raises(QueryError) as exc_info:
        raise NotFoundError("Book 'XYZ' not found", errors=raw)

    assert exc_info.value.errors == raw


def test_server_error_keeps_status():
    error = ServerError("HTTP 503", status=503)

    assert error.status == 503
    assert isinstance(error, APIError)


def test_rate_limit_error_caught_as_api_error():
    with pytest.raises(APIError) as exc_info:
        raise RateLimitError("HTTP 429", status=429)

    assert exc_info.value.status == 429
