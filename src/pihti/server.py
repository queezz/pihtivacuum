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
from cryptography.fernet import Fernet, InvalidToken
from flask import (
    Flask,
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
from pihti.utils.hostinfo import get_hostinfo


PKG_DIR = Path(__file__).resolve().parent
MAX_LOGS = 1000


def _default_private_dir() -> Path:
    if local_app_data := os.environ.get("LOCALAPPDATA"):
        return Path(local_app_data) / "pihti-diagram"
    return Path.home() / ".config" / "pihti-diagram"


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else default


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


def _load_operator_names(app: Flask) -> list[str]:
    inline_key = os.environ.get("PIHTI_USERS_KEY")
    key = (
        inline_key.encode("ascii")
        if inline_key
        else Path(app.config["USERS_KEY_FILE"]).read_bytes().strip()
    )
    encrypted_data = Path(app.config["USERS_FILE_ENCRYPTED"]).read_bytes()
    try:
        users = json.loads(Fernet(key).decrypt(encrypted_data).decode("utf-8"))
    except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("The encrypted users file or its key is invalid.") from exc
    if not isinstance(users, dict) or not all(
        isinstance(name, str) and isinstance(password_hash, str)
        for name, password_hash in users.items()
    ):
        raise RuntimeError("The encrypted users file has an invalid structure.")
    return sorted(users, key=str.casefold)


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
    figure = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1)
    for column in columns_linear:
        figure.add_trace(
            go.Scatter(x=dataframe["date"], y=dataframe[column], mode="lines", name=column),
            row=1,
            col=1,
        )
    for column in columns_log:
        figure.add_trace(
            go.Scatter(x=dataframe["date"], y=dataframe[column], mode="lines", name=column),
            row=2,
            col=1,
        )
    figure.update_layout(
        height=800,
        yaxis={"title": "Signals (Linear)", "type": "linear"},
        yaxis2={"title": "Signals (Log)", "type": "log", "tickformat": ".1e"},
        legend={"title": "Signals"},
    )
    return pio.to_html(figure, full_html=False)


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
    operators_cache: list[str] | None = None
    last_plot_html: str | None = None

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
        return {"hostinfo": get_hostinfo(), "app_version": __version__}

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

    @app.route("/history/state/<int:idx>")
    def get_history_state(idx):
        events = load_history_events(Path(app.config["LOG_FILE"]))
        if idx < 0 or idx >= len(events):
            return jsonify({"error": "Invalid index"}), 400
        state_now = {key: value == "active" for key, value in elements_state.items()}
        return jsonify({"index": idx, "state": state_at_index(events, state_now, idx)})

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

    @app.route("/navbar")
    def navbar():
        return render_template("navbar.html")

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

    @app.route("/plot", methods=["POST"])
    def plot_file():
        nonlocal last_plot_html
        file_path = resolve_cu_file(request.form.get("file"))
        columns = get_cu_columns(file_path)
        dataframe = pd.read_csv(file_path, skiprows=10, names=columns)
        last_plot_html = generate_plot_html(
            dataframe, ["Ip_c"], ["Pu_c", "Pd_c", "Bu_c"]
        )
        plot_path = Path(app.config["LAST_PLOT_FILE"])
        plot_path.parent.mkdir(parents=True, exist_ok=True)
        plot_path.write_text(last_plot_html, encoding="utf-8")
        return jsonify(plot=last_plot_html)

    @app.route("/get_last_plot")
    def get_last_plot():
        if last_plot_html:
            return jsonify({"plot": last_plot_html})
        try:
            plot = Path(app.config["LAST_PLOT_FILE"]).read_text(encoding="utf-8")
            return jsonify({"plot": plot})
        except FileNotFoundError:
            return jsonify({"plot": "<p>No plot available. Please generate one.</p>"})

    @app.route("/download_controlunit_csv")
    def download_controlunit_csv():
        file_path = resolve_cu_file(request.args.get("file"))
        return send_file(file_path, as_attachment=True, download_name=file_path.name)

    def available_operators() -> list[str]:
        nonlocal operators_cache
        if operators_cache is None:
            operators_cache = _load_operator_names(app)
        return operators_cache

    @app.route("/api/identify", methods=["POST"])
    @app.route("/login", methods=["POST"])
    def choose_operator():
        try:
            operators = available_operators()
        except (FileNotFoundError, RuntimeError):
            current_app.logger.exception("Operator identities are unavailable")
            return jsonify({"message": "Operator identities are not configured on this machine."}), 503
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

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("identity_page"))

    @app.route("/identify")
    def identity_page():
        try:
            operators = available_operators()
            unavailable = False
        except (FileNotFoundError, RuntimeError):
            current_app.logger.exception("Operator identities are unavailable")
            operators = []
            unavailable = True
        return render_template(
            "identify.html", operators=operators, identities_unavailable=unavailable
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
    host = os.environ.get("PIHTI_HOST", "127.0.0.1")
    port = int(os.environ.get("PIHTI_PORT", "5000"))
    debug = _boolean_env("PIHTI_DEBUG")
    if debug and host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("PIHTI_DEBUG may only be used on a loopback host.")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
