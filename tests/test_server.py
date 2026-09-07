from __future__ import annotations

import json
import tomllib
import xml.etree.ElementTree as ET
from datetime import timedelta
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from pihti import __version__
from pihti import plumbing as plumbing_map
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
        # Inside the sandbox, never the operator's own machine-local file: the
        # default settings path is the repository root, whose gitignored
        # `settings.json` carries this machine's real neighbour addresses, and
        # a test that reads it passes or fails by whose PC it runs on.
        "SETTINGS_FILE": tmp_path / "settings.json",
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
    assert project["project"]["version"] == __version__ == "0.11.1"
    assert client.get("/version").json == {"name": "pihti", "version": "0.11.1"}
    assert b"v0.11.1" in client.get("/").data


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
    for path, endpoint_label in (("/", "Vacuum"), ("/history", "History"), ("/plasmaplots", "Plot"), ("/services", "Services")):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        # SAMEORIGIN, not DENY, since 0.9.1: the Plot tab frames its own plot
        # document so Plotly parses outside this page. Other origins still may
        # not frame us.
        assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
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
    for path in ("/", "/history", "/plasmaplots", "/services"):
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
        for step in guide["steps"]:
            targets = step.get("targets") or [{"id": step["targetId"]}]
            assert targets, step
            assert all(target["id"] in svg_ids for target in targets), step
            if not step.get("manual"):
                assert step["desiredStatus"] in {"active", "inactive"}
    # Owner shape 2026-09-04: ionization gauges off first (Baratron, Pirani and
    # membrane gauges stay on at one atmosphere), then gate valve with its
    # turbo, then every route between the two vessels, then nitrogen in
    # through the gas line: venting means letting N2 in, not just opening up.
    plasma = next(guide for guide in guides["guides"] if guide["id"] == "vent-plasma")
    ids = [[target["id"] for target in step["targets"]] for step in plasma["steps"]]
    assert ids[0] == ["bypass-ionization-gauge"]
    assert ids[1] == ["GVU", "TMPU"]
    assert "valve_qms" in ids[2] and len(ids[2]) == 4
    assert ids[3] == ["gaspanel-valve-n", "gasline-main"]
    assert plasma["steps"][3]["desiredStatus"] == "active"
    assert "upstream-baratron" not in sum(ids[:4], [])


def test_plot_finds_recordings_by_calendar_day_not_by_one_long_list(client, tmp_path):
    control_data = tmp_path / "control-data"
    for name in ("cu_20260610_194248.csv", "cu_20260610_185959.csv", "cu_20260609_211051.csv", "cu_notes.csv"):
        (control_data / name).write_text("t,Ip_c\n", encoding="utf-8")
    page = client.get("/plasmaplots").data.decode("utf-8")
    assert 'id="plot-calendar"' in page and 'id="calendar-latest"' in page
    assert 'id="file-list"' in page and "calendar.js" in page
    # The archive reaches the browser as data, never as thirteen hundred buttons.
    assert "<details" not in page and 'data-file="cu_' not in page
    payload = json.loads(page.split('id="archive-data">', 1)[1].split("</script>", 1)[0])
    # Since 0.9.1 the page carries the newest month and the index of months,
    # not the whole archive; the rest is fetched a month at a time.
    assert payload["months"] == ["2026-06", "2026-01", "undated"]
    assert payload["month"] == "2026-06"
    assert [group["date"] for group in payload["days"]] == ["2026-06-10", "2026-06-09"]
    assert payload["latest"] == "cu_20260610_194248.csv"
    assert payload["days"][0]["files"] == [
        {"name": "cu_20260610_194248.csv", "time": "19:42:48"},
        {"name": "cu_20260610_185959.csv", "time": "18:59:59"},
    ]
    assert "cu_20260101_120000.csv" not in page
    older = client.get("/plot/recordings?month=2026-01").json
    assert [group["date"] for group in older["days"]] == ["2026-01-01"]
    assert client.get("/plot/recordings?month=undated").json["days"][0]["date"] == "undated"
    assert client.get("/history").data.decode("utf-8").count("calendar.js") == 1
    from pihti.server import group_files_by_day

    groups = group_files_by_day(["cu_20260101_120000.csv"])
    assert groups[0]["label"].startswith("2026-01-01 · ") and groups[0]["files"][0]["time"] == "12:00:00"


def test_pages_carry_this_project_s_own_icon(client):
    # The inherited .ico was another site's mark, and a tab showing it sent the
    # reader to the wrong project. The tile is this repository's own drawing.
    page = client.get("/").data.decode("utf-8")
    assert 'type="image/svg+xml"' in page and "favicon.svg" in page
    assert "favicon.ico" not in page
    icon = client.get("/static/favicon.svg")
    assert icon.status_code == 200 and b"<svg" in icon.data


def test_static_assets_are_cacheable_only_when_they_carry_the_release(client):
    # Before 0.9.1 every response was `no-store`, so each tab switch re-fetched
    # the 185 kB drawing, the stylesheet and every script. Now a static URL
    # stamped with the running release may be kept, and one without it may not,
    # so a stale asset can never outlive its release.
    stamped = client.get(f"/static/css/styles.css?v={__version__}")
    assert stamped.status_code == 200
    assert stamped.headers["Cache-Control"] == "public, max-age=31536000, immutable"
    for url in ("/static/css/styles.css", f"/static/css/styles.css?v={__version__}-old"):
        assert client.get(url).headers["Cache-Control"] == "no-store"
    page = client.get("/").data.decode("utf-8")
    assert f"styles.css?v={__version__}" in page
    assert 'href="/static/css/styles.css"' not in page
    # Pages and data stay uncacheable whatever else changes.
    assert client.get("/elements-state").headers["Cache-Control"] == "no-store"


def test_the_archive_travels_one_month_at_a_time(app, client, tmp_path):
    # Thirteen hundred recordings used to ride in the page. Now the page
    # carries the newest month and going back asks for one month, which a
    # passed month answers with a 304 (queezz, 2026-09-07: "we know our
    # history, so that should not be slower").
    folder = Path(app.config["CUDATA_DIRECTORY"])
    for name in ("cu_20260905_101500.csv", "cu_20260905_120000.csv", "cu_20260712_090000.csv", "notes.txt"):
        (folder / name).write_text("sample", encoding="utf-8")
    page = client.get("/plasmaplots").data.decode("utf-8")
    assert "cu_20260905_101500.csv" in page          # the newest month is in the page
    assert "cu_20260712_090000.csv" not in page      # an older one is not
    assert 'id="archive-data"' in page

    older = client.get("/plot/recordings?month=2026-07")
    assert older.status_code == 200
    assert older.headers["Cache-Control"] == "no-cache"
    assert [day["date"] for day in older.json["days"]] == ["2026-07-12"]
    assert older.json["days"][0]["files"] == [{"name": "cu_20260712_090000.csv", "time": "09:00:00"}]

    # History does not change, so asking again costs a 304 and no body.
    again = client.get("/plot/recordings?month=2026-07", headers={"If-None-Match": older.headers["ETag"]})
    assert again.status_code == 304
    assert not again.data

    # A month that gains a recording stops matching, so nothing is served stale.
    (folder / "cu_20260713_090000.csv").write_text("sample", encoding="utf-8")
    fresh = client.get("/plot/recordings?month=2026-07", headers={"If-None-Match": older.headers["ETag"]})
    assert fresh.status_code == 200
    assert len(fresh.json["days"]) == 2

    assert client.get("/plot/recordings?month=nonsense").status_code == 400
    assert client.get("/plot/recordings?month=undated").json["days"] == []


def test_health_endpoint_keeps_the_ensemble_contract(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    body = response.json
    assert set(body) == {"service", "version", "status", "detail"}
    assert body["service"] == "pihti-diagram" and body["status"] == "ok"
    assert body["version"] == __version__
    assert body["detail"] == "no diagram changes recorded yet"
    assert "/" not in body["detail"] and "\\" not in body["detail"]
    identify(client)
    client.post("/update", json={"id": "GVU", "status": "active"})
    assert client.get("/api/health").json["detail"] == "diagram changed less than a minute ago"


def test_services_board_names_five_states_and_never_guesses(tmp_path):
    answers = {
        "http://log.test:4310": ("ok", "0.20.1", "a session is open"),
        "http://rig.test:4187": ("unreachable", "", "no answer within two seconds"),
    }
    app = make_app(
        tmp_path,
        NEIGHBOURS={"pihti-log": "http://log.test:4310/", "controlunit": "http://rig.test:4187"},
        NEIGHBOUR_PROBE=lambda url: answers[url],
    )
    client = app.test_client()
    rows = client.get("/api/neighbours").json["services"]
    assert [row["alias"] for row in rows] == ["pihti-diagram", "pihti-log", "controlunit"]
    assert rows[0]["state"] == "ok" and rows[0]["url"] == ""
    assert rows[1] == {"alias": "pihti-log", "name": "PIHTI Log", "url": "http://log.test:4310",
                       "state": "ok", "version": "0.20.1", "detail": "a session is open",
                       "start_how": "Start it on the PC that keeps the journal.",
                       "start_command": "lab pihti-log"}
    assert rows[2]["state"] == "unreachable" and rows[2]["url"] == "http://rig.test:4187"
    # ControlUnit is started by the rig's own GUI: there is no `lab` alias for
    # it anywhere in this lab, so the card must offer no command at all.
    assert rows[2]["start_command"] == ""
    assert "Raspberry Pi" in rows[2]["start_how"] and "lab" not in rows[2]["start_how"]
    assert rows[0]["start_how"] == "Already running — this page is it."
    page = client.get("/services").data.decode("utf-8")
    assert "has not been told" not in page and 'id="services-board"' in page

    bare = make_app(tmp_path).test_client()
    rows = bare.get("/api/neighbours").json["services"]
    assert [row["state"] for row in rows[1:]] == ["not configured", "not configured"]
    assert "has not been told where the other two services live" in bare.get("/services").data.decode("utf-8")

    from pihti import neighbours

    assert neighbours.read_addresses({"NEIGHBOURS": {"pihti-log": {"url": "http://a/"}, "x": 3}}) == {"pihti-log": "http://a"}

    # A machine whose layout differs corrects the sentence in its own settings;
    # the command stays the tool's, never the machine's.
    settings = {"NEIGHBOURS": {"controlunit": {"url": "http://a", "start": "Ask the rig operator."}}}
    assert neighbours.read_starts(settings) == {"controlunit": "Ask the rig operator."}
    assert neighbours.start_hint("controlunit", "Ask the rig operator.") == ("Ask the rig operator.", "")
    assert neighbours.start_hint("pihti-log")[1] == "lab pihti-log"
    local = make_app(tmp_path, NEIGHBOURS=settings["NEIGHBOURS"], NEIGHBOUR_PROBE=lambda url: ("ok", "4.0.0", "acquiring"))
    board = local.test_client().get("/api/neighbours").json["services"]
    assert board[2]["start_how"] == "Ask the rig operator." and board[2]["start_command"] == ""


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
    assert app.test_client().get("/plot/meta").json["has_plot"] is False
    assert app.test_client().get("/plot/last.html").status_code == 404


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
    # The megabytes of Plotly never ride in this answer: the page frames the
    # plot's own document instead (0.9.1).
    assert "plot" not in response.json
    document = client.get("/plot/last.html")
    assert document.status_code == 200 and document.mimetype == "text/html"
    body = document.data.decode("utf-8")
    assert "plotly" in body
    assert '<script src="https://cdn.plot.ly' not in body
    meta = client.get("/plot/meta").json
    assert meta["has_plot"] is True and meta["file"] == "cu_20260102_080000.csv"
    assert "plot" not in meta
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


def test_every_component_has_a_readable_name_and_no_page_prints_a_raw_key(client):
    """A person reads equipment names; the keys stay in the files and the log.

    Mac audit 2026-09-07 (letter ``20260907-8cbfd520-ca289d``): the guide said
    "Next · bypass-ionization-gauge" and History's Element field printed
    ``event.id``. Fleet ``WEBUI.md``: no surface renders a string meant for the
    machine.
    """
    config = client.get("/elements-config").json
    labels = {item["id"]: item.get("label", "") for item in config}
    assert all(labels.values()), [key for key, value in labels.items() if not value]
    assert len(set(labels.values())) == len(labels), "two components would read alike"
    # The three the audit named, and the designation kept beside the words.
    assert labels["bypass-ionization-gauge"] == "Bypass ionization gauge"
    assert labels["gaspanel-valve-n"] == "Gas panel nitrogen valve"
    assert labels["gasline-main"] == "Main gas line"
    assert labels["GVU"].endswith("(GVU)") and labels["TMPD"].endswith("(TMPD)")

    guides = client.get("/operation-guides").json
    for guide in guides["guides"]:
        for step in guide["steps"]:
            for target in step.get("targets") or [{"id": step["targetId"]}]:
                assert labels.get(target["id"]), target

    scripts = Path(PROJECT_ROOT / "src" / "pihti" / "static" / "js")
    diagram_js = (scripts / "diagram.js").read_text(encoding="utf-8")
    history_js = (scripts / "history.js").read_text(encoding="utf-8")
    assert "window.pihtiElementName = elementName;" in diagram_js
    assert "displayName(target.id)" in diagram_js
    assert "displayName(element.id)" in diagram_js
    assert ".map((target) => target.id).join" not in diagram_js
    # History reads the same names, and says so when the diagram no longer
    # carries a component rather than passing its key off as a name.
    assert "window.pihtiElementName?.(id)" in history_js
    assert "escapeHtml(event.id)" not in history_js
    assert 'getElementById("moment-element").textContent = event.id' not in history_js
    assert "not on the current diagram" in history_js


def test_the_top_bar_wraps_instead_of_pushing_the_operator_off_the_screen():
    """At 390px the five tabs and the selector wanted 454px of a 390px screen.

    The bar wraps: one DOM in a different placement, no phone-only control.
    """
    css = (PROJECT_ROOT / "src" / "pihti" / "static" / "css" / "styles.css").read_text(encoding="utf-8")
    tabbar = css.split(".tabbar {", 1)[1].split("}", 1)[0]
    assert "flex-wrap: wrap;" in tabbar
    meta = css.split(".tab-meta {", 1)[1].split("}", 1)[0]
    assert "margin-left: auto;" in meta
    assert "flex-wrap: wrap" in css.split(".tab-group {", 1)[1].split("}", 1)[0]


def test_a_neighbour_s_own_status_is_taken_at_its_word(tmp_path):
    """Two owner decisions of 2026-09-07 land on the producers, not here.

    An idle ControlUnit reports ``ok`` with an idle detail; PIHTI Log stops
    reporting ``degraded`` for a pending draft. This board renders what
    ``/api/health`` says and never re-reads a producer's own status.
    """
    reports = {
        "http://log.test:4310": ("ok", "0.37.1", "no session open"),
        "http://rig.test:4187": ("ok", "4.2.1", "idle, not recording"),
    }
    app = make_app(
        tmp_path,
        NEIGHBOURS={"pihti-log": "http://log.test:4310", "controlunit": "http://rig.test:4187"},
        NEIGHBOUR_PROBE=lambda url: reports[url],
    )
    rows = app.test_client().get("/api/neighbours").json["services"]
    assert [(row["state"], row["detail"]) for row in rows[1:]] == [
        ("ok", "no session open"),
        ("ok", "idle, not recording"),
    ]


def test_two_spellings_of_one_operator_never_become_two_identical_options(tmp_path):
    """The roster is this machine's own flat list of account names.

    There is no shared trio roster file and no display-name/username pair here,
    so the trio's "Display Name (username)" rule has nothing to disambiguate;
    what this roster must never do is offer the reader two options that read
    exactly alike.
    """
    roster_file = tmp_path / "operators.json"
    roster_file.write_text(json.dumps(["Kaoru Hayashi", "kaoru hayashi", " Kaoru  Hayashi "]), encoding="utf-8")
    assert roster.read_roster(roster_file) == ["Kaoru Hayashi"]
    page = make_app(tmp_path, OPERATORS_FILE=roster_file).test_client().get("/").data.decode("utf-8")
    assert page.count('<option value="Kaoru Hayashi"') == 1


def test_every_pipe_in_the_volume_map_is_really_on_the_diagram(client):
    """The map names drawn elements, and every valve it uses can be toggled.

    A volume map that names a pipe the drawing does not carry would colour
    nothing and say nothing about it, which is the quiet kind of wrong.
    """
    plumbing = client.get("/plumbing").json
    svg_root = ET.parse(PROJECT_ROOT / "src" / "pihti" / "static" / "diagram.svg").getroot()
    svg_ids = {element.get("id") for element in svg_root.iter() if element.get("id")}
    config_ids = {item["id"] for item in client.get("/elements-config").json}

    named = [
        element
        for volume in plumbing["volumes"].values()
        for element in volume["elements"]
    ]
    assert named, "the volume map is empty"
    assert len(named) == len(set(named)), "an element belongs to two volumes"
    missing = sorted(element for element in named if element not in svg_ids)
    assert missing == [], missing

    for volume in plumbing["volumes"].values():
        assert volume["group"] in svg_ids, volume["group"]

    operable = [item["id"] for item in plumbing["valves"]]
    operable += [item["id"] for item in plumbing["pumps"]]
    operable += [item["id"] for item in plumbing["gas_sources"]]
    operable += [item["id"] for item in plumbing["gauges"]]
    assert sorted(set(operable) - config_ids) == []

    volume_names = set(plumbing["volumes"])
    for valve in plumbing["valves"]:
        assert set(valve["joins"]) <= volume_names, valve
    for pump in plumbing["pumps"]:
        assert pump["volume"] in volume_names, pump


def test_pipe_colour_is_predicted_from_the_valves_and_says_air_first(client):
    """Three valve configurations, and the honest order of the five states."""
    plumbing = client.get("/plumbing").json
    colours = {state["id"]: state["color"] for state in plumbing["states"]}

    everything_shut = plumbing_map.predict(plumbing, {})["volumes"]
    assert everything_shut["plasma-vessel"] == "isolated"
    assert everything_shut["qms-vessel"] == "isolated"
    assert everything_shut["atmosphere"] == "air"

    pumping = plumbing_map.predict(
        plumbing, {"TMPU": "active", "GVU": "active", "RoughU": "active"}
    )
    assert pumping["volumes"]["plasma-vessel"] == "high-vacuum"
    assert pumping["volumes"]["plasma-turbo-line"] == "high-vacuum"
    assert pumping["volumes"]["plasma-foreline"] == "rough-vacuum"
    assert pumping["volumes"]["qms-vessel"] == "isolated"
    assert pumping["elements"]["plasma-vacuum"]["stroke"] == colours["high-vacuum"]
    assert pumping["air"] == []

    vented = plumbing_map.predict(
        plumbing,
        {
            "TMPU": "active",
            "GVU": "active",
            "RoughU": "active",
            "upstream-pumpline-vent-valve": "active",
        },
    )
    assert vented["volumes"]["plasma-foreline"] == "air"
    assert vented["volumes"]["plasma-vessel"] == "high-vacuum"
    assert vented["air"] == ["Plasma backing line"]
    assert vented["elements"]["upstream-tmp-to-rotary-pipe"]["stroke"] == colours["air"]

    gas = plumbing_map.predict(
        plumbing, {"hydrogen-bottle": "active", "gasline-h": "active", "gasline-main": "active"}
    )
    assert gas["volumes"]["hydrogen-line"] == "gas"
    assert gas["volumes"]["plasma-vessel"] == "gas"


def test_the_prediction_reaches_the_page_and_a_replayed_moment(client):
    live = client.get("/predicted-vacuum")
    assert live.status_code == 200
    assert set(live.json) == {"volumes", "elements", "air"}
    assert client.get("/predicted-vacuum", query_string={"at": "bad"}).status_code == 400
    identify(client)
    client.post("/update", json={"id": "upstream-pumpline-vent-valve", "status": "active"})
    stamp = client.get("/history/events").json[-1]["ts"]
    replayed = client.get("/predicted-vacuum", query_string={"at": stamp})
    assert replayed.json["volumes"]["plasma-foreline"] == "air"
    # The key sits under the drawing on both pages that draw it, and each page
    # states the prediction once — a second telling is the textbook defect.
    for path in ("/", "/history"):
        page = client.get(path).data.decode("utf-8")
        assert page.count("Predicted from the valve positions") == 1, path
        assert 'id="vacuum-legend"' in page, path
        assert 'class="diagram-legend"' in page, path
        assert "measure pressure" not in page, path


def test_an_old_permalink_still_selects_the_renamed_element(tmp_path):
    """logs.csv and elements_state.json carry real ids from real days; the
    2026-09-08 spelling/oddity correction renamed GVU-6 in diagram.svg and
    plumbing.json to upstream-pumpline-vent-valve, but a stored event or a
    permalink pointing at the old id must still find the current element.
    The alias is applied only on read — the files on disk stay untouched."""
    old_ts = "2026-09-01 12:00:00"
    (tmp_path / "elements_state.json").write_text(
        json.dumps({"GVU-6": "active"}), encoding="utf-8"
    )
    (tmp_path / "logs.csv").write_text(
        "timestamp,id,status,user\n" f"{old_ts},GVU-6,active,operator\n",
        encoding="utf-8",
    )
    client = make_app(tmp_path).test_client()

    assert client.get("/elements-state").json == {"upstream-pumpline-vent-valve": "active"}

    events = client.get("/history/events").json
    assert events[-1]["id"] == "upstream-pumpline-vent-valve"

    replayed = client.get("/predicted-vacuum", query_string={"at": old_ts})
    assert replayed.json["volumes"]["plasma-foreline"] == "air"

    assert json.loads((tmp_path / "elements_state.json").read_text(encoding="utf-8")) == {
        "GVU-6": "active"
    }
    assert "GVU-6" in (tmp_path / "logs.csv").read_text(encoding="utf-8")
