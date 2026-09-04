"""Ask the other two PIHTI services how they are, from this machine's side.

The browser never talks to a neighbour: it would need cross-origin reads on
every service and each address would have to travel into the page. This
server asks each neighbour itself over a two-second timeout and remembers
the answer for ten seconds. The design and the five states are ControlUnit's
(`controlunit/web/neighbours.py`), kept identical so the three tabs agree.

Addresses come only from machine-local configuration: the ``NEIGHBOURS`` key
of the settings file in the data root (``{"pihti-log": "http://host:4310",
"controlunit": "http://host:4187"}``), or the ``PIHTI_NEIGHBOURS`` environment
variable holding the same JSON object. The repository carries no address.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request

TIMEOUT_SECONDS = 2.0
CACHE_SECONDS = 10.0
HEALTH_PATH = "/api/health"

SELF_ALIAS = "pihti-diagram"
#: The two neighbours, in the order the page shows them after this service.
NEIGHBOUR_ALIASES = ("pihti-log", "controlunit")

DISPLAY_NAMES = {
    "pihti-diagram": "PIHTI diagram",
    "pihti-log": "PIHTI Log",
    "controlunit": "ControlUnit",
}

#: Five states, never conflated. ``down`` means something at the address
#: answered and said so (or refused); ``unreachable`` means nothing answered
#: from this machine at all; ``not configured`` means this machine was never
#: told where the service lives.
STATE_OK = "ok"
STATE_DEGRADED = "degraded"
STATE_DOWN = "down"
STATE_UNREACHABLE = "unreachable"
STATE_NOT_CONFIGURED = "not configured"


def read_addresses(settings: dict | None) -> dict[str, str]:
    """Alias -> address from the settings mapping, then the environment."""
    block = (settings or {}).get("NEIGHBOURS") if isinstance(settings, dict) else None
    if env_value := os.environ.get("PIHTI_NEIGHBOURS"):
        try:
            block = json.loads(env_value)
        except json.JSONDecodeError:
            block = None
    if not isinstance(block, dict):
        return {}
    addresses: dict[str, str] = {}
    for alias, value in block.items():
        url = value.get("url") if isinstance(value, dict) else value
        if isinstance(url, str) and url.strip():
            addresses[str(alias).strip()] = url.strip().rstrip("/")
    return addresses


def read_health(url: str, timeout: float = TIMEOUT_SECONDS) -> tuple[str, str, str]:
    """Fetch one neighbour's health report: ``(state, version, detail)``."""
    target = url.rstrip("/") + HEALTH_PATH
    try:
        with urllib.request.urlopen(target, timeout=timeout) as response:
            payload = response.read(64 * 1024)
    except urllib.error.HTTPError as error:
        return STATE_DOWN, "", f"answered with an error, code {getattr(error, 'code', '?')}"
    except urllib.error.URLError as error:
        reason = getattr(error, "reason", None)
        if isinstance(reason, ConnectionRefusedError):
            return STATE_DOWN, "", "the machine answered, but nothing listens at that port"
        return STATE_UNREACHABLE, "", "no answer within two seconds"
    except Exception:
        return STATE_UNREACHABLE, "", "no answer within two seconds"
    try:
        report = json.loads(payload.decode("utf-8"))
    except Exception:
        report = None
    if not isinstance(report, dict):
        return STATE_DEGRADED, "", "answered, but not with a health report"
    reported = str(report.get("status") or "").strip().lower()
    version = str(report.get("version") or "")
    detail = str(report.get("detail") or "")
    if not detail and "active_session" in report:
        # PIHTI Log's report carries facts instead of a sentence.
        detail = "a session is open" if report.get("active_session") else "no session open"
    if reported in (STATE_OK, STATE_DEGRADED, STATE_DOWN):
        return reported, version, detail
    return STATE_DEGRADED, version, detail or "answered, but not with a health report"


class NeighbourBoard:
    """The two neighbours' states, refreshed no more than once every ten seconds."""

    def __init__(self, addresses, cache_seconds: float = CACHE_SECONDS, probe=read_health, clock=time.monotonic):
        self._addresses = addresses  # callable returning alias -> url
        self._cache_seconds = cache_seconds
        self._probe = probe
        self._clock = clock
        self._lock = threading.RLock()
        self._cached: list[dict] | None = None
        self._cached_at: float | None = None

    def _probe_all(self) -> list[dict]:
        addresses = self._addresses()
        rows = []
        for alias in NEIGHBOUR_ALIASES:
            url = addresses.get(alias, "")
            if not url:
                rows.append(
                    {"alias": alias, "name": DISPLAY_NAMES[alias], "url": "",
                     "state": STATE_NOT_CONFIGURED, "version": "", "detail": ""}
                )
                continue
            state, version, detail = self._probe(url)
            rows.append(
                {"alias": alias, "name": DISPLAY_NAMES[alias], "url": url,
                 "state": state, "version": version, "detail": detail}
            )
        return rows

    def neighbours(self) -> list[dict]:
        now = self._clock()
        with self._lock:
            fresh = (
                self._cached is not None
                and self._cached_at is not None
                and (now - self._cached_at) < self._cache_seconds
            )
            if fresh:
                return [dict(row) for row in self._cached]
        rows = self._probe_all()
        with self._lock:
            self._cached = rows
            self._cached_at = self._clock()
        return [dict(row) for row in rows]

    def forget(self) -> None:
        with self._lock:
            self._cached = None
            self._cached_at = None
