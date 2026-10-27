"""Measure how quickly a live game's data changes between polls.

The clock and sleep functions are injectable, so the same logic is tested
offline with a fake clock and run for real against the live API.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from .models import Event, parse_scoreboard


class StaleDataError(AssertionError):
    pass


@dataclass(frozen=True)
class Snapshot:
    home: int
    away: int
    period: int
    clock: float
    state: str

    @classmethod
    def of(cls, e: Event) -> "Snapshot":
        return cls(
            home=e.side("home").score,
            away=e.side("away").score,
            period=e.status.period,
            clock=e.status.clock,
            state=e.status.type.state,
        )


@dataclass
class FreshnessResult:
    event_id: str
    seconds_to_change: float
    polls: int
    before: Snapshot
    after: Snapshot


class FreshnessMonitor:
    def __init__(
        self,
        fetch: Callable[[], dict],
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.fetch = fetch
        self.clock = clock
        self.sleep = sleep

    def _snapshot(self, event_id: str) -> Snapshot:
        events = {e.id: e for e in parse_scoreboard(self.fetch()).scoreboard.events}
        if event_id not in events:
            raise StaleDataError(f"event {event_id} disappeared from the scoreboard")
        return Snapshot.of(events[event_id])

    def time_to_change(self, event_id: str, sla_seconds: float, interval: float = 5.0) -> FreshnessResult:
        """Poll until the event's score/clock/period changes. Raise if it takes longer than the SLA."""
        start = self.clock()
        first = self._snapshot(event_id)
        polls = 1
        while True:
            self.sleep(interval)
            current = self._snapshot(event_id)
            polls += 1
            elapsed = self.clock() - start
            if current != first:
                return FreshnessResult(event_id, elapsed, polls, first, current)
            if elapsed >= sla_seconds:
                raise StaleDataError(
                    f"event {event_id} unchanged for {elapsed:.0f}s over {polls} polls "
                    f"(SLA {sla_seconds:.0f}s); last snapshot {current}"
                )

    def assert_monotonic(self, event_id: str, polls: int, interval: float = 5.0) -> list[Snapshot]:
        """Scores must never go down and the period must never go backwards between polls."""
        history = [self._snapshot(event_id)]
        for _ in range(polls - 1):
            self.sleep(interval)
            history.append(self._snapshot(event_id))
        for prev, cur in zip(history, history[1:]):
            if cur.home < prev.home or cur.away < prev.away:
                raise AssertionError(f"score went backwards: {prev} -> {cur}")
            if cur.period < prev.period:
                raise AssertionError(f"period went backwards: {prev} -> {cur}")
        return history
