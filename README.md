# 🏀 Shot Clock API Tests

![Tests](https://github.com/wesleycheungg/shot-clock-api-tests/actions/workflows/api-tests.yml/badge.svg)

**An automated test suite that checks whether live NBA score data is correct, on time, and safe to use.**

Sports apps live and die by their data feeds. If a score is wrong, late, or broken, fans notice right away. Shot Clock tests ESPN's public NBA scoreboard API the way a QA team would test a production feed.

## What it checks

| | Question | Example |
|---|---|---|
| ✅ | **Is the data shaped correctly?** | Every game has two teams, numeric scores, and a valid status |
| 🧠 | **Does the data make sense?** | No tied finals, no points before tip-off, winner has the higher score |
| ⏱️ | **Are live scores updating on time?** | A game in progress must update within 60 seconds, and scores never go backwards |
| 🛡️ | **Does bad data fail safely?** | Empty responses, broken JSON, outages and timeouts are handled cleanly, and one corrupted game doesn't break the rest |

**28 tests**: 24 run offline in under a second, and 4 run against the live ESPN API during real games.

## Built with

Python · pytest · Requests · JSON Schema · Pydantic · GitHub Actions

## Run it

```bash
pip install -r requirements.txt
pytest              # offline tests
pytest -m live -s   # live tests (best during an NBA game)
```

GitHub Actions runs the offline tests on every push and the live tests automatically during evening game hours.

## Related

- [K6 performance suite](https://github.com/wesleycheungg) for the same API: Shot Clock checks that the data is **correct**, K6 checks that it's **fast**.
- [Design notes](docs/DESIGN.md) for the technical decisions behind the suite.

---

Built by [Wesley Cheung](https://wesleycheungg.github.io/portfolio/), SDET and frontend engineer.
