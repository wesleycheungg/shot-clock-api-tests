"""Typed models for the scoreboard payload, plus a lenient parser.

The parser never lets one bad event take down the whole scoreboard: malformed
events are skipped and reported, so a UI built on this could still render the
games that are fine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .client import ESPNPayloadError


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Team(_Base):
    id: str
    abbreviation: str = Field(min_length=1)
    displayName: str = Field(min_length=1)


class Competitor(_Base):
    id: str
    homeAway: Literal["home", "away"]
    score: int = Field(ge=0)
    winner: bool | None = None
    team: Team

    @field_validator("score", mode="before")
    @classmethod
    def score_from_string(cls, v: Any) -> Any:
        # ESPN sends scores as strings ("102"); reject anything non-numeric.
        if isinstance(v, str):
            if not v.strip().isdigit():
                raise ValueError(f"score is not a non-negative integer: {v!r}")
            return int(v)
        if isinstance(v, bool):
            raise ValueError("score must not be a boolean")
        return v


class StatusType(_Base):
    id: str
    name: str
    state: Literal["pre", "in", "post"]
    completed: bool
    detail: str | None = None
    shortDetail: str | None = None


class Status(_Base):
    clock: float = Field(ge=0)
    displayClock: str
    period: int = Field(ge=0)
    type: StatusType


class Competition(_Base):
    id: str
    competitors: list[Competitor] = Field(min_length=2, max_length=2)
    status: Status | None = None


class Event(_Base):
    id: str
    date: str
    name: str
    shortName: str
    competitions: list[Competition] = Field(min_length=1)
    status: Status

    @property
    def competition(self) -> Competition:
        return self.competitions[0]

    def side(self, home_away: str) -> Competitor:
        return next(c for c in self.competition.competitors if c.homeAway == home_away)


class Scoreboard(_Base):
    events: list[Event]


@dataclass
class ParseResult:
    scoreboard: Scoreboard
    skipped: list[tuple[int, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.skipped


def parse_scoreboard(data: Any) -> ParseResult:
    """Parse a raw scoreboard dict, isolating malformed events."""
    if not isinstance(data, dict):
        raise ESPNPayloadError(f"Scoreboard must be an object, got {type(data).__name__}")
    raw_events = data.get("events")
    if raw_events is None:
        raise ESPNPayloadError("Scoreboard has no 'events' key")
    if not isinstance(raw_events, list):
        raise ESPNPayloadError(f"'events' must be a list, got {type(raw_events).__name__}")

    events: list[Event] = []
    skipped: list[tuple[int, str]] = []
    for i, raw in enumerate(raw_events):
        try:
            events.append(Event.model_validate(raw))
        except ValidationError as exc:
            first = exc.errors()[0]
            loc = ".".join(str(p) for p in first["loc"])
            skipped.append((i, f"{loc}: {first['msg']}"))
    return ParseResult(Scoreboard(events=events), skipped)
