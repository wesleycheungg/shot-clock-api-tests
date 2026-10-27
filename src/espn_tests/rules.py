"""Business rules a schema can't express: cross-field consistency of a game."""
from __future__ import annotations

from .models import Event, Scoreboard

MAX_REGULATION_CLOCK = 720.0  # 12-minute NBA quarter
MAX_PERIOD = 10  # 4 quarters + 6 overtimes is already historic
# Games that end in state "post" without being played to a result.
NOT_PLAYED = {"STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_SUSPENDED", "STATUS_FORFEIT"}


def event_violations(e: Event) -> list[str]:
    v: list[str] = []
    comp = e.competition
    sides = sorted(c.homeAway for c in comp.competitors)
    if sides != ["away", "home"]:
        v.append(f"expected one home and one away team, got {sides}")
    if comp.competitors[0].team.id == comp.competitors[1].team.id:
        v.append("a team is playing itself")

    st = e.status
    state = st.type.state
    scores = [c.score for c in comp.competitors]

    if st.period > MAX_PERIOD:
        v.append(f"period {st.period} exceeds {MAX_PERIOD}")
    if st.clock > MAX_REGULATION_CLOCK:
        v.append(f"clock {st.clock}s exceeds a 12-minute period")

    if state == "pre":
        if any(scores):
            v.append(f"pre-game event has non-zero score {scores}")
        if st.type.completed:
            v.append("pre-game event marked completed")
    elif state == "in":
        if st.type.completed:
            v.append("in-progress event marked completed")
        if st.period < 1:
            v.append("in-progress event has period < 1")
    elif state == "post" and st.type.name in NOT_PLAYED:
        pass  # no winner or completed flag expected
    elif state == "post":
        if not st.type.completed:
            v.append("final event not marked completed")
        winners = [c for c in comp.competitors if c.winner]
        if len(winners) != 1:
            v.append(f"final event should have exactly one winner, got {len(winners)}")
        elif winners[0].score != max(scores):
            v.append("winner flag is on the team with the lower score")
        if scores[0] == scores[1]:
            v.append("final NBA game cannot end tied")
    return v


def scoreboard_violations(sb: Scoreboard) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    ids = [e.id for e in sb.events]
    dupes = {i for i in ids if ids.count(i) > 1}
    for e in sb.events:
        problems = event_violations(e)
        if e.id in dupes:
            problems.append("duplicate event id")
        if problems:
            out[e.id] = problems
    return out
