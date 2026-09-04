"""Operator roster: plain account names, attribution only.

The roster is a JSON list of names in the application's data root. It travels
with the other runtime data (state, logs) and never carries a password, a hash,
or a key. The encrypted legacy registry remains a fallback for deployments
that still hold its Fernet key.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


def default_private_dir() -> Path:
    if local_app_data := os.environ.get("LOCALAPPDATA"):
        return Path(local_app_data) / "pihti-diagram"
    return Path.home() / ".config" / "pihti-diagram"


def env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else default


def data_root() -> Path:
    return env_path("PIHTI_DATA_ROOT", Path.cwd()).resolve()


def roster_path(root: Path | None = None) -> Path:
    return env_path("PIHTI_OPERATORS_FILE", (root or data_root()) / "operators.json")


def normalize_names(names) -> list[str]:
    seen: dict[str, str] = {}
    for name in names:
        if not isinstance(name, str):
            continue
        cleaned = " ".join(name.split())
        if cleaned and cleaned.casefold() not in seen:
            seen[cleaned.casefold()] = cleaned
    return sorted(seen.values(), key=str.casefold)


def read_roster(path: Path) -> list[str] | None:
    """Return the roster names, or ``None`` when no roster file exists."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("The operator roster file could not be read.") from exc
    if isinstance(payload, dict):
        payload = payload.get("operators", [])
    if not isinstance(payload, list):
        raise RuntimeError("The operator roster must be a JSON list of names.")
    return normalize_names(payload)


def write_roster(path: Path, names) -> list[str]:
    names = normalize_names(names)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"operators": names}, indent=4) + "\n", encoding="utf-8")
    return names


def legacy_names(users_file: Path, key_file: Path) -> list[str]:
    """Account names from the encrypted legacy registry. Values are ignored."""
    inline_key = os.environ.get("PIHTI_USERS_KEY")
    key = inline_key.encode("ascii") if inline_key else key_file.read_bytes().strip()
    encrypted = users_file.read_bytes()
    try:
        users = json.loads(Fernet(key).decrypt(encrypted).decode("utf-8"))
    except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("The encrypted users file or its key is invalid.") from exc
    if not isinstance(users, dict) or not all(isinstance(name, str) for name in users):
        raise RuntimeError("The encrypted users file has an invalid structure.")
    return normalize_names(users)


def history_names(log_file: Path) -> list[str]:
    """Operators who appear in the diagram history log."""
    try:
        with log_file.open("r", newline="", encoding="utf-8") as csvfile:
            return normalize_names(row.get("user", "") for row in csv.DictReader(csvfile))
    except FileNotFoundError:
        return []


def resolve_operators(roster_file: Path, users_file: Path, key_file: Path) -> tuple[list[str], str]:
    """Return ``(names, source)`` where source is ``roster``, ``legacy`` or ``missing``."""
    names = read_roster(roster_file)
    if names is not None:
        return names, "roster"
    try:
        return legacy_names(users_file, key_file), "legacy"
    except (FileNotFoundError, RuntimeError):
        return [], "missing"
