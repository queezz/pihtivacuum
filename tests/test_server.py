from __future__ import annotations

import json
import tomllib
import xml.etree.ElementTree as ET
from datetime import timedelta
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from pihti import __version__
from pihti import roster
from pihti.cli import main as cli_main
from pihti.server import _load_or_create_session_secret, create_app


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def make_app(tmp_path, **overrides):
    state_file = tmp_path / "elements_state.json"
    if not state_file.exists():
        state_file.write_text("{}", encoding="utf-8")
    log_file = tmp_path / "logs.csv"
    if not log_file.exists():
        log_file.write_text("timestamp,id,status,user\n", encoding="utf-8")
    control_data = tmp_path / "control-data"
    control_data.mkdir(exist_ok=True)
    (control_data / "cu_20260101_120000.csv").write_text("sample", encoding="utf-8")
    config = {
        "TESTING": True,
        "SECRET_KEY": "test-only-secret",
        "STATE_FILE": state_file,
        "LOG_FILE": log_file,
        "OPERATION_CONTEXT_FILE": tmp_path / "operation_context.json",
        "OPERATION_CONTEXT_LOG_FILE": tmp_path / "operation_context_log.csv",
        "LAST_PLOT_FILE": tmp_path / "last_plot.html",
        "LAST_PLOT_META_FILE": tmp_path / "last_plot.json",
        "OPERATORS_FILE": tmp_path / "operators.json",
        "USERS_FILE_ENCRYPTED": tmp_path / "users.json.enc",
        "USERS_KEY_FILE": tmp_path / "users.key",
        "CUDATA_DIRECTORY": str(control_data),
    }
    config.update(overrides)
    return create_app(config)


@pytest.fixture()
def app(tmp_path):
    (tmp_path / "operators.json").write_text(
        json.dumps({"operators": ["operator", "Second Operator"]}), encoding="utf-8"
    )
    return make_app(tmp_path)


@pytest.fixture()
def client(app):
    return app.test_client()


def identify(client):
    return client.post("/api/identify", json={"username": "operator"})


def test_release_version_is_single_sourced_and_visible(client):
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == __version__ == "0.4.1"
    assert client.get("/version").json == {"name": "pihti", "version": "0.4.1"}
    assert b"v0.4.1" in client.get("/").data


def test_session_signing_key_is_machine_private_and_persistent(monkeypatch, tmp_path):
    key_file = tmp_path / "session.key"
    monkeypatch.delenv("PIHTI_SESSION_SECRET", raising=False)
    monkeypatch.setenv("PIHTI_SESSION_KEY_FILE", str(key_file))
    first = _load_or_create_session_secret()
    second = _load_or_create_session_secret()
    assert first == second
    assert len(first) == 32
    assert key_file.read_bytes() == first


def test_every_page_shares_the_rail_grid_and_marks_its_tab(client):
    for path, endpoint_label in (("/", "Vacuum"), ("/history", "History"), ("/plasmaplots", "Plot")):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["X-Frame-Options"] == "DENY"
        page = response.data.decode("utf-8")
        assert 'class="page"' in page
        assert page.count('class="rail rail-left"') == 1
        assert page.count('class="rail rail-right"') == 1
        assert f'aria-current="page">{endpoint_label}<' in page
        assert page.count('aria-current="page"') == 1
        assert "cdn." not in page
    home = client.get("/").data
    assert b'id="guide-controls"' in home
    assert b'id="guide-steps"' in home
    assert b"Prototype diagram guidance only" in home


def test_operator_roster_is_plain_names_without_passwords(client, app):
    page = client.get("/identify")
    assert page.status_code == 200
    assert b'value="operator"' in page.data
    assert b'value="Second Operator"' in page.data
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
    assert client.post("/api/identify", json={"username": "stranger"}).status_code == 404


def test_operator_is_chosen_in_the_top_bar_on_every_page(client):
    for path in ("/", "/history", "/plasmaplots"):
        page = client.get(path).data.decode("utf-8")
        assert 'id="operator-select"' in page
        assert ">Read only<" in page
        assert '<option value="operator"' in page
    identify(client)
    page = client.get("/history").data.decode("utf-8")
    assert '<option value="operator" selected>' in page
    assert 'data-current="operator"' in page
    cleared = client.post("/api/identity/clear")
    assert cleared.status_code == 200
    with client.session_transaction() as browser_session:
        assert "username" not in browser_session
    assert client.get("/get_current_user").json["is_identified"] is False


def test_top_bar_says_when_no_operator_exists(tmp_path):
    page = make_app(tmp_path).test_client().get("/").data.decode("utf-8")
    assert 'id="operator-select"' not in page
    assert "No operators on this machine" in page


def test_missing_roster_falls_back_to_legacy_registry_names_only(tmp_path):
    key = Fernet.generate_key()
    (tmp_path / "users.key").write_bytes(key)
    (tmp_path / "users.json.enc").write_bytes(
        Fernet(key).encrypt(json.dumps({"legacy": "hash-value", "Another": "x"}).encode())
    )
    client = make_app(tmp_path).test_client()
    page = client.get("/identify").data.decode("utf-8")
    assert 'value="Another"' in page and 'value="legacy"' in page
    assert "hash-value" not in page
    assert client.post("/api/identify", json={"username": "legacy"}).status_code == 200
    assert not (tmp_path / "users.json").exists()


def test_missing_roster_and_key_gives_an_honest_state_and_a_command(tmp_path):
    client = make_app(tmp_path).test_client()
    page = client.get("/identify").data.decode("utf-8")
    assert "No operator roster exists on this machine" in page
    assert "-m pihti operators add" in page
    assert "<select" in page and "disabled" in page
    assert client.post("/api/identify", json={"username": "x"}).status_code == 503


def test_history_is_parsed_once_until_the_log_changes(client, tmp_path):
    from pihti.server import load_history_events

    log_file = tmp_path / "logs.csv"
    identify(client)
    assert client.post("/update", json={"id": "GVU", "status": "active"}).status_code == 200
    first = load_history_events(log_file)
    assert load_history_events(log_file) is first
    assert len(first) == 1
    assert client.post("/update", json={"id": "GVU", "status": "inactive"}).status_code == 200
    second = load_history_events(log_file)
    assert second is not first and len(second) == 2
    assert len(client.get("/history/events").json) == 2
    # The browser rebuilds a moment from the events list and the current state,
    # so the served events carry everything that reconstruction needs.
    assert set(client.get("/history/events").json[0]) == {"ts", "id", "state", "user"}
    assert client.get("/elements-state").json == {"GVU": "inactive"}


def test_server_answers_on_the_lan_by_default_and_debug_stays_loopback(monkeypatch):
    from pihti.cli import build_parser

    monkeypatch.delenv("PIHTI_HOST", raising=False)
    monkeypatch.delenv("PIHTI_PORT", raising=False)
    args = build_parser().parse_args(["run"])
    assert (args.host, args.port) == ("0.0.0.0", 5000)
    monkeypatch.setenv("PIHTI_HOST", "127.0.0.1")
    monkeypatch.setenv("PIHTI_PORT", "4186")
    args = build_parser().parse_args(["run"])
    assert (args.host, args.port) == ("127.0.0.1", 4186)
    with pytest.raises(SystemExit):
        cli_main(["run", "--host", "0.0.0.0", "--debug"])


def test_operators_cli_manages_the_roster(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PIHTI_DATA_ROOT", str(tmp_path))
    monkeypatch.delenv("PIHTI_OPERATORS_FILE", raising=False)
    (tmp_path / "logs.csv").write_text(
        "timestamp,id,status,user\n2026-01-01 10:00:00,GVU,active,From History\n",
        encoding="utf-8",
    )
    assert cli_main(["operators", "add", "Alice", "alice", " Bob  Smith "]) == 0
    assert cli_main(["operators", "import-history"]) == 0
    assert cli_main(["operators", "remove", "bob smith"]) == 0
    assert cli_main(["operators", "remove", "nobody"]) == 1
    capsys.readouterr()
    assert cli_main(["operators", "list"]) == 0
    assert capsys.readouterr().out.splitlines() == ["Alice", "From History"]
    saved = json.loads((tmp_path / "operators.json").read_text(encoding="utf-8"))
    assert saved == {"operators": ["Alice", "From History"]}
    assert roster.read_roster(tmp_path / "missing.json") is None


def test_read_only_history_plots_and_downloads_are_public(client):
    history = client.get("/history")
    assert history.status_code == 200
    assert b"calendar-grid" in history.data
    assert client.get("/history/events").status_code == 200
    assert client.get("/plasmaplots").status_code == 200
    assert client.get("/download_logs").status_code == 200
    assert client.get("/download_controlunit_csv?file=cu_20260101_120000.csv").status_code == 200
    assert client.get("/state.svg").status_code == 200


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


def test_history_moment_and_rendered_state_svg(client):
    identify(client)
    assert client.post("/update", json={"id": "TMPU", "status": "active"}).status_code == 200
    assert client.post("/update", json={"id": "GVU", "status": "active"}).status_code == 200
    events = client.get("/history/events").json
    assert [event["id"] for event in events] == ["TMPU", "GVU"]
    first_ts = events[0]["ts"]

    at_first = client.get("/history/state-at", query_string={"ts": first_ts})
    assert at_first.status_code == 200
    # Two changes in the same second share a timestamp; the moment resolves to the last one.
    expected_index = 1 if events[1]["ts"] == first_ts else 0
    assert at_first.json["index"] == expected_index
    assert at_first.json["state"]["TMPU"] is True
    assert bool(at_first.json["state"].get("GVU")) is (expected_index == 1)
    assert client.get("/history/state-at", query_string={"ts": "1999-01-01 00:00:00"}).status_code == 404
    assert client.get("/history/state-at", query_string={"ts": "not-a-time"}).status_code == 400

    current = client.get("/state.svg")
    assert current.mimetype == "image/svg+xml"
    body = current.data.decode("utf-8")
    assert "#TMPU{fill:yellow !important}" in body
    assert "#GVU{fill:#9bf08d !important}" in body
    assert body.rstrip().endswith("</svg>")
    ET.fromstring(current.data)

    historical = client.get("/state.svg", query_string={"at": first_ts.replace(" ", "T")})
    assert historical.status_code == 200
    assert "#TMPU{fill:yellow !important}" in historical.data.decode("utf-8")
    assert client.get("/state.svg", query_string={"at": "bad"}).status_code == 400


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
    app = make_app(tmp_path, CUDATA_DIRECTORY=None, SETTINGS_FILE=tmp_path / "missing-settings.json")
    response = app.test_client().get("/plasmaplots")
    assert response.status_code == 200
    assert b"No control-unit data directory is configured" in response.data
    assert b'id="file-list"' not in response.data
    assert b"cdn.plot.ly" not in response.data
    assert b"code.jquery.com" not in response.data
    last = app.test_client().get("/get_last_plot")
    assert last.status_code == 200
    assert last.json == {"plot": None}


def test_plot_records_which_file_it_shows(client, app, tmp_path):
    csv_path = Path(app.config["CUDATA_DIRECTORY"]) / "cu_20260102_080000.csv"
    header = ["# header"] * 9 + ["# Columns, date, Ip_c, Pu_c, Pd_c, Bu_c"]
    rows = [f"2026-01-02 08:00:0{i},{i},{10 ** i},{2 * 10 ** i},{3 * 10 ** i}" for i in range(3)]
    csv_path.write_text("\n".join(header + rows) + "\n", encoding="utf-8")
    response = client.post("/plot", data={"file": "cu_20260102_080000.csv"})
    assert response.status_code == 200
    assert response.json["file"] == "cu_20260102_080000.csv"
    assert response.json["linear"] == ["Ip_c"]
    assert response.json["log"] == ["Pu_c", "Pd_c", "Bu_c"]
    assert "plotly" in response.json["plot"]
    assert '<script src="https://cdn.plot.ly' not in response.json["plot"]
    last = client.get("/get_last_plot").json
    assert last["file"] == "cu_20260102_080000.csv"
    meta = json.loads(Path(app.config["LAST_PLOT_META_FILE"]).read_text(encoding="utf-8"))
    assert meta["file"] == "cu_20260102_080000.csv"
    assert client.post("/plot", data={"file": "cu_20260101_120000.csv"}).status_code == 422


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
