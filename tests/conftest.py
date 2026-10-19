import json

import httpx
import pytest
import respx

from bibleql import Client

API_URL = "https://bibleql.test/graphql"


@pytest.fixture(autouse=True)
def api():
    """Mock all HTTP: an unmocked request fails the test instead of reaching the network."""
    with respx.mock(assert_all_called=False) as router:
        yield router


@pytest.fixture
def client():
    with Client(api_key="test-key", api_url=API_URL) as c:
        yield c


@pytest.fixture
def mock_graphql(api):
    """Make the API answer with ``{"data": data}``. Returns the respx route to inspect calls."""

    def _mock(data, *, status=200):
        return api.post(API_URL).mock(return_value=httpx.Response(status, json={"data": data}))

    return _mock


def sent_body(route, call=-1):
    """The JSON body of a request a route received (the last one by default)."""
    return json.loads(route.calls[call].request.content)
