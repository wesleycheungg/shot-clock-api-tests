"""Generate the offline fixtures in ESPN's scoreboard shape.

Run `python tests/fixtures/make_fixtures.py --record` to replace them with a
real capture from the live API instead.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent

TEAMS = {
    "LAL": ("13", "Los Angeles Lakers"),
    "GS": ("9", "Golden State Warriors"),
    "BOS": ("2", "Boston Celtics"),
    "NY": ("18", "New York Knicks"),
    "DEN": ("7", "Denver Nuggets"),
    "PHX": ("21", "Phoenix Suns"),
}

STATUS = {
    "pre": ("1", "STATUS_SCHEDULED", False, "Mon, October 26th at 7:30 PM EDT", "10/26 - 7:30 PM EDT"),
    "in": ("2", "STATUS_IN_PROGRESS", False, "5:12 - 2nd Quarter", "5:12 - 2nd"),
    "post": ("3", "STATUS_FINAL", True, "Final", "Final"),
}


def status(state, period=0, clock=720.0, display="12:00"):
    sid, name, completed, detail, short = STATUS[state]
    return {
        "clock": clock,
        "displayClock": display,
        "period": period,
        "type": {"id": sid, "name": name, "state": state, "completed": completed,
                 "description": name.title(), "detail": detail, "shortDetail": short},
    }


def competitor(abbr, home_away, score, winner=None):
    tid, name = TEAMS[abbr]
    c = {"id": tid, "homeAway": home_away, "score": str(score),
         "team": {"id": tid, "abbreviation": abbr, "displayName": name, "location": name.rsplit(" ", 1)[0]}}
    if winner is not None:
        c["winner"] = winner
    return c


def event(eid, away, home, st, away_score=0, home_score=0):
    winner_known = st["type"]["state"] == "post"
    a = competitor(away, "away", away_score, (away_score > home_score) if winner_known else None)
    h = competitor(home, "home", home_score, (home_score > away_score) if winner_known else None)
    return {
        "id": eid,
        "uid": f"s:40~l:46~e:{eid}",
        "date": "2026-10-26T23:30Z",
        "name": f"{TEAMS[away][1]} at {TEAMS[home][1]}",
        "shortName": f"{away} @ {home}",
        "season": {"year": 2027, "type": 2, "slug": "regular-season"},
        "competitions": [{"id": eid, "date": "2026-10-26T23:30Z", "attendance": 18064,
                          "competitors": [h, a], "status": st}],
        "status": st,
    }


def scoreboard(events):
    return {
        "leagues": [{"id": "46", "abbreviation": "NBA", "name": "National Basketball Association"}],
        "season": {"type": 2, "year": 2027},
        "day": {"date": "2026-10-26"},
        "events": events,
    }


def build():
    live = scoreboard([
        event("401810001", "LAL", "GS", status("in", 2, 312.0, "5:12"), 54, 58),
        event("401810002", "BOS", "NY", status("post", 4, 0.0, "0.0"), 112, 104),
        event("401810003", "DEN", "PHX", status("pre"), 0, 0),
    ])
    # A second poll of the same night: the live game has moved on.
    live_later = json.loads(json.dumps(live))
    later = status("in", 2, 268.0, "4:28")
    ev = live_later["events"][0]
    ev["status"] = ev["competitions"][0]["status"] = later
    ev["competitions"][0]["competitors"][0]["score"] = "61"  # GS (home) scores

    empty = scoreboard([])
    return {"scoreboard_live.json": live, "scoreboard_live_later.json": live_later,
            "scoreboard_empty.json": empty}


def record():
    import requests
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    data = requests.get(url, timeout=10).json()
    (HERE / "scoreboard_recorded.json").write_text(json.dumps(data, indent=2))
    print(f"recorded {len(data.get('events', []))} events -> scoreboard_recorded.json")


if __name__ == "__main__":
    if "--record" in sys.argv:
        record()
    else:
        for name, payload in build().items():
            (HERE / name).write_text(json.dumps(payload, indent=2))
            print("wrote", name)
