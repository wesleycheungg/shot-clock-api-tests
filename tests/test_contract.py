"""Is the data shaped correctly?"""
import pytest

from espn_tests.models import parse_scoreboard

pytestmark = pytest.mark.contract


def errors(validator, data):
    return list(validator.iter_errors(data))


def test_scoreboard_matches_schema(schema_validator, live_board):
    assert errors(schema_validator, live_board) == []


def test_scoreboard_parses_into_typed_models(live_board):
    result = parse_scoreboard(live_board)
    assert result.ok
    game = result.scoreboard.events[0]
    assert game.side("home").team.abbreviation == "GS"
    assert game.side("home").score == 58  # ESPN sends "58" as a string


def test_empty_slate_is_valid(schema_validator):
    """Days with no games return an empty list, which is not an error."""
    assert errors(schema_validator, {"events": []}) == []


def _home(board):
    return board["events"][0]["competitions"][0]["competitors"][0]


BREAKING_CHANGES = {
    "missing game id": lambda b: b["events"][0].pop("id"),
    "score is not a number": lambda b: _home(b).update(score="fifty"),
    "unknown game state": lambda b: b["events"][0]["status"]["type"].update(state="live"),
    "only one team": lambda b: b["events"][0]["competitions"][0]["competitors"].pop(),
}


@pytest.mark.parametrize("change", BREAKING_CHANGES.values(), ids=BREAKING_CHANGES.keys())
def test_schema_catches_breaking_change(schema_validator, live_board, change):
    change(live_board)
    assert errors(schema_validator, live_board)


@pytest.mark.live
def test_live_api_matches_schema(schema_validator, live_scoreboard):
    assert live_scoreboard.status == 200
    found = errors(schema_validator, live_scoreboard.data)
    assert not found, [f"{list(e.path)}: {e.message}" for e in found[:5]]
