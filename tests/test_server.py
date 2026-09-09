from __future__ import annotations

import json
import math
import re
import tomllib
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
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


@pytest.mark.parametrize("mode", ["membrane", "open", "blank", "boron"])
def test_dark_palette_preserves_connectivity_and_matches_browser_paints(client, mode):
    mapping = client.get("/plumbing").json
    before = json.dumps(mapping, sort_keys=True)
    dark = plumbing_map.themed_map(mapping, "dark")
    palette = mapping["dark_palette"]["colours"]
    now = datetime.fromisoformat("2026-09-08T12:00:00")
    states = [
        {},
        {"TMPU": "active", "GVU": "active", "TMPD": "active", "GVD": "active"},
        {"RoughU": "active", "GVU": "active"},
        {"RoughD": "active", "GVD": "active", "downstream-pumpline-vent-valve": "active"},
        {"TMPU": "active", "TMPD": "active", "GVBU": "active", "bypass-l1": "active",
         "GVBD": "active", "GVU": "active", "GVD": "active"},
    ]
    running = plumbing_map.predict(mapping, states[1], mode, now=now)
    memory = plumbing_map.update_memory(mapping, {}, running, now)
    memory = plumbing_map.update_memory(mapping, memory, plumbing_map.predict(mapping, {}, mode), now)
    states.append({plumbing_map.MEMORY_KEY: memory})
    assert any(item.get("sealed_paint") for item in
               plumbing_map.predict(mapping, states[-1], mode, now=now)["elements"].values())
    for state in states:
        light_result = plumbing_map.predict(mapping, state, mode, now=now)
        dark_result = plumbing_map.predict(dark, state, mode, now=now)
        assert light_result["connections"] == dark_result["connections"]
        assert light_result["elements"].keys() == dark_result["elements"].keys()
        marker = dark_result["elements"]["Membrane"]
        assert marker["stroke"] == "#aebfce"
        assert marker["opacity"] == (1.0 if marker["plug"] else 0.9)
        for key, light in light_result["elements"].items():
            shaded = dark_result["elements"][key]
            inks = {**palette, **mapping["dark_palette"]["valve_inks"]} if light.get("valve") else palette
            for paint in ("fill", "stroke", "mix"):
                assert inks.get(light.get(paint), light.get(paint)) == shaded.get(paint)
    assert json.dumps(mapping, sort_keys=True) == before


def test_dark_svg_is_public_and_theme_reads_do_not_write(app, client):
    identify(client)
    assert client.post("/update", json={"id": "TMPU", "status": "active"}).status_code == 200
    paths = [Path(app.config[key]) for key in ("STATE_FILE", "LOG_FILE")]
    before = [path.read_bytes() for path in paths]
    dark = client.get("/state.svg?theme=dark").get_data(as_text=True)
    assert "background:#293440" in dark
    assert "#42c5ff" in dark
    ET.fromstring(dark)
    light = client.get("/state.svg?theme=light").data
    assert light == client.get("/state.svg?theme=invalid").data
    client.get("/plumbing")
    assert [path.read_bytes() for path in paths] == before


def test_release_version_is_single_sourced_and_visible(client):
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == __version__ == "0.20.4"
    assert client.get("/version").json == {"name": "pihti", "version": "0.20.4"}
    assert b"v0.20.4" in client.get("/").data


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
    # The guides stopped being a prototype when queezz corrected them in his own
    # words (2026-09-08); the half of the sentence that matters stayed.
    assert b"Operator guidance only" in home
    assert b"does not operate hardware or replace an interlock" in home
    assert b"Prototype" not in home


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
    assert set(client.get("/history/events").json[0]) == {
        "ts",
        "id",
        "state",
        "user",
        # One press ordinarily, a whole practised sequence when the event is a
        # practice save (0.19.0), and the note that says which it was.
        "changes",
        "note",
    }
    assert client.get("/history/events").json[0]["changes"] == [
        {"id": "GVU", "state": True}
    ]
    assert client.get("/history/events").json[0]["note"] == ""
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
    # A running turbo wears the high-vacuum colour of the side it serves (0.16.0)
    # over the black rim queezz drew: TMPU is running here, so it is the plasma
    # side's blue.
    assert "#TMPU{stroke:#000000 !important;fill:#1f5fd0 !important}" in body
    # A stopped pump keeps his own grey body -- nothing writes it a fill -- and
    # its rim and inner lines recede to dark grey (0.17.0, letter
    # 20260908-e2498698-5c9c50: "we can also gray out pump edges and lines").
    assert "#TMPD{stroke:#5f5f5f !important}" in body
    assert "#path1563-6{stroke:#5f5f5f !important}" in body
    assert "#path1563{stroke:#000000 !important}" in body
    assert "yellow" not in body
    # A valve wears the prediction's own colour, never the operator green
    # (0.15.0), and its edge goes with its fill (0.16.0): GVU is open onto a
    # turbo-pumped plasma vessel, so both its fill and its outline are that
    # vessel's own high-vacuum colour.
    assert "#GVU{stroke:#1f5fd0 !important;fill:#1f5fd0 !important}" in body
    assert "#GVU{fill:#9bf08d !important}" not in body
    # And a closed valve is white with a black outline, the one dark-rimmed
    # shape on the drawing, so the colour visibly stops on both sides.
    assert "#GVD{stroke:#000000 !important;fill:#ffffff !important}" in body
    assert body.rstrip().endswith("</svg>")
    ET.fromstring(current.data)

    historical = client.get("/state.svg", query_string={"at": first_ts.replace(" ", "T")})
    assert historical.status_code == 200
    assert "#TMPU{stroke:#000000 !important;fill:#1f5fd0 !important}" in historical.data.decode("utf-8")
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
    """Four guides, every part they name really on the drawing, in queezz's shape.

    The vent guides stopped being a prototype on 2026-09-08, when he read the
    deployed 0.13.0 and corrected them line by line (letter
    ``20260908-7a3c9ac3-bbd7aa``): the QMS valve and the roughing bypass are not
    routes between the vessels and left the isolation step; the plasma turbo is
    the operator's own choice, not a required press; nitrogen comes in through
    the big manual needle valve on the argon line, never the mass-flow
    controllers. The two pump-down guides are the inverse, from the same letter.
    """
    guides = client.get("/operation-guides").json
    assert guides["prototype"] is False
    svg_root = ET.parse(PROJECT_ROOT / "src" / "pihti" / "static" / "diagram.svg").getroot()
    svg_ids = {element.get("id") for element in svg_root.iter() if element.get("id")}
    plumbing = client.get("/plumbing").json
    assert [guide["id"] for guide in guides["guides"]] == [
        "vent-plasma",
        "vent-qms",
        "pump-plasma",
        "pump-qms",
    ]
    for guide in guides["guides"]:
        assert guide["steps"][-1]["manual"] is True
        for step in guide["steps"]:
            targets = step.get("targets") or [{"id": step["targetId"]}] if (
                step.get("targets") or step.get("targetId")
            ) else []
            marks = step.get("marks") or []
            # A step with no beacon at all is allowed only for a manual one that
            # says why, so nobody drops a marker by accident.
            assert targets or marks or (step.get("manual") and step.get("note")), step
            assert all(target["id"] in svg_ids for target in targets + marks), step
            if step.get("separates"):
                # An isolation step asks the prediction, not a list of valves.
                assert not step.get("desiredStatus"), step
                assert all(name in plumbing["volumes"] for name in step["separates"]), step
            elif not step.get("manual"):
                assert step["desiredStatus"] in {"active", "inactive"}
                assert targets, step
    plasma = next(guide for guide in guides["guides"] if guide["id"] == "vent-plasma")
    steps = plasma["steps"]
    ids = [
        [target["id"] for target in (step.get("targets") or []) + (step.get("marks") or [])]
        for step in steps
    ]
    # Ionization gauges off first; then the gate valve alone, with the turbo
    # marked but never demanded ("we can just close the gate. No need to stop
    # TMP... It's up for the operator to select").
    assert ids[0] == ["bypass-ionization-gauge"]
    assert [target["id"] for target in steps[1]["targets"]] == ["GVU"]
    assert [mark["id"] for mark in steps[1]["marks"]] == ["TMPU"]
    # Isolation is read from the prediction, and the two 0.5.0 guesses are gone.
    assert steps[2]["separates"] == ["plasma-vessel", "qms-vessel"]
    assert [mark["id"] for mark in steps[2]["marks"]] == ["GVBU", "GVBD"]
    assert "valve_qms" not in sum(ids, []) and "Rough-Bypass" not in sum(ids, [])
    # The valve to bypass pumping is checked, on its own step.
    assert [target["id"] for target in steps[3]["targets"]] == ["bypass-l2"]
    assert steps[3]["desiredStatus"] == "inactive"
    # Nitrogen through the argon line's manual needle valve, four parts not two.
    assert [target["id"] for target in steps[4]["targets"]] == [
        "gaspanel-valve-n",
        "gaspanel-valve-ar",
        "gasline-ar",
        "gasline-main",
    ]
    assert steps[4]["desiredStatus"] == "active"
    # The Baratron does not read atmosphere, so it is not the gauge to watch.
    assert "upstream-baratron" not in sum(ids, [])
    assert ids[5] == ["upstream-single-gauge"]

    # Vent QMS: one valve is the isolation, and the double isolation is gone.
    qms = next(guide for guide in guides["guides"] if guide["id"] == "vent-qms")
    isolate = next(step for step in qms["steps"] if step.get("separates"))
    assert isolate["separates"] == ["qms-vessel", "plasma-vessel"]
    assert [mark["id"] for mark in isolate["marks"]] == ["GVBD"]

    # Both pump-downs offer the two ways and name the gauge that reads
    # atmosphere; neither ever asks for a Baratron.
    for name in ("pump-plasma", "pump-qms"):
        guide = next(item for item in guides["guides"] if item["id"] == name)
        words = " ".join(step["action"] for step in guide["steps"]) + guide["summary"]
        assert "turbo must never see atmosphere" in guide["summary"]
        assert "bypass" in words and "----" in words
        assert "bypass-absolute-gauge" in [
            target["id"]
            for step in guide["steps"]
            for target in (step.get("targets") or []) + (step.get("marks") or [])
        ]
        assert "baratron" not in " ".join(
            target["id"]
            for step in guide["steps"]
            for target in (step.get("targets") or []) + (step.get("marks") or [])
        )


def test_a_guide_step_can_wait_on_a_fact_this_rig_alone_knows(client, app, tmp_path):
    """Nitrogen into the QMS vessel only when the flow-calibration pipe is on.

    queezz, 2026-09-08: "venting the downstream is also better with N2, but the
    flow calibration pipe is currently disconnected. We can connect." Which it
    is is a fact about this machine's rig, so it lives in the machine-local
    settings file, defaults to *disconnected*, and reaches the page with the
    guides. The page shows one step or the other, never both.
    """
    guides = client.get("/operation-guides").json
    assert guides["facts"]["flow-calibration-pipe-connected"] is False
    qms = next(guide for guide in guides["guides"] if guide["id"] == "vent-qms")
    gated = [step for step in qms["steps"] if step.get("onlyWhen")]
    assert len(gated) == 2
    assert {step["onlyWhen"]["is"] for step in gated} == {True, False}
    assert all(
        step["onlyWhen"]["fact"] == "flow-calibration-pipe-connected" for step in gated
    )
    nitrogen = next(step for step in gated if step["onlyWhen"]["is"] is True)
    assert [mark["id"] for mark in nitrogen["marks"]] == [
        "gaspanel-valve-n",
        "gaspanel-valve-ar",
        "flow-calibration-valve",
        "GVBD",
    ]
    air = next(step for step in gated if step["onlyWhen"]["is"] is False)
    assert "vent with air" in air["action"] and "good base pressure" in air["action"]

    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps({"FLOW_CALIBRATION_PIPE_CONNECTED": True}), encoding="utf-8"
    )
    app.config["SETTINGS_FILE"] = str(settings)
    assert client.get("/operation-guides").json["facts"][
        "flow-calibration-pipe-connected"
    ] is True


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
        "http://log.test:4310": ("ok", "0.20.2", "a session is open"),
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
                       "state": "ok", "version": "0.20.2", "detail": "a session is open",
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
    assert labels["bypass-ionization-gauge"] == "Upstream ionization gauge"
    assert labels["gaspanel-valve-n"] == "Gas panel nitrogen valve"
    assert labels["gasline-main"] == "Main gas line"
    assert labels["GVU"].endswith("(GVU)") and labels["TMPD"].endswith("(TMPD)")

    guides = client.get("/operation-guides").json
    for guide in guides["guides"]:
        for step in guide["steps"]:
            # `marks` are beacons the step places without asking the diagram
            # whether they are right, and they are read out loud in the rail
            # exactly like a target, so they need a name just as much.
            for target in (step.get("targets") or []) + (step.get("marks") or []):
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
    """Three valve configurations, and the honest order of the seven states."""
    plumbing = client.get("/plumbing").json
    colours = {state["id"]: state["color"] for state in plumbing["states"]}

    everything_shut = plumbing_map.predict(plumbing, {})["volumes"]
    assert everything_shut["plasma-vessel"] == "isolated"
    assert everything_shut["qms-vessel"] == "isolated"
    assert everything_shut["atmosphere"] == "air"

    pumping = plumbing_map.predict(
        plumbing, {"TMPU": "active", "GVU": "active", "RoughU": "active"}
    )
    # High vacuum takes its colour from the vessel it is joined to (0.15.0).
    assert pumping["volumes"]["plasma-vessel"] == "upstream-high-vacuum"
    assert pumping["volumes"]["plasma-turbo-line"] == "upstream-high-vacuum"
    assert pumping["volumes"]["plasma-foreline"] == "rough-vacuum"
    assert pumping["volumes"]["qms-vessel"] == "isolated"
    assert pumping["elements"]["plasma-vacuum"]["fill"] == colours["upstream-high-vacuum"]
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
    assert vented["volumes"]["plasma-vessel"] == "upstream-high-vacuum"
    assert vented["air"] == ["Plasma backing line"]
    assert vented["elements"]["upstream-tmp-to-rotary-pipe"]["stroke"] == colours["air"]

    gas = plumbing_map.predict(
        plumbing, {"hydrogen-bottle": "active", "gasline-h": "active", "gasline-main": "active"}
    )
    assert gas["volumes"]["hydrogen-line"] == "gas"
    assert gas["volumes"]["plasma-vessel"] == "gas"


def test_the_line_between_the_vessels_follows_the_line_configuration(client):
    """One configuration per button, and what each means for the narrow pipe.

    queezz, 2026-09-08: "membrane open/closed is flipped". With a membrane
    installed the pipe between the two vessels is not a route — the membrane is
    what separates them — and only ``Pipe open`` is. A configuration nobody has
    recorded is not a licence to claim a connection either.
    """
    plumbing = client.get("/plumbing").json
    colours = {state["id"]: state["color"] for state in plumbing["states"]}
    both_vcr_open = {
        "TMPU": "active",
        "GVU": "active",
        "RoughU": "active",
        "bypass-vcr-u": "active",
        "bypass-vcr-d": "active",
    }

    connected = plumbing_map.predict(plumbing, both_vcr_open, "open")
    # One space reaching both vessels: it wears the plasma side's colour, and
    # only the drawn shapes carry the QMS side's as their contribution.
    assert connected["volumes"]["qms-vessel"] == "upstream-high-vacuum"
    assert connected["volumes"]["vessel-crossover"] == "upstream-high-vacuum"
    assert connected["mixes"]["qms-vessel"] == "downstream-high-vacuum"
    assert connected["elements"]["qms-vacuum"]["mix"] == colours["downstream-high-vacuum"]
    # A pipe wears one colour and never the contribution.
    assert "mix" not in connected["elements"]["upstream-to-downstream-narrow-pipe"]

    for shut in ("membrane", "unknown", None):
        divided = plumbing_map.predict(plumbing, both_vcr_open, shut)
        assert divided["volumes"]["plasma-vessel"] == "upstream-high-vacuum", shut
        assert divided["volumes"]["qms-vessel"] == "isolated", shut
        # One drawn line, a barrier partway along it: it may only claim a state
        # both sides agree on.
        assert divided["volumes"]["vessel-crossover"] == "isolated", shut

    both_sides_pumped = dict(both_vcr_open, TMPD="active", GVD="active", RoughD="active")
    agreed = plumbing_map.predict(plumbing, both_sides_pumped, "membrane")
    # Both sides are high vacuum and disagree only about which chamber they
    # belong to, so the one drawn line takes the plasma side rather than going
    # grey and claiming less than the truth.
    assert agreed["volumes"]["vessel-crossover"] == "upstream-high-vacuum"
    assert agreed["volumes"]["qms-vessel"] == "downstream-high-vacuum"

    # Every button the page offers is a configuration the map knows, and the
    # card offers exactly the four queezz named, in his order (owner decision
    # 2026-09-08, letter 20260908-b429ce4b-2ad897).
    config = plumbing["line_configuration"]
    modes = config["modes"]
    assert {"membrane", "open", "blank", "boron", "unknown"} == set(modes)
    assert config["order"] == ["membrane", "open", "blank", "boron"]
    assert [modes[name]["label"] for name in config["order"]] == [
        "Membrane installed",
        "Pipe open",
        "Blank",
        "Boron deposition",
    ]
    # One line of meaning each, for the card's More.
    for name in config["order"]:
        assert modes[name]["meaning"].strip()
    assert [name for name, mode in modes.items() if mode["connects"]] == ["open"]
    assert config["volume"] in plumbing["volumes"]


def test_boron_deposition_leaves_the_pipe_a_dead_end_on_the_plasma_side(client):
    """Boron uses the same pipe, but its downstream end is never joined.

    queezz, 2026-09-08 (letter `20260907-dc825e44-e6d89e`): "Boron uses same
    pipe. But other end not connected to downstream. Could be pumped from
    plasma side via bypass." Unlike a membrane -- which divides the pipe into
    two private sides that may happen to agree -- Boron deposition's
    downstream valve never reaches the pipe at all, whatever position it is
    in, so the pipe simply mirrors the plasma vessel.
    """
    plumbing = client.get("/plumbing").json
    both_vcr_open = {
        "TMPU": "active",
        "GVU": "active",
        "RoughU": "active",
        "bypass-vcr-u": "active",
        "bypass-vcr-d": "active",
    }

    # The plasma side is pumped and the downstream valve is open too, but
    # under Boron deposition that downstream valve reaches nothing: the pipe
    # takes the plasma vessel's own state, not "isolated", and the QMS vessel
    # never joins it even though its own valve is open.
    boron = plumbing_map.predict(plumbing, both_vcr_open, "boron")
    assert boron["volumes"]["plasma-vessel"] == "upstream-high-vacuum"
    assert boron["volumes"]["vessel-crossover"] == "upstream-high-vacuum"
    assert boron["volumes"]["qms-vessel"] == "isolated"

    # Even when the QMS side is independently pumped to a *different* state,
    # the pipe still only ever reads the plasma side -- never an "isolated"
    # disagreement the way a membrane would show, and never the QMS state.
    qms_pumped_differently = dict(
        both_vcr_open,
        **{"hydrogen-bottle": "active", "gasline-h": "active", "gasline-main": "active"},
    )
    boron_disagreeing = plumbing_map.predict(plumbing, qms_pumped_differently, "boron")
    assert boron_disagreeing["volumes"]["plasma-vessel"] == "gas"
    assert boron_disagreeing["volumes"]["vessel-crossover"] == "gas"

    # With the plasma-side valve shut, the dead end has nothing to mirror.
    plasma_side_shut = {"TMPU": "active", "GVU": "active", "RoughU": "active", "bypass-vcr-d": "active"}
    isolated = plumbing_map.predict(plumbing, plasma_side_shut, "boron")
    assert isolated["volumes"]["vessel-crossover"] == "isolated"

    modes = plumbing["line_configuration"]["modes"]
    assert modes["boron"]["dead_end_valve"] == "bypass-vcr-d"


def test_the_readout_never_claims_the_qms_vessel_during_boron_deposition(client):
    """The plasma vessel's own sentence may not say it is joined to the QMS one.

    Both crossover valves can be open at once during Boron deposition -- the
    downstream one simply reaches nothing -- and the readout ("I'd like to see
    if upstream and downstream are connected to a) each other...") would be
    lying if it still said "Open to the QMS vessel." from that.
    """
    plumbing = client.get("/plumbing").json
    both_vcr_open_and_pumped = {
        "TMPU": "active",
        "GVU": "active",
        "RoughU": "active",
        "bypass-vcr-u": "active",
        "bypass-vcr-d": "active",
        "TMPD": "active",
        "GVD": "active",
        "RoughD": "active",
    }
    connections = plumbing_map.predict(plumbing, both_vcr_open_and_pumped, "boron")["connections"]
    assert connections["plasma-vessel"]["joined"] == []
    assert connections["qms-vessel"]["joined"] == []
    # The same valve positions under "open", for contrast: the sentence would
    # be right to say so there, because the pipe genuinely joins them.
    open_mode = plumbing_map.predict(plumbing, both_vcr_open_and_pumped, "open")["connections"]
    assert open_mode["plasma-vessel"]["joined"] == ["qms-vessel"]


def test_the_probe_pipe_belongs_to_the_bypass_side_under_boron_deposition(client):
    """The probe pipe never reaches the plasma vessel through its own holder end.

    queezz, 2026-09-09 (letter `20260908-5d638879-1b617e`), on 0.17.x with Boron
    selected and both vessels drawn joined: "Boron deposition, the pipe to the
    bypass cross (probe cross) is not connected then." The sample holder occupies
    the same spot a membrane, a blank flange or a probe would -- so, like them, it
    blocks the ``Membrane`` valve's own position, and `probe-line` can only ever
    reach `bypass-manifold` through the real `bypass-l1` valve at the cross, never
    through a `Membrane` the map used to force open for every mode but *Membrane
    installed* and *Blank*.  The crossover's own dead end (`bypass-vcr-d`) is
    unchanged: it is a separate physical pipe and this is not a second special
    case bolted onto it, just `Membrane` joining the modes that already shut it.
    """
    plumbing = client.get("/plumbing").json

    # Every bypass valve shut: the two vessels are separate, the crossover
    # mirrors the plasma vessel it dead-ends against, and the probe pipe (both
    # drawn segments of it) reads its own -- the bypass cross's -- state, which
    # here is "isolated" because nothing reaches that side either.
    plasma_pumped_only = {
        "TMPU": "active",
        "GVU": "active",
        "RoughU": "active",
        "bypass-vcr-u": "active",
        "bypass-vcr-d": "active",
    }
    isolated_bypass = plumbing_map.predict(plumbing, plasma_pumped_only, "boron")
    assert isolated_bypass["volumes"]["plasma-vessel"] == "upstream-high-vacuum"
    assert isolated_bypass["volumes"]["qms-vessel"] == "isolated"
    assert isolated_bypass["volumes"]["vessel-crossover"] == "upstream-high-vacuum"
    assert isolated_bypass["volumes"]["probe-line"] == "isolated"
    assert isolated_bypass["elements"]["probe-pipe"]["state"] == "isolated"
    assert isolated_bypass["elements"]["probe-pipe-cross-to-GVBD"]["state"] == "isolated"
    assert isolated_bypass["connections"]["plasma-vessel"]["joined"] == []

    # Opening only the two bypass gate valves, with the cross's own bypass-l1
    # still shut, proves the fix: before it, the map's own forced-open
    # `Membrane` alone used to bridge bypass-manifold to probe-line and this
    # combination joined the vessels. Now it does not -- the holder end really
    # is a dead end, and a real valve has to carry the route.
    gates_alone = {
        "TMPU": "active",
        "GVU": "active",
        "RoughU": "active",
        "TMPD": "active",
        "GVD": "active",
        "RoughD": "active",
        "GVBU": "active",
        "GVBD": "active",
    }
    still_separate = plumbing_map.predict(plumbing, gates_alone, "boron")
    assert still_separate["connections"]["plasma-vessel"]["joined"] == []
    assert still_separate["volumes"]["vessel-crossover"] == "isolated"

    # With bypass-l1 open too -- a real route through the cross -- the two
    # vessels join through the bypass, and the readout says so: the crossover
    # stays isolated throughout, because the join never runs through it.
    through_the_bypass = dict(gates_alone, **{"bypass-l1": "active"})
    joined = plumbing_map.predict(plumbing, through_the_bypass, "boron")
    assert joined["volumes"]["plasma-vessel"] == "upstream-high-vacuum"
    assert joined["volumes"]["qms-vessel"] == "upstream-high-vacuum"
    assert joined["volumes"]["probe-line"] == "upstream-high-vacuum"
    assert joined["volumes"]["vessel-crossover"] == "isolated"
    assert joined["connections"]["plasma-vessel"]["joined"] == ["qms-vessel"]
    assert joined["connections"]["qms-vessel"]["joined"] == ["plasma-vessel"]


def test_the_membrane_element_follows_the_line_configuration_not_a_press(client):
    """One source of truth: the drawn valve has no press that could disagree.

    0.11.0 recorded the `Membrane` ellipse inverted, on the reasoning that
    "membrane installed" is a barrier; 0.11.2 corrected that but still let it
    be pressed on its own. queezz, 2026-09-08 (letter `20260907-dc825e44-e6d89e`):
    "Membrane installed and the membrane 'valve' should be linked." It is now
    display-only, closed under *Membrane installed* and open under every other
    configuration, whatever a stored `elements_state.json` says for it.

    **Amended 2026-09-09** (owner correction, letter `20260908-5d638879-1b617e`):
    Boron deposition joined *closed_modes* too. The sample holder occupies the
    same physical spot the membrane, blank flange and probe all share, so it
    blocks that spot exactly as they do -- the probe pipe reaches bypass-manifold
    only through `bypass-l1` now, never through a Membrane the map used to force
    open for it.
    """
    plumbing = client.get("/plumbing").json
    element_config = client.get("/elements-config").json
    membrane_config = next(item for item in element_config if item["id"] == "Membrane")
    assert membrane_config["followsLineMode"] is True

    linked = plumbing["line_configuration"]["linked_valve"]
    # Shut by three configurations now, and only one of them draws a plug: a
    # blank flange or a sample holder closes the crossover exactly as a
    # membrane does, but there is no probe mounted at that position to draw.
    assert linked == {
        "id": "Membrane",
        "closed_modes": ["membrane", "blank", "boron"],
        "plug_mode": "membrane",
    }

    # A stale "active" (open) press recorded for Membrane is overridden by the
    # configuration on every mode -- it never gets a say.
    stale_state = {"Membrane": "active", "Rough-Bypass": "active", "bypass-l2": "active"}
    for mode, expect_open in (
        ("membrane", False),
        ("blank", False),
        ("open", True),
        ("boron", False),
        ("unknown", True),
        (None, True),
    ):
        prediction = plumbing_map.predict(plumbing, stale_state, mode)
        assert prediction["linked_valve"] == {
            "id": "Membrane",
            "status": "active" if expect_open else "inactive",
            "plug": mode == "membrane",
        }, mode
        assert prediction["volumes"]["probe-line"] == (
            "rough-vacuum" if expect_open else "isolated"
        ), mode
        # And the plug is drawn only where a probe really is mounted.
        drawn = prediction["elements"]["Membrane"]
        assert drawn["plug"] is (mode == "membrane"), mode
        assert drawn["fill"] == ("#ffffff" if mode == "membrane" else "none"), mode

    # And the reverse: a stale "inactive" (closed) press is overridden too.
    stale_closed = {"Membrane": "inactive", "Rough-Bypass": "active", "bypass-l2": "active"}
    open_from_configuration = plumbing_map.predict(plumbing, stale_closed, "open")
    assert open_from_configuration["volumes"]["probe-line"] == "rough-vacuum"


def test_the_four_line_configurations_each_paint_the_line_their_own_way(client):
    """The four queezz runs, and what each one does to the drawing.

    Owner decision 2026-09-08 (letter ``20260908-b429ce4b-2ad897``), in his own
    words: "1. membrane installed. 2. pipe open, but the membrane probe in or
    bellows, which is vacuum wise the same. 3. blank, bellows not connected.
    4. boron deposition sample holder installed. Are good and actual variants we
    run now."

    **Blank** is the new one, and it is vacuum-wise a membrane -- the crossover
    is closed at the flange -- so the connectivity assertions below are
    identical for the two. What differs is the drawing: the probe segment is
    painted in the blank-flange tone, because with the bellows disconnected
    there is no volume in it to predict, and no plug is drawn at the membrane
    position, because there is no probe mounted there.
    """
    plumbing = client.get("/plumbing").json
    colours = {state["id"]: state["color"] for state in plumbing["states"]}
    flange = plumbing["drawing"]["flange"]
    # Both sides fully pumped, every valve on both routes open, so each
    # configuration's own answer is the only thing that can differ.
    everything_open = {
        "TMPU": "active",
        "GVU": "active",
        "RoughU": "active",
        "TMPD": "active",
        "GVD": "active",
        "RoughD": "active",
        "bypass-vcr-u": "active",
        "bypass-vcr-d": "active",
        "GVBD": "active",
        "bypass-l1": "active",
    }

    # (mode, the narrow pipe, the probe segment, the cross-to-GVBD segment,
    #  the plasma vessel, the QMS vessel)
    expected = [
        (
            "membrane",
            "upstream-high-vacuum",
            "downstream-high-vacuum",
            "downstream-high-vacuum",
            "upstream-high-vacuum",
            "downstream-high-vacuum",
        ),
        (
            "open",
            "upstream-high-vacuum",
            "upstream-high-vacuum",
            "upstream-high-vacuum",
            "upstream-high-vacuum",
            "upstream-high-vacuum",
        ),
        (
            "blank",
            "upstream-high-vacuum",
            None,  # the flange tone, not a state at all
            "downstream-high-vacuum",
            "upstream-high-vacuum",
            "downstream-high-vacuum",
        ),
        (
            "boron",
            "upstream-high-vacuum",
            "downstream-high-vacuum",
            "downstream-high-vacuum",
            "upstream-high-vacuum",
            "downstream-high-vacuum",
        ),
    ]
    for mode, narrow, probe, to_gvbd, plasma, qms in expected:
        prediction = plumbing_map.predict(plumbing, everything_open, mode)
        assert prediction["volumes"]["vessel-crossover"] == narrow, mode
        assert prediction["volumes"]["plasma-vessel"] == plasma, mode
        assert prediction["volumes"]["qms-vessel"] == qms, mode
        assert prediction["elements"]["probe-pipe-cross-to-GVBD"]["stroke"] == colours[to_gvbd], mode
        segment = prediction["elements"]["probe-pipe"]
        if probe is None:
            # The blank flange: neither a state colour nor the closed grey.
            assert segment["flange"] is True, mode
            assert segment["stroke"] == flange, mode
            assert flange not in set(colours.values())
        else:
            assert segment["stroke"] == colours[probe], mode
        # And the plug is drawn under Membrane installed alone.
        assert prediction["elements"]["Membrane"]["plug"] is (mode == "membrane"), mode

    # Only *Pipe open* joins the two vessels through the narrow pipe.
    for mode in ("membrane", "blank", "boron", "unknown"):
        connections = plumbing_map.predict(plumbing, everything_open, mode)["connections"]
        assert connections["plasma-vessel"]["joined"] == [], mode
    joined = plumbing_map.predict(plumbing, everything_open, "open")["connections"]
    assert joined["plasma-vessel"]["joined"] == ["qms-vessel"]

    # The segment queezz split off in Inkscape is really in the map: it was
    # drawn and unmapped before this release, so nothing coloured it at all.
    probe_line = plumbing["volumes"]["probe-line"]["elements"]
    assert "probe-pipe-cross-to-GVBD" in probe_line
    assert "probe-pipe" in probe_line

    # The server takes the fourth configuration and refuses anything else.
    identify(client)
    assert client.post("/operation-context", json={"line_mode": "blank"}).status_code == 200
    assert client.get("/operation-context").json["line_mode"] == "blank"
    assert client.post("/operation-context", json={"line_mode": "bellows"}).status_code == 400


def test_a_stored_line_configuration_is_read_through_the_map_s_own_aliases(client):
    """A configuration recorded under an older spelling still names its mode.

    A stored annotation outlives the release that wrote it, so the map carries
    an alias table and every read goes through it. Anything the map does not
    know becomes ``unknown``: the prediction says nothing rather than guessing
    which configuration an unreadable value meant.
    """
    plumbing = client.get("/plumbing").json
    assert plumbing_map.resolve_line_mode(plumbing, "blank-flange") == "blank"
    assert plumbing_map.resolve_line_mode(plumbing, "membrane-installed") == "membrane"
    assert plumbing_map.resolve_line_mode(plumbing, "blank") == "blank"
    assert plumbing_map.resolve_line_mode(plumbing, "something-else") == "unknown"
    assert plumbing_map.resolve_line_mode(plumbing, None) == "unknown"
    # An alias predicts exactly as the mode it names.
    state = {"TMPU": "active", "GVU": "active", "bypass-vcr-u": "active"}
    assert plumbing_map.predict(plumbing, state, "blank-flange")["volumes"] == (
        plumbing_map.predict(plumbing, state, "blank")["volumes"]
    )
    # `unknown` is never offered as a button.
    assert "unknown" not in plumbing_map.line_modes(plumbing)


def test_a_pump_wears_what_it_is_doing(client):
    """A running pump says which vacuum it is making; a stopped one stays yellow.

    queezz, 2026-09-08 (letter ``20260908-3688eabd-587dfe``): "why don't we
    change the TMP on color to its HV color? Same for rough pumps. Rotaries and
    Scroll?" -- so a stopped turbo is visible at a glance and the pump-down
    guide's "start the turbo when the pressure is low" has a shape to point at.

    A turbo takes the high-vacuum colour of the **side it serves**, which is a
    fact about the rig rather than about today's valves: TMPU belongs to the
    plasma vessel whether or not GVU is open. Every pump here already had a
    confirmed on/off recorded in history like a valve, and the prediction has
    always read it -- a stopped turbo has never made high vacuum here, which
    this test also pins down.

    **A stopped pump carries no ink of ours at all (0.16.1).** 0.16.0 made it
    yellow, on a relayed line reading "stays as drawn (yellow)"; the drawing's
    own fill is grey and the yellow was the app's *on* colour, so the release
    turned the off signal into the on one. queezz, at once (letter
    ``20260908-93fb84a6-5a69cf``): "No, no! Blue and yellow, yellow reads like
    on. Gray for off was lost. Why? WHY???" So neither the prediction nor the
    operator palette gives a stopped pump a fill, and his grey stands.

    **And the whole pump recedes (0.17.0, letter ``20260908-e2498698-5c9c50``).**
    queezz: "In diagram, we can also gray out pump edges and lines. Dark gray.
    So it speaks more loudly that that is closed." A stopped pump's rim and its
    inner symbol lines go dark grey; a running one keeps the black rim and lines
    he drew, over its state colour.
    """
    plumbing = client.get("/plumbing").json
    colours = {state["id"]: state["color"] for state in plumbing["states"]}
    element_config = client.get("/elements-config").json
    pressable = {item["id"]: item for item in element_config}
    # Yellow is gone from the pumps, in the map and in the operator palette.
    assert "pump_idle" not in plumbing["drawing"]
    for pump in plumbing["pumps"]:
        assert "colors" not in pressable[pump["id"]], pump["id"]

    running = plumbing_map.predict(
        plumbing,
        {
            "TMPU": "active",
            "TMPD": "active",
            "RoughU": "active",
            "Rough-Bypass": "active",
        },
        "membrane",
    )
    assert running["elements"]["TMPU"]["fill"] == colours["upstream-high-vacuum"]
    assert running["elements"]["TMPD"]["fill"] == colours["downstream-high-vacuum"]
    assert running["elements"]["RoughU"]["fill"] == colours["rough-vacuum"]
    assert running["elements"]["Rough-Bypass"]["fill"] == colours["rough-vacuum"]
    # RoughD was not pressed, so nothing gives it a fill and it keeps his grey.
    # Its rim and inner lines recede to the map's own dark grey.
    recessed = plumbing["drawing"]["pump_stopped_edge"]
    assert running["elements"]["RoughD"]["running"] is False
    assert "fill" not in running["elements"]["RoughD"]
    assert running["elements"]["RoughD"]["stroke"] == recessed
    for part in next(p for p in plumbing["pumps"] if p["id"] == "RoughD")["parts"]:
        assert running["elements"][part]["stroke"] == recessed, part
    # And a running pump's parts keep the black he drew them with.
    for part in next(p for p in plumbing["pumps"] if p["id"] == "TMPU")["parts"]:
        assert running["elements"][part]["stroke"] == "#000000", part

    # Every pump answers, keeps the black outline it was drawn with, and is an
    # ordinary confirmed toggle an operator presses and history records.
    for pump in plumbing["pumps"]:
        item = running["elements"][pump["id"]]
        assert item["pump"] is True, pump["id"]
        assert pump["id"] in pressable, pump["id"]
        if item["running"]:
            assert item["stroke"] == "#000000", pump["id"]
            assert item["fill"] in set(colours.values()), pump["id"]
        else:
            assert "fill" not in item, pump["id"]
            assert item["stroke"] == recessed, pump["id"]

    # A turbo that is not running makes no high vacuum, and nothing has shut on
    # its own line either, so that line is not sealed: it is simply isolated.
    stopped = plumbing_map.predict(plumbing, {"GVU": "active"}, "membrane")
    assert stopped["volumes"]["plasma-vessel"] == "isolated"
    assert "fill" not in stopped["elements"]["TMPU"]
    # The saved render writes a stopped pump its recessed rim and nothing else:
    # no fill at all, so the grey queezz drew still stands underneath it.
    saved = plumbing_map.style_rules(plumbing, {"GVU": "active"}, "membrane")
    assert f"#TMPU{{stroke:{recessed} !important}}" in saved
    # And a turbo behind a shut gate still says which side it belongs to -- and
    # so does the stub between them, which is high vacuum, not a state of its
    # own (owner correction 2026-09-08, letter 20260908-fe94c769-493d71).
    behind_the_gate = plumbing_map.predict(plumbing, {"TMPU": "active"}, "membrane")
    assert behind_the_gate["volumes"]["plasma-turbo-line"] == "upstream-high-vacuum"
    assert behind_the_gate["elements"]["TMPU"]["fill"] == colours["upstream-high-vacuum"]


def test_a_beacon_stands_off_the_shape_and_never_takes_the_pointer(client):
    """The numbered beacons stopped covering the valves they point at.

    queezz, 2026-09-08, with Vent Plasma running (letter
    ``20260908-3688eabd-587dfe``): "venting plasma works. But numbered circles
    are obstructing the interactions." The disc sat on the middle of the very
    valve the step was asking him to press. Two halves to the repair, and the
    larger one is the placement: the disc now stands at the element's top-right
    corner, stepped further out along the diagonal, so the valve underneath
    stays visible and can be aimed at. The other half is that every part of a
    beacon says it takes no pointer, rather than relying on inheritance.

    The pulse itself is proved in a browser, never here: a stylesheet that reads
    correct is exactly what hid the dead beacon for two releases.
    """
    css = (PROJECT_ROOT / "src" / "pihti" / "static" / "css" / "styles.css").read_text(
        encoding="utf-8"
    )
    assert "#operation-guide-overlay { pointer-events: none; }" in css
    assert ".operation-marker { pointer-events: none;" in css
    assert ".operation-marker circle, .operation-marker text { pointer-events: none; }" in css

    script = (PROJECT_ROOT / "src" / "pihti" / "static" / "js" / "diagram.js").read_text(
        encoding="utf-8"
    )
    # The corner, not the middle: `rect.right`/`rect.top` rather than the
    # centre the placement used before.
    assert "corner.x = rect.right;" in script
    assert "corner.y = rect.top;" in script
    assert "MARKER_STEP" in script
    # A step's own authored nudge still applies on top of the corner.
    assert 'point.x += (offset || [0, 0])[0];' in script

    # And every id a guide step marks is still a real element with a name, so
    # the moved beacon is still pointing at something a person can be told to
    # press.
    guides = client.get("/operation-guides").json
    names = {item["id"] for item in client.get("/elements-config").json}
    svg = (PROJECT_ROOT / "src" / "pihti" / "static" / "diagram.svg").read_text(
        encoding="utf-8"
    )
    for guide in guides["guides"]:
        for step in guide["steps"]:
            marked = list(step.get("targets") or [])
            marked += list(step.get("marks") or [])
            if step.get("targetId"):
                marked.append({"id": step["targetId"]})
            for target in marked:
                assert target["id"] in names, (guide["id"], target["id"])
                assert f'id="{target["id"]}"' in svg, (guide["id"], target["id"])


def test_membrane_cannot_be_set_directly(client):
    """`/update` refuses the linked valve outright -- no press of its own."""
    identify(client)
    response = client.post("/update", json={"id": "Membrane", "status": "active"})
    assert response.status_code == 400
    assert "Line configuration" in response.json["error"]


def test_a_press_that_would_reach_a_live_ion_gauge_warns(client):
    """queezz, 2026-09-08: "create warning when putting gas/air on to IG".

    The same valve press either warns or does not, and the only difference
    between the two runs is whether the ionization gauge is switched on. Both
    halves of the warning are checked: vent air arriving at the QMS vessel's
    own ionization gauge, and gas arriving at the upstream one -- which sits on
    the plasma vessel's gauge manifold since queezz moved it there in the
    drawing (2026-09-08, letter ``20260908-c8ef7df5-5f5e40``), which is exactly
    why the plasma side has a gas-and-air warning at all now.
    """
    plumbing = client.get("/plumbing").json

    # Vent air, one gate valve away from a switched-on QMS ionization gauge:
    # the gas panel is vented, its argon valve and the flow-calibration valve
    # are open, so only GVBD stands between that air and the QMS vessel.
    route = {
        "gaspanel-valve-vent": "active",
        "gaspanel-valve-ar": "active",
        "flow-calibration-valve": "active",
    }
    live = {**route, "downstream-ionization-gauge": "active"}
    warned = plumbing_map.press_warnings(plumbing, live, "GVBD", "active", "unknown")
    assert warned == [
        {
            "kind": "gauge",
            "id": "downstream-ionization-gauge",
            "volume": "qms-vessel",
            "state": "air",
            "level": 2,
        }
    ]
    # The identical press with the gauge switched off is an ordinary press.
    assert plumbing_map.press_warnings(plumbing, route, "GVBD", "active", "unknown") == []

    # Gas, and the upstream ionization gauge on the plasma vessel. Argon is on
    # the argon line and through to the gas manifold; the press is the main gas
    # valve, which is the one that lets it into the vessel.
    gas = {"argon-bottle": "active", "gasline-ar": "active"}
    assert [
        gauge["volume"]
        for gauge in plumbing["gauges"]
        if gauge["id"] == "bypass-ionization-gauge"
    ] == ["plasma-vessel"]
    on_gas = plumbing_map.press_warnings(
        plumbing,
        {**gas, "bypass-ionization-gauge": "active"},
        "gasline-main",
        "active",
        "membrane",
    )
    assert [(item["id"], item["state"]) for item in on_gas] == [
        ("bypass-ionization-gauge", "gas")
    ]
    assert plumbing_map.press_warnings(plumbing, gas, "gasline-main", "active", "membrane") == []

    # Switching the gauge on into a volume that already holds air is the same
    # mistake from the other side, and warns too.
    into_air = plumbing_map.press_warnings(
        plumbing, {**route, "GVBD": "active"}, "downstream-ionization-gauge", "active", "unknown"
    )
    assert [item["id"] for item in into_air] == ["downstream-ionization-gauge"]


def test_a_press_that_would_vent_a_running_turbo_warns(client):
    """queezz, 2026-09-08: "and when vent goes on to TMP".

    A running turbo is a boundary in the prediction, so the volume that matters
    is the pump's own — the one the vent would actually join — never everything
    behind it. Venting the backing line under a spinning turbo therefore does
    not warn: nothing in this map joins a foreline to the vessel above its
    pump.
    """
    plumbing = client.get("/plumbing").json
    vented_gas_line = {
        "gaspanel-valve-vent": "active",
        "gaspanel-valve-ar": "active",
        "gasline-ar": "active",
        "gasline-main": "active",
    }
    warned = plumbing_map.press_warnings(
        plumbing, {**vented_gas_line, "TMPU": "active"}, "GVU", "active", "unknown"
    )
    assert warned == [
        {
            "kind": "turbo",
            "id": "TMPU",
            "volume": "plasma-turbo-line",
            "state": "air",
            "level": 2,
        }
    ]
    # The same press with the turbo stopped is an ordinary press.
    assert plumbing_map.press_warnings(
        plumbing, vented_gas_line, "GVU", "active", "unknown"
    ) == []
    # The backing line is on the far side of the pump, so its vent is quiet.
    assert plumbing_map.press_warnings(
        plumbing, {"TMPU": "active"}, "upstream-pumpline-vent-valve", "active", "unknown"
    ) == []


def test_a_press_that_changes_nothing_dangerous_is_quiet(client):
    """Only what a press makes worse is worth a sentence.

    A gauge that works at one atmosphere is never warned about, a press that
    joins nothing has nothing to say, closing a vent is an improvement rather
    than a warning, and a hazard that is already standing does not cry twice.
    """
    plumbing = client.get("/plumbing").json
    vented = {
        "gaspanel-valve-vent": "active",
        "gaspanel-valve-ar": "active",
        "flow-calibration-valve": "active",
        "GVBD": "active",
        # ...and on to the plasma vessel as well, which is where the upstream
        # ionization gauge has sat since queezz moved it (2026-09-08).
        "gasline-ar": "active",
        "gasline-main": "active",
    }
    # Only the two gauges the map marks `ionization` are counted; queezz named
    # the rest as working at one atmosphere (2026-09-04).
    ionization = {gauge["id"] for gauge in plumbing["gauges"] if gauge.get("kind") == "ionization"}
    assert ionization == {"bypass-ionization-gauge", "downstream-ionization-gauge"}
    for gauge in plumbing["gauges"]:
        expected = [gauge["id"]] if gauge["id"] in ionization else []
        warned = plumbing_map.press_warnings(
            plumbing, vented, gauge["id"], "active", "unknown"
        )
        assert [item["id"] for item in warned] == expected, gauge["id"]

    # A press that joins nothing dangerous, on a rig with everything shut.
    assert plumbing_map.press_warnings(plumbing, {}, "bypass-l2", "active", "unknown") == []
    # Closing the vent that caused the exposure is not a new exposure.
    live = {**vented, "downstream-ionization-gauge": "active"}
    assert plumbing_map.press_warnings(
        plumbing, live, "gaspanel-valve-vent", "inactive", "unknown"
    ) == []
    # Nor is an unrelated press while the gauge already stands in that air.
    assert plumbing_map.press_warnings(plumbing, live, "bypass-l2", "active", "unknown") == []


def test_the_press_warning_route_answers_before_the_press_and_writes_nothing(tmp_path):
    """The page asks this before its confirm box; it is a read, never a press."""
    state_file = tmp_path / "elements_state.json"
    before = {
        "gaspanel-valve-vent": "active",
        "gaspanel-valve-ar": "active",
        "flow-calibration-valve": "active",
        "downstream-ionization-gauge": "active",
    }
    state_file.write_text(json.dumps(before), encoding="utf-8")
    client = make_app(tmp_path).test_client()

    answer = client.get("/press-warnings", query_string={"id": "GVBD", "status": "active"})
    assert answer.status_code == 200
    assert [item["id"] for item in answer.json["warnings"]] == ["downstream-ionization-gauge"]
    assert answer.json["warnings"][0]["state"] == "air"

    quiet = client.get("/press-warnings", query_string={"id": "bypass-l2", "status": "active"})
    assert quiet.json == {"warnings": []}

    # An old id from a real history still resolves, and junk is refused.
    assert client.get(
        "/press-warnings", query_string={"id": "GVU-6", "status": "active"}
    ).status_code == 200
    for query in (
        {"id": "not-an-element", "status": "active"},
        {"id": "GVBD", "status": "maybe"},
        {},
    ):
        assert client.get("/press-warnings", query_string=query).status_code == 400

    # Asking about a press does not make it: the stored state is untouched.
    assert json.loads(state_file.read_text(encoding="utf-8")) == before
    assert client.get("/elements-state").json == before


def test_every_body_on_the_drawing_is_filled_with_its_full_state_colour(client):
    """A vessel says its state by its body, and so does a tee and a cross.

    queezz, 2026-09-08: "main vessels shape fill is a bit too quiet. We can go
    very loud, why not? Color it the color of the vacuum I say. Or gas. Or
    air." — which supersedes the light tint of 0.11.2. And, the same morning:
    "the Ts and Cross in the bypass don't get colored, stay white. Bad." These
    are the drawing's opaque white junction shapes, so no white tee
    or cross can survive in any state. Every other element the map names is a
    line and keeps its authored fill.
    """
    plumbing = client.get("/plumbing").json
    colours = {state["id"]: state["color"] for state in plumbing["states"]}
    svg_root = ET.parse(PROJECT_ROOT / "src" / "pihti" / "static" / "diagram.svg").getroot()
    authored = {
        element.get("id"): element.get("style") or ""
        for element in svg_root.iter()
        if element.get("id")
    }

    bodies = {}
    for name, volume in plumbing["volumes"].items():
        for element_id in list(volume.get("junctions") or ()) + (
            [volume["vessel"]] if volume.get("vessel") else []
        ):
            bodies[element_id] = name
    assert set(bodies) == {
        "plasma-vacuum",
        "qms-vacuum",
        "bypass-manifold-t-downstream-t",
        "bypass-manifold-t-downstream-t-abs",
        "bypass-manifold-t-upstream",
        "probe-pipe-cross",
    }
    for element_id, name in bodies.items():
        assert element_id in authored, element_id
        assert element_id in plumbing["volumes"][name]["elements"], element_id
    # Exactly the shapes queezz drew with an opaque body, and nothing else.
    white = sorted(
        element_id for element_id, style in authored.items() if "fill:#ffffff" in style
    )
    assert set(white) <= set(bodies)

    # "membrane" here (rather than "open") keeps the linked `Membrane` valve
    # closed (0.12.1), so probe-pipe-cross stays genuinely isolated from the
    # high-vacuum bypass manifold beside it rather than joining through it.
    prediction = plumbing_map.predict(
        plumbing,
        {"TMPU": "active", "GVU": "active", "RoughU": "active", "GVBU": "active"},
        "membrane",
    )
    upstream = colours["upstream-high-vacuum"]
    assert prediction["elements"]["plasma-vacuum"]["fill"] == upstream
    assert prediction["elements"]["qms-vacuum"]["fill"] == colours["isolated"]
    assert prediction["elements"]["bypass-manifold-t-upstream"]["fill"] == upstream
    assert prediction["elements"]["bypass-manifold-t-downstream-t-abs"]["fill"] == upstream
    assert prediction["elements"]["bypass-manifold-downstream-line-two-t"]["stroke"] == upstream
    assert prediction["elements"]["probe-pipe-cross"]["fill"] == colours["isolated"]
    # A body says its state with its body, edge and all. queezz, 2026-09-08:
    # "I think I'd like it without black shape borders. All one color. Why not?
    # Color speaks vacuum. Black border speaks... shapes?" So the outline takes
    # the same colour as the fill and stops reading as an outline; valves,
    # pumps and gauges keep the black he drew.
    for element_id in bodies:
        item = prediction["elements"][element_id]
        assert item["stroke"] == item["fill"], element_id
    rendered = plumbing_map.style_rules(
        plumbing,
        {"TMPU": "active", "GVU": "active", "RoughU": "active", "GVBU": "active"},
        "membrane",
    )
    assert (
        f"#plasma-vacuum{{stroke:{upstream} !important;fill:{upstream} !important;"
        "stroke-linecap:round;stroke-linejoin:round}" in rendered
    )
    assert "fill" not in prediction["elements"]["plasma-vacuum-gate-port"]
    assert "fill" not in prediction["elements"]["upstream-to-downstream-narrow-pipe"]


def test_every_gauge_stem_takes_the_colour_of_the_volume_it_reads(client):
    """The short line from a gauge to what it reads is part of that volume.

    queezz, 2026-09-08: "all gauges stems don't have colors. They are inside a
    gauge group. If we can work with that, fine. If not, I'll name them." It
    can be worked with, and this test is why it is not a guess: each recorded
    stem is the one plain line that is either the gauge's own sibling inside its
    group, or the line drawn immediately before the gauge at the top level. A
    regroup in Inkscape that moved a stem away from its gauge fails here rather
    than quietly colouring the wrong pipe.
    """
    plumbing = client.get("/plumbing").json
    svg_root = ET.parse(PROJECT_ROOT / "src" / "pihti" / "static" / "diagram.svg").getroot()
    svg = "{http://www.w3.org/2000/svg}"
    parents = {child: parent for parent in svg_root.iter() for child in parent}

    by_id = {element.get("id"): element for element in svg_root.iter() if element.get("id")}
    mapped = {
        element_id
        for volume in plumbing["volumes"].values()
        for element_id in volume["elements"]
    }
    seen = set()
    for gauge in plumbing["gauges"]:
        stem_id = gauge["stem"]
        assert gauge["volume"] in plumbing["volumes"], gauge
        assert stem_id not in seen, stem_id
        seen.add(stem_id)
        assert stem_id not in mapped, stem_id
        stem, symbol = by_id.get(stem_id), by_id.get(gauge["id"])
        assert stem is not None and symbol is not None, gauge
        assert stem.tag == f"{svg}path", stem_id
        siblings = list(parents[symbol])
        assert parents[stem] is parents[symbol], stem_id
        assert siblings.index(stem) == siblings.index(symbol) - 1, stem_id

    prediction = plumbing_map.predict(
        plumbing, {"TMPD": "active", "GVD": "active", "RoughD": "active"}, "open"
    )
    colours = {state["id"]: state["color"] for state in plumbing["states"]}
    for gauge in plumbing["gauges"]:
        item = prediction["elements"][gauge["stem"]]
        assert item["volume"] == gauge["volume"], gauge
        assert item["stroke"] == colours[prediction["volumes"][gauge["volume"]]], gauge
    assert prediction["elements"]["path1464-1-2-8-9-3-8"]["state"] == "downstream-high-vacuum"
    assert prediction["elements"]["path1464-1-2-8-9-7"]["state"] == "isolated"
    # The upstream ionization gauge reads the plasma vessel since queezz moved
    # it onto that vessel's gauge manifold (2026-09-08), so its stem takes the
    # plasma vessel's colour and the bypass manifold keeps only its Ulvac.
    assert prediction["elements"]["path1464-1-2-8-9-3"]["volume"] == "plasma-vessel"
    on_bypass = [
        gauge["id"] for gauge in plumbing["gauges"] if gauge["volume"] == "bypass-manifold"
    ]
    assert on_bypass == ["bypass-absolute-gauge"]


def test_a_coloured_pipe_is_widened_solidly_and_an_isolated_one_is_not(client):
    """The band replaces the glow queezz called ugly, and it is solid.

    "That's more readable, yes. Also way more ugly" (2026-09-08), of the 0.11.2
    halo: a translucent 2.8x clone under every pipe, the same weight whatever
    the state, which read as a neon sign. What replaces it is a plain multiple
    of the width he drew each line with — his own thin-tubing-thick-pipe
    hierarchy survives it — with no second layer, no opacity, and nothing at all
    added to an isolated line.
    """
    plumbing = client.get("/plumbing").json
    band = plumbing["drawing"]["band"]
    assert 1 < band <= 2, band
    # Off by default from 0.15.0: his own strokes are the width he wants
    # (letter 20260908-c8ef7df5-5f5e40), and the switch still offers the widening.
    assert plumbing["drawing"]["band_default"] is False

    prediction = plumbing_map.predict(
        plumbing, {"TMPU": "active", "GVU": "active", "RoughU": "active"}, "open"
    )
    assert prediction["elements"]["plasma-vacuum-gv-to-tmp-pipe"]["band"] == band
    assert "band" not in prediction["elements"]["qms-sensor-pipe"]
    assert prediction["elements"]["qms-sensor-pipe"]["state"] == "isolated"

    script = (PROJECT_ROOT / "src" / "pihti" / "static" / "js" / "diagram.js").read_text(
        encoding="utf-8"
    )
    css = (PROJECT_ROOT / "src" / "pihti" / "static" / "css" / "styles.css").read_text(
        encoding="utf-8"
    )
    assert 'box.id = "pipe-band"' in script
    assert "authored * item.band" in script
    assert 'bandOn = stored === "on";' in script
    assert "let bandOn = false;" in script
    # No clone layer, no translucency, and the drawing itself is never edited.
    assert "pipe-halo-layer" not in script and "pipe-halo-layer" not in css
    assert "strokeOpacity" not in script
    svg = (PROJECT_ROOT / "src" / "pihti" / "static" / "diagram.svg").read_text(encoding="utf-8")
    assert "pipe-band" not in svg


def test_every_state_colour_is_readable_on_the_diagram_ground(client):
    """Seven colours, designed for the eye and checked by arithmetic.

    Two owner letters wrote this test. The first (2026-09-08,
    ``20260908-630efd50-e4c7ab``) retired the constraint the previous seven were
    built under: "On the Tol muted colors... I don't want muted, actually. No
    color blind people here. But those colors are nicer than maxed RGBs. So
    design nice, not color blind nice. Tol inspired is still fine." The second
    (``20260908-92656592-3a679a``) said what had gone wrong without it: "Gas
    color and rough vacuum color are indistinguishable", and asked for the check
    to be **pairwise**, in numbers, with the smallest pair named.

    So the ladder of weight is gone -- it was the colour-vision aid, and it was
    what crowded all seven into the dark end where a plum and an ochre look
    alike on a 4 px line. What replaces it is hue: six of the seven now sit at
    nearly one lightness and are told apart by where they stand on the colour
    circle. What stays is the floor -- 3:1 against the stone field the drawing
    is painted on, and against the one green valve the prediction does not
    paint -- which caps a colour's own luminance at about 0.204 and is why these
    are deep jewel tones rather than Tol's own lightness.
    """
    css = (PROJECT_ROOT / "src" / "pihti" / "static" / "css" / "styles.css").read_text(
        encoding="utf-8"
    )
    plumbing = client.get("/plumbing").json
    ground = plumbing["drawing"]["ground"]
    # One field, recorded in two places because CSS paints it and the map
    # documents it; they may never drift apart.
    assert f"--diagram-ground: {ground};" in css
    # The gas panel's nitrogen valve is a gas source rather than a valve in the
    # map, so it keeps the operator green and a state colour must stay readable
    # against it too.
    operator_green = "#9bf08d"

    def channels(value):
        return [int(value.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]

    def linear(value):
        return [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels(value)]

    def luminance(value):
        red, green, blue = linear(value)
        return 0.2126 * red + 0.7152 * green + 0.0722 * blue

    def contrast(one, other):
        first, second = luminance(one), luminance(other)
        return (max(first, second) + 0.05) / (min(first, second) + 0.05)

    def lab(value):
        """CIE L*a*b*, so two colours can be compared as the eye compares them."""
        rgb = linear(value)
        matrix = (
            (0.4124564, 0.3575761, 0.1804375),
            (0.2126729, 0.7151522, 0.0721750),
            (0.0193339, 0.1191920, 0.9503041),
        )
        white = (0.95047, 1.0, 1.08883)
        xyz = [sum(row[i] * rgb[i] for i in range(3)) / white[j] for j, row in enumerate(matrix)]
        f = [t ** (1 / 3) if t > 216 / 24389 else (841 / 108) * t + 4 / 29 for t in xyz]
        return (116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2]))

    def chroma(value):
        _, a, b = lab(value)
        return math.hypot(a, b)

    def hue(value):
        _, a, b = lab(value)
        return math.degrees(math.atan2(b, a)) % 360

    def ciede2000(one, other):
        """The CIE's own 2000 colour-difference formula, as the letter asked."""
        light1, a1, b1 = lab(one)
        light2, a2, b2 = lab(other)
        chroma1, chroma2 = math.hypot(a1, b1), math.hypot(a2, b2)
        mean_chroma = (chroma1 + chroma2) / 2
        grey = 0.5 * (1 - math.sqrt(mean_chroma**7 / (mean_chroma**7 + 25**7))) if mean_chroma else 0.5
        a1p, a2p = (1 + grey) * a1, (1 + grey) * a2
        c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
        h1p = math.degrees(math.atan2(b1, a1p)) % 360 if (a1p or b1) else 0.0
        h2p = math.degrees(math.atan2(b2, a2p)) % 360 if (a2p or b2) else 0.0
        d_light = light2 - light1
        d_chroma = c2p - c1p
        if c1p * c2p == 0:
            d_hue_angle = 0.0
        else:
            raw = h2p - h1p
            d_hue_angle = raw - 360 if raw > 180 else raw + 360 if raw < -180 else raw
        d_hue = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(d_hue_angle) / 2)
        mean_light = (light1 + light2) / 2
        mean_c = (c1p + c2p) / 2
        if c1p * c2p == 0:
            mean_hue = h1p + h2p
        else:
            total = h1p + h2p
            if abs(h1p - h2p) > 180:
                mean_hue = (total + 360) / 2 if total < 360 else (total - 360) / 2
            else:
                mean_hue = total / 2
        weight = (
            1
            - 0.17 * math.cos(math.radians(mean_hue - 30))
            + 0.24 * math.cos(math.radians(2 * mean_hue))
            + 0.32 * math.cos(math.radians(3 * mean_hue + 6))
            - 0.20 * math.cos(math.radians(4 * mean_hue - 63))
        )
        turn = 30 * math.exp(-(((mean_hue - 275) / 25) ** 2))
        roll = 2 * math.sqrt(mean_c**7 / (mean_c**7 + 25**7)) if mean_c else 0.0
        s_light = 1 + (0.015 * (mean_light - 50) ** 2) / math.sqrt(20 + (mean_light - 50) ** 2)
        s_chroma = 1 + 0.045 * mean_c
        s_hue = 1 + 0.015 * mean_c * weight
        rotation = -math.sin(math.radians(2 * turn)) * roll
        return math.sqrt(
            (d_light / s_light) ** 2
            + (d_chroma / s_chroma) ** 2
            + (d_hue / s_hue) ** 2
            + rotation * (d_chroma / s_chroma) * (d_hue / s_hue)
        )

    states = {state["id"]: state["color"] for state in plumbing["states"]}
    # Six since 0.17.0: the teal seventh, "pumped, sealed off", was retired by
    # the owner's own correction -- sealed off is a remembered state now, and it
    # wears the hatched colour of whatever the volume was last under.
    assert set(states) == {
        "air",
        "gas",
        "upstream-high-vacuum",
        "downstream-high-vacuum",
        "rough-vacuum",
        "isolated",
    }
    assert len(set(states.values())) == len(states)

    # The floor, on both fields the colours are read against.
    for name, colour in states.items():
        assert contrast(colour, ground) >= 3.0, (name, contrast(colour, ground))
        assert contrast(colour, operator_green) >= 3.0, (name, contrast(colour, operator_green))
    # Isolated is the quietest of them on purpose: it is the absence of a
    # claim, not one more thing competing for the eye.
    quietest = min(states, key=lambda name: contrast(states[name], ground))
    assert quietest == "isolated"

    # Designed, not muted and not maxed. Every colour but the deliberately grey
    # `isolated` carries real chroma, and none of them is a maxed primary.
    for name, colour in states.items():
        if name == "isolated":
            assert chroma(colour) < 15, (name, chroma(colour))
            continue
        assert chroma(colour) >= 25, (name, round(chroma(colour), 1))
        assert set(channels(colour)) != {0.0, 1.0}, name
        assert max(channels(colour)) < 1.0, name

    # Every PAIR must be told apart, on a 4 px line and on a chip alike -- the
    # letter's own rule, checked pairwise rather than only against the field.
    # 18 CIEDE2000 units is a comfortable margin; the closest pair of the seven
    # was the plasma blue against the sealed teal at about 21, where the palette
    # this replaced had a pair at 11.6, and the teal has since gone.
    names = sorted(states)
    pairs = [
        (ciede2000(states[first], states[second]), first, second)
        for index, first in enumerate(names)
        for second in names[index + 1 :]
    ]
    closest = min(pairs)
    assert closest[0] >= 18, (closest[1], closest[2], round(closest[0], 1))

    # And the one pair queezz named by hand may not merely clear that bar: gas
    # and rough vacuum must sit in different hue families. "Gas color and rough
    # vacuum color are indistinguishable" was said about a plum and an ochre,
    # both warm and both dark.
    apart = abs(hue(states["gas"]) - hue(states["rough-vacuum"])) % 360
    assert min(apart, 360 - apart) >= 90, round(apart, 1)

    # And the legend shows enough of each colour to judge it there: a full
    # swatch rather than a thin bar. **One legend, not two** since 0.19.0
    # (owner, letter 20260908-c03c1788-9def42, on the first build of the rail
    # card: "Why do we need two legends?"). The chips ARE the swatches, two to
    # a row so seven fit the rail; the second board of bigger ones inside More
    # is gone, and so are the thirteen sentences that followed it.
    script = (PROJECT_ROOT / "src" / "pihti" / "static" / "js" / "diagram.js").read_text(
        encoding="utf-8"
    )
    assert "swatch.style.backgroundColor = colour;" in script
    assert "vacuum-swatch-row" not in script and "vacuum-swatch-row" not in css
    assert "vacuum-swatch-big" not in script and "vacuum-swatch-big" not in css
    assert "grid-template-columns: repeat(auto-fit, minmax(104px, 1fr));" in css
    # One short line per chip behind More, and three for the drawing's rules.
    for state in json.loads(
        (PROJECT_ROOT / "src" / "pihti" / "static" / "plumbing.json").read_text(
            encoding="utf-8"
        )
    )["states"]:
        assert len(state["meaning"].split()) <= 6, state["id"]
    # Three short lines for the drawing's own rules, where thirteen sentences
    # and a second swatch board used to stand.
    rules = script.split('document.getElementById("vacuum-meanings")?.replaceChildren(...lines);')[0].rsplit("].forEach", 1)[0]
    rules = rules.rsplit("[", 1)[1]
    assert len([line for line in rules.splitlines() if line.strip().startswith('"')]) == 2
    # Owner dark-mode review: both switches lead More, before its meanings,
    # where they cannot be toggled accidentally while reading the legend.
    assert 'document.getElementById("vacuum-band")' in script
    assert '" Draw thick pipes"' in script
    for path in ("index.html", "history.html"):
        page = (PROJECT_ROOT / "src" / "pihti" / "templates" / path).read_text(
            encoding="utf-8"
        )
        assert page.index('id="vacuum-more"') < page.index('id="vacuum-band"'), path
        assert page.index('id="vacuum-band"') < page.index('id="vacuum-meanings"'), path
    # The old thin-bar rule is gone rather than left behind to confuse the next
    # reader: nothing writes a `<i>` inside a swatch any more. The readout under
    # the drawing still did until 0.17.0, and its chips drew empty for it.
    assert ".vacuum-swatch i" not in css
    assert 'document.createElement("i")' not in script
    # The colour is written as `backgroundColor`, never the `background`
    # shorthand, which would reset the background-image the sealed hatch is.
    assert "style.background =" not in script


def test_a_saved_render_really_carries_the_prediction(client):
    """The drawing's own inline styles used to win, so nothing was coloured.

    Every pipe in ``diagram.svg`` carries ``stroke:#000000`` in a ``style``
    attribute, and an inline style beats a stylesheet — so the plain rules
    ``/state.svg`` used to write were overridden and a saved render came back
    black. They are ``!important`` now, and a test reads the rendered file.
    """
    plumbing = client.get("/plumbing").json
    rendered = client.get("/state.svg").data.decode("utf-8")
    assert "#upstream-tmp-to-rotary-pipe{stroke:" in rendered
    assert rendered.count("!important") > len(plumbing["volumes"])
    colours = {state["color"] for state in plumbing["states"]}
    assert any(f"stroke:{colour} !important" in rendered for colour in colours)
    assert "#plasma-vacuum{" in rendered
    assert any(f"fill:{colour} !important" in rendered for colour in colours)
    # A saved render carries the band too, or it reads differently from the
    # screen it was saved from. The width is a multiple of the authored one.
    widths = plumbing_map.authored_stroke_widths(
        (PROJECT_ROOT / "src" / "pihti" / "static" / "diagram.svg").read_text(encoding="utf-8")
    )
    assert widths["upstream-tmp-to-rotary-pipe"] == pytest.approx(8)
    banded = round(widths["upstream-tmp-to-rotary-pipe"] * plumbing["drawing"]["band"], 3)
    # The widening is off on both sides by default now, so the saved render is
    # his own widths — and `?wide=1` matches a browser with the switch on.
    assert f"stroke-width:{banded} !important" not in rendered
    widened = client.get("/state.svg", query_string={"wide": "1"}).data.decode("utf-8")
    assert f"stroke-width:{banded} !important" in widened
    # Round caps and joins close the seams a butt end leaves at a junction.
    assert "stroke-linecap:round;stroke-linejoin:round" in rendered


def test_the_guide_beacons_keep_their_ring_under_the_colour_layer():
    """The numbered beacons, and the one cascade rule that broke them.

    queezz, 2026-09-08: "pic 2, the beacon css broken in the vent guide". The
    ring behind a current step is a `<circle class="halo">` that must stay
    unfilled — but `.operation-marker.current circle` is one element more
    specific than `.operation-marker .halo`, so its fill won and the ring was a
    solid disc of the step's colour breathing outward. Every disc rule now says
    `circle:not(.halo)`, and this test fails if one is ever written without it.
    """
    css = (PROJECT_ROOT / "src" / "pihti" / "static" / "css" / "styles.css").read_text(
        encoding="utf-8"
    )
    marker_rules = [
        line
        for line in css.splitlines()
        if line.startswith(".operation-marker")
        and "circle" in line
        and "pointer-events" not in line
    ]
    assert len(marker_rules) >= 4
    for rule in marker_rules:
        assert "circle:not(.halo)" in rule, rule
    assert ".operation-marker .halo { display: none; fill: none;" in css
    # The ring is drawn in the marker's own ink: white vanished on the field
    # that replaced coral.
    assert "stroke: #1c1f26; stroke-width: 3; opacity: 0.9; }" in css

    # 0.14.0, and the reason the 0.12.0 repair above did not make the beacon
    # pulse: `prefers-reduced-motion: reduce` said `animation: none`, and
    # Windows with its animation effects switched off makes Chromium — so
    # Brave — answer true to that query. Measured live: `getAnimations()` empty,
    # computed `animation-name: none`, the ring frozen. Under reduce the beacon
    # now keeps a pulse and loses only the motion: one radius, opacity alone.
    reduced = css.split("@media (prefers-reduced-motion: reduce)")[1].split("}\n}")[0]
    assert "animation: none" not in reduced
    assert "marker-halo-quiet" in reduced
    assert "@keyframes marker-halo-quiet" in css
    quiet = css.split("@keyframes marker-halo-quiet")[1]
    assert "r:" not in quiet.split("}\n}")[0], "reduced motion must not move the ring"
    # A CSS length needs its unit; `r: 18` is not one everywhere.
    for frame in css.split("@keyframes marker-halo {")[1].split("}")[0].split(";"):
        if frame.strip().startswith("r:"):
            assert "px" in frame, frame
    script = (PROJECT_ROOT / "src" / "pihti" / "static" / "js" / "diagram.js").read_text(
        encoding="utf-8"
    )
    # The beacons are still drawn last, so nothing the colour layer fills can
    # ever be painted over them.
    assert script.index("svg.appendChild(overlay)") > script.index('overlay.id = "operation-guide-overlay"')


def test_each_vessel_says_in_words_what_it_is_joined_to(client):
    """The readout queezz asked for, in his own order and from one prediction.

    "I'd like to see if upstream and downstream are connected to a) each other
    b) gas c) vent air" (2026-09-08). The facts come from the same open valves
    the colours come from; the page turns them into a sentence using the names
    a person uses at the rig.

    One difference from the colouring, and it matters here: the room is not a
    pipe. Two separately vented lines share the ``atmosphere`` volume and are
    both honestly painted red, but they are not plumbed to each other, so the
    reach used for this readout never runs through open air.
    """
    plumbing = client.get("/plumbing").json

    shut = plumbing_map.predict(plumbing, {}, "membrane")["connections"]
    assert list(shut) == ["plasma-vessel", "qms-vessel"]
    assert shut["plasma-vessel"]["label"] == "Plasma vessel"
    for vessel in shut.values():
        assert vessel["state"] == "isolated"
        assert (vessel["joined"], vessel["gas"], vessel["air"], vessel["pumps"]) == ([], [], [], [])

    joined = plumbing_map.predict(
        plumbing,
        {
            "bypass-vcr-u": "active",
            "bypass-vcr-d": "active",
            "TMPU": "active",
            "GVU": "active",
            "gasline-main": "active",
            "gasline-ar": "active",
            "argon-bottle": "active",
        },
        "open",
    )["connections"]
    assert joined["plasma-vessel"]["joined"] == ["qms-vessel"]
    assert joined["qms-vessel"]["joined"] == ["plasma-vessel"]
    assert [source["gas"] for source in joined["plasma-vessel"]["gas"]] == ["argon"]
    assert [pump["id"] for pump in joined["qms-vessel"]["pumps"]] == ["TMPU"]
    assert joined["plasma-vessel"]["state"] == "gas"

    # Air reaches the plasma vessel down the gas line, which is a route; it does
    # not reach it through a running turbo, which is a boundary.
    through_the_gas_line = {
        "gaspanel-valve-vent": "active",
        "gaspanel-valve-ar": "active",
        "gasline-ar": "active",
        "gasline-main": "active",
    }
    vented = plumbing_map.predict(plumbing, through_the_gas_line, "membrane")["connections"]
    assert [valve["id"] for valve in vented["plasma-vessel"]["air"]] == ["gaspanel-valve-vent"]
    assert vented["plasma-vessel"]["state"] == "air"
    assert vented["qms-vessel"]["state"] == "isolated"
    # Through a *running* turbo it does not: the running turbo is the boundary.
    # Through a stopped one it does, because a stationary rotor is a piece of
    # pipe (owner ruling 2026-09-09, letter 20260908-948b8dbc-b1eb0d).
    backing_line_vent = {"GVU": "active", "upstream-pumpline-vent-valve": "active"}
    not_through_a_running_turbo = plumbing_map.predict(
        plumbing, dict(backing_line_vent, TMPU="active"), "membrane"
    )["connections"]
    assert not_through_a_running_turbo["plasma-vessel"]["air"] == []
    through_a_stopped_turbo = plumbing_map.predict(
        plumbing, backing_line_vent, "membrane"
    )["connections"]
    assert [valve["id"] for valve in through_a_stopped_turbo["plasma-vessel"]["air"]] == [
        "upstream-pumpline-vent-valve"
    ]

    # Both vessels open to air, and still not joined to each other: the room is
    # not a pipe, so the reach behind this readout never runs through open air.
    both_vented = plumbing_map.predict(
        plumbing,
        dict(
            through_the_gas_line,
            **{
                "bypass-pumpline-vent-valve": "active",
                "bypass-l2": "active",
                "bypass-l1": "active",
                "GVBD": "active",
            },
        ),
        "membrane",
    )["connections"]
    assert both_vented["plasma-vessel"]["state"] == "air"
    assert both_vented["qms-vessel"]["state"] == "air"
    assert both_vented["plasma-vessel"]["joined"] == []
    assert [valve["id"] for valve in both_vented["qms-vessel"]["air"]] == [
        "bypass-pumpline-vent-valve"
    ]

    # The page renders it, and says once that the whole card is a prediction.
    # The answer is groups rather than a running sentence since 0.18.0 (owner,
    # letter 20260908-aa2558c2-f3d03e: "With proper groups, not a long-line
    # which is a list"), and the row labels are his own order.
    page = client.get("/").data.decode("utf-8")
    assert 'id="vacuum-connections"' in page
    assert page.count("not measured") == 1
    script = (PROJECT_ROOT / "src" / "pihti" / "static" / "js" / "diagram.js").read_text(
        encoding="utf-8"
    )
    for phrase in ('"Open to"', '"Gas"', '"Vent"', '"Pumped by"', '"Sealed since"',
                   "Nothing open to it."):
        assert phrase in script, phrase
    # And nothing writes the old running sentence any more.
    for gone in ("Open to the ", "Vent air through the ", "Pumped by the "):
        assert gone not in script, gone


def test_a_replayed_moment_uses_the_line_configuration_of_that_moment(tmp_path):
    """History is coloured by the state it replays, and the line is part of it."""
    from pihti.server import line_mode_at
    from pihti.server import parse_timestamp

    log = tmp_path / "operation_context_log.csv"
    log.write_text(
        "timestamp,line_mode,user\n"
        "2026-09-01 10:00:00,open,KAA\n"
        "2026-09-02 10:00:00,membrane,KAA\n",
        encoding="utf-8",
    )
    assert line_mode_at(log, parse_timestamp("2026-08-31 09:00:00")) == "unknown"
    assert line_mode_at(log, parse_timestamp("2026-09-01 12:00:00")) == "open"
    assert line_mode_at(log, parse_timestamp("2026-09-03 12:00:00")) == "membrane"
    assert line_mode_at(tmp_path / "absent.csv", parse_timestamp("2026-09-03 12:00:00")) == "unknown"


def test_the_prediction_reaches_the_page_and_a_replayed_moment(client):
    live = client.get("/predicted-vacuum")
    assert live.status_code == 200
    assert set(live.json) == {
        "volumes",
        "mixes",
        "gases",
        "sealed",
        "elements",
        "air",
        "connections",
        "gas_symbols",
        "line_mode",
        "linked_valve",
    }
    assert client.get("/predicted-vacuum", query_string={"at": "bad"}).status_code == 400
    identify(client)
    client.post("/update", json={"id": "upstream-pumpline-vent-valve", "status": "active"})
    stamp = client.get("/history/events").json[-1]["ts"]
    replayed = client.get("/predicted-vacuum", query_string={"at": stamp})
    assert replayed.json["volumes"]["plasma-foreline"] == "air"
    # Every page that draws the diagram carries the key, and states the
    # prediction once — a second telling is the textbook defect. Where the key
    # sits differs by page since 0.18.0: on the Vacuum page it is the right
    # rail's own state card (owner order, letter 20260908-aa2558c2-f3d03e), and
    # on History it stays under the drawing, because that page's right rail
    # already carries its own cargo.
    for path in ("/", "/history"):
        page = client.get(path).data.decode("utf-8")
        assert page.count("Predicted from the valve positions") == 1, path
        assert 'id="vacuum-legend"' in page, path
        assert "measure pressure" not in page, path
    assert 'class="diagram-legend"' in client.get("/history").data.decode("utf-8")
    assert 'class="diagram-legend"' not in client.get("/").data.decode("utf-8")


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


def test_a_closed_gate_never_lets_its_turbo_colour_the_vessel(client):
    """The glance queezz reported, and the colour rule that answers it.

    2026-09-08, on the deployed drawing: "GVU is closed, so TMP is not pumping
    plasma-vacuum. Yet at a glance it seems that it does." The pipe from the
    shut gate up to the spinning turbo was the same blue as the vessel, because
    both were simply "high vacuum".

    0.16.0 answered that with a seventh colour for the stub, and **queezz took
    that answer back the same evening** (letter ``20260908-fe94c769-493d71``):
    "between the turbo and its gate, the vacuum is High, not pumped sealed off."
    A volume with a running pump on it is that pump's state now, so the stub is
    the turbo's own side colour again -- and what says the colour stops at the
    gate is the gate itself, white with the only black rim on the drawing.
    """
    plumbing = client.get("/plumbing").json

    shut_gate = plumbing_map.predict(
        plumbing,
        {
            "TMPU": "active",
            "RoughU": "active",
            "Rough-Bypass": "active",
            "bypass-l2": "active",
            "GVBU": "active",
        },
        "membrane",
    )
    # The stub is high vacuum in the turbo's own side colour; the vessel beside
    # it is being roughed through the bypass, so the two still do not match.
    assert shut_gate["volumes"]["plasma-turbo-line"] == "upstream-high-vacuum"
    assert shut_gate["volumes"]["plasma-vessel"] == "rough-vacuum"
    assert (
        shut_gate["elements"]["plasma-vacuum-gv-to-tmp-pipe"]["stroke"]
        != shut_gate["elements"]["plasma-vacuum"]["fill"]
    )
    # The break is the gate: white, with the one black outline on the drawing.
    gate = shut_gate["elements"]["GVU"]
    assert gate["open"] is False
    assert (gate["fill"], gate["stroke"]) == ("#ffffff", "#000000")
    # And the retired teal is gone from the map rather than left lying about.
    assert "sealed" not in {state["id"] for state in plumbing["states"]}

    # With the gate open the same pipe is the plasma vessel's own colour again,
    # and the backing line behind the turbo is forevacuum.
    open_gate = plumbing_map.predict(
        plumbing, {"TMPU": "active", "GVU": "active", "RoughU": "active"}, "membrane"
    )
    assert open_gate["volumes"]["plasma-turbo-line"] == "upstream-high-vacuum"
    assert open_gate["volumes"]["plasma-foreline"] == "rough-vacuum"

    # Each vessel names its own high-vacuum colour, and the two differ.
    upstream = plumbing["volumes"]["plasma-vessel"]["high_vacuum"]
    downstream = plumbing["volumes"]["qms-vessel"]["high_vacuum"]
    assert {upstream, downstream} == {"upstream-high-vacuum", "downstream-high-vacuum"}
    assert (
        plumbing["volumes"]["plasma-vessel"]["rank"]
        < plumbing["volumes"]["qms-vessel"]["rank"]
    )


def test_a_valve_says_its_position_with_its_own_body(client):
    """An open valve wears what runs through it; a closed one is a white break.

    queezz, 2026-09-08, on the small valves at 1440 wide: they read too
    quietly, "a green wedge against a grey wedge at that size". So an open
    valve takes the colour of the volume flowing through it and a closed one
    takes the closed ink, which makes the colour stop short on both sides of
    it -- the same rule at every valve size, from GVBD down to a gas-panel
    valve.
    """
    plumbing = client.get("/plumbing").json
    colours = {state["id"]: state["color"] for state in plumbing["states"]}
    closed_ink = plumbing["drawing"]["valve_closed"]
    # The closed ink is not any state's colour, so a colour can never appear to
    # run through a shut valve.
    assert closed_ink not in set(colours.values())

    pumping = plumbing_map.predict(
        plumbing, {"TMPU": "active", "GVU": "active", "RoughU": "active"}, "membrane"
    )
    big, small = pumping["elements"]["GVU"], pumping["elements"]["bypass-vcr-u"]
    assert big["open"] is True and big["fill"] == colours["upstream-high-vacuum"]
    assert small["open"] is False and small["fill"] == closed_ink
    # Every valve the map knows answers, and only with those two inks.
    for valve in plumbing["valves"]:
        item = pumping["elements"][valve["id"]]
        assert item["valve"] is True, valve["id"]
        if item.get("linked"):
            # The Line-configuration valve is drawn as present or absent rather
            # than open or shut, and has its own test.
            continue
        assert item["fill"] == closed_ink or item["fill"] in set(colours.values())
        # An open valve's edge goes with its fill, so it reads as part of the
        # pipe; a closed one keeps a black outline and is the single dark-rimmed
        # shape on the drawing (queezz, 2026-09-08, letter
        # 20260908-3308e02d-3021dd: "I think I like the valves edge to be same
        # color as the fill. When closed, black border white fill is good.
        # Stands out.").
        assert item["stroke"] == (
            item["fill"] if item["open"] else plumbing["drawing"]["valve_closed_edge"]
        ), valve["id"]

    # The page reads a press from the recorded state now, never off the paint,
    # because a valve's fill no longer says whether it is open.
    script = (PROJECT_ROOT / "src" / "pihti" / "static" / "js" / "diagram.js").read_text(
        encoding="utf-8"
    )
    assert "normalizedStatus(vacuumState[element.id])" in script
    assert "currentFill === config.colors.active" not in script


def test_two_things_reaching_one_volume_show_on_the_shape_and_not_the_pipe(client):
    """Mixing is a two-tone body; a pipe wears one colour and only one.

    queezz asked the question -- "Is it possible to indicate pumping mixing
    with a gradient, maybe?? Cause if I open a rotary into the TMP pumped
    volume, the pressure may drop a bit, but stay HV side" -- and then settled
    where it goes: "Well, we have shapes in all important places.
    plasma-vacuum, bypass connector, and qms-vacuum." A gradient is painted
    across a shape's bounding box rather than along a path, so on a bent pipe
    it would streak the wrong way; on a body it reads. His own words on the
    signal: "I think the shape gradient is a good signal. You are pumping from
    two sides, take note."
    """
    plumbing = client.get("/plumbing").json
    colours = {state["id"]: state["color"] for state in plumbing["states"]}
    svg_text = (PROJECT_ROOT / "src" / "pihti" / "static" / "diagram.svg").read_text(
        encoding="utf-8"
    )

    # A rough pump reaching a turbo-pumped volume: the dominant state stays the
    # high vacuum, and the rough pump is the contribution.
    both_pumps = plumbing_map.predict(
        plumbing,
        {
            "TMPU": "active",
            "GVU": "active",
            "RoughU": "active",
            "GVBU": "active",
            "Rough-Bypass": "active",
            "bypass-l2": "active",
        },
        "membrane",
    )
    assert both_pumps["volumes"]["plasma-vessel"] == "upstream-high-vacuum"
    assert both_pumps["mixes"]["plasma-vessel"] == "rough-vacuum"
    cross = both_pumps["elements"]["plasma-vacuum"]
    assert cross["fill"] == colours["upstream-high-vacuum"]
    assert cross["mix"] == colours["rough-vacuum"]
    for element_id in ("plasma-vacuum-gate-port", "plasma-vacuum-pump-manifold"):
        assert "mix" not in both_pumps["elements"][element_id], element_id

    # The two vessels joined: the plasma side leads and the QMS side is the
    # contribution, on both bodies.
    joined_state = {
        "TMPU": "active",
        "GVU": "active",
        "TMPD": "active",
        "GVD": "active",
        "bypass-vcr-u": "active",
        "bypass-vcr-d": "active",
    }
    joined = plumbing_map.predict(plumbing, joined_state, "open")
    for body in ("plasma-vacuum", "qms-vacuum"):
        assert joined["elements"][body]["fill"] == colours["upstream-high-vacuum"], body
        assert joined["elements"][body]["mix"] == colours["downstream-high-vacuum"], body

    # A saved render carries the same two-tone body, through a gradient it
    # writes into the drawing's own defs.
    rendered = plumbing_map.style_rules(plumbing, joined_state, "open")
    assert "fill:url(#pihti-mix-" in rendered
    markup = plumbing_map.overlay_markup(plumbing, joined_state, "open", svg_text)
    assert "<linearGradient" in markup
    assert colours["upstream-high-vacuum"] in markup
    assert colours["downstream-high-vacuum"] in markup

    # Gas and air still beat every pump for the *dominant* reading -- and, since
    # 0.16.0, they no longer suppress the second tone. queezz, 2026-09-08, on a
    # vented plasma vessel with the roughing bypass still reaching it (letter
    # 20260908-aed40a4e-c9a286): "Rotary from bypass is pumping, but I see no
    # gradient." The vented vessel is red, and the rotary is the amber tone
    # beside it -- which is exactly the case worth a glance.
    vented_and_roughed = plumbing_map.predict(
        plumbing,
        {
            "GVBU": "active",
            "bypass-l2": "active",
            "bypass-pumpline-vent-valve": "active",
            "Rough-Bypass": "active",
        },
        "membrane",
    )
    assert vented_and_roughed["volumes"]["plasma-vessel"] == "air"
    assert vented_and_roughed["mixes"]["plasma-vessel"] == "rough-vacuum"
    assert vented_and_roughed["elements"]["plasma-vacuum"]["mix"] == colours["rough-vacuum"]

    # A vessel on gas with a rough pump still reaching it says the same way.
    gassed_and_roughed = plumbing_map.predict(
        plumbing,
        {
            "argon-bottle": "active",
            "gasline-ar": "active",
            "gasline-main": "active",
            "GVBU": "active",
            "Rough-Bypass": "active",
            "bypass-l2": "active",
        },
        "membrane",
    )
    assert gassed_and_roughed["volumes"]["plasma-vessel"] == "gas"
    assert gassed_and_roughed["mixes"]["plasma-vessel"] == "rough-vacuum"

    # One thing reaching it, no gradient.
    vented_only = plumbing_map.predict(
        plumbing, {"GVU": "active", "upstream-pumpline-vent-valve": "active"}, "membrane"
    )
    assert vented_only["volumes"]["plasma-foreline"] == "air"
    assert "plasma-foreline" not in vented_only["mixes"]

    # And a pipe never carries the second tone, whatever reaches its volume.
    for element_id in ("plasma-vacuum-gate-port", "plasma-vacuum-pump-manifold"):
        assert "mix" not in vented_and_roughed["elements"][element_id], element_id


def test_a_vessel_holding_gas_wears_its_bottle_symbol(client):
    """Ar, O2, H2, He or N2, drawn large inside the vessel, one per gas.

    queezz, 2026-09-08: "for the gas fill, we can put a gas in a circle (same
    as the bottle sign) inside the plasma vessel. Ar, O2, H2. So it's visible
    big at a glance." The symbol is written beside its bottle in the map rather
    than derived from the gas's name, and where it may stand is written beside
    the vessel -- the plasma vessel is a cross, and the middle of its bounding
    box is not the middle of anything a circle fits inside.
    """
    plumbing = client.get("/plumbing").json
    svg_text = (PROJECT_ROOT / "src" / "pihti" / "static" / "diagram.svg").read_text(
        encoding="utf-8"
    )
    assert {source["symbol"] for source in plumbing["gas_sources"]} == {
        "H2",
        "O2",
        "Ar",
        "He",
        "N2",
    }

    argon = {"argon-bottle": "active", "gasline-ar": "active", "gasline-main": "active"}
    one = plumbing_map.predict(plumbing, argon, "membrane")["gas_symbols"]
    assert [(item["volume"], item["symbols"]) for item in one] == [
        ("plasma-vessel", ["Ar"])
    ]

    two = plumbing_map.predict(
        plumbing,
        {**argon, "gaspanel-valve-n": "active", "gaspanel-valve-ar": "active"},
        "membrane",
    )["gas_symbols"]
    assert two[0]["symbols"] == ["Ar", "N2"]

    # Nothing at all when no vessel is holding gas.
    assert plumbing_map.predict(plumbing, {}, "membrane")["gas_symbols"] == []

    # Every authored box really is inside the shape it names, so an edit in
    # Inkscape that moved a vessel cannot leave a symbol floating outside it.
    for name, volume in plumbing["volumes"].items():
        if "symbol_box" not in volume:
            continue
        assert plumbing_map.box_inside(
            svg_text, volume["vessel"], volume["symbol_box"]
        ), name
    assert not plumbing_map.box_inside(svg_text, "plasma-vacuum", [0, 0, 10, 10])
    assert not plumbing_map.box_inside(svg_text, "not-an-element", [0, 0, 10, 10])

    # And the saved render carries the symbols, not only the page.
    markup = plumbing_map.overlay_markup(plumbing, argon, "membrane", svg_text)
    assert ">Ar</text>" in markup
    assert 'id="pihti-gas-symbols"' in markup


def test_a_change_costs_one_request_and_one_redraw(client):
    """queezz, 2026-09-08: "membrane installed to open pipe is VERY slow."

    It was three round trips: the write, then a re-read of the whole state,
    then the prediction. The answer to the write now carries the new prediction
    with it, so the page redraws from what it already has -- and a valve press,
    which had the same shape, does too.
    """
    identify(client)
    switched = client.post("/operation-context", json={"line_mode": "open"})
    assert switched.status_code == 200
    assert switched.json["line_mode"] == "open"
    assert "prediction" in switched.json and "state" in switched.json
    assert switched.json["prediction"]["line_mode"] == "open"
    # The same walk /predicted-vacuum would answer with a moment later.
    live = client.get("/predicted-vacuum").json
    assert switched.json["prediction"]["volumes"] == live["volumes"]
    # Pressing the same configuration again is idempotent and still answers.
    again = client.post("/operation-context", json={"line_mode": "open"})
    assert again.status_code == 200 and "prediction" in again.json

    pressed = client.post("/update", json={"id": "TMPU", "status": "active"})
    assert pressed.status_code == 200
    assert (
        pressed.json["prediction"]["volumes"]["plasma-turbo-line"]
        == "upstream-high-vacuum"
    )
    unchanged = client.post("/update", json={"id": "TMPU", "status": "active"})
    assert unchanged.json["message"] == "State unchanged"
    assert "prediction" in unchanged.json

    # And the page uses the answer instead of asking again.
    script = (PROJECT_ROOT / "src" / "pihti" / "static" / "js" / "diagram.js").read_text(
        encoding="utf-8"
    )
    assert "applyState(vacuumState, undefined, result.prediction)" in script
    assert "function applyState(state, moment, prediction)" in script


# --- Sealed off is a remembered, dated state (0.17.0) ------------------------
#
# queezz, 2026-09-08, correcting the seventh colour of 0.16.0 (letters
# ``20260908-fe94c769-493d71`` and ``20260908-2c3d9837-37ab4a``): "between the
# turbo and its gate, the vacuum is High, not pumped sealed off. Not sealed.
# Pumped sealed off means I pump, close the valve. Vacuum holds, and degrades
# per the vessel's leak rate... If we have air/N2 or isolation especially in the
# main two vessels, we need to keep a date so we can say: 'ah, that upstream was
# under N2 for two weeks!'"


def nitrogen_route():
    """The valves queezz opens to let nitrogen into the plasma vessel.

    His own route, corrected on the deployed guides (letter
    ``20260908-7a3c9ac3-bbd7aa``): "Let Nitrogen in.. we are using the big
    manual needle valve, not massflows for venting. So the argon line must
    provide gas."
    """
    return {
        "gaspanel-valve-n": "active",
        "gaspanel-valve-ar": "active",
        "gasline-ar": "active",
        "gasline-main": "active",
    }


def sealed_state_of(plumbing, state, memory, now):
    """One prediction with an explicit memory and an explicit clock."""
    return plumbing_map.predict(plumbing, state, "membrane", memory=memory, now=now)


def test_a_pumped_vessel_shut_off_is_sealed_and_its_stub_is_high_vacuum(client):
    """Pump it, close the gate: the vessel holds what it had, the stub does not.

    The letter's own first test. The vessel is isolated *and* remembers high
    vacuum, so it is sealed and says since when; the stub between the shut gate
    and the still-spinning turbo is simply high vacuum in that turbo's own side
    colour, because a volume with a running pump on it is that pump's state now.
    """
    plumbing = client.get("/plumbing").json
    colours = {state["id"]: state["color"] for state in plumbing["states"]}
    pumping = {"TMPU": "active", "GVU": "active"}
    started = datetime(2026, 9, 8, 12, 0, 0)

    # Pumped: the gate is open, the vessel is plasma-side high vacuum, and
    # nothing is remembered as sealed because nothing is shut.
    open_gate = sealed_state_of(plumbing, pumping, {}, started)
    assert open_gate["volumes"]["plasma-vessel"] == "upstream-high-vacuum"
    assert open_gate["sealed"] == {}
    memory = plumbing_map.update_memory(plumbing, {}, open_gate, started)
    assert memory["plasma-vessel"] == {"state": "upstream-high-vacuum", "since": None}

    # The gate closes. The memory takes its stamp from that moment, and never
    # re-stamps: "since when" means since it was closed.
    shut = {"TMPU": "active"}
    closing = sealed_state_of(plumbing, shut, memory, started)
    memory = plumbing_map.update_memory(plumbing, memory, closing, started)
    assert memory["plasma-vessel"]["since"] == "2026-09-08 12:00:00"
    later = plumbing_map.update_memory(
        plumbing, memory, closing, started + timedelta(days=1)
    )
    assert later["plasma-vessel"]["since"] == "2026-09-08 12:00:00"

    a_day_later = started + timedelta(days=1)
    reading = sealed_state_of(plumbing, shut, memory, a_day_later)
    held = reading["sealed"]["plasma-vessel"]
    assert held["was"] == "upstream-high-vacuum"
    assert held["duration"] == "1 day"
    # The vessel wears what it is holding, hatched -- never the grey of a volume
    # with no memory at all, and never a second tone, because nothing reaches it.
    body = reading["elements"]["plasma-vacuum"]
    assert body["fill"] == colours["upstream-high-vacuum"]
    assert body["sealed"] is True and body["sealed_paint"].startswith("pihti-sealed-")
    assert "mix" not in body
    # And the stub between the shut gate and the spinning turbo is high vacuum
    # in the turbo's own side colour -- not sealed, and not a state of its own.
    assert reading["volumes"]["plasma-turbo-line"] == "upstream-high-vacuum"
    assert "plasma-turbo-line" not in reading["sealed"]
    assert reading["elements"]["TMPU"]["fill"] == colours["upstream-high-vacuum"]
    # The break the eye reads is the gate: the one white shape with a black rim.
    gate = reading["elements"]["GVU"]
    assert (gate["open"], gate["fill"], gate["stroke"]) == (False, "#ffffff", "#000000")


def test_a_vessel_vented_with_nitrogen_and_shut_is_sealed_under_nitrogen(client):
    """His own sentence: "ah, that upstream was under N2 for two weeks!"

    A closed vessel full of nitrogen is still full of nitrogen: the memory keeps
    the gas and its bottle symbols, so the readout can say which gas and the
    mark stays drawn inside the vessel after the bottle is shut.
    """
    plumbing = client.get("/plumbing").json
    # Nitrogen reaches the plasma vessel through the gas panel and the argon
    # line, the route queezz named for venting (letter 20260908-7a3c9ac3-bbd7aa).
    venting = nitrogen_route()
    started = datetime(2026, 8, 25, 9, 0, 0)
    vented = sealed_state_of(plumbing, venting, {}, started)
    assert vented["volumes"]["plasma-vessel"] == "gas"
    assert vented["gases"]["plasma-vessel"] == ["N2"]
    memory = plumbing_map.update_memory(plumbing, {}, vented, started)
    assert memory["plasma-vessel"]["symbols"] == ["N2"]

    shut = sealed_state_of(plumbing, {}, memory, started)
    memory = plumbing_map.update_memory(plumbing, memory, shut, started)

    two_weeks = started + timedelta(days=14)
    reading = sealed_state_of(plumbing, {}, memory, two_weeks)
    held = reading["sealed"]["plasma-vessel"]
    assert held["was"] == "gas"
    assert held["symbols"] == ["N2"]
    assert held["duration"] == "2 weeks"
    # The mark stays inside the vessel, so a glance still says what is in there.
    marks = {item["volume"]: item for item in reading["gas_symbols"]}
    assert marks["plasma-vessel"]["symbols"] == ["N2"]
    assert marks["plasma-vessel"]["sealed"] is True


def test_the_duration_and_the_advice_change_as_a_fake_clock_runs(client):
    """The thresholds, said out loud rather than left in the code.

    ``bake_air_days`` 2, ``bake_gas_days`` 7, ``fresh_vacuum_days`` 3, all in
    the map. Air is the shortest because air brings water vapour in and dry
    nitrogen does not; three days is how long a vacuum stays fresh enough that
    opening the turbo straight in may be fine rather than roughing through the
    bypass first. The advice is his own three sentences, and it names the gauge
    on that volume, because the diagram predicts and the gauge measures.
    """
    plumbing = client.get("/plumbing").json
    limits = plumbing_map.hint_thresholds(plumbing)
    assert limits == {
        "bake_air_days": 2.0,
        "bake_gas_days": 7.0,
        "fresh_vacuum_days": 3.0,
    }
    started = datetime(2026, 9, 1, 8, 0, 0)

    def hint_after(was, days, symbols=None):
        memory = {
            "qms-vessel": {
                "state": was,
                "since": started.strftime(plumbing_map.TIME_FORMAT),
                "symbols": symbols or [],
            }
        }
        reading = sealed_state_of(plumbing, {}, memory, started + timedelta(days=days))
        return reading["sealed"]["qms-vessel"]

    # Under vacuum: fresh for three days, then rough through the bypass to be
    # safe rather than opening the turbo straight in.
    fresh = hint_after("downstream-high-vacuum", 1)
    assert fresh["duration"] == "1 day"
    assert "may be fine" in fresh["hint"]["text"]
    assert fresh["hint"]["bake"] is False
    stale_vacuum = hint_after("downstream-high-vacuum", 5)
    assert stale_vacuum["duration"] == "5 days"
    assert "rough through the bypass" in stale_vacuum["hint"]["text"]
    assert stale_vacuum["hint"]["bake"] is False

    # Under air: baking is advised from the second day.
    assert hint_after("air", 1)["hint"]["bake"] is False
    month_of_air = hint_after("air", 31)
    assert month_of_air["duration"] == "1 month"
    assert month_of_air["hint"]["bake"] is True
    assert "Consider baking." in month_of_air["hint"]["text"]

    # Under nitrogen: dry gas buys a week before the same advice.
    assert hint_after("gas", 3, ["N2"])["hint"]["bake"] is False
    assert hint_after("gas", 10, ["N2"])["hint"]["bake"] is True

    # The gauge on that volume is named as the thing to read, by id -- the page
    # says it by the name a person uses at the rig.
    named = hint_after("downstream-high-vacuum", 1)["hint"]["gauges"]
    assert set(named) == {"downstream-ionization-gauge", "downstream-baratron"}

    # And the pump-down guides' own question -- which of their two ways -- is
    # answered from the same memory: a turbo still spinning behind its shut gate
    # has to be roughed through the bypass; a stopped one can pump through the
    # gate it sits behind.
    memory = {
        "plasma-vessel": {
            "state": "upstream-high-vacuum",
            "since": started.strftime(plumbing_map.TIME_FORMAT),
        }
    }
    spinning = sealed_state_of(plumbing, {"TMPU": "active"}, memory, started)
    assert spinning["sealed"]["plasma-vessel"]["hint"]["way"] == "bypass"
    quiet = sealed_state_of(plumbing, {}, memory, started)
    assert quiet["sealed"]["plasma-vessel"]["hint"]["way"] == "gate"

    # Plain units all the way up, never a decimal.
    assert plumbing_map.duration_words(600) == "less than an hour"
    assert plumbing_map.duration_words(3600) == "1 hour"
    assert plumbing_map.duration_words(3600 * 6) == "6 hours"
    assert plumbing_map.duration_words(86400 * 3) == "3 days"
    assert plumbing_map.duration_words(86400 * 21) == "3 weeks"
    assert plumbing_map.duration_words(86400 * 70) == "2 months"


def test_a_fresh_state_is_isolated_unknown_and_a_replayed_one_is_not(tmp_path):
    """A fresh record says it does not know; a log two weeks old says two weeks.

    Rule three of the letter: "Isolated, unknown is only for a volume with no
    remembered state." And the memory is derivable as well as stored, because a
    state file can be new, copied to another machine, or simply older than the
    log beside it -- so the log is replayed once on the first read and the
    answer is written back with the next real change rather than on a read.
    """
    (tmp_path / "operators.json").write_text(
        json.dumps({"operators": ["operator"]}), encoding="utf-8"
    )
    # A fresh record: an empty state file, and no history at all.
    fresh = make_app(tmp_path).test_client()
    blank = fresh.get("/predicted-vacuum").json
    assert blank["volumes"]["plasma-vessel"] == "isolated"
    assert blank["sealed"] == {}
    plumbing = fresh.get("/plumbing").json
    states = {state["id"]: state for state in plumbing["states"]}
    assert states["isolated"]["label"] == "Isolated, unknown"

    # Now a history that pumped the plasma vessel and shut the gate a fortnight
    # ago, with nothing since, and a state file that never heard of a memory.
    long_ago = datetime.now() - timedelta(days=14, hours=2)
    rows = [
        (long_ago - timedelta(minutes=10), "TMPU", "active"),
        (long_ago - timedelta(minutes=5), "GVU", "active"),
        (long_ago, "GVU", "inactive"),
    ]
    (tmp_path / "logs.csv").write_text(
        "timestamp,id,status,user\n"
        + "".join(
            "{},{},{},operator\n".format(
                when.strftime("%Y-%m-%d %H:%M:%S"), name, status
            )
            for when, name, status in rows
        ),
        encoding="utf-8",
    )
    (tmp_path / "elements_state.json").write_text(
        json.dumps({"TMPU": "active", "GVU": "inactive"}), encoding="utf-8"
    )
    replayed = make_app(tmp_path).test_client()
    reading = replayed.get("/predicted-vacuum").json
    held = reading["sealed"]["plasma-vessel"]
    assert held["was"] == "upstream-high-vacuum"
    assert held["duration"] == "2 weeks"
    # The turbo is still spinning behind the shut gate, so its own stub is high
    # vacuum rather than sealed, and the guide's question answers "bypass".
    assert reading["volumes"]["plasma-turbo-line"] == "upstream-high-vacuum"
    assert held["hint"]["way"] == "bypass"


def test_the_memory_lives_in_the_state_file_beside_the_valves(client, tmp_path):
    """Written with the valve positions, in one file, under one reserved key.

    It is not an element and never will be -- every id on the drawing comes from
    Inkscape and none of them starts with an underscore -- and ``/elements-state``
    still answers with valve positions alone, so no page has to know to skip it.
    """
    identify(client)
    client.post("/update", json={"id": "TMPU", "status": "active"})
    client.post("/update", json={"id": "GVU", "status": "active"})
    client.post("/update", json={"id": "GVU", "status": "inactive"})

    stored = json.loads((tmp_path / "elements_state.json").read_text(encoding="utf-8"))
    assert plumbing_map.MEMORY_KEY == "_volumes"
    memory = stored[plumbing_map.MEMORY_KEY]
    assert memory["plasma-vessel"]["state"] == "upstream-high-vacuum"
    assert memory["plasma-vessel"]["since"]
    # The valves are still valves, and the memory is not one of them.
    assert stored["GVU"] == "inactive" and stored["TMPU"] == "active"
    assert plumbing_map.MEMORY_KEY not in client.get("/elements-state").json

    # And the prediction the press answered with already knew it was sealed.
    reading = client.get("/predicted-vacuum").json
    held = reading["sealed"]["plasma-vessel"]
    assert held["was"] == "upstream-high-vacuum"
    assert held["duration"] == "less than an hour"
    # The readout under the drawing carries it, so the page says what and since
    # when without asking a second question.
    assert reading["connections"]["plasma-vessel"]["sealed"]["was"] == held["was"]


def test_a_gas_mark_is_sized_to_the_vessel_it_sits_in(client):
    """queezz: "The qms-vacuum gas circle is bigger for some reason."

    It was drawn at one absolute size in both vessels, which is nearly the whole
    width of the narrower QMS box. The rule he gave (letter
    ``20260908-8eaaa7a9-334955``): the mark's diameter is about 0.45 of the
    SMALLER side of the vessel body it sits in, capped at the plasma mark's own
    size, centred, and smaller again with several gases in a row.
    """
    plumbing = client.get("/plumbing").json
    volumes = plumbing["volumes"]
    # Under *Pipe open*, with the two bypass gates open, one bottle of nitrogen
    # reaches both vessels -- the frame his letter was written on.
    joined = dict(nitrogen_route())
    joined.update({"GVBU": "active", "GVBD": "active"})
    reading = plumbing_map.predict(plumbing, joined, "open")
    marks = {item["volume"]: item for item in reading["gas_symbols"]}
    assert set(marks) == {"plasma-vessel", "qms-vessel"}

    for name, mark in marks.items():
        left, top, right, bottom = volumes[name]["symbol_box"]
        shorter = min(right - left, bottom - top)
        # 0.45 of the smaller side, as a diameter, so half of that as a radius.
        assert mark["radius"] <= 0.45 * shorter / 2 + 0.01, name
    # The QMS box is the narrower one and used to carry the bigger mark. Neither
    # is bigger than the other now, and neither is bigger than the cap.
    assert marks["qms-vessel"]["radius"] <= marks["plasma-vessel"]["radius"] + 0.01
    cap = plumbing_map._mark_cap(volumes)
    assert marks["plasma-vessel"]["radius"] <= cap + 0.01

    # Several gases in a row are drawn smaller so they fit side by side.
    crowded = plumbing_map.mark_radius(volumes["qms-vessel"]["symbol_box"], 3, cap)
    assert crowded < marks["qms-vessel"]["radius"]

    # And the page reads the radius off the prediction rather than working out
    # its own, so a saved render and the screen cannot size a mark differently.
    script = (PROJECT_ROOT / "src" / "pihti" / "static" / "js" / "diagram.js").read_text(
        encoding="utf-8"
    )
    assert "Number(item.radius)" in script


def test_h2_and_o2_are_written_with_a_true_subscript(client):
    """queezz: "Can we do H2, O2 with a subscript?"

    Drawn the way his own bottle symbols draw it -- a tspan dropped by a
    fraction of the mark's size and set smaller -- never a Unicode subscript
    glyph a font may not carry. ``Ar`` and ``He`` have no digit and are
    untouched.
    """
    assert plumbing_map.split_formula("H2") == ("H", "2")
    assert plumbing_map.split_formula("O2") == ("O", "2")
    assert plumbing_map.split_formula("N2") == ("N", "2")
    assert plumbing_map.split_formula("Ar") == ("Ar", "")
    assert plumbing_map.split_formula("He") == ("He", "")

    plumbing = client.get("/plumbing").json
    svg_text = (PROJECT_ROOT / "src" / "pihti" / "static" / "diagram.svg").read_text(
        encoding="utf-8"
    )
    markup = plumbing_map.overlay_markup(plumbing, nitrogen_route(), "membrane", svg_text)
    # The letters stand at the mark's own size; the digit is a tspan of its own,
    # dropped and smaller. No Unicode subscript character anywhere.
    assert "<tspan dy=" in markup
    assert ">N<tspan" in markup and ">2</tspan>" in markup
    for glyph in "₀₁₂₃₄₅₆₇₈₉":
        assert glyph not in markup

    # And the page draws it the same way, at the small QMS size as at the large
    # plasma one, from the same two fractions.
    script = (PROJECT_ROOT / "src" / "pihti" / "static" / "js" / "diagram.js").read_text(
        encoding="utf-8"
    )
    assert "function writeFormula(text, symbol, radius)" in script
    assert "(radius * 0.22).toFixed(2)" in script
    assert "(radius * 0.62).toFixed(2)" in script
    # The legend and the readout say it in HTML, where <sub> is the right thing.
    assert "function formulaHtml(symbol)" in script
    assert 'document.createElement("sub")' in script


def test_the_sealed_hatch_touches_a_chamber_body_and_nothing_else(client):
    """A pipe is a solid stroke in every state, and a valve is never hatched.

    Three letters in five minutes, 2026-09-09, on the first build of the hatch.
    queezz watching the tree live: "The predictor is inventing something
    hallucinogenic... for some reason lines broke down. Inventive destruction."
    Then, plainly: "I don't like the broken lines. They are pipes. That reads
    like a breakage." And on a close-up of the cross, the tee above it and the
    gate valve between them all under one hatch: "the dashed valve, it's like
    'guess what shape this is and what this blob does'."

    A hatch painted onto a 4 px stroke *is* a dashed line, whatever it was meant
    to be. So the hatch is on the two chamber bodies alone, and every pipe, tee,
    cross, gauge stem and open valve in a sealed volume is **solid** in a paler
    tone of what the volume is holding.
    """
    plumbing = client.get("/plumbing").json
    colours = {state["id"]: state["color"] for state in plumbing["states"]}
    started = datetime(2026, 9, 9, 14, 0, 0)
    # Both sides of the open gas-line valve remember high vacuum, so the valve
    # itself stands inside a sealed space and has to say so without a hatch.
    memory = {
        name: {
            "state": "upstream-high-vacuum",
            "since": started.strftime(plumbing_map.TIME_FORMAT),
        }
        for name in ("plasma-vessel", "gas-manifold")
    }
    reading = sealed_state_of(plumbing, {"gasline-main": "active"}, memory, started)
    assert "plasma-vessel" in reading["sealed"]
    blue = colours["upstream-high-vacuum"]
    pale = plumbing_map.sealed_pale(plumbing, blue)
    assert pale != blue

    volume = plumbing["volumes"]["plasma-vessel"]
    chamber = volume["vessel"]
    # The chamber body, and only it, carries the hatch.
    body = reading["elements"][chamber]
    assert body["sealed_paint"] == "pihti-sealed-" + blue.lstrip("#")
    assert body["fill"] == body["stroke"] == blue

    # Every other element of that volume -- pipes, and the tees and crosses the
    # map calls junctions -- is solid in the paler tone and carries no pattern.
    others = [name for name in volume["elements"] if name != chamber]
    assert others
    for name in others:
        item = reading["elements"][name]
        assert "sealed_paint" not in item, name
        assert item.get("stroke") == pale, name
        assert "dash" not in item, name

    # A gauge stem on that volume is a pipe like any other.
    stems = [
        gauge["stem"]
        for gauge in plumbing["gauges"]
        if gauge.get("volume") == "plasma-vessel" and gauge.get("stem")
    ]
    for stem in stems:
        assert reading["elements"][stem]["stroke"] == pale, stem
        assert "sealed_paint" not in reading["elements"][stem], stem

    # And no valve anywhere is ever hatched: each keeps its own two looks, so it
    # stays unmistakably a valve at arm's length in every state.
    valves = [item for item in reading["elements"].values() if item.get("valve")]
    assert valves
    for item in valves:
        assert "sealed_paint" not in item
        if item["open"]:
            assert item["fill"] == item["stroke"]
        else:
            assert (item["fill"], item["stroke"]) == ("#ffffff", "#000000")
    # An open valve standing in a sealed space wears that space's paler tone, so
    # it belongs to those pipes rather than shouting over them.
    inside = [item for item in valves if item.get("sealed")]
    assert inside
    for item in inside:
        held = reading["sealed"][item["volume"]]
        assert item["fill"] == plumbing_map.sealed_pale(plumbing, colours[held["was"]])

    # Nothing anywhere in a saved render paints a stroke with a pattern, and no
    # element of any kind asks for a dash: a pipe is solid in every state.
    saved = plumbing_map.style_rules(
        plumbing, {"gasline-main": "active", plumbing_map.MEMORY_KEY: memory}, "membrane"
    )
    # No element is ever given an actual dash pattern. The one `stroke-dasharray`
    # the render writes is the explicit `none` on the drawn valve the Line
    # configuration governs, which is the opposite of a dash.
    dashes = re.findall(r"stroke-dasharray:([^ ;}]+)", saved)
    assert dashes and set(dashes) == {"none"}, dashes
    # Exactly one rule in the whole render mentions the hatch, and it is the
    # chamber's own -- fill and stroke alike, because a vessel body is one
    # colour edge and all. Every other rule is a flat colour.
    hatched_rules = [
        rule for rule in saved.split("}") if "url(#pihti-sealed-" in rule
    ]
    assert len(hatched_rules) == 1
    assert hatched_rules[0].startswith(f"#{chamber}{{")


def test_live_always_beats_the_memory(client):
    """"The rough pump pumps, it can really do that."

    The sealed state belongs to a volume nothing reaches. The instant a pump, a
    gas or air reaches it through open valves the memory stops being what the
    drawing says and the live prediction takes over again -- and the memory is
    rewritten to what it now holds, with no isolation moment on it, so the clock
    restarts from the next time it is shut rather than from the last one.
    """
    plumbing = client.get("/plumbing").json
    started = datetime(2026, 9, 9, 14, 0, 0)
    memory = {
        "plasma-vessel": {
            "state": "upstream-high-vacuum",
            "since": started.strftime(plumbing_map.TIME_FORMAT),
        }
    }
    shut = sealed_state_of(plumbing, {}, memory, started)
    assert shut["volumes"]["plasma-vessel"] == "isolated"
    assert shut["sealed"]["plasma-vessel"]["was"] == "upstream-high-vacuum"

    # Open the gate onto the running turbo: the vessel is high vacuum now, and
    # nothing about it is sealed any more.
    reached = sealed_state_of(
        plumbing, {"GVU": "active", "TMPU": "active"}, memory, started
    )
    assert reached["volumes"]["plasma-vessel"] == "upstream-high-vacuum"
    assert "plasma-vessel" not in reached["sealed"]
    assert "sealed" not in reached["elements"][plumbing["volumes"]["plasma-vessel"]["vessel"]]

    # And the memory follows the live reading, with its clock cleared.
    after = plumbing_map.update_memory(plumbing, memory, reached, started)
    assert after["plasma-vessel"] == {"state": "upstream-high-vacuum", "since": None}

    # Air reaching it wins the same way, and the memory becomes air.
    vented = sealed_state_of(plumbing, {"gaspanel-valve-vent": "active",
                                        "gaspanel-valve-ar": "active",
                                        "gasline-ar": "active",
                                        "gasline-main": "active"}, memory, started)
    assert vented["volumes"]["plasma-vessel"] == "air"
    assert "plasma-vessel" not in vented["sealed"]


# --- A stopped turbo is a passage, not a wall (0.17.1) -----------------------
#
# queezz, 2026-09-09, watching the 0.17.0 tree with TMPD stopped and the QMS
# rotary running on its backing line (letter ``20260908-948b8dbc-b1eb0d``):
# "The rough pump pumps, it can really do that." Gas goes through a stationary
# rotor, so a turbo has two states in the map now -- running, when it is the
# pump and the wall, and stopped, when it is a piece of pipe. Only a closed
# valve blocks.


def test_a_stopped_turbo_lets_the_rough_pump_through_to_the_vessel(client):
    """His own frame: the QMS rotary pumping the vessel through a stopped TMPD.

    The gate above the turbo is open, the turbo is off, and the scroll pump on
    its backing line is running. The vessel above it is rough vacuum -- pumped
    by the QMS rotary through the stopped turbo -- and the readout names that
    pump, because the same walk answers the colours and the words.
    """
    plumbing = client.get("/plumbing").json
    through = plumbing_map.predict(
        plumbing, {"GVD": "active", "TMPD": "inactive", "RoughD": "active"}, "membrane"
    )
    assert through["volumes"]["qms-vessel"] == "rough-vacuum"
    assert through["volumes"]["qms-turbo-line"] == "rough-vacuum"
    assert through["volumes"]["qms-foreline"] == "rough-vacuum"
    assert [pump["id"] for pump in through["connections"]["qms-vessel"]["pumps"]] == [
        "RoughD"
    ]

    # The plasma side is untouched by it: its own gate is shut.
    assert through["volumes"]["plasma-vessel"] == "isolated"

    # And the gate is what blocks, exactly as before. Close GVD and the vessel
    # is on its own again while the backing line stays rough.
    gate_shut = plumbing_map.predict(
        plumbing, {"TMPD": "inactive", "RoughD": "active"}, "membrane"
    )
    assert gate_shut["volumes"]["qms-vessel"] == "isolated"
    assert gate_shut["volumes"]["qms-turbo-line"] == "rough-vacuum"


def test_a_running_turbo_is_still_the_pump_and_still_the_wall(client):
    """The other of the turbo's two states, and it is unchanged.

    With TMPD spinning, the vessel above it is high vacuum in the QMS side's
    own colour and the scroll pump behind it is the turbo's backing rather than
    a second thing reaching the vessel: the rough pump is on the far side of a
    running turbo, which is a boundary.
    """
    plumbing = client.get("/plumbing").json
    running = plumbing_map.predict(
        plumbing, {"GVD": "active", "TMPD": "active", "RoughD": "active"}, "membrane"
    )
    assert running["volumes"]["qms-vessel"] == "downstream-high-vacuum"
    assert running["volumes"]["qms-turbo-line"] == "downstream-high-vacuum"
    assert running["volumes"]["qms-foreline"] == "rough-vacuum"
    assert [pump["id"] for pump in running["connections"]["qms-vessel"]["pumps"]] == [
        "TMPD"
    ]


def test_only_a_turbo_declared_a_passage_ever_becomes_one(client):
    """A rough pump exhausts to the room, so a stopped one joins nothing.

    The two sides a stopped turbo joins are the ones the map itself names --
    the pump's own ``volume`` and its ``backed_by`` line -- and the passage
    exists only where the map says ``stopped: "passage"``. The rough pumps
    carry neither field, so nothing about them changed.
    """
    plumbing = client.get("/plumbing").json
    turbos = [pump for pump in plumbing["pumps"] if pump.get("kind") == "turbo"]
    assert [pump["id"] for pump in turbos] == ["TMPU", "TMPD"]
    for pump in turbos:
        assert pump["stopped"] == "passage"
        assert pump["backed_by"] in plumbing["volumes"]
    for pump in plumbing["pumps"]:
        if pump.get("kind") != "turbo":
            assert "stopped" not in pump and "backed_by" not in pump

    everything_stopped = dict(plumbing_map.passage_edges(plumbing, {}))
    assert everything_stopped == {
        "plasma-turbo-line": "plasma-foreline",
        "qms-turbo-line": "qms-foreline",
    }
    assert plumbing_map.passage_edges(plumbing, {"TMPU": "active", "TMPD": "active"}) == []


def test_venting_a_backing_line_under_a_stopped_turbo_now_warns(client):
    """The knock-on queezz named when he answered the standing question.

    Venting the backing line under a *stopped* turbo has a path up to the
    vessel above it now, so the 0.13.0 press warning has something to warn
    about: the ionization gauge standing in that vessel would newly see air.
    Under a *running* turbo the same press reaches nothing new, and the
    prediction stays quiet -- a warning is owed for what a press changes.
    """
    plumbing = client.get("/plumbing").json
    standing = {"GVD": "active", "downstream-ionization-gauge": "active"}
    warned = plumbing_map.press_warnings(
        plumbing, standing, "downstream-pumpline-vent-valve", "active", "membrane"
    )
    assert [(item["kind"], item["id"], item["state"]) for item in warned] == [
        ("gauge", "downstream-ionization-gauge", "air")
    ]

    quiet = plumbing_map.press_warnings(
        plumbing,
        dict(standing, TMPD="active"),
        "downstream-pumpline-vent-valve",
        "active",
        "membrane",
    )
    assert quiet == []


# --- The predicted state moves into the right rail (0.18.0) ------------------
#
# queezz, 2026-09-08, on the Predicted state card under the drawing (letter
# ``20260908-aa2558c2-f3d03e``): "I think the bottom card deserves a proper
# place in the rail, no? And not hiding in small sizes, shying away. Proper.
# With proper groups, not a long-line which is a list." Amended the same
# afternoon (``20260908-50f93f77-8e8a28``): "We should keep the predicted state
# somewhere, and maybe not hide, but collapse.. Both may benefit from collapse
# then." And the guide card's own overflow (``20260908-8853f919-4c54b6``): "the
# right procedure card gets a nasty scroll bar.. Would be nice if we can avoid
# that."


def diagram_script():
    return (PROJECT_ROOT / "src" / "pihti" / "static" / "js" / "diagram.js").read_text(
        encoding="utf-8"
    )


def diagram_styles():
    return (PROJECT_ROOT / "src" / "pihti" / "static" / "css" / "styles.css").read_text(
        encoding="utf-8"
    )


def test_the_predicted_state_is_a_right_rail_card_on_the_vacuum_page(client):
    """It stands in the rail with the guide, at every width, in one DOM.

    The rail exists at desktop widths and becomes a drawer below the
    breakpoint; the card is inside it either way, so no breakpoint can drop it.
    """
    page = client.get("/").data.decode("utf-8")
    rail = page.split('id="guide-steps"', 1)[1].split("</aside>", 1)[0]
    for marker in (
        'id="state-card"',
        'id="state-card-toggle"',
        'id="state-card-body"',
        'id="vacuum-compact"',
        'id="vacuum-connections"',
        'id="vacuum-legend"',
        'id="vacuum-more"',
        'id="guide-card"',
        'id="guide-card-toggle"',
        'id="guide-step-list"',
    ):
        assert marker in rail, marker
    # And nothing of it is left under the drawing on this page.
    main = page.split('class="page-main"', 1)[1].split("</main>", 1)[0]
    assert "vacuum-connections" not in main
    assert "diagram-legend" not in main
    # The drawer button that summons the rail says what is in it now.
    assert "State &amp; guide" in page


def test_both_right_rail_cards_collapse_to_a_headline_and_never_vanish(client):
    """A collapsed card still says its own headline; neither is ever hidden.

    The state card collapsed is one line per vessel, chip and state word; the
    guide card collapsed is the guide's name and the current step with its
    number. The default follows the situation — guide running, guide open and
    state compact; no guide, state open — and the reader's own press is
    remembered per browser and wins over it.
    """
    page = client.get("/").data.decode("utf-8")
    assert page.count('class="card-toggle"') == 2
    assert page.count('aria-expanded="true"') >= 2
    script = diagram_script()
    assert 'state: "pihti.rail.stateCard"' in script
    assert 'guide: "pihti.rail.guideCard"' in script
    assert 'function renderStateCompact' in script
    assert 'function renderGuideCompact' in script
    assert '`Step ${currentIndex + 1} of ${steps.length}' in script
    # The default: with a guide running the state is compact, with none it is
    # open, and the guide card is open either way.
    assert '[["state", !running], ["guide", true]]' in script
    # A stored choice always wins over the default.
    assert 'stored === null ? fallback : stored === "open"' in script
    # Collapsing hides the body and shows the headline, never the other way.
    assert "body.hidden = !open;" in script
    assert "if (compact) compact.hidden = open;" in script


def test_the_guide_card_folds_before_it_scrolls_and_the_page_never_does(client):
    """Grow, then fold, then a thin quiet bar — and the rail owns the overflow.

    Three stages in that order, all measured in the rendered DOM rather than
    counted in rows, plus the floor that stops a crushed card: below it the
    rail takes the overflow instead, which is Fleet ``WEBUI.md``'s 2026-09-08
    amendment ("a card the reader opens takes its natural height... when the
    rail's content is taller than the rail, the *rail* scrolls inside its own
    box"). The page itself never scrolls for the rail.
    """
    script = diagram_script()
    assert "function fitRail()" in script
    # 2. Everything but the current step and the one after it may fold.
    assert 'rows.findIndex((item) => item.classList.contains("current"))' in script
    assert "new Set(current < 0 ? [] : [current, current + 1])" in script
    assert 'item.classList.add("folded")' in script
    # 3. The thin quiet bar, and the floor that stops a crushed card.
    assert "const STEP_LIST_FLOOR" in script
    assert "if (capped < STEP_LIST_FLOOR) return;" in script
    assert 'list.classList.add("guide-steps--scrolls")' in script
    # Measured after the layout settles, never in the middle of it.
    assert "function scheduleFit()" in script
    assert "window.setTimeout(" in script
    # Exactly one direct call, the scheduler's own: every other caller goes
    # through `scheduleFit`, so nothing measures a layout that is still moving.
    assert script.count("fitRail();") == 1
    assert script.count("scheduleFit();") >= 5

    css = diagram_styles()
    # The rail scrolls inside its own box, thin and quiet.
    rail_rule = css.split(".rail {", 1)[1].split("}", 1)[0]
    assert "overflow-y: auto" in rail_rule
    assert "scrollbar-width: thin" in rail_rule
    assert ".guide-steps li.folded" in css
    assert ".guide-steps--scrolls" in css
    assert ".rail-card--collapsible { flex: 0 0 auto; }" in css
    # A card header is a real target under a thumb in the drawer.
    assert ".card-toggle { padding: 11px 6px; margin: -11px -6px; }" in css


def test_the_readout_answers_in_groups_with_his_own_row_labels(client):
    """Chip and state first, then Open to / Gas / Vent / Pumped by / Sealed since.

    Empty rows are not drawn: a vessel with nothing open to it says so in one
    line rather than printing four empty labels.
    """
    script = diagram_script()
    assert "function connectionRows(item)" in script
    assert 'className = "vacuum-group__rows"' in script
    for label in ('"Open to"', '"Gas"', '"Vent"', '"Pumped by"', '"Sealed since"'):
        assert label in script, label
    assert 'nothing.textContent = "Nothing open to it.";' in script
    css = diagram_styles()
    assert ".vacuum-group__head" in css
    assert ".vacuum-group__rows" in css


# --- Practice: rehearse the presses, record the procedure once (0.19.0) ------
#
# queezz, 2026-09-08 (letters ``20260908-9d38bf34-8415c7`` and
# ``20260908-e460b66f-616b53``): "I want now a 'practice' before recording
# history mode somehow. You open the valve, and see where color (vacuum/air)
# goes. Then you can undo. Also maybe using that we can do a procedure, then
# save state. That way one state jump, less history spamming. And better
# operational safety." And: "In the new 'practice' mode we really need to teach
# to save the state. And maybe have a timer fallback, which saves
# automatically."


def csv_rows(path):
    import csv as _csv

    with path.open(newline="", encoding="utf-8") as handle:
        return list(_csv.reader(handle))


def test_practising_writes_nothing_until_save(client, tmp_path):
    """The history file is byte-unchanged through a whole practised sequence.

    Every press in practice asks the same two questions a real press asks --
    what would this join, and what would the drawing look like -- and neither
    route writes a byte. The state file does not move either.
    """
    identify(client)
    log_file = tmp_path / "logs.csv"
    state_file = tmp_path / "elements_state.json"
    client.post("/update", json={"id": "GVU", "status": "active"})
    log_before = log_file.read_bytes()
    state_before = state_file.read_bytes()

    practised = dict(client.get("/elements-state").json)
    for element_id, status in (("TMPD", "inactive"), ("GVD", "active"), ("RoughD", "active")):
        warned = client.post(
            "/press-warnings",
            json={"id": element_id, "status": status, "state": practised},
        )
        assert warned.status_code == 200
        practised[element_id] = status
        answer = client.post("/practice/prediction", json={"state": practised})
        assert answer.status_code == 200
        assert set(answer.json) == {"prediction", "memory"}

    # Nothing has been recorded: not one byte of either file has moved.
    assert log_file.read_bytes() == log_before
    assert state_file.read_bytes() == state_before
    assert client.get("/elements-state").json.get("TMPD") != "inactive"

    # The practised prediction is the real one for that copy: a stopped turbo
    # with its gate open and the scroll running reads rough vacuum.
    predicted = client.post("/practice/prediction", json={"state": practised}).json
    assert predicted["prediction"]["volumes"]["qms-vessel"] == "rough-vacuum"


def test_save_writes_exactly_one_event_carrying_the_presses_in_order(client, tmp_path):
    """One row, one timeline entry, one state jump -- signed by the operator."""
    identify(client)
    log_file = tmp_path / "logs.csv"
    client.post("/update", json={"id": "GVU", "status": "active"})
    before = len(client.get("/history/events").json)

    presses = [
        {"id": "TMPD", "status": "inactive"},
        {"id": "GVD", "status": "active"},
        {"id": "RoughD", "status": "active"},
    ]
    saved = client.post("/practice/save", json={"presses": presses})
    assert saved.status_code == 200
    assert saved.json["presses"] == 3
    assert saved.json["auto"] is False
    assert saved.json["note"] == "practice sequence, 3 presses"

    events = client.get("/history/events").json
    assert len(events) == before + 1
    event = events[-1]
    assert event["user"] == "operator"
    assert [(change["id"], change["state"]) for change in event["changes"]] == [
        ("TMPD", False),
        ("GVD", True),
        ("RoughD", True),
    ]
    # The final state is the recorded one, and the answer carries the new
    # prediction so the page redraws from the same walk that made the change.
    state = client.get("/elements-state").json
    assert (state["TMPD"], state["GVD"], state["RoughD"]) == ("inactive", "active", "active")
    assert saved.json["prediction"]["volumes"]["qms-vessel"] == "rough-vacuum"
    # And exactly one new line in the log, not three.
    lines = [line for line in log_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len([line for line in lines if "practice sequence" in line]) == 1


def test_a_saved_sequence_replays_as_one_jump(client):
    """Undoing the event undoes every press in it, in reverse."""
    identify(client)
    client.post("/update", json={"id": "GVU", "status": "active"})
    before_state = dict(client.get("/elements-state").json)
    client.post(
        "/practice/save",
        json={
            "presses": [
                {"id": "TMPD", "status": "inactive"},
                {"id": "GVD", "status": "active"},
            ]
        },
    )
    events = client.get("/history/events").json
    # The moment before the sequence is the state before every press in it.
    replayed = client.get("/history/state/{}".format(len(events) - 2)).json["state"]
    assert replayed["GVU"] is True
    assert replayed.get("GVD", False) is (before_state.get("GVD") == "active")
    assert replayed.get("TMPD", False) is (before_state.get("TMPD") == "active")
    # And the moment of the sequence itself is the state after all of it.
    after = client.get("/history/state/{}".format(len(events) - 1)).json["state"]
    assert after["GVD"] is True and after["TMPD"] is False


def test_the_timer_saves_the_same_event_and_says_it_did(client):
    """An auto-save is the same one event, marked so nobody thinks it was pressed."""
    identify(client)
    saved = client.post(
        "/practice/save",
        json={"presses": [{"id": "GVU", "status": "active"}], "auto": True},
    )
    assert saved.status_code == 200
    assert saved.json["auto"] is True
    assert saved.json["note"] == "practice sequence, 1 press, saved by the timer"
    assert client.get("/history/events").json[-1]["note"].endswith("saved by the timer")


def test_the_fallback_interval_is_a_setting_within_honest_bounds(tmp_path):
    """Three minutes by default, and a typo cannot turn the fallback off."""
    (tmp_path / "operators.json").write_text(
        json.dumps({"operators": ["operator"]}), encoding="utf-8"
    )
    app = make_app(tmp_path)
    assert app.test_client().get("/practice/settings").json == {"autosave_seconds": 180}
    for written, expected in ((600, 600), (1, 30), (99999, 1800), ("soon", 180)):
        (tmp_path / "settings.json").write_text(
            json.dumps({"PRACTICE_AUTOSAVE_SECONDS": written}), encoding="utf-8"
        )
        client = make_app(tmp_path).test_client()
        assert client.get("/practice/settings").json["autosave_seconds"] == expected


def test_practice_refuses_what_it_cannot_record(client):
    """An unsigned save, an unknown element, the linked valve, an endless list."""
    assert client.post(
        "/practice/save", json={"presses": [{"id": "GVU", "status": "active"}]}
    ).status_code == 428
    identify(client)
    assert client.post("/practice/save", json={"presses": []}).status_code == 400
    assert client.post("/practice/save", json={"presses": "GVU"}).status_code == 400
    assert client.post(
        "/practice/save", json={"presses": [{"id": "not-an-element", "status": "active"}]}
    ).status_code == 400
    assert client.post(
        "/practice/save", json={"presses": [{"id": "GVU", "status": "maybe"}]}
    ).status_code == 400
    assert client.post(
        "/practice/save", json={"presses": [{"id": "Membrane", "status": "active"}]}
    ).status_code == 400
    assert client.post(
        "/practice/save", json={"presses": [{"id": "GVU", "status": "active"}] * 201}
    ).status_code == 400
    assert client.post("/practice/prediction", json={"state": "open"}).status_code == 400
    assert client.post(
        "/press-warnings", json={"id": "GVU", "status": "active", "state": 3}
    ).status_code == 400


def test_an_older_four_column_log_is_widened_once_and_keeps_every_row(tmp_path):
    """The two new columns arrive without losing a byte of recorded history."""
    from pihti.server import LEGACY_LOG_FIELDS, LOG_FIELDS, widen_log_header

    log_file = tmp_path / "logs.csv"
    log_file.write_text(
        "timestamp,id,status,user\n"
        "2026-09-01 10:00:00,GVU,active,KAA\n"
        "2026-09-01 10:00:05,TMPU,inactive,KAA\n",
        encoding="utf-8",
    )
    widen_log_header(log_file)
    rows = csv_rows(log_file)
    assert rows[0] == LOG_FIELDS
    assert [row[:4] for row in rows[1:]] == [
        ["2026-09-01 10:00:00", "GVU", "active", "KAA"],
        ["2026-09-01 10:00:05", "TMPU", "inactive", "KAA"],
    ]
    # Idempotent, and a log whose header is neither shape is left alone.
    widen_log_header(log_file)
    assert csv_rows(log_file)[0] == LOG_FIELDS
    other = tmp_path / "other.csv"
    other.write_text("when,what\n1,2\n", encoding="utf-8")
    widen_log_header(other)
    assert other.read_text(encoding="utf-8") == "when,what\n1,2\n"
    assert LEGACY_LOG_FIELDS == ["timestamp", "id", "status", "user"]


def test_the_page_teaches_saving_and_says_it_is_practising(client):
    """The switch, the standing line, a loud Save that is never hidden."""
    page = client.get("/").data.decode("utf-8")
    for marker in (
        'id="practice-toggle"',
        'id="practice-note"',
        'id="practice-save"',
        'id="practice-undo"',
        'id="practice-discard"',
        'id="practice-timer"',
        'id="practice-banner"',
    ):
        assert marker in page, marker
    # The banner stands above the drawing, where the presses are made.
    assert page.index('id="practice-banner"') < page.index('id="diagram-container"')
    script = diagram_script()
    assert '"Nothing is recorded until you press Save."' in script
    assert "Save ${count} press" in script
    assert "Saves itself in ${minutes}:${seconds}." in script
    # The five-second poll never paints the record over a rehearsal, Discard
    # cancels the timer, and leaving with unsaved practice asks first.
    assert "if (practiceOn) return;" in script
    assert 'window.addEventListener("beforeunload"' in script
    assert "if (!practiceUnsaved() || isInteracting) return;" in script
    css = diagram_styles()
    assert ".practice-save {" in css
    assert ".practice-banner {" in css


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("opened", [False, True])
@pytest.mark.parametrize("vented", [False, True])
def test_nitrogen_source_handle_uses_shared_valve_paint(client, theme, opened, vented):
    mapping = plumbing_map.themed_map(client.get("/plumbing").json, theme)
    state = {"gaspanel-valve-n": "active" if opened else "inactive"}
    if vented:
        state["gaspanel-valve-vent"] = "active"
    prediction = plumbing_map.predict(mapping, state, "membrane")
    valve = prediction["elements"]["gaspanel-valve-n"]
    assert valve["valve"] and valve["open"] is opened
    if opened:
        pipe = prediction["elements"]["gaspanel-manifold"]
        assert valve["fill"] == valve["stroke"] == pipe["stroke"]
    else:
        assert valve["fill"] == mapping["drawing"]["valve_closed"]
        assert valve["stroke"] == mapping["drawing"]["valve_closed_edge"]
    assert "gaspanel-valve-n" not in mapping["dark_theme"]["surfaces"]
    rendered = plumbing_map.style_rules(mapping, state, "membrane")
    assert f'#gaspanel-valve-n{{stroke:{valve["stroke"]} !important;fill:{valve["fill"]} !important}}' in rendered
