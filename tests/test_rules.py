"""Does the data make sense?"""
import pytest

from espn_tests.models import parse_scoreboard
from espn_tests.rules import scoreboard_violations

pytestmark = pytest.mark.rules


def violations(board):
    return scoreboard_violations(parse_scoreboard(board).scoreboard)


def teams(board, game):
    return board["events"][game]["competitions"][0]["competitors"]


def test_sample_data_has_no_problems(live_board):
    assert violations(live_board) == {}


def test_points_before_tipoff_are_flagged(live_board):
    teams(live_board, 2)[0]["score"] = "7"  # game 2 hasn't started
    assert "401810003" in violations(live_board)


def test_tied_final_is_flagged(live_board):
    for team in teams(live_board, 1):  # game 1 is final
        team["score"] = "100"
    assert "final NBA game cannot end tied" in violations(live_board)["401810002"]


def test_winner_with_fewer_points_is_flagged(live_board):
    home, away = teams(live_board, 1)
    home["winner"], away["winner"] = True, False  # NY 104 marked as beating BOS 112
    assert "winner flag is on the team with the lower score" in violations(live_board)["401810002"]


@pytest.mark.live
def test_live_api_data_makes_sense(live_scoreboard):
    assert violations(live_scoreboard.data) == {}
