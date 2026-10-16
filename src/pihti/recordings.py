"""Find ControlUnit recordings without reading their samples.

The browser reads a recording's original files and decides every unit, label
and gap itself (`static/js/recording-reader.js`, since 0.29.0): parsing a long
recording here took the Pi minutes. This module only pairs a recording with
its same-run companions and, for the legacy POST /plot route, reads a header.
"""
import csv
import re
from pathlib import Path

RUN = re.compile(r"^(?:cu|kikusui|pid)_(\d{8}_\d{6})\.csv$")


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


def recording_columns(path):
    """The column header of one recording, read up to its first sample row."""
    columns = None
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
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
            break
    if not columns or not ({"date", "timestamp"} & set(columns)):
        raise ValueError("The recording has no timestamp column.")
    return columns
