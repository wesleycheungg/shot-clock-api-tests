# Design Notes

**Two layers of validation.** The JSON Schema (`schemas/scoreboard.schema.json`) is the language-neutral contract and could be shared with a frontend or another team. The pydantic models enforce the same shape in code and coerce ESPN's string scores (`"58"`) into integers. Rules that span fields, like "a final game has exactly one winner", live in `rules.py` because a schema can't express them.

**Open-world schema.** Extra fields are allowed. ESPN adds data all the time, and a contract test that fails on every addition gets muted. The suite tests that explicitly.

**Graceful degradation, not all-or-nothing.** `parse_scoreboard` skips a malformed event and reports why, while the valid games still parse. A scoreboard UI built on this would show nine good games instead of an error page because the tenth was corrupt.

**Deterministic timing tests.** `FreshnessMonitor` takes injectable `clock` and `sleep` functions. Offline tests drive it with a fake clock and scripted payloads, so "detects a frozen feed at exactly 60 seconds" runs in milliseconds with no flakiness. The live tests use the same class with the real clock.

**Typed errors at the boundary.** The client converts every failure into `ESPNHTTPError`, `ESPNPayloadError` or `ESPNError`, so callers handle three cases instead of a dozen library exceptions.

