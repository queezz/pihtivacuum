"""PIHTI interactive vacuum diagram server."""

from __future__ import annotations

import csv
import json
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from flask import (
    Flask,
    Response,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from plotly.subplots import make_subplots
from pihti import __version__
from pihti.roster import default_private_dir as _default_private_dir
from pihti.roster import env_path as _env_path
from pihti.roster import resolve_operators, roster_path
from pihti.utils.hostinfo import get_hostinfo


PKG_DIR = Path(__file__).resolve().parent
MAX_LOGS = 1000
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# Plot series colours: the dataviz reference palette's dark categorical slots
# 1-4 in fixed order, validated against the page's panel surface (#161b22).
PLOT_SERIES_COLORS = ["#3987e5", "#d95926", "#199e70", "#c98500"]
PLOT_SURFACE = "#161b22"
PLOT_INK = "rgba(228, 234, 242, 0.92)"
PLOT_MUTED = "rgba(228, 234, 242, 0.55)"
PLOT_GRID = "rgba(255, 255, 255, 0.08)"


def _boolean_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _operator_timeout() -> timedelta:
    try:
        hours = float(os.environ.get("PIHTI_OPERATOR_TIMEOUT_HOURS", "12"))
    except ValueError:
        hours = 12
    return timedelta(hours=max(1, hours))


def _load_or_create_session_secret() -> bytes:
    if inline_secret := os.environ.get("PIHTI_SESSION_SECRET"):
        return inline_secret.encode("utf-8")
    key_file = _env_path(
        "PIHTI_SESSION_KEY_FILE", _default_private_dir() / "session.key"
    )
    try:
        return key_file.read_bytes()
    except FileNotFoundError:
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(secrets.token_bytes(32))
        key_file.chmod(0o600)
        return key_file.read_bytes()


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def load_logs_from_csv(file_path: Path) -> list[dict[str, str]]:
    try:
        with file_path.open("r", newline="", encoding="utf-8") as csvfile:
            return list(csv.DictReader(csvfile))
    except FileNotFoundError:
        return []


def save_log_csv(log_entry: dict[str, str], file_path: Path) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = file_path.exists()
    with file_path.open("a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["timestamp", "id", "status", "user"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(log_entry)


def load_history_events(file_path: Path) -> list[dict]:
    events = []
    for row in load_logs_from_csv(file_path):
        try:
            timestamp = datetime.strptime(row.get("timestamp", ""), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            timestamp = datetime.min
        events.append(
            {
                "ts": timestamp,
                "id": row.get("id", ""),
                "state": (row.get("status", "inactive") or "inactive").strip().lower()
                == "active",
                "user": row.get("user", ""),
            }
        )
    return events


def state_at_index(events: list[dict], state_now: dict[str, bool], idx: int) -> dict[str, bool]:
    """Reconstruct absolute element state after event ``idx``."""
    state = dict(state_now)
    last_by_id: dict[str, bool] = {}
    previous: list[bool | None] = [None] * len(events)
    for event_idx, event in enumerate(events):
        element_id = event["id"]
        previous[event_idx] = last_by_id.get(element_id)
        last_by_id[element_id] = event["state"]
    for event_idx in range(len(events) - 1, idx, -1):
        event = events[event_idx]
        state[event["id"]] = (
            previous[event_idx] if previous[event_idx] is not None else False
        )
    return state


def parse_timestamp(value: str | None) -> datetime | None:
    """Parse ``YYYY-MM-DD HH:MM:SS`` (a ``T`` separator is accepted too)."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip().replace("T", " "), TIMESTAMP_FORMAT)
    except ValueError:
        return None


def index_at_timestamp(events: list[dict], moment: datetime) -> int | None:
    """Index of the last event at or before ``moment``; ``None`` when none is."""
    idx = None
    for event_idx, event in enumerate(events):
        if event["ts"] <= moment:
            idx = event_idx
    return idx


def render_state_svg(svg_text: str, element_config: list[dict], state: dict) -> str:
    """Return the authored SVG with operator-entered fills applied as a style block."""
    rules = []
    for item in element_config:
        element_id = item.get("id")
        colors = item.get("colors") or {}
        if not element_id or not isinstance(colors, dict):
            continue
        active = state.get(element_id) in ("active", True)
        fill = colors.get("active" if active else "inactive")
        if fill and all(ch.isalnum() or ch in "#-_" for ch in element_id) and all(
            ch.isalnum() or ch in "#(),. " for ch in fill
        ):
            rules.append(f"#{element_id}{{fill:{fill} !important}}")
    style = "<style>" + "".join(rules) + "</style>"
    closing = svg_text.rfind("</svg>")
    if closing < 0:
        return svg_text
    return svg_text[:closing] + style + svg_text[closing:]


def operator_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            wants_json = (
                request.accept_mimetypes.best == "application/json"
                or request.is_json
                or request.path.startswith("/download")
                or request.path.startswith("/history/")
            )
            if wants_json:
                return jsonify({"error": "Operator identity required"}), 428
            return redirect(url_for("identity_page", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def parse_datetime_from_filename(file_name: str) -> datetime:
    try:
        return datetime.strptime(file_name[3:18], "%Y%m%d_%H%M%S")
    except ValueError:
        return datetime.min


def get_cu_columns(file_path: Path) -> list[str]:
    with file_path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.startswith("# Columns"):
                return line.split(",", 1)[1].strip().split(", ")
    raise ValueError(f"No '# Columns' header found in {file_path.name}.")


def generate_plot_html(dataframe, columns_linear, columns_log):
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("Linear channels", "Log channels"),
    )
    colors = iter(PLOT_SERIES_COLORS)
    for row, columns in ((1, columns_linear), (2, columns_log)):
        for column in columns:
            figure.add_trace(
                go.Scatter(
                    x=dataframe["date"],
                    y=dataframe[column],
                    mode="lines",
                    name=column,
                    line={"width": 2, "color": next(colors, None)},
                    hovertemplate="%{y:.3g}<extra>" + column + "</extra>",
                ),
                row=row,
                col=1,
            )
    axis = {
        "gridcolor": PLOT_GRID,
        "zerolinecolor": PLOT_GRID,
        "linecolor": PLOT_GRID,
        "tickfont": {"color": PLOT_MUTED},
        "title_font": {"color": PLOT_MUTED},
    }
    figure.update_layout(
        height=760,
        margin={"l": 60, "r": 20, "t": 40, "b": 40},
        paper_bgcolor=PLOT_SURFACE,
        plot_bgcolor=PLOT_SURFACE,
        font={"color": PLOT_INK, "family": "Aptos, Calibri, system-ui, sans-serif"},
        hovermode="x unified",
        hoverlabel={"bgcolor": "#1b222c", "font": {"color": PLOT_INK}},
        legend={"orientation": "h", "y": -0.06, "font": {"color": PLOT_INK}},
        xaxis={**axis},
        xaxis2={**axis, "title": "Time"},
        yaxis={**axis, "title": "Value (linear)", "type": "linear"},
        yaxis2={**axis, "title": "Value (log)", "type": "log", "tickformat": ".1e"},
    )
    for annotation in figure.layout.annotations:
        annotation.font.color = PLOT_MUTED
        annotation.font.size = 12
    return pio.to_html(figure, full_html=False, config={"displaylogo": False})


def create_app(test_config: dict | None = None) -> Flask:
    runtime_root = _env_path("PIHTI_DATA_ROOT", Path.cwd()).resolve()
    supplied_secret = (test_config or {}).get("SECRET_KEY")
    app = Flask(
        __name__,
        static_folder=str(PKG_DIR / "static"),
        static_url_path="/static",
        template_folder=str(PKG_DIR / "templates"),
    )
    app.config.from_mapping(
        SECRET_KEY=supplied_secret or _load_or_create_session_secret(),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=_boolean_env("PIHTI_COOKIE_SECURE"),
        PERMANENT_SESSION_LIFETIME=_operator_timeout(),
        SESSION_REFRESH_EACH_REQUEST=False,
        MAX_CONTENT_LENGTH=64 * 1024,
        SETTINGS_FILE=_env_path("PIHTI_SETTINGS_FILE", runtime_root / "settings.json"),
        LOG_FILE=runtime_root / "logs.csv",
        STATE_FILE=runtime_root / "elements_state.json",
        OPERATION_CONTEXT_FILE=runtime_root / "operation_context.json",
        OPERATION_CONTEXT_LOG_FILE=runtime_root / "operation_context_log.csv",
        LAST_PLOT_FILE=runtime_root / "last_plot.html",
        LAST_PLOT_META_FILE=runtime_root / "last_plot.json",
        OPERATORS_FILE=roster_path(runtime_root),
        ELEMENTS_CONFIG_FILE=PKG_DIR / "static" / "elementsConfig.json",
        USERS_FILE_ENCRYPTED=_env_path(
            "PIHTI_USERS_FILE", runtime_root / "users.json.enc"
        ),
        USERS_KEY_FILE=_env_path(
            "PIHTI_USERS_KEY_FILE", _default_private_dir() / "users.key"
        ),
        CUDATA_DIRECTORY=os.environ.get("PIHTI_CUDATA_DIRECTORY"),
    )
    if test_config:
        app.config.update(test_config)

    state_file = Path(app.config["STATE_FILE"])
    elements_state: dict[str, str] = _load_json(state_file, {})
    logs = load_logs_from_csv(Path(app.config["LOG_FILE"]))[-MAX_LOGS:]
    element_config = _load_json(Path(app.config["ELEMENTS_CONFIG_FILE"]), [])
    valid_elements = {
        item["id"] for item in element_config if isinstance(item, dict) and "id" in item
    }
    last_plot_html: str | None = None
    last_plot_meta: dict | None = None

    def touch_operator() -> None:
        session["last_activity"] = datetime.now().isoformat(timespec="seconds")

    def load_settings() -> Path:
        if app.config.get("CUDATA_DIRECTORY"):
            directory = Path(app.config["CUDATA_DIRECTORY"])
        else:
            settings = _load_json(Path(app.config["SETTINGS_FILE"]), {})
            directory_value = settings.get("CUDATA_DIRECTORY")
            if not directory_value:
                raise RuntimeError(
                    "Set PIHTI_CUDATA_DIRECTORY or CUDATA_DIRECTORY in the local settings file."
                )
            directory = Path(directory_value)
        if not directory.is_dir():
            raise RuntimeError("The configured control-unit data directory is unavailable.")
        return directory.resolve()

    def available_cu_files() -> list[str]:
        return sorted(
            (
                path.name
                for path in load_settings().iterdir()
                if path.is_file()
                and path.name.startswith("cu_")
                and path.suffix.lower() == ".csv"
            ),
            key=parse_datetime_from_filename,
            reverse=True,
        )

    def resolve_cu_file(file_name: str | None) -> Path:
        if (
            not file_name
            or Path(file_name).name != file_name
            or file_name not in available_cu_files()
        ):
            abort(404)
        return load_settings() / file_name

    @app.context_processor
    def inject_page_context():
        operators, roster_source = available_operators()
        return {
            "hostinfo": get_hostinfo(),
            "app_version": __version__,
            "active_nav": request.endpoint,
            "operators": operators,
            "roster_source": roster_source,
        }

    @app.before_request
    def reject_cross_origin_writes():
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("Origin")
            if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
                abort(403)

    @app.after_request
    def security_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/history")
    def serve_history_view():
        return render_template("history.html")

    @app.route("/history/events")
    def get_history_events():
        events = load_history_events(Path(app.config["LOG_FILE"]))
        return jsonify(
            [
                {
                    "ts": event["ts"].strftime("%Y-%m-%d %H:%M:%S"),
                    "id": event["id"],
                    "state": event["state"],
                    "user": event["user"],
                }
                for event in events
            ]
        )

    def current_state_flags() -> dict[str, bool]:
        return {key: value == "active" for key, value in elements_state.items()}

    @app.route("/history/state/<int:idx>")
    def get_history_state(idx):
        events = load_history_events(Path(app.config["LOG_FILE"]))
        if idx < 0 or idx >= len(events):
            return jsonify({"error": "Invalid index"}), 400
        return jsonify({"index": idx, "state": state_at_index(events, current_state_flags(), idx)})

    @app.route("/history/state-at")
    def get_history_state_at():
        """Absolute diagram state at a timestamp: the last change at or before it."""
        moment = parse_timestamp(request.args.get("ts"))
        if moment is None:
            return jsonify({"error": "ts must be YYYY-MM-DD HH:MM:SS"}), 400
        events = load_history_events(Path(app.config["LOG_FILE"]))
        idx = index_at_timestamp(events, moment)
        if idx is None:
            return jsonify({"error": "No diagram change at or before that moment"}), 404
        return jsonify(
            {
                "index": idx,
                "ts": events[idx]["ts"].strftime(TIMESTAMP_FORMAT),
                "state": state_at_index(events, current_state_flags(), idx),
            }
        )

    @app.route("/state.svg")
    def state_svg():
        """The authored diagram with operator-entered fills applied server-side.

        ``?at=YYYY-MM-DD HH:MM:SS`` renders the state at that moment instead.
        This is the same operator-entered annotation the page shows, not a
        pressure measurement.
        """
        state: dict = elements_state
        if raw_moment := request.args.get("at"):
            moment = parse_timestamp(raw_moment)
            if moment is None:
                return jsonify({"error": "at must be YYYY-MM-DD HH:MM:SS"}), 400
            events = load_history_events(Path(app.config["LOG_FILE"]))
            idx = index_at_timestamp(events, moment)
            if idx is None:
                return jsonify({"error": "No diagram change at or before that moment"}), 404
            state = state_at_index(events, current_state_flags(), idx)
        svg_text = (Path(app.static_folder) / "diagram.svg").read_text(encoding="utf-8")
        return Response(
            render_state_svg(svg_text, element_config, state), mimetype="image/svg+xml"
        )

    @app.route("/update", methods=["POST"])
    @operator_required
    def update_element():
        data = request.get_json(silent=True) or {}
        element_id = data.get("id")
        status = data.get("status")
        if element_id not in valid_elements or status not in {"active", "inactive"}:
            return jsonify({"error": "Invalid element or status"}), 400
        if elements_state.get(element_id, "inactive") == status:
            return jsonify({"message": "State unchanged", "state": elements_state})

        touch_operator()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elements_state[element_id] = status
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(elements_state, indent=4) + "\n", encoding="utf-8")
        log_entry = {
            "timestamp": timestamp,
            "id": element_id,
            "status": status,
            "user": session["username"],
        }
        logs.append(log_entry)
        del logs[:-MAX_LOGS]
        save_log_csv(log_entry, Path(app.config["LOG_FILE"]))
        return jsonify({"message": "State updated successfully", "state": elements_state})

    @app.route("/download_logs")
    def download_logs():
        return send_file(Path(app.config["LOG_FILE"]), as_attachment=True)

    @app.route("/logs-raw")
    def get_logs():
        return jsonify(logs)

    @app.route("/state")
    def get_state():
        return jsonify(elements_state)

    @app.route("/elements-state")
    def get_elements_state():
        return jsonify(elements_state)

    @app.route("/elements-config")
    def serve_config():
        return send_from_directory(directory=app.static_folder, path="elementsConfig.json")

    @app.route("/operation-guides")
    def serve_operation_guides():
        return send_from_directory(directory=app.static_folder, path="operationGuides.json")

    @app.route("/operation-context", methods=["GET", "POST"])
    def operation_context():
        context_file = Path(app.config["OPERATION_CONTEXT_FILE"])
        context = _load_json(
            context_file,
            {"line_mode": "unknown", "updated_at": None, "updated_by": None},
        )
        if request.method == "GET":
            return jsonify(context)
        if "username" not in session:
            return jsonify({"error": "Operator identity required"}), 428
        data = request.get_json(silent=True) or {}
        mode = data.get("line_mode")
        if mode not in {"membrane", "open", "boron"}:
            return jsonify({"error": "Invalid line configuration"}), 400
        if context.get("line_mode") == mode:
            return jsonify(context)
        touch_operator()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        context = {
            "line_mode": mode,
            "updated_at": timestamp,
            "updated_by": session["username"],
        }
        context_file.parent.mkdir(parents=True, exist_ok=True)
        context_file.write_text(json.dumps(context, indent=4) + "\n", encoding="utf-8")
        context_log = Path(app.config["OPERATION_CONTEXT_LOG_FILE"])
        context_log.parent.mkdir(parents=True, exist_ok=True)
        exists = context_log.exists()
        with context_log.open("a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(
                csvfile, fieldnames=["timestamp", "line_mode", "user"]
            )
            if not exists:
                writer.writeheader()
            writer.writerow(
                {"timestamp": timestamp, "line_mode": mode, "user": session["username"]}
            )
        return jsonify(context)

    @app.route("/version")
    def version():
        return jsonify({"name": "pihti", "version": __version__})

    @app.route("/plasmaplots")
    def plasmaplots():
        try:
            files = available_cu_files()
            configured = True
        except RuntimeError:
            files = []
            configured = False
        return render_template(
            "plasmaplots.html", files=files, data_path_configured=configured
        )

    PLOT_LINEAR_CHANNELS = ["Ip_c"]
    PLOT_LOG_CHANNELS = ["Pu_c", "Pd_c", "Bu_c"]

    @app.route("/plot", methods=["POST"])
    def plot_file():
        nonlocal last_plot_html, last_plot_meta
        file_name = request.form.get("file")
        file_path = resolve_cu_file(file_name)
        try:
            columns = get_cu_columns(file_path)
            dataframe = pd.read_csv(file_path, skiprows=10, names=columns)
        except (ValueError, UnicodeDecodeError, pd.errors.ParserError) as exc:
            return jsonify({"error": f"This file is not a readable control-unit log: {exc}"}), 422
        missing = [
            column
            for column in PLOT_LINEAR_CHANNELS + PLOT_LOG_CHANNELS
            if column not in dataframe.columns
        ]
        if missing:
            return jsonify({"error": f"Missing channels in this file: {', '.join(missing)}"}), 422
        last_plot_html = generate_plot_html(dataframe, PLOT_LINEAR_CHANNELS, PLOT_LOG_CHANNELS)
        last_plot_meta = {
            "file": file_name,
            "generated_at": datetime.now().strftime(TIMESTAMP_FORMAT),
            "linear": PLOT_LINEAR_CHANNELS,
            "log": PLOT_LOG_CHANNELS,
        }
        plot_path = Path(app.config["LAST_PLOT_FILE"])
        plot_path.parent.mkdir(parents=True, exist_ok=True)
        plot_path.write_text(last_plot_html, encoding="utf-8")
        Path(app.config["LAST_PLOT_META_FILE"]).write_text(
            json.dumps(last_plot_meta, indent=4) + "\n", encoding="utf-8"
        )
        return jsonify(plot=last_plot_html, **last_plot_meta)

    @app.route("/get_last_plot")
    def get_last_plot():
        """The last generated plot, with the file it was generated from when known."""
        if last_plot_html:
            return jsonify({"plot": last_plot_html, **(last_plot_meta or {})})
        try:
            plot = Path(app.config["LAST_PLOT_FILE"]).read_text(encoding="utf-8")
        except FileNotFoundError:
            return jsonify({"plot": None})
        meta = _load_json(Path(app.config["LAST_PLOT_META_FILE"]), {})
        return jsonify({"plot": plot, **(meta if isinstance(meta, dict) else {})})

    @app.route("/download_controlunit_csv")
    def download_controlunit_csv():
        file_path = resolve_cu_file(request.args.get("file"))
        return send_file(file_path, as_attachment=True, download_name=file_path.name)

    def available_operators() -> tuple[list[str], str]:
        """Names and their source: ``roster``, ``legacy`` registry, or ``missing``."""
        try:
            return resolve_operators(
                Path(app.config["OPERATORS_FILE"]),
                Path(app.config["USERS_FILE_ENCRYPTED"]),
                Path(app.config["USERS_KEY_FILE"]),
            )
        except RuntimeError:
            current_app.logger.exception("The operator roster could not be read")
            return [], "missing"

    @app.route("/api/identify", methods=["POST"])
    @app.route("/login", methods=["POST"])
    def choose_operator():
        operators, source = available_operators()
        if source == "missing":
            return jsonify({"message": "No operator roster exists on this machine."}), 503
        data = request.get_json(silent=True) or request.form
        username = str(data.get("username", ""))
        if username in operators:
            session.clear()
            session.permanent = True
            session["username"] = username
            touch_operator()
            return jsonify(
                {"status": "accepted", "message": "Operator selected", "username": username}
            )
        return jsonify({"message": "Operator identity not found"}), 404

    @app.route("/api/identity/clear", methods=["POST"])
    def clear_operator():
        """Return to read-only. Reading was never gated; this drops the label."""
        session.clear()
        return jsonify({"status": "cleared"})

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("home"))

    @app.route("/identify")
    def identity_page():
        operators, source = available_operators()
        return render_template(
            "identify.html",
            operators=operators,
            roster_source=source,
            roster_command=(
                '& "$env:USERPROFILE\\.venvs\\pihti-diagram\\Scripts\\python.exe" '
                '-m pihti operators add "Name"'
            ),
        )

    @app.route("/login", methods=["GET"])
    @app.route("/loginpage")
    def legacy_login_page():
        return redirect(url_for("identity_page"))

    @app.route("/get_current_user")
    def get_current_user():
        return jsonify(
            {
                "is_authenticated": "username" in session,
                "is_identified": "username" in session,
                "username": session.get("username"),
            }
        )

    @app.route("/<path:path>")
    def serve_static_files(path):
        return send_from_directory(app.static_folder, path)

    return app


app = create_app()


def main():
    # LAN by default: served from one machine, read on a laptop or a phone
    # (owner decision 2026-09-04). Debug stays loopback-only below.
    host = os.environ.get("PIHTI_HOST", "0.0.0.0")
    port = int(os.environ.get("PIHTI_PORT", "5000"))
    debug = _boolean_env("PIHTI_DEBUG")
    if debug and host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("PIHTI_DEBUG may only be used on a loopback host.")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
