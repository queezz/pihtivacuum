"""Predict what is inside each pipe from the valve positions an operator entered.

This is a diagram connectivity prediction and nothing else. It reads the volume
map in ``static/plumbing.json`` — which drawn pipe belongs to which volume, and
which valve joins which two volumes — walks the volumes that open valves join
together, and names the result. It never reads a pressure, and every surface
that shows it says so.
"""

from __future__ import annotations

import json
from pathlib import Path

ISOLATED = "isolated"


def load_plumbing(static_folder: str | Path) -> dict:
    """The volume map as authored, or an empty map when the file is absent."""
    path = Path(static_folder) / "plumbing.json"
    if not path.is_file():
        return {"volumes": {}, "valves": [], "pumps": [], "gas_sources": [], "states": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _is(state: dict, element_id: str, wanted: str) -> bool:
    current = "active" if state.get(element_id) in ("active", True) else "inactive"
    return current == wanted


def _components(volumes: list[str], edges: list[tuple[str, str]]) -> list[set[str]]:
    """Volumes that open valves have joined into one continuous space."""
    parent = {name: name for name in volumes}

    def find(name: str) -> str:
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    for left, right in edges:
        if left in parent and right in parent:
            parent[find(left)] = find(right)
    groups: dict[str, set[str]] = {}
    for name in volumes:
        groups.setdefault(find(name), set()).add(name)
    return list(groups.values())


def line_connects(plumbing: dict, line_mode: str | None) -> bool:
    """Is the line between the two vessels a connection in this configuration?

    Only ``Pipe open`` is. With a membrane installed, or with the line set up
    for boron deposition, something is mounted in that pipe and the two vessels
    are separate spaces (owner review 2026-09-08). An unrecorded configuration
    is not a connection either: the prediction does not claim a route nobody
    has told it about.
    """
    config = plumbing.get("line_configuration") or {}
    modes = config.get("modes") or {}
    mode = modes.get(line_mode or "unknown", modes.get("unknown") or {})
    return bool(mode.get("connects"))


def _divided_volume(plumbing: dict, line_mode: str | None) -> str | None:
    """The volume a barrier in the line divides, or ``None`` when it is open."""
    config = plumbing.get("line_configuration") or {}
    volume = config.get("volume")
    if not volume or line_connects(plumbing, line_mode):
        return None
    return volume


def predict(plumbing: dict, state: dict, line_mode: str | None = None) -> dict:
    """Name the predicted content of every volume, and of every drawn element.

    Air beats gas beats high vacuum beats rough vacuum: a volume open to
    atmosphere is reported as air even while a turbo is marked running on it,
    because that is the reading an operator needs first.

    ``line_mode`` is the Line configuration annotation. When it says something
    is mounted in the pipe between the two vessels, that volume is divided:
    each valve on it opens onto its own side of the barrier, so the two vessels
    never join through it. The one drawn pipe then takes the state both sides
    agree on, or ``isolated`` when they differ — a single line cannot honestly
    carry two answers.
    """
    volumes: dict = plumbing.get("volumes") or {}
    names = list(volumes)
    divided = _divided_volume(plumbing, line_mode)
    if divided in volumes:
        names = [name for name in names if name != divided]
    else:
        divided = None
    edges = []
    stubs: list[str] = []
    for valve in plumbing.get("valves") or []:
        joins = list(valve.get("joins") or ())
        if len(joins) != 2 or not _is(state, valve["id"], valve.get("open_when", "active")):
            continue
        if divided and divided in joins:
            # One side of the barrier, private to this valve: an open valve
            # reaches the pipe, and the pipe reaches nothing through it.
            stub = f"{divided}@{valve['id']}"
            stubs.append(stub)
            names.append(stub)
            joins = [stub if name == divided else name for name in joins]
        edges.append(tuple(joins))
    by_volume: dict[str, str] = {}
    for component in _components(list(dict.fromkeys(names)), edges):
        verdict = ISOLATED
        if any(volumes.get(name, {}).get("always") == "air" for name in component):
            verdict = "air"
        elif any(
            source["volume"] in component and _is(state, source["id"], "active")
            for source in plumbing.get("gas_sources") or []
        ):
            verdict = "gas"
        else:
            running = [
                pump
                for pump in plumbing.get("pumps") or []
                if pump["volume"] in component and _is(state, pump["id"], "active")
            ]
            if any(pump.get("kind") == "turbo" for pump in running):
                verdict = "high-vacuum"
            elif running:
                verdict = "rough-vacuum"
        for name in component:
            by_volume[name] = verdict

    if divided:
        # The drawn pipe is one line with a barrier partway along it. It may
        # only claim a state both sides agree on.
        sides = {by_volume.pop(stub) for stub in stubs}
        by_volume[divided] = sides.pop() if len(sides) == 1 else ISOLATED

    colors = {item["id"]: item["color"] for item in plumbing.get("states") or []}
    tints = {item["id"]: item.get("tint") for item in plumbing.get("states") or []}
    elements: dict[str, dict] = {}
    for name, volume in volumes.items():
        verdict = by_volume.get(name, ISOLATED)
        vessel = volume.get("vessel")
        for element_id in volume.get("elements") or []:
            item = {
                "volume": name,
                "state": verdict,
                "stroke": colors.get(verdict, "#000000"),
            }
            # A vessel is a volume you can see into, so it says its state with
            # a light tint of the same colour rather than an outline alone
            # (owner review 2026-09-08). Every other element is a line.
            if element_id == vessel and tints.get(verdict):
                item["fill"] = tints[verdict]
            elements[element_id] = item
    air = sorted(
        volumes[name].get("label", name)
        for name, verdict in by_volume.items()
        if verdict == "air" and volumes.get(name, {}).get("always") != "air"
    )
    return {"volumes": by_volume, "elements": elements, "air": air}


def _safe_id(element_id: str) -> bool:
    return bool(element_id) and all(ch.isalnum() or ch in "#-_" for ch in element_id)


def _safe_color(color: str | None) -> bool:
    return bool(color) and all(ch.isalnum() or ch == "#" for ch in color)


def style_rules(plumbing: dict, state: dict, line_mode: str | None = None) -> str:
    """The prediction as CSS, for the server-rendered ``/state.svg``.

    Every rule carries ``!important``: queezz authored each pipe with an inline
    ``style`` attribute, and an inline style beats a stylesheet, so the plain
    rules this used to write were overridden by the drawing's own black and the
    saved render came back uncoloured.
    """
    prediction = predict(plumbing, state, line_mode)
    rules = []
    for element_id, item in sorted(prediction["elements"].items()):
        if not _safe_id(element_id):
            continue
        declarations = []
        if _safe_color(item.get("stroke")):
            declarations.append(f"stroke:{item['stroke']} !important")
        if _safe_color(item.get("fill")):
            declarations.append(f"fill:{item['fill']} !important")
        if declarations:
            rules.append(f"#{element_id}{{{';'.join(declarations)}}}")
    return "".join(rules)
