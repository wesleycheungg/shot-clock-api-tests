import copy
import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from espn_tests.client import ESPNClient

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def live_board() -> dict:
    """A fresh deep copy each test, so mutations never leak between tests."""
    return copy.deepcopy(load_fixture("scoreboard_live.json"))


@pytest.fixture
def live_board_later() -> dict:
    return load_fixture("scoreboard_live_later.json")


@pytest.fixture(scope="session")
def schema_validator() -> Draft202012Validator:
    schema = json.loads((ROOT / "schemas" / "scoreboard.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.fixture(scope="session")
def client() -> ESPNClient:
    return ESPNClient(timeout=float(os.getenv("ESPN_TIMEOUT", "5")))


@pytest.fixture(scope="session")
def live_scoreboard(client):
    """One real call shared by every live test in the session."""
    return client.scoreboard()


class FakeClock:
    """Deterministic time: sleep() advances now() instantly."""

    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()
