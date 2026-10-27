"""Thin HTTP client for ESPN's public site API.

Everything the tests need to observe (latency, headers, raw body) is exposed,
and every failure mode is turned into a typed exception instead of a crash.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"


class ESPNError(Exception):
    """Base class for all client errors."""


class ESPNHTTPError(ESPNError):
    def __init__(self, status: int, url: str):
        super().__init__(f"HTTP {status} from {url}")
        self.status = status


class ESPNPayloadError(ESPNError):
    """Response arrived but the body is unusable (empty, not JSON, wrong shape)."""


@dataclass
class APIResponse:
    url: str
    status: int
    headers: dict[str, str]
    elapsed_ms: float
    data: dict[str, Any]


class ESPNClient:
    def __init__(self, base_url: str = BASE_URL, timeout: float = 5.0, retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        retry = Retry(
            total=retries,
            backoff_factor=0.3,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            raise_on_status=False,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.headers["User-Agent"] = "shot-clock-api-tests/1.0 (portfolio project)"

    def scoreboard(self, sport: str = "basketball", league: str = "nba", dates: str | None = None) -> APIResponse:
        params = {"dates": dates} if dates else None
        return self.get(f"{sport}/{league}/scoreboard", params=params)

    def get(self, path: str, params: dict | None = None) -> APIResponse:
        url = f"{self.base_url}/{path.lstrip('/')}"
        start = time.perf_counter()
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
        except requests.Timeout as exc:
            raise ESPNError(f"Timed out after {self.timeout}s: {url}") from exc
        except requests.ConnectionError as exc:
            raise ESPNError(f"Connection failed: {url}") from exc
        elapsed_ms = (time.perf_counter() - start) * 1000

        if resp.status_code >= 400:
            raise ESPNHTTPError(resp.status_code, url)

        return APIResponse(
            url=resp.url,
            status=resp.status_code,
            headers=dict(resp.headers),
            elapsed_ms=elapsed_ms,
            data=decode_body(resp.content, resp.headers.get("Content-Type", "")),
        )


def decode_body(body: bytes, content_type: str = "application/json") -> dict[str, Any]:
    """Decode a response body, raising ESPNPayloadError for anything unusable."""
    if not body or not body.strip():
        raise ESPNPayloadError("Empty response body")
    if "json" not in content_type.lower():
        raise ESPNPayloadError(f"Unexpected Content-Type: {content_type!r}")
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ESPNPayloadError(f"Body is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ESPNPayloadError(f"Expected a JSON object, got {type(data).__name__}")
    return data
