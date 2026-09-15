"""Read self-describing ControlUnit recordings without touching their originals."""
import csv
import math
import re
from datetime import datetime
from pathlib import Path

RUN = re.compile(r"^(?:cu|kikusui|pid)_(\d{8}_\d{6})\.csv$")
LABELS = {
    "Ip": "Plasma current", "Pu": "Upstream Pfeiffer pressure",
    "Pd": "Downstream ion gauge pressure", "Pu2": "Upstream ion gauge pressure",
    "Bu": "Upstream Baratron pressure", "Bd": "Downstream Baratron pressure",
    "MFC1": "Hydrogen MFC signal", "MFC2": "Oxygen MFC signal",
    "Ci": "Cathode ADC current signal", "Cv": "Cathode ADC voltage signal",
}
UNITS = {
    "voltage_v": "V", "current_a": "A", "commanded_cathode_mv": "mV",
    "plasma_target_a": "A", "logger_elapsed_s": "s", "query_ms": "ms",
    "output_on": "0/1", "time": "s", "QMS_signal": "0/1",
    "PresetV_mfc1": "V", "PresetV_mfc2": "V", "PresetV_cathode": "mV",
}
DEFAULT_CHANNELS = {
    "Ip_c", "Pu_c", "Pd_c", "Pu2_c", "Bu_c", "Bd_c", "voltage_v", "current_a",
}
TELEMETRY_LABELS = {
    "voltage_v": "Cathode supply voltage", "current_a": "Cathode current (Ic)",
    "commanded_cathode_mv": "Commanded cathode drive",
    "plasma_target_a": "Plasma current target", "output_on": "Supply output",
    "query_ms": "Query duration", "logger_elapsed_s": "Logger elapsed time",
}
SETTING_LABELS = {
    "PresetV_mfc1": "Hydrogen MFC setpoint",
    "PresetV_mfc2": "Oxygen MFC setpoint",
    "PresetV_cathode": "Commanded cathode drive",
    "time": "ADC elapsed time",
    "QMS_signal": "QMS trigger",
}


def companion_paths(path):
    """Return same-run CSV companions; undated legacy files stand alone."""
    path = Path(path)
    if path.suffix.lower() != ".csv":
        raise ValueError("Choose a named ControlUnit CSV recording.")
    parent = path.parent.resolve()
    if path.resolve().parent != parent:
        raise ValueError("A recording leaves the recording directory.")
    if not path.is_file():
        raise ValueError("The recording is unavailable.")
    match = RUN.fullmatch(path.name)
    if not match:
        return [path]
    result = []
    for prefix in ("cu", "kikusui", "pid"):
        candidate = parent / (prefix + "_" + match.group(1) + ".csv")
        if candidate.exists():
            if candidate.resolve().parent != parent:
                raise ValueError("A recording companion leaves the recording directory.")
            result.append(candidate)
    return result


def _read(path):
    columns = None
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        # One reader preserves quoted multiline fields in sidecar error/identity text.
        for values in csv.reader(stream):
            if not values or not any(value.strip() for value in values):
                continue
            first = values[0].strip()
            if first.startswith("#"):
                if first[1:].strip().lower() == "columns":
                    columns = [value.strip() for value in values[1:]]
                continue
            if first.lower() in ("date", "timestamp"):
                columns = [value.strip() for value in values]
                continue
            if columns is None or len(set(columns)) != len(columns):
                raise ValueError("The recording needs a unique column header.")
            if len(values) != len(columns):
                raise ValueError("A recording row does not match its column header.")
            rows.append(dict(zip(columns, values)))
    if not columns or not ({"date", "timestamp"} & set(columns)):
        raise ValueError("The recording has no timestamp column.")
    return columns, rows


def _number(value):
    if str(value).strip().lower() in ("true", "false"):
        return float(str(value).strip().lower() == "true")
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def _describe(column, source):
    base = column[:-2] if column.endswith("_c") else column
    label = LABELS.get(base, column.replace("_", " "))
    unit = UNITS.get(column, "unknown")
    group = "Recorded settings"
    if source == "kikusui":
        group = "Kikusui telemetry"
        label = TELEMETRY_LABELS.get(column, label)
        if column == "voltage_v":
            group = "Cathode voltage"
        elif column in ("current_a", "plasma_target_a"):
            group = "Cathode current"
    elif base in LABELS:
        group = "Converted signals" if column.endswith("_c") else "Raw signals"
        unit = "V"
        label += f" ({base})" if column.endswith("_c") else f" ({base} raw)"
        if column.endswith("_c"):
            if base in ("Pu", "Pd", "Pu2", "Bu", "Bd"):
                unit = "Torr"
                group = "Pressure"
            elif base == "Ip":
                unit = "A"
                group = "Plasma current"
    elif column.startswith("IGmode"):
        place = "Upstream" if column == "IGmode_Pu2" else "Downstream"
        label = place + " ion gauge output mode"
        unit = "0=Torr linear; 1=Pa log"
    elif column.startswith("IGscale"):
        place = "Upstream" if column == "IGscale_Pu2" else "Downstream"
        label = place + " ion gauge range exponent"
        unit = "exponent"
    elif column.endswith("_off"):
        unit = "0/1"
        label = LABELS.get(column[:-4], column[:-4]) + " off"
    label = SETTING_LABELS.get(column, label)
    return label, unit, group


def _off(row, column):
    base = column.removesuffix("_c")
    flags = row.get(column + "_flags", row.get(base + "_flags", ""))
    return "instrument_off" in flags or _number(row.get(base + "_off")) == 1


def load_recording(path):
    """Return numeric channels with explicit gaps and original source inventory."""
    payload = {"series": [], "sources": [], "notes": [], "time_label": "Recorder local time"}
    offsets = set()
    seen_columns = set()
    invalid_times = invalid_values = off_values = telemetry_gaps = pa_values = 0
    unknown_modes = 0
    has_kikusui = False
    for source_path in companion_paths(path):
        columns, rows = _read(source_path)
        seen_columns.update(columns)
        source = source_path.name.split("_", 1)[0]
        has_kikusui |= source == "kikusui"
        payload["sources"].append({
            "name": source_path.name, "columns": columns, "rows": len(rows),
        })
        stamps = []
        for row in rows:
            try:
                text = row.get("date", row.get("timestamp", ""))
                stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                stamps.append(None)
                invalid_times += 1
                continue
            if stamp.utcoffset() is not None:
                offsets.add(stamp.utcoffset())
            stamps.append(stamp.replace(tzinfo=None).isoformat())
        for column in columns:
            if column in ("date", "timestamp"):
                continue
            numbers = [_number(row[column]) for row in rows]
            label, unit, group = _describe(column, source)
            if not any(value is not None for value in numbers) and unit == "unknown":
                continue
            x, y = [], []
            for stamp, row, value in zip(stamps, rows, numbers):
                if stamp is None:
                    # A null pair breaks the line without inventing a timestamp.
                    x.append(None)
                    y.append(None)
                    continue
                if value is None:
                    invalid_values += 1
                measured = column in ("voltage_v", "current_a", "output_on")
                if source == "kikusui" and measured and row.get("status", "").strip() != "ok":
                    value = None
                    telemetry_gaps += 1
                if _off(row, column):
                    value = None
                    off_values += 1
                if column in ("Pd_c", "Pu2_c"):
                    mode_column = "IGmode" if column == "Pd_c" else "IGmode_Pu2"
                    mode = _number(row.get(mode_column))
                    if mode == 1 and value is not None:
                        value /= 133.32236842105263
                        pa_values += 1
                    elif mode != 0:
                        if value is not None:
                            unknown_modes += 1
                        value = None
                x.append(stamp)
                y.append(value)
            payload["series"].append({
                "id": source + ":" + column, "column": column, "label": label,
                "unit": unit, "group": group, "source": source_path.name,
                "x": x, "y": y, "default_visible": column in DEFAULT_CHANNELS,
                "meaning": (
                    "Recorded linear range exponent: -6 means 10^-6 Torr; "
                    "converted pressure already includes this multiplier."
                    if column.startswith("IGscale") else ""
                ),
                "summary": (
                    ", ".join(
                        f"10^{value:g}" for value in list(dict.fromkeys(
                            value for value in numbers if value is not None
                        ))[:12]
                    ) + " Torr"
                    if column.startswith("IGscale") and any(
                        value is not None for value in numbers
                    ) else ""
                ),
            })
    notes = payload["notes"]
    notes.append("Recorder local time; no viewer timezone conversion.")
    if has_kikusui:
        notes.append("Kikusui uses local receipt time with its recorded offset; queries are sequential.")
    else:
        notes.append("No same-run Kikusui telemetry file is available.")
    if {"Pd_c", "Pu2_c"} & seen_columns:
        notes.append("Linear ion gauge pressure is recorded in Torr; range scaling is already applied.")
    if pa_values:
        notes.append(f"{pa_values} explicitly recorded Pa-mode readings were converted to Torr.")
    if unknown_modes:
        notes.append(
            f"{unknown_modes} ion gauge pressure readings have missing or invalid "
            "recorded output modes and are shown as gaps."
        )
    if {"MFC1_c", "MFC2_c"} & seen_columns:
        notes.append("MFC converted signals remain volts.")
    if invalid_times:
        notes.append(f"{invalid_times} rows have invalid timestamps; lines break at those rows.")
    if invalid_values:
        notes.append(f"{invalid_values} missing or non-numeric channel values are gaps.")
    if off_values:
        notes.append(f"{off_values} readings marked instrument off are gaps.")
    if telemetry_gaps:
        notes.append(f"{telemetry_gaps} non-ok Kikusui measurement values are gaps.")
    if len(offsets) > 1:
        raise ValueError("UTC offsets change within this recording; local-time alignment is ambiguous.")
    payload["series"].sort(key=lambda s: (
        0 if s["default_visible"] else
        1 if s["column"].startswith("PresetV_mfc") or s["column"] in ("MFC1_c", "MFC2_c") else
        3 if s["group"] == "Raw signals" else 2
    ))
    return payload
