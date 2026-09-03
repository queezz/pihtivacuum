from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash

from pihti import __version__
from pihti.server import _load_or_create_session_secret, create_app


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def app(tmp_path):
    key = Fernet.generate_key()
    key_file = tmp_path / "users.key"
    key_file.write_bytes(key)
    users_file = tmp_path / "users.json.enc"
    users_file.write_bytes(
        Fernet(key).encrypt(
            json.dumps({"operator": generate_password_hash("correct horse")}).encode()
        )
    )
    state_file = tmp_path / "elements_state.json"
    state_file.write_text("{}", encoding="utf-8")
    log_file = tmp_path / "logs.csv"
    log_file.write_text("timestamp,id,status,user\n", encoding="utf-8")
    control_data = tmp_path / "control-data"
    control_data.mkdir()
    (control_data / "cu_20260101_120000.csv").write_text("sample", encoding="utf-8")

    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "STATE_FILE": state_file,
            "LOG_FILE": log_file,
            "LAST_PLOT_FILE": tmp_path / "last_plot.html",
            "USERS_FILE_ENCRYPTED": users_file,
            "USERS_KEY_FILE": key_file,
            "CUDATA_DIRECTORY": str(control_data),
        }
    )


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client):
    return client.post("/login", data={"username": "operator", "password": "correct horse"})


def test_release_version_is_single_sourced_and_visible(client):
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == __version__ == "0.2.0"
    assert client.get("/version").json == {"name": "pihti", "version": "0.2.0"}
    assert b"v0.2.0" in client.get("/").data


def test_session_signing_key_is_machine_private_and_persistent(monkeypatch, tmp_path):
    key_file = tmp_path / "session.key"
    monkeypatch.delenv("PIHTI_SESSION_SECRET", raising=False)
    monkeypatch.setenv("PIHTI_SESSION_KEY_FILE", str(key_file))
    first = _load_or_create_session_secret()
    second = _load_or_create_session_secret()
    assert first == second
    assert len(first) == 32
    assert key_file.read_bytes() == first


def test_public_diagram_has_security_headers_and_accessible_navigation(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert b'aria-controls="navbarItems"' in response.data
    assert b'onclick="toggleNavbar()"' not in response.data


def test_history_is_restored_and_requires_login(client):
    assert client.get("/history").status_code == 302
    assert client.get("/history/events").status_code == 401
    assert login(client).status_code == 200
    response = client.get("/history")
    assert response.status_code == 200
    assert b"calendar-grid" in response.data
    assert b"history-timeline-content" in response.data
    assert b"diagram-container" in response.data


def test_sensitive_data_views_require_login(client):
    assert client.get("/plasmaplots").status_code == 302
    assert client.get("/download_logs").status_code == 401
    assert client.get("/download_controlunit_csv?file=cu_20260101_120000.csv").status_code == 401


def test_missing_plot_folder_has_friendly_notice(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "STATE_FILE": tmp_path / "state.json",
            "LOG_FILE": tmp_path / "logs.csv",
            "USERS_FILE_ENCRYPTED": tmp_path / "users.json.enc",
            "USERS_KEY_FILE": tmp_path / "users.key",
            "CUDATA_DIRECTORY": None,
            "SETTINGS_FILE": tmp_path / "missing-settings.json",
        }
    )
    client = app.test_client()
    with client.session_transaction() as session:
        session["username"] = "operator"
    response = client.get("/plasmaplots")
    assert response.status_code == 200
    assert b"No data directory configured" in response.data
    assert b'id="fileForm"' not in response.data
    assert b"cdn.plot.ly" not in response.data
    assert b"code.jquery.com" not in response.data


def test_login_and_state_update_validate_known_elements(client):
    assert login(client).status_code == 200
    assert client.post("/update", json={"id": "TMPU", "status": "active"}).status_code == 200
    assert client.post("/update", json={"id": "not-an-element", "status": "active"}).status_code == 400
    assert client.post("/update", json={"id": "TMPU", "status": "broken"}).status_code == 400


def test_cross_origin_write_is_rejected(client):
    response = client.post(
        "/login",
        data={"username": "operator", "password": "correct horse"},
        headers={"Origin": "https://attacker.invalid"},
    )
    assert response.status_code == 403


def test_control_data_download_rejects_path_traversal(client):
    login(client)
    assert client.get("/download_controlunit_csv?file=../users.json.enc").status_code == 404
    response = client.get("/download_controlunit_csv?file=cu_20260101_120000.csv")
    assert response.status_code == 200
    assert response.data == b"sample"


def test_login_decrypts_users_in_memory(client, tmp_path):
    assert login(client).status_code == 200
    assert not (tmp_path / "users.json").exists()
