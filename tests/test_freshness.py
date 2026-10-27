"""Are live scores updating on time?

Offline tests use a fake clock, so timing checks run instantly and never flake.
"""
import copy
import os

import pytest

from espn_tests.freshness import FreshnessMonitor, StaleDataError
from espn_tests.models import parse_scoreboard

pytestmark = pytest.mark.freshness

GAME = "401810001"
SLA = float(os.getenv("LIVE_UPDATE_SLA_SECONDS", "60"))
INTERVAL = float(os.getenv("POLL_INTERVAL_SECONDS", "5"))


def feed(*payloads):
    """Returns each payload in turn, then keeps returning the last one."""
    queue = list(payloads)
    return lambda: queue.pop(0) if len(queue) > 1 else queue[0]


def test_score_update_is_detected(fake_clock, live_board, live_board_later):
    monitor = FreshnessMonitor(feed(live_board, live_board_later), fake_clock, fake_clock.sleep)
    result = monitor.time_to_change(GAME, sla_seconds=SLA, interval=INTERVAL)
    assert (result.before.home, result.after.home) == (58, 61)


def test_frozen_feed_fails(fake_clock, live_board):
    monitor = FreshnessMonitor(feed(live_board), fake_clock, fake_clock.sleep)
    with pytest.raises(StaleDataError):
        monitor.time_to_change(GAME, sla_seconds=60, interval=10)


def test_score_going_backwards_fails(fake_clock, live_board, live_board_later):
    rollback = copy.deepcopy(live_board)
    rollback["events"][0]["competitions"][0]["competitors"][0]["score"] = "50"
    monitor = FreshnessMonitor(feed(live_board, live_board_later, rollback), fake_clock, fake_clock.sleep)
    with pytest.raises(AssertionError, match="went backwards"):
        monitor.assert_monotonic(GAME, polls=3, interval=INTERVAL)


# ---------- live API ----------

def _game_in_play(client):
    for e in parse_scoreboard(client.scoreboard().data).scoreboard.events:
        if e.status.type.state == "in" and "halftime" not in (e.status.type.detail or "").lower():
            return e
    pytest.skip("no NBA game in play right now")


@pytest.mark.live
def test_live_game_updates_on_time(client):
    game = _game_in_play(client)
    result = FreshnessMonitor(lambda: client.scoreboard().data).time_to_change(
        game.id, sla_seconds=SLA, interval=INTERVAL)
    print(f"\n{game.shortName} updated after {result.seconds_to_change:.0f}s")


@pytest.mark.live
def test_live_scores_never_go_backwards(client):
    game = _game_in_play(client)
    FreshnessMonitor(lambda: client.scoreboard().data).assert_monotonic(game.id, polls=6, interval=INTERVAL)
