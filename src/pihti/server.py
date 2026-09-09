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


#: The history log's columns. The first four are the ones every release since
#: the beginning has written: one press per row. ``changes`` and ``note`` were
#: added in 0.19.0 for the practice mode, which records a whole practised
#: sequence as **one** event rather than one row per valve (queezz, 2026-09-08:
#: "That way one state jump, less history spamming"). An ordinary press leaves
#: both empty and reads exactly as it always did.
LOG_FIELDS = ["timestamp", "id", "status", "user", "changes", "note"]
LEGACY_LOG_FIELDS = ["timestamp", "id", "status", "user"]


def widen_log_header(file_path: Path) -> None:
    """Give an older four-column log its two new columns, once, atomically.

    A row with six values under a four-column header is a corrupt log, so the
    header has to move before the first practice sequence is written. Every
    existing row is preserved exactly and simply gains two empty fields; the
    rewrite goes to a temporary file beside the log and lands with one
    ``os.replace``, so an interrupted run leaves the original untouched. A log
    whose header is neither shape is left completely alone.
    """
    if not file_path.is_file():
        return
    with file_path.open(newline="", encoding="utf-8") as csvfile:
        header = next(csv.reader(csvfile), [])
    if header[: len(LOG_FIELDS)] == LOG_FIELDS or header != LEGACY_LOG_FIELDS:
        return
    rows = load_logs_from_csv(file_path)
    temp = file_path.with_name(file_path.name + ".widening")
    with temp.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=LOG_FIELDS, restval="")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name) or "" for name in LOG_FIELDS})
    os.replace(temp, file_path)


def save_log_csv(log_entry: dict[str, str], file_path: Path) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    widen_log_header(file_path)
    file_exists = file_path.exists()
    with file_path.open("a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=LOG_FIELDS, restval="")
        if not file_exists:
            writer.writeheader()
        writer.writerow({name: log_entry.get(name, "") for name in LOG_FIELDS})


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
        changes = parse_changes(row.get("changes"))
        if not changes:
            changes = [
                {
                    "id": apply_id_alias(row.get("id", "")),
                    "state": (row.get("status", "inactive") or "inactive").strip().lower()
                    == "active",
                }
            ]
        events.append(
            {
                "ts": timestamp,
                # The last change is the event's own id and status, so anything
                # reading a single press off an event still reads what it did.
                "id": changes[-1]["id"],
                "state": changes[-1]["state"],
                "user": row.get("user", ""),
                "changes": changes,
                "note": (row.get("note") or "").strip(),
            }
        )
    _EVENTS_CACHE[file_path] = (stamp, events)
    return events


def parse_changes(raw) -> list[dict]:
    """The presses one recorded event carries, in order, or an empty list.

    A practice sequence lands as one event with every press inside it (0.19.0),
    written as JSON in the log's own ``changes`` column. An ordinary press
    leaves that column empty and this returns nothing, so the row's own
    ``id``/``status`` stand as the one change they always were. Anything
    unreadable is treated the same way: a row is never guessed at.
    """
    if not isinstance(raw, str) or not raw.strip():
        return []
    try:
        items = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(items, list):
        return []
    changes = []
    for item in items:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        changes.append(
            {
                "id": apply_id_alias(str(item["id"])),
                "state": str(item.get("status", "inactive")).strip().lower() == "active",
            }
        )
    return changes


def state_at_index(events: list[dict], state_now: dict[str, bool], idx: int) -> dict[str, bool]:
    """Reconstruct absolute element state after event ``idx``.

    An event carries one press ordinarily and a whole practised sequence when
    it is a practice save, so this walks each event's own list of changes —
    forwards to remember what each element was before, backwards to put it
    back. A sequence is undone press by press in reverse, which is what makes
    a saved procedure one jump on the timeline rather than one per valve.
    """
    state = dict(state_now)
    last_by_id: dict[str, bool] = {}
    previous: list[list[bool | None]] = []
    for event in events:
        row: list[bool | None] = []
        for change in event["changes"]:
            row.append(last_by_id.get(change["id"]))
            last_by_id[change["id"]] = change["state"]
        previous.append(row)
    for event_idx in range(len(events) - 1, idx, -1):
        changes = events[event_idx]["changes"]
        for change_idx in range(len(changes) - 1, -1, -1):
            before = previous[event_idx][change_idx]
            state[changes[change_idx]["id"]] = before if before is not None else False
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


def load_line_mode_history(context_log: Path) -> list[tuple[datetime, str]]:
    """Every recorded Line configuration change, oldest first.

    Read once and walked, rather than re-read per question: rebuilding the
    volume memory asks this for every diagram change in the log, and reopening
    a CSV a thousand times to answer the same thousand questions is how a
    Raspberry Pi gets slow.
    """
    rows: list[tuple[datetime, str]] = []
    if not context_log.is_file():
        return rows
    try:
        with context_log.open(newline="", encoding="utf-8") as csvfile:
            for row in csv.DictReader(csvfile):
                stamp = parse_timestamp(row.get("timestamp"))
                if stamp is not None and row.get("line_mode"):
                    rows.append((stamp, row["line_mode"]))
    except (OSError, csv.Error):
        return []
    rows.sort(key=lambda item: item[0])
    return rows


def line_mode_at(context_log: Path, moment: datetime) -> str:
    """The Line configuration recorded at or before ``moment``.

    A replayed diagram is coloured by the state it is replaying, and what was
    mounted in the pipe between the two vessels is part of that state. Before
    the first recorded change the honest answer is ``unknown``.
    """
    mode = "unknown"
    for stamp, value in load_line_mode_history(context_log):
        if stamp <= moment:
            mode = value
    return mode


def memory_timeline(
    plumbing: dict,
    events: list[dict],
    base_state: dict,
    modes: list[tuple[datetime, str]],
) -> list[dict]:
    """What each volume was last under, replayed forward through history.

    The memory lives in the state file, but a state file can be new, copied to
    another machine, or simply older than the log beside it — so it is also
    derivable, by walking the recorded presses from the beginning and asking the
    same predictor at each one. Snapshot ``0`` is before the first press ever
    recorded; snapshot ``i + 1`` is the memory just after event ``i``.

    Each snapshot is a fresh dictionary (``update_memory`` never mutates), so
    the list can be kept and indexed without copying it again.
    """
    memory: dict = {}
    state = dict(base_state)
    snapshots = [memory]
    cursor = 0
    mode = "unknown"
    for event in events:
        # A practice sequence is one event with several presses in it, so the
        # whole sequence lands before the memory is asked what it now holds:
        # one prediction per event, which is the "one state jump" the mode
        # exists for.
        for change in event["changes"]:
            state[change["id"]] = "active" if change["state"] else "inactive"
        while cursor < len(modes) and modes[cursor][0] <= event["ts"]:
            mode = modes[cursor][1]
            cursor += 1
        prediction = plumbing_map.predict(
            plumbing, state, mode, memory=memory, now=event["ts"]
        )
        memory = plumbing_map.update_memory(plumbing, memory, prediction, event["ts"])
        snapshots.append(memory)
    return snapshots


def render_state_svg(
    svg_text: str,
    element_config: list[dict],
    state: dict,
    plumbing: dict | None = None,
    line_mode: str | None = None,
    wide: bool = False,
    now=None,
    theme: str = "light",
) -> str:
    """Return the authored SVG with operator-entered fills applied as a style block.

    With a volume map, the pipes also carry their predicted vacuum state as a
    stroke colour with round caps and joins, the two vessels and the manifold
    junctions their state colour as a fill — two-tone where two things reach
    them — every valve its open or closed ink, and any vessel holding gas the
    bottle symbols drawn inside it. That is the same prediction the page paints,
    so a saved or historical render reads the same way. ``wide`` is the page's
    own widening switch, off by default since 0.15.0.

    A drawn valve the map links to the Line configuration (the ``Membrane``
    element) is read through that configuration here too, so its own fill in
    a saved render can never disagree with what it did to the prediction next
    to it.
    """
    rules = []
    overlay = ""
    predicted_fills: set[str] = set()
    if plumbing:
        plumbing = plumbing_map.themed_map(plumbing, theme)
        ground = plumbing["drawing"]["ground"]
        rules.append(f"svg{{background:{ground}}}")
        if theme == "dark":
            for element_id, paints in plumbing.get("dark_theme", {}).get("surfaces", {}).items():
                if plumbing_map._safe_id(element_id):
                    ink = ";".join(
                        f"{key}:{value} !important" for key, value in paints.items()
                        if key in {"fill", "stroke"} and plumbing_map._safe_color(value)
                    )
                    rules.append(f"#{element_id}{{{ink}}}")
        state = plumbing_map.apply_line_mode_to_state(plumbing, state, line_mode)
        prediction = plumbing_map.predict(plumbing, state, line_mode, now=now)
        rules.append(
            plumbing_map.style_rules(
                plumbing,
                state,
                line_mode,
                plumbing_map.authored_stroke_widths(svg_text),
                wide=wide,
                now=now,
            )
        )
        overlay = plumbing_map.overlay_markup(
            plumbing, state, line_mode, svg_text, now=now
        )
        predicted_fills = {
            element_id
            for element_id, item in prediction["elements"].items()
            if item.get("fill")
        }
    for item in element_config:
        element_id = item.get("id")
        colors = item.get("colors") or {}
        if not element_id or not isinstance(colors, dict):
            continue
        # A valve says its position in the prediction's own colours now, so the
        # operator palette must not paint over it (0.15.0). Pumps, gauges and
        # the gas bottles keep theirs: they are equipment, not volumes.
        if element_id in predicted_fills:
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
    return svg_text[:closing] + style + overlay + svg_text[closing:]


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
    _stored_state = _load_json(state_file, {})
    if not isinstance(_stored_state, dict):
        _stored_state = {}
    # The valve positions and, beside them under one reserved key, what each
    # volume was last under and since when. The two are read apart here so that
    # `/state` keeps answering with valves alone — the memory is not an element
    # and no page should have to skip it.
    elements_state: dict[str, str] = apply_id_aliases_to_state(
        {key: value for key, value in _stored_state.items() if key != plumbing_map.MEMORY_KEY}
    )
    volume_memory: dict = plumbing_map.read_memory(_stored_state)
    memory_rebuilt = bool(volume_memory)
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
    # The replayed memory, cached against the two logs it is read from.
    memory_cache: tuple | None = None

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
                    # One press ordinarily; a whole practised sequence when the
                    # event is a practice save, with the note that says so.
                    "changes": [
                        {"id": change["id"], "state": change["state"]}
                        for change in event["changes"]
                    ],
                    "note": event["note"],
                }
                for event in events
            ]
        )

    def current_state_flags() -> dict[str, bool]:
        return {key: value == "active" for key, value in elements_state.items()}

    def replayed_memory() -> list[dict]:
        """The memory after each recorded press, rebuilt only when history moves.

        One walk over the log per change to it, cached against the same stamp
        `load_history_events` uses plus the Line-configuration log's own, so a
        page that asks about ten historical moments pays for one walk.
        """
        nonlocal memory_cache
        log_file = Path(app.config["LOG_FILE"])
        context_log = Path(app.config["OPERATION_CONTEXT_LOG_FILE"])

        def stamp_of(path: Path):
            try:
                stat = path.stat()
            except FileNotFoundError:
                return None
            return (stat.st_mtime_ns, stat.st_size)

        stamp = (stamp_of(log_file), stamp_of(context_log))
        if memory_cache is not None and memory_cache[0] == stamp:
            return memory_cache[1]
        events = load_history_events(log_file)
        snapshots = memory_timeline(
            plumbing,
            events,
            state_at_index(events, current_state_flags(), -1),
            load_line_mode_history(context_log),
        )
        memory_cache = (stamp, snapshots)
        return snapshots

    def live_memory() -> dict:
        """The memory as it stands now, rebuilt from history the first time.

        A state file written before this release carries no memory, and so does
        a fresh checkout on another machine. Rather than start blind — every
        volume "isolated, unknown" until somebody presses something — the log
        beside it is replayed once, and the answer is written to the state file
        with the next real change rather than on a read.
        """
        nonlocal volume_memory, memory_rebuilt
        if not memory_rebuilt:
            snapshots = replayed_memory()
            if snapshots:
                volume_memory = snapshots[-1]
            memory_rebuilt = True
        return volume_memory

    def save_state() -> None:
        """Valves and memory, in the one file, written together."""
        state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {**elements_state, plumbing_map.MEMORY_KEY: live_memory()}
        state_file.write_text(json.dumps(payload, indent=4) + "\n", encoding="utf-8")

    def remember_now(mode: str | None = None) -> dict:
        """Update the memory from the state as it now stands, and return it."""
        nonlocal volume_memory
        memory = live_memory()
        prediction = plumbing_map.predict(
            plumbing, elements_state, mode or current_line_mode(), memory=memory
        )
        volume_memory = plumbing_map.update_memory(
            plumbing, memory, prediction, datetime.now()
        )
        return volume_memory

    def current_prediction(mode: str | None = None) -> dict:
        """The prediction for the state as it stands, this second.

        One walk over the volume map: a few hundred dictionary lookups, no file
        read and no drawing parsed. It rides back on the two routes that change
        something so the page can repaint from the same answer that made the
        change (0.15.0), instead of asking ``/predicted-vacuum`` for it in a
        second round trip — which is what queezz felt as "membrane installed to
        open pipe is VERY slow. And no reason for it to be slow."
        """
        return plumbing_map.predict(
            plumbing,
            elements_state,
            mode or current_line_mode(),
            memory=live_memory(),
        )

    def prediction_at(moment: datetime, idx: int, state: dict) -> dict:
        """The prediction for a replayed moment, memory and all.

        The memory is the replayed one, not today's: a moment is read as it was,
        including how long a vessel had been shut *by then*.
        """
        snapshots = replayed_memory()
        memory = snapshots[idx + 1] if 0 <= idx + 1 < len(snapshots) else {}
        mode = plumbing_map.resolve_line_mode(
            plumbing, line_mode_at(Path(app.config["OPERATION_CONTEXT_LOG_FILE"]), moment)
        )
        return plumbing_map.predict(plumbing, state, mode, memory=memory, now=moment)

    def current_line_mode() -> str:
        """What an operator last said is mounted in the line between the vessels.

        Read through the map's own alias table, so a configuration recorded
        under an older spelling still names the same mode and an unreadable one
        falls back to ``unknown`` rather than to a guess.
        """
        context = _load_json(Path(app.config["OPERATION_CONTEXT_FILE"]), {})
        return plumbing_map.resolve_line_mode(plumbing, context.get("line_mode"))

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
        state: dict = {**elements_state, plumbing_map.MEMORY_KEY: live_memory()}
        mode = current_line_mode()
        when = None
        if raw_moment := request.args.get("at"):
            moment = parse_timestamp(raw_moment)
            if moment is None:
                return jsonify({"error": "at must be YYYY-MM-DD HH:MM:SS"}), 400
            events = load_history_events(Path(app.config["LOG_FILE"]))
            idx = index_at_timestamp(events, moment)
            if idx is None:
                return jsonify({"error": "No diagram change at or before that moment"}), 404
            snapshots = replayed_memory()
            memory = snapshots[idx + 1] if 0 <= idx + 1 < len(snapshots) else {}
            state = {
                **state_at_index(events, current_state_flags(), idx),
                plumbing_map.MEMORY_KEY: memory,
            }
            when = moment
            mode = plumbing_map.resolve_line_mode(
                plumbing,
                line_mode_at(Path(app.config["OPERATION_CONTEXT_LOG_FILE"]), moment),
            )
        svg_text = (Path(app.static_folder) / "diagram.svg").read_text(encoding="utf-8")
        # `?wide=1` matches a browser whose reading-aid switch is on. Off is the
        # default on both sides since 0.15.0, so the two agree without asking.
        wide = request.args.get("wide") in {"1", "true", "on"}
        return Response(
            render_state_svg(
                svg_text, element_config, state, plumbing, mode, wide=wide, now=when,
                theme=request.args.get("theme", "light"),
            ),
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
            return jsonify(
                {
                    "message": "State unchanged",
                    "state": elements_state,
                    "prediction": current_prediction(),
                }
            )

        warnings = plumbing_map.press_warnings(plumbing, elements_state, element_id, status, current_line_mode())
        if warnings:
            record_warning_attempt(element_id, status, elements_state, warnings)
            return jsonify({"requires_practice": True, "warnings": warnings,
                            "error": "Try this change in Practice and review the warning first."}), 409

        touch_operator()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Preserve inlet vacuum even on the first press of a legacy state file.
        remember_now()
        elements_state[element_id] = status
        # What each volume was last under is updated from the state this press
        # just made, and saved in the one file beside the valve positions.
        remember_now()
        save_state()
        log_entry = {
            "timestamp": timestamp,
            "id": element_id,
            "status": status,
            "user": session["username"],
        }
        logs.append(log_entry)
        del logs[:-MAX_LOGS]
        save_log_csv(log_entry, Path(app.config["LOG_FILE"]))
        # The new prediction travels back with the press. It is the same walk
        # `/predicted-vacuum` would answer with a moment later, and sending it
        # here is what lets the page redraw in one round trip instead of two.
        return jsonify(
            {
                "message": "State updated successfully",
                "state": elements_state,
                "prediction": current_prediction(),
            }
        )

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
        return jsonify({**plumbing, "dark_palette": plumbing_map.theme_palette(plumbing)})

    @app.route("/predicted-vacuum")
    def predicted_vacuum():
        """What each volume most likely holds, read off the entered valve positions.

        A prediction from the diagram's own connectivity, never a measurement.
        ``?at=YYYY-MM-DD HH:MM:SS`` answers for that moment instead of now, so a
        replayed diagram is coloured by the state it is replaying — including
        what the Line configuration said was mounted between the two vessels
        then.
        """
        if raw_moment := request.args.get("at"):
            moment = parse_timestamp(raw_moment)
            if moment is None:
                return jsonify({"error": "at must be YYYY-MM-DD HH:MM:SS"}), 400
            events = load_history_events(Path(app.config["LOG_FILE"]))
            idx = index_at_timestamp(events, moment)
            if idx is None:
                return jsonify({"error": "No diagram change at or before that moment"}), 404
            state = state_at_index(events, current_state_flags(), idx)
            return jsonify(prediction_at(moment, idx, state))
        return jsonify(current_prediction())

    # -- practice: a local copy of the state, saved as one event ------------
    #
    # queezz, 2026-09-08 (letters ``20260908-9d38bf34-8415c7`` and
    # ``20260908-e460b66f-616b53``): "I want now a 'practice' before recording
    # history mode somehow. You open the valve, and see where color
    # (vacuum/air) goes. Then you can undo. Also maybe using that we can do a
    # procedure, then save state. That way one state jump, less history
    # spamming. And better operational safety."
    #
    # The predictor has been state-in, prediction-out since 0.17.0 precisely so
    # this could exist: the page keeps its own copy of the valve positions and
    # of the volume memory, and these two routes answer about *that* copy
    # without touching the recorded one. Neither writes anything.

    #: A practised sequence is a procedure, not a session's whole afternoon.
    #: The bound is here so a malformed or hostile body cannot make the server
    #: walk an unbounded list; four guides' worth of steps is well inside it.
    MAX_PRACTICE_PRESSES = 200

    #: How long a quiet practice waits before it saves itself. Three minutes:
    #: long enough that nobody is interrupted mid-procedure — the longest guide
    #: here is six steps and a slow one is a minute or two — and short enough
    #: that a person called away from the rig does not lose the sequence. It is
    #: a setting because a rig is not a stopwatch: ``PRACTICE_AUTOSAVE_SECONDS``
    #: in the machine-local settings file, held between half a minute and half
    #: an hour so a typo cannot turn the fallback off or make it fire mid-press.
    PRACTICE_AUTOSAVE_DEFAULT = 180
    PRACTICE_AUTOSAVE_MIN = 30
    PRACTICE_AUTOSAVE_MAX = 1800

    def practice_autosave_seconds() -> int:
        settings = _load_json(Path(app.config["SETTINGS_FILE"]), {})
        try:
            value = int(settings.get("PRACTICE_AUTOSAVE_SECONDS", PRACTICE_AUTOSAVE_DEFAULT))
        except (TypeError, ValueError):
            value = PRACTICE_AUTOSAVE_DEFAULT
        return max(PRACTICE_AUTOSAVE_MIN, min(PRACTICE_AUTOSAVE_MAX, value))

    def practised_state(raw) -> dict[str, str] | None:
        """A state supplied by the page, read as this diagram's own elements.

        Anything that is not a drawn element is dropped rather than trusted,
        and every value becomes one of the two words the rest of this server
        uses. A body that is not an object at all is refused.
        """
        if not isinstance(raw, dict):
            return None
        return {
            apply_id_alias(str(key)): "active" if value in ("active", True) else "inactive"
            for key, value in raw.items()
            if apply_id_alias(str(key)) in valid_elements
        }

    @app.route("/practice/settings")
    def practice_settings():
        """How long the practice fallback timer waits, in seconds."""
        return jsonify({"autosave_seconds": practice_autosave_seconds()})

    @app.route("/practice/prediction", methods=["POST"])
    def practice_prediction():
        """The prediction for a practised state, and the memory it leaves.

        The same walk ``/predicted-vacuum`` answers with, over the copy the
        page is holding rather than over the recorded state. The volume memory
        travels with it — out and back — so a vessel shut *in practice* reads
        as sealed since that moment without a single byte of the recorded
        memory moving. Nothing here is written to disk.
        """
        data = request.get_json(silent=True) or {}
        state = practised_state(data.get("state"))
        if state is None:
            return jsonify({"error": "state must be an object of element ids"}), 400
        supplied = data.get("memory")
        memory = (
            plumbing_map.read_memory({plumbing_map.MEMORY_KEY: supplied})
            if isinstance(supplied, dict)
            else live_memory()
        )
        moment = datetime.now()
        prediction = plumbing_map.predict(
            plumbing, state, current_line_mode(), memory=memory, now=moment
        )
        return jsonify(
            {
                "prediction": prediction,
                "memory": plumbing_map.update_memory(plumbing, memory, prediction, moment),
            }
        )

    @app.route("/practice/save", methods=["POST"])
    @operator_required
    def practice_save():
        """Record a whole practised sequence as one signed history event.

        Every press in order, the final state, and the operator who practised
        it — one row in the log and one entry on the timeline, so a procedure
        lands as a single jump rather than as one entry per valve. ``auto``
        says the fallback timer saved it rather than a person, and the note
        carried in the event says so out loud: a record nobody pressed Save on
        must not pretend somebody did.
        """
        data = request.get_json(silent=True) or {}
        presses = data.get("presses")
        auto = bool(data.get("auto"))
        if not isinstance(presses, list) or not presses:
            return jsonify({"error": "presses must be a non-empty list"}), 400
        if len(presses) > MAX_PRACTICE_PRESSES:
            return jsonify({"error": "Too many presses in one sequence"}), 400
        changes: list[dict[str, str]] = []
        for item in presses:
            element_id = apply_id_alias(str((item or {}).get("id") or ""))
            status = (item or {}).get("status")
            if element_id not in valid_elements or status not in {"active", "inactive"}:
                return jsonify({"error": "Invalid element or status"}), 400
            if element_id == linked_valve_id:
                return jsonify(
                    {"error": f"{element_id} follows the Line configuration and cannot be set directly."}
                ), 400
            changes.append({"id": element_id, "status": status})

        rehearsed = dict(elements_state)
        warnings = []
        for change in changes:
            warnings.extend(plumbing_map.press_warnings(plumbing, rehearsed, change["id"], change["status"], current_line_mode()))
            memory = plumbing_map.update_memory(plumbing, plumbing_map.read_memory(rehearsed),
                                                plumbing_map.predict(plumbing, rehearsed, current_line_mode()), datetime.now())
            rehearsed[change["id"]] = change["status"]
            rehearsed[plumbing_map.MEMORY_KEY] = memory
        if warnings and (auto or data.get("acknowledge_warnings") is not True):
            return jsonify({"warnings": warnings, "error": "Warnings require an explicit review before saving."}), 409

        touch_operator()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        remember_now()
        for change in changes:
            elements_state[change["id"]] = change["status"]
            remember_now()
        save_state()
        count = len(changes)
        note = f"practice sequence, {count} press{'' if count == 1 else 'es'}"
        if auto:
            note += ", saved by the timer"
        if warnings:
            note += ", warnings reviewed"
        log_entry = {
            "timestamp": timestamp,
            "id": changes[-1]["id"],
            "status": changes[-1]["status"],
            "user": session["username"],
            "changes": json.dumps(changes, separators=(",", ":")),
            "note": note,
        }
        logs.append(log_entry)
        del logs[:-MAX_LOGS]
        save_log_csv(log_entry, Path(app.config["LOG_FILE"]))
        return jsonify(
            {
                "message": "Practice sequence recorded",
                "presses": count,
                "auto": auto,
                "note": note,
                "timestamp": timestamp,
                "state": elements_state,
                "prediction": current_prediction(),
            }
        )

    def record_warning_attempt(element_id, status, state, warnings):
        # Separate from state history: an intention is not a hardware action.
        path = Path(app.config["LOG_FILE"]).with_name("warning_attempts.jsonl")
        entry = {"timestamp": datetime.now().astimezone().isoformat(),
                 "user": session["username"], "id": element_id, "status": status,
                 "warnings": warnings, "state": state, "line_mode": current_line_mode()}
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")

    @app.route("/warning-attempt", methods=["POST"])
    @operator_required
    def warning_attempt():
        data = request.get_json(silent=True) or {}
        element_id, status = data.get("id"), data.get("status")
        if element_id not in valid_elements or status not in {"active", "inactive"} or element_id == linked_valve_id:
            return jsonify({"error": "Invalid element or status"}), 400
        state = practised_state(data.get("state")) if "state" in data else dict(elements_state)
        if state is None:
            return jsonify({"error": "state must be an object of element ids"}), 400
        if isinstance(data.get("memory"), dict):
            state[plumbing_map.MEMORY_KEY] = plumbing_map.read_memory({plumbing_map.MEMORY_KEY: data["memory"]})
        warnings = plumbing_map.press_warnings(plumbing, state, element_id, status, current_line_mode())
        if warnings:
            record_warning_attempt(element_id, status, state, warnings)
        return jsonify({"warnings": warnings})

    @app.route("/download-warning-attempts")
    def download_warning_attempts():
        path = Path(app.config["LOG_FILE"]).with_name("warning_attempts.jsonl")
        if not path.exists():
            return Response("", mimetype="application/x-ndjson", headers={"Content-Disposition": "attachment; filename=warning_attempts.jsonl"})
        return send_file(path, as_attachment=True)

    @app.route("/press-warnings", methods=["GET", "POST"])
    def press_warnings():
        """What one press would newly join to gas or vent air, before it is made.

        Asked by the page just before its confirm box appears, so the box can
        carry the sentence. It answers about a *copy* of the entered state with
        the press applied and changes nothing: this route reads, and the press
        itself still goes to ``/update``.

        The two things it answers about are a switched-on ionization gauge and
        a spinning turbo pump. It is a prediction from the valve positions an
        operator entered — the same walk that colours the pipes — and never an
        interlock: it reads no pressure, refuses no press, and protects no
        hardware.
        """
        data = request.get_json(silent=True) or {} if request.method == "POST" else {}
        element_id = apply_id_alias(str(data.get("id") or request.args.get("id") or ""))
        status = data.get("status") or request.args.get("status")
        if element_id not in valid_elements or status not in {"active", "inactive"}:
            return jsonify({"error": "Invalid element or status"}), 400
        # A POST may carry the practised state to judge the press against, so a
        # rehearsal gets the same warnings a real press would — seeing them is
        # the point of practising (queezz, 2026-09-08). Absent, or on a GET, the
        # question is asked of the recorded state exactly as before.
        practised = practised_state(data.get("state")) if data.get("state") is not None else None
        if data.get("state") is not None and practised is None:
            return jsonify({"error": "state must be an object of element ids"}), 400
        if practised is not None and isinstance(data.get("memory"), dict):
            practised[plumbing_map.MEMORY_KEY] = plumbing_map.read_memory({plumbing_map.MEMORY_KEY: data["memory"]})
        return jsonify(
            {
                "warnings": plumbing_map.press_warnings(
                    plumbing,
                    practised if practised is not None else elements_state,
                    element_id,
                    status,
                    current_line_mode(),
                )
            }
        )

    @app.route("/operation-guides")
    def serve_operation_guides():
        """The guides, plus the facts about this rig that are not valve positions.

        A guide step can apply only when something is physically plugged in, and
        that is a fact about this machine's rig rather than about the drawing:
        queezz, 2026-09-08, "venting the downstream is also better with N2, but
        the flow calibration pipe is currently disconnected. We can connect."
        So it lives in the machine-local settings file beside the control-unit
        directory, defaults to *disconnected*, and travels to the page with the
        guides — one guide file serving a rig with that pipe plugged in and a
        rig without it. Nothing about the diagram is read here, and nothing is
        written anywhere.
        """
        guides = _load_json(Path(app.static_folder) / "operationGuides.json", {})
        settings = _load_json(Path(app.config["SETTINGS_FILE"]), {})
        guides["facts"] = {
            "flow-calibration-pipe-connected": bool(
                settings.get("FLOW_CALIBRATION_PIPE_CONNECTED", False)
            ),
        }
        return jsonify(guides)

    @app.route("/operation-context", methods=["GET", "POST"])
    def operation_context():
        context_file = Path(app.config["OPERATION_CONTEXT_FILE"])
        context = _load_json(
            context_file,
            {"line_mode": "unknown", "updated_at": None, "updated_by": None},
        )
        context = {
            **context,
            "line_mode": plumbing_map.resolve_line_mode(plumbing, context.get("line_mode")),
        }
        if request.method == "GET":
            return jsonify(context)
        if "username" not in session:
            return jsonify({"error": "Operator identity required"}), 428
        data = request.get_json(silent=True) or {}
        mode = data.get("line_mode")
        if mode not in set(plumbing_map.line_modes(plumbing)):
            return jsonify({"error": "Invalid line configuration"}), 400
        if context.get("line_mode") == mode:
            return jsonify({**context, "prediction": current_prediction(mode)})
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
        # A configuration change joins or separates the two vessels, so it can
        # seal a volume exactly as a valve can: the memory moves with it.
        remember_now(mode)
        save_state()
        # The prediction for the configuration just recorded rides back with it,
        # so the drawing redraws from this answer rather than from two more
        # round trips (0.15.0; queezz on 0.13.0: "membrane installed to open pipe
        # is VERY slow. And no reason for it to be slow.").
        return jsonify({**context, "state": elements_state, "prediction": current_prediction(mode)})

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
