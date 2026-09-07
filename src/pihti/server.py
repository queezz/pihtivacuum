"""PIHTI interactive vacuum diagram server."""

from __future__ import annotations

import csv
import json
import os
import secrets
from hashlib import sha256
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
from pihti import neighbours as ensemble
from pihti import plumbing as plumbing_map
from pihti.roster import default_private_dir as _default_private_dir
from pihti.roster import env_path as _env_path
from pihti.roster import resolve_operators, roster_path
from pihti.utils.hostinfo import get_hostinfo


PKG_DIR = Path(__file__).resolve().parent
MAX_LOGS = 1000
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# Old id -> current id, from the 2026-09-08 spelling-and-oddity correction of
# diagram.svg (owner decision 2026-09-08, letter 20260907-b9fddf7b-4768ce).
# History (logs.csv) and the state file (elements_state.json) carry real ids
# from real days; this is applied only when reading them back, so a stored
# event or permalink from before the rename still finds the current element.
# Stored history is never rewritten.
ID_ALIASES: dict[str, str] = {
    "bypas-manifold-downstream-line": "bypass-manifold-downstream-line",
    "bypas-manifold-main": "bypass-manifold-main",
    "bypas-manifold-t-downstream-t": "bypass-manifold-t-downstream-t",
    "bypas-manifold-t-upsteram": "bypass-manifold-t-upstream",
    "bypas-manifold-upstream-gv": "bypass-manifold-upstream-gv",
    "bypas-manifold-upstream-t-to-pipe": "bypass-manifold-upstream-t-to-pipe",
    "bypas-pumpline": "bypass-pumpline",
    "bypas-pumpline-vent": "bypass-pumpline-vent",
    "bypas-pumpline-vent-air-side": "bypass-pumpline-vent-air-side",
    "plasma-vacuum-pump-portt": "plasma-vacuum-pump-port",
    "gasapanel-manifold-argon": "gaspanel-manifold-argon",
    "GVU-6": "upstream-pumpline-vent-valve",
    "GVU-6-9": "downstream-pumpline-vent-valve",
    "Rough-bypass-vent": "bypass-pumpline-vent-valve",
    "nitrogen-line": "nitrogen-bottle",
    "path1464-3-2-6": "gasline-argon-1",
}


def apply_id_alias(element_id: str) -> str:
    """The current id for a possibly-retired one; unrecognised ids pass through."""
    return ID_ALIASES.get(element_id, element_id)


def apply_id_aliases_to_state(state: dict[str, str]) -> dict[str, str]:
    """A state mapping with every old id rewritten to its current id, read-only."""
    return {apply_id_alias(key): value for key, value in state.items()}

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


_EVENTS_CACHE: dict[Path, tuple[tuple[int, int], list[dict]]] = {}


def load_history_events(file_path: Path) -> list[dict]:
    """Parsed history, re-read only when the log file's size or mtime changes.

    Every History request used to parse the whole CSV again; on the Raspberry
    Pi that was most of the click-to-replay delay (0.4.1).
    """
    try:
        stat = file_path.stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
    except FileNotFoundError:
        stamp = None
    cached = _EVENTS_CACHE.get(file_path)
    if cached is not None and cached[0] == stamp:
        return cached[1]
    events = []
    for row in load_logs_from_csv(file_path):
        try:
            timestamp = datetime.strptime(row.get("timestamp", ""), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            timestamp = datetime.min
        events.append(
            {
                "ts": timestamp,
                "id": apply_id_alias(row.get("id", "")),
                "state": (row.get("status", "inactive") or "inactive").strip().lower()
                == "active",
                "user": row.get("user", ""),
            }
        )
    _EVENTS_CACHE[file_path] = (stamp, events)
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


def line_mode_at(context_log: Path, moment: datetime) -> str:
    """The Line configuration recorded at or before ``moment``.

    A replayed diagram is coloured by the state it is replaying, and what was
    mounted in the pipe between the two vessels is part of that state. Before
    the first recorded change the honest answer is ``unknown``.
    """
    mode = "unknown"
    if not context_log.is_file():
        return mode
    try:
        with context_log.open(newline="", encoding="utf-8") as csvfile:
            for row in csv.DictReader(csvfile):
                stamp = parse_timestamp(row.get("timestamp"))
                if stamp is not None and stamp <= moment and row.get("line_mode"):
                    mode = row["line_mode"]
    except (OSError, csv.Error):
        return "unknown"
    return mode


def render_state_svg(
    svg_text: str,
    element_config: list[dict],
    state: dict,
    plumbing: dict | None = None,
    line_mode: str | None = None,
) -> str:
    """Return the authored SVG with operator-entered fills applied as a style block.

    With a volume map, the pipes also carry their predicted vacuum state as a
    stroke colour, the solid band that widens them, and the two vessels and the
    manifold junctions their state colour as a fill — the same prediction the
    page draws, so a saved or historical render reads the same way.

    A drawn valve the map links to the Line configuration (the ``Membrane``
    element) is read through that configuration here too, so its own fill in
    a saved render can never disagree with what it did to the prediction next
    to it.
    """
    rules = []
    if plumbing:
        state = plumbing_map.apply_line_mode_to_state(plumbing, state, line_mode)
        rules.append(
            plumbing_map.style_rules(
                plumbing,
                state,
                line_mode,
                plumbing_map.authored_stroke_widths(svg_text),
            )
        )
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


def group_files_by_day(files: list[str]) -> list[dict]:
    """Newest-first control-unit files folded into one group per recording day.

    Each group is ``{"date": "2026-06-10", "label": "2026-06-10 · Wed",
    "files": [{"name", "time"}]}``; a file whose name carries no timestamp
    lands in a last group labelled "Undated" with its whole name as the time.
    """
    groups: list[dict] = []
    by_date: dict[str, dict] = {}
    for name in files:
        recorded = parse_datetime_from_filename(name)
        if recorded == datetime.min:
            key, label, time = "undated", "Undated", name
        else:
            key = recorded.strftime("%Y-%m-%d")
            label = f"{key} · {recorded.strftime('%a')}"
            time = recorded.strftime("%H:%M:%S")
        group = by_date.get(key)
        if group is None:
            group = by_date[key] = {"date": key, "label": label, "files": []}
            groups.append(group)
        group["files"].append({"name": name, "time": time})
    groups.sort(key=lambda group: group["date"] != "undated", reverse=True)
    return groups


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
        # No fixed height: the plot is framed, and the frame decides how tall
        # it is. A fixed height gave the frame its own scrollbars.
        autosize=True,
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
    return pio.to_html(
        figure,
        full_html=False,
        default_height="100%",
        config={"displaylogo": False, "responsive": True},
    )


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
    elements_state: dict[str, str] = apply_id_aliases_to_state(
        _load_json(state_file, {})
    )
    logs = load_logs_from_csv(Path(app.config["LOG_FILE"]))[-MAX_LOGS:]
    element_config = _load_json(Path(app.config["ELEMENTS_CONFIG_FILE"]), [])
    plumbing = plumbing_map.load_plumbing(app.static_folder)
    valid_elements = {
        item["id"] for item in element_config if isinstance(item, dict) and "id" in item
    }
    # The drawn valve the Line configuration links to itself (queezz,
    # 2026-09-08: "the membrane 'valve' should be linked"). It has no press of
    # its own: `/update` refuses it outright, so the configuration is the only
    # way its state can ever change.
    _linked = plumbing_map.linked_valve(plumbing)
    linked_valve_id = _linked[0] if _linked else None
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
            # Every static URL a template writes carries the release, which is
            # what makes the long cache above safe.
            "asset": lambda filename: url_for("static", filename=filename, v=__version__),
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
        # Static files carry `?v=<release>`, so every release is a new URL and
        # a browser may keep the old copy for a year. Before this, `no-store`
        # on everything meant each tab switch re-fetched the 185 kB diagram,
        # the stylesheet and every script over the lab's WiFi — queezz, on all
        # three tabs, 2026-09-07: "always the lag". A static URL that arrives
        # without the current release on it stays uncacheable, so a stale asset
        # can never outlive the release it belongs to. Pages, data and the plot
        # are never stored.
        versioned = request.endpoint == "static" and request.args.get("v") == __version__
        if versioned:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif request.endpoint == "plot_recordings":
            # A past month never changes, so this may be kept — but it is
            # always revalidated against its ETag, so a month that does gain a
            # recording is never served stale.
            response.headers["Cache-Control"] = "no-cache"
        else:
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        # The last plot is a document of its own, framed by the Plot tab from
        # this same origin so Plotly's megabytes parse outside the page's
        # document instead of freezing it. Other origins still may not frame us.
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
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

    def current_line_mode() -> str:
        """What an operator last said is mounted in the line between the vessels."""
        context = _load_json(Path(app.config["OPERATION_CONTEXT_FILE"]), {})
        mode = context.get("line_mode")
        return mode if isinstance(mode, str) and mode else "unknown"

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
        mode = current_line_mode()
        if raw_moment := request.args.get("at"):
            moment = parse_timestamp(raw_moment)
            if moment is None:
                return jsonify({"error": "at must be YYYY-MM-DD HH:MM:SS"}), 400
            events = load_history_events(Path(app.config["LOG_FILE"]))
            idx = index_at_timestamp(events, moment)
            if idx is None:
                return jsonify({"error": "No diagram change at or before that moment"}), 404
            state = state_at_index(events, current_state_flags(), idx)
            mode = line_mode_at(Path(app.config["OPERATION_CONTEXT_LOG_FILE"]), moment)
        svg_text = (Path(app.static_folder) / "diagram.svg").read_text(encoding="utf-8")
        return Response(
            render_state_svg(svg_text, element_config, state, plumbing, mode),
            mimetype="image/svg+xml",
        )

    @app.route("/update", methods=["POST"])
    @operator_required
    def update_element():
        data = request.get_json(silent=True) or {}
        element_id = data.get("id")
        status = data.get("status")
        if element_id not in valid_elements or status not in {"active", "inactive"}:
            return jsonify({"error": "Invalid element or status"}), 400
        if element_id == linked_valve_id:
            return jsonify(
                {"error": f"{element_id} follows the Line configuration and cannot be set directly."}
            ), 400
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
        # Raw stored state, including whatever a pre-0.12.1 press left for the
        # linked `Membrane` valve. Nothing here disagrees with the Line
        # configuration in practice: the page never colours that element from
        # this endpoint any more (paintPrediction does, from `/predicted-vacuum`),
        # and `/update` refuses to write it going forward.
        return jsonify(elements_state)

    @app.route("/elements-state")
    def get_elements_state():
        return jsonify(elements_state)

    @app.route("/elements-config")
    def serve_config():
        return send_from_directory(directory=app.static_folder, path="elementsConfig.json")

    @app.route("/plumbing")
    def serve_plumbing():
        return send_from_directory(directory=app.static_folder, path="plumbing.json")

    @app.route("/predicted-vacuum")
    def predicted_vacuum():
        """What each volume most likely holds, read off the entered valve positions.

        A prediction from the diagram's own connectivity, never a measurement.
        ``?at=YYYY-MM-DD HH:MM:SS`` answers for that moment instead of now, so a
        replayed diagram is coloured by the state it is replaying — including
        what the Line configuration said was mounted between the two vessels
        then.
        """
        state: dict = elements_state
        mode = current_line_mode()
        if raw_moment := request.args.get("at"):
            moment = parse_timestamp(raw_moment)
            if moment is None:
                return jsonify({"error": "at must be YYYY-MM-DD HH:MM:SS"}), 400
            events = load_history_events(Path(app.config["LOG_FILE"]))
            idx = index_at_timestamp(events, moment)
            if idx is None:
                return jsonify({"error": "No diagram change at or before that moment"}), 404
            state = state_at_index(events, current_state_flags(), idx)
            mode = line_mode_at(Path(app.config["OPERATION_CONTEXT_LOG_FILE"]), moment)
        return jsonify(plumbing_map.predict(plumbing, state, mode))

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

    # -- the three-service ensemble -----------------------------------------
    # Contract agreed with PIHTI Log and ControlUnit (2026-09-04): one
    # unauthenticated GET /api/health per service, {service, version, status,
    # detail}, status in ok/degraded/down, no path or secret in the body.

    def neighbour_settings() -> dict:
        if isinstance(app.config.get("NEIGHBOURS"), dict):
            return {"NEIGHBOURS": app.config["NEIGHBOURS"]}
        return _load_json(Path(app.config["SETTINGS_FILE"]), {})

    def neighbour_addresses() -> dict[str, str]:
        return ensemble.read_addresses(neighbour_settings())

    board = ensemble.NeighbourBoard(neighbour_addresses, probe=app.config.get("NEIGHBOUR_PROBE") or ensemble.read_health)

    def self_health() -> dict:
        events = load_history_events(Path(app.config["LOG_FILE"]))
        if events:
            age = datetime.now() - events[-1]["ts"]
            minutes = int(age.total_seconds() // 60)
            if minutes < 1:
                detail = "diagram changed less than a minute ago"
            elif minutes < 120:
                detail = f"diagram changed {minutes} min ago"
            elif minutes < 48 * 60:
                detail = f"diagram changed {minutes // 60} h ago"
            else:
                detail = f"diagram changed {minutes // (60 * 24)} days ago"
        else:
            detail = "no diagram changes recorded yet"
        return {"service": ensemble.SELF_ALIAS, "version": __version__, "status": "ok", "detail": detail}

    @app.route("/api/health")
    def api_health():
        return jsonify(self_health())

    @app.route("/api/neighbours")
    def api_neighbours():
        if request.args.get("fresh"):
            board.forget()
        me = self_health()
        rows = [
            {"alias": ensemble.SELF_ALIAS, "name": ensemble.DISPLAY_NAMES[ensemble.SELF_ALIAS],
             "url": "", "state": me["status"], "version": me["version"], "detail": me["detail"]},
            *board.neighbours(),
        ]
        # How to start each one, in plain words. The command travels only where
        # one exists: ControlUnit is started by the rig's own GUI.
        starts = ensemble.read_starts(neighbour_settings())
        for row in rows:
            how, command = ensemble.start_hint(row["alias"], starts.get(row["alias"], ""))
            row["start_how"], row["start_command"] = how, command
        return jsonify({"services": rows, "checked_at": datetime.now().strftime(TIMESTAMP_FORMAT)})

    @app.route("/services")
    def services():
        return render_template("services.html", configured=bool(neighbour_addresses()))

    @app.route("/plasmaplots")
    def plasmaplots():
        try:
            files = available_cu_files()
            configured = True
        except RuntimeError:
            files = []
            configured = False
        months = months_with_recordings(files)
        newest = months[0] if months else ""
        opening = files_in_month(newest) if newest else []
        return render_template(
            "plasmaplots.html",
            files=files,
            # Only the newest month travels in the page; the rest is fetched a
            # month at a time and revalidated (see `/plot/recordings`).
            months=months,
            opening_month=newest,
            opening_days=group_files_by_day(opening),
            latest_file=files[0] if files else "",
            data_path_configured=configured,
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
        # The plot itself is not sent back here: it is megabytes of Plotly, and
        # the page loads it into its own frame instead (see `/plot/last.html`).
        return jsonify(**last_plot_meta)

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

    def stored_plot_html() -> str:
        """The last plot's HTML, from memory or from the file it was saved to."""
        if last_plot_html:
            return last_plot_html
        try:
            return Path(app.config["LAST_PLOT_FILE"]).read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""

    def month_of_file(name: str) -> str:
        recorded = parse_datetime_from_filename(name)
        return "undated" if recorded == datetime.min else recorded.strftime("%Y-%m")

    def files_in_month(month: str) -> list[str]:
        return [name for name in available_cu_files() if month_of_file(name) == month]

    def months_with_recordings(files: list[str]) -> list[str]:
        """Newest first, the months that hold at least one recording."""
        seen = []
        for name in files:
            month = month_of_file(name)
            if month not in seen:
                seen.append(month)
        return seen

    @app.route("/plot/recordings")
    def plot_recordings():
        """One month of the archive.

        The page used to carry every recording — thirteen hundred of them, a
        hundred kilobytes of JSON on every visit, and it could not be cached
        because the newest day changes. A month is a few dozen entries, and a
        month that has passed never changes again, so this answer carries an
        ETag: going back a year costs one round trip the first time and a
        304 afterwards (queezz, 2026-09-07: "going back is fine to be slower.
        However we know our history, so that should not be slower").
        """
        month = request.args.get("month", "")
        dated = len(month) == 7 and month[4] == "-" and month[:4].isdigit() and month[5:].isdigit()
        if not dated and month != "undated":
            return jsonify({"error": "A month reads YYYY-MM, or `undated`."}), 400
        try:
            names = files_in_month(month)
        except RuntimeError:
            return jsonify({"error": "No control-unit directory is configured."}), 404
        payload = {"month": month, "days": group_files_by_day(names)}
        response = jsonify(payload)
        response.set_etag(sha256(chr(10).join(names).encode("utf-8")).hexdigest()[:32])
        return response.make_conditional(request)

    @app.route("/plot/meta")
    def plot_meta():
        """What the last plot is, without the plot: a few hundred bytes."""
        meta = last_plot_meta
        if meta is None:
            stored = _load_json(Path(app.config["LAST_PLOT_META_FILE"]), {})
            meta = stored if isinstance(stored, dict) else {}
        return jsonify({"has_plot": bool(stored_plot_html()), **meta})

    # A framed document brings its own margins, its own white page and its own
    # scrollbars unless it is told otherwise, and a plot saved by an older
    # release carries a fixed height that does not fit the frame. This is
    # prepended when the document is served, so plots made before 0.9.1 lose
    # the white border and the inner scrollbars too.
    PLOT_FRAME_STYLE = (
        "<style>html,body{margin:0;padding:0;height:100%;"
        f"background:{PLOT_SURFACE};}}"
        # Plotly's off-screen measuring SVG is a body child and would otherwise
        # give the document a scrollbar of its own.
        "body>svg{position:absolute;top:0;left:0;visibility:hidden;}</style>"
    )

    @app.route("/plot/last.html")
    def plot_last_html():
        """The last plot as its own document, for the Plot tab's frame.

        Plotly's bundle rides inside this HTML and is measured in megabytes.
        Injected into the page it froze the whole tab while it parsed, so the
        plot is framed instead and the page around it stays usable.
        """
        html = stored_plot_html()
        if not html:
            abort(404)
        return Response(PLOT_FRAME_STYLE + html, mimetype="text/html")

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
