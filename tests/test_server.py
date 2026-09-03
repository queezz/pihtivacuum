from __future__ import annotations

import json
import tomllib
import xml.etree.ElementTree as ET
from datetime import timedelta
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from pihti import __version__
from pihti.server import _load_or_create_session_secret, create_app


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def app(tmp_path):
    key = Fernet.generate_key()
    key_file = tmp_path / "users.key"
    key_file.write_bytes(key)
    users_file = tmp_path / "users.json.enc"
    users_file.write_bytes(Fernet(key).encrypt(json.dumps({"operator": "legacy-value"}).encode()))
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
            "OPERATION_CONTEXT_FILE": tmp_path / "operation_context.json",
            "OPERATION_CONTEXT_LOG_FILE": tmp_path / "operation_context_log.csv",
            "LAST_PLOT_FILE": tmp_path / "last_plot.html",
            "USERS_FILE_ENCRYPTED": users_file,
            "USERS_KEY_FILE": key_file,
            "CUDATA_DIRECTORY": str(control_data),
        }
    )


@pytest.fixture()
def client(app):
    return app.test_client()


def identify(client):
    return client.post("/api/identify", json={"username": "operator"})


def test_release_version_is_single_sourced_and_visible(client):
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == __version__ == "0.3.0"
    assert client.get("/version").json == {"name": "pihti", "version": "0.3.0"}
    assert b"v0.3.0" in client.get("/").data


def test_session_signing_key_is_machine_private_and_persistent(monkeypatch, tmp_path):
    key_file = tmp_path / "session.key"
    monkeypatch.delenv("PIHTI_SESSION_SECRET", raising=False)
    monkeypatch.setenv("PIHTI_SESSION_KEY_FILE", str(key_file))
    first = _load_or_create_session_secret()
    second = _load_or_create_session_secret()
    assert first == second
    assert len(first) == 32
    assert key_file.read_bytes() == first


def test_public_diagram_has_guide_rails_and_security_headers(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert b'id="guide-controls"' in response.data
    assert b'id="guide-steps"' in response.data
    assert b"Prototype diagram guidance only" in response.data
    assert b'aria-controls="navbarItems"' in response.data


def test_operator_selection_is_attribution_without_password(client, app):
    page = client.get("/identify")
    assert page.status_code == 200
    assert b'value="operator"' in page.data
    assert b'type="password"' not in page.data
    assert b"It does not control access" in page.data
    response = identify(client)
    assert response.status_code == 200
    assert response.json["status"] == "accepted"
    assert app.config["PERMANENT_SESSION_LIFETIME"] == timedelta(hours=12)
    with client.session_transaction() as browser_session:
        assert browser_session.permanent
        assert browser_session["username"] == "operator"
        assert browser_session["last_activity"]


def test_read_only_history_plots_and_downloads_are_public(client):
    history = client.get("/history")
    assert history.status_code == 200
    assert b"calendar-grid" in history.data
    assert client.get("/history/events").status_code == 200
    assert client.get("/plasmaplots").status_code == 200
    assert client.get("/download_logs").status_code == 200
    assert client.get("/download_controlunit_csv?file=cu_20260101_120000.csv").status_code == 200


def test_diagram_writes_require_operator_and_validate_known_elements(client):
    assert client.post("/update", json={"id": "TMPU", "status": "active"}).status_code == 428
    assert identify(client).status_code == 200
    response = client.post("/update", json={"id": "TMPU", "status": "active"})
    assert response.status_code == 200
    assert response.headers.get("Set-Cookie")
    assert client.post("/update", json={"id": "not-an-element", "status": "active"}).status_code == 400
    assert client.post("/update", json={"id": "TMPU", "status": "broken"}).status_code == 400


def test_passive_poll_does_not_extend_operator_selection(client):
    identify(client)
    response = client.get("/elements-state")
    assert response.status_code == 200
    assert response.headers.get("Set-Cookie") is None


def test_line_configuration_is_attributed_and_persistent(client, app):
    assert client.get("/operation-context").json["line_mode"] == "unknown"
    assert client.post("/operation-context", json={"line_mode": "membrane"}).status_code == 428
    identify(client)
    response = client.post("/operation-context", json={"line_mode": "boron"})
    assert response.status_code == 200
    assert response.json["line_mode"] == "boron"
    assert response.json["updated_by"] == "operator"
    saved = json.loads(Path(app.config["OPERATION_CONTEXT_FILE"]).read_text(encoding="utf-8"))
    assert saved["line_mode"] == "boron"
    assert "operator" in Path(app.config["OPERATION_CONTEXT_LOG_FILE"]).read_text(encoding="utf-8")
    assert client.post("/operation-context", json={"line_mode": "unsafe"}).status_code == 400


def test_operation_guide_targets_exist_and_manual_boundary_is_explicit(client):
    guides = client.get("/operation-guides").json
    assert guides["prototype"] is True
    svg_root = ET.parse(PROJECT_ROOT / "src" / "pihti" / "static" / "diagram.svg").getroot()
    svg_ids = {element.get("id") for element in svg_root.iter() if element.get("id")}
    for guide in guides["guides"]:
        assert guide["steps"][-1]["manual"] is True
        assert all(step["targetId"] in svg_ids for step in guide["steps"])


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
    response = app.test_client().get("/plasmaplots")
    assert response.status_code == 200
    assert b"No data directory configured" in response.data
    assert b'id="fileForm"' not in response.data
    assert b"cdn.plot.ly" not in response.data
    assert b"code.jquery.com" not in response.data
    assert app.test_client().get("/get_last_plot").status_code == 200


def test_cross_origin_write_is_rejected(client):
    response = client.post(
        "/api/identify",
        json={"username": "operator"},
        headers={"Origin": "https://attacker.invalid"},
    )
    assert response.status_code == 403


def test_control_data_download_rejects_path_traversal(client):
    assert client.get("/download_controlunit_csv?file=../users.json.enc").status_code == 404
    response = client.get("/download_controlunit_csv?file=cu_20260101_120000.csv")
    assert response.status_code == 200
    assert response.data == b"sample"


def test_operator_registry_is_decrypted_in_memory(client, tmp_path):
    assert identify(client).status_code == 200
    assert not (tmp_path / "users.json").exists()
