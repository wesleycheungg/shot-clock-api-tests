"""Does bad data fail safely?"""
import pytest
import requests
import responses

from espn_tests.client import ESPNClient, ESPNError, ESPNHTTPError, ESPNPayloadError
from espn_tests.models import parse_scoreboard

pytestmark = pytest.mark.resilience

URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"


@pytest.fixture
def api():
    with responses.RequestsMock() as mock:
        yield mock


@pytest.fixture
def client():
    return ESPNClient(timeout=1, retries=2)


BAD_RESPONSES = {
    "empty response": (b"", "application/json"),
    "cut-off json": (b'{"events": [{"id": "4018', "application/json"),
    "html error page": (b"<html>Service Unavailable</html>", "text/html"),
    "list instead of object": (b"[]", "application/json"),
}


@pytest.mark.parametrize("body,content_type", BAD_RESPONSES.values(), ids=BAD_RESPONSES.keys())
def test_bad_response_raises_clear_error(api, client, body, content_type):
    api.add(responses.GET, URL, body=body, content_type=content_type)
    with pytest.raises(ESPNPayloadError):
        client.scoreboard()


def test_server_outage_retries_then_gives_up(api, client):
    for _ in range(3):
        api.add(responses.GET, URL, status=503)
    with pytest.raises(ESPNHTTPError):
        client.scoreboard()
    assert len(api.calls) == 3  # first try + 2 retries


def test_brief_outage_recovers_on_retry(api, client):
    api.add(responses.GET, URL, status=502)
    api.add(responses.GET, URL, json={"events": []})
    assert client.scoreboard().data == {"events": []}


def test_timeout_raises_clear_error(api, client):
    api.add(responses.GET, URL, body=requests.Timeout())
    with pytest.raises(ESPNError, match="Timed out"):
        client.scoreboard()


def _first_team(event):
    return event["competitions"][0]["competitors"][0]


CORRUPTED_GAMES = {
    "score missing": lambda e: _first_team(e).update(score=None),
    "team missing": lambda e: _first_team(e).pop("team"),
    "status missing": lambda e: e.pop("status"),
}


@pytest.mark.parametrize("corrupt", CORRUPTED_GAMES.values(), ids=CORRUPTED_GAMES.keys())
def test_one_bad_game_does_not_break_the_rest(live_board, corrupt):
    corrupt(live_board["events"][0])
    result = parse_scoreboard(live_board)
    assert [index for index, _ in result.skipped] == [0]  # bad game reported
    assert len(result.scoreboard.events) == 2  # other games still load
