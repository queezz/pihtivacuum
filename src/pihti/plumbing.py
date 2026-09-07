"""Predict what is inside each pipe from the valve positions an operator entered.

This is a diagram connectivity prediction and nothing else. It reads the volume
map in ``static/plumbing.json`` — which drawn pipe belongs to which volume, and
which valve joins which two volumes — walks the volumes that open valves join
together, and names the result. It never reads a pressure, and every surface
that shows it says so.
"""

from __future__ import annotations

import json
import re
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


def _connections(
    plumbing: dict, state: dict, names: list[str], edges: list, by_volume: dict[str, str]
) -> dict:
    """What each vessel is joined to right now, in facts rather than sentences.

    queezz, 2026-09-08: "I'd like to see if upstream and downstream are
    connected to a) each other b) gas c) vent air." The answer is read from the
    same open valves the colours are read from — one prediction, never two — and
    is returned as ids so the page can say each one by the name a person uses at
    the rig. His own order is kept: the other vessel first, then gas, then vent
    air, then the pumps.

    One difference from the colouring: the room is not a pipe. ``atmosphere``
    is one volume in the map, so two separately vented lines land in the same
    component and both are honestly painted red — but they are not plumbed to
    each other, and saying so would be a lie in a readout whose whole purpose is
    to answer "are these two joined". So the reach used here drops every edge
    that runs through open air, and a vent valve is named for a vessel only when
    its other side is really in that vessel's space.
    """
    volumes: dict = plumbing.get("volumes") or {}
    open_air = {name for name, volume in volumes.items() if volume.get("always") == "air"}
    plumbed = [edge for edge in edges if not (set(edge) & open_air)]
    reach = {
        name: component
        for component in _components(names, plumbed)
        for name in component
    }
    vessels = [name for name, volume in volumes.items() if volume.get("vessel")]
    answers = {}
    for name in vessels:
        space = reach.get(name, {name})
        answers[name] = {
            "label": volumes[name].get("label", name),
            "state": by_volume.get(name, ISOLATED),
            "joined": [other for other in vessels if other != name and other in space],
            "gas": [
                {"id": source["id"], "gas": source.get("gas", "gas")}
                for source in plumbing.get("gas_sources") or []
                if source["volume"] in space and _is(state, source["id"], "active")
            ],
            "air": [
                {"id": valve["id"]}
                for valve in plumbing.get("valves") or []
                if valve.get("vent")
                and _is(state, valve["id"], valve.get("open_when", "active"))
                and any(joined in space for joined in valve.get("joins") or ())
            ],
            "pumps": [
                {"id": pump["id"], "kind": pump.get("kind", "pump")}
                for pump in plumbing.get("pumps") or []
                if pump["volume"] in space and _is(state, pump["id"], "active")
            ],
        }
    return answers


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
    band = float((plumbing.get("drawing") or {}).get("band") or 1)
    elements: dict[str, dict] = {}
    for name, volume in volumes.items():
        verdict = by_volume.get(name, ISOLATED)
        colour = colors.get(verdict, "#000000")
        # A vessel is a volume you can see into, and a T or a cross is a small
        # one, so they say their state by their body rather than by an outline.
        # queezz, 2026-09-08: "We can go very loud, why not? Color it the color
        # of the vacuum I say. Or gas. Or air." So the fill is the full state
        # colour, not a tint of it, and the shape keeps the dark outline he drew
        # so it still reads. Every other element the map names is a line.
        bodies = set(volume.get("junctions") or ())
        if volume.get("vessel"):
            bodies.add(volume["vessel"])
        for element_id in volume.get("elements") or []:
            if element_id in bodies:
                elements[element_id] = {"volume": name, "state": verdict, "fill": colour}
            else:
                elements[element_id] = _line(name, verdict, colour, band)
    # A gauge's stem is the short line from its symbol to what it reads, and it
    # belongs to that volume as much as any pipe does (queezz, 2026-09-08:
    # "all gauges stems don't have colors... If we can work with that, fine").
    for gauge in plumbing.get("gauges") or []:
        stem = gauge.get("stem")
        volume_name = gauge.get("volume")
        if not stem or volume_name not in volumes:
            continue
        verdict = by_volume.get(volume_name, ISOLATED)
        elements[stem] = _line(volume_name, verdict, colors.get(verdict, "#000000"), band)
    air = sorted(
        volumes[name].get("label", name)
        for name, verdict in by_volume.items()
        if verdict == "air" and volumes.get(name, {}).get("always") != "air"
    )
    return {
        "volumes": by_volume,
        "elements": elements,
        "air": air,
        "connections": _connections(plumbing, state, list(dict.fromkeys(names)), edges, by_volume),
    }


def _line(volume: str, verdict: str, colour: str, band: float) -> dict:
    """A drawn line in its volume's colour, and how much wider to draw it.

    The band is a solid widening of the pipe's own stroke, never a translucent
    glow: queezz saw the 0.11.2 halo and said "that's more readable, yes. Also
    way more ugly". An isolated line is never widened — the absence of a claim
    should not be the loudest thing on the drawing.
    """
    item = {"volume": volume, "state": verdict, "stroke": colour}
    if verdict != ISOLATED and band > 1:
        item["band"] = band
    return item


def _safe_id(element_id: str) -> bool:
    return bool(element_id) and all(ch.isalnum() or ch in "#-_" for ch in element_id)


def _safe_color(color: str | None) -> bool:
    return bool(color) and all(ch.isalnum() or ch == "#" for ch in color)


_TAG = re.compile(r"<[^>]+>")
_ID = re.compile(r'\bid="([^"]+)"')
_WIDTH = re.compile(r"stroke-width:\s*([0-9.]+)")


def authored_stroke_widths(svg_text: str) -> dict[str, float]:
    """The stroke width queezz drew each element with, read off its own tag.

    The band the page draws is a multiple of the authored width, so a saved
    render can only match the page if it knows that width. Nothing else is read
    from the drawing here, and an element without an inline width simply has no
    entry.
    """
    widths: dict[str, float] = {}
    for tag in _TAG.findall(svg_text):
        found_id = _ID.search(tag)
        found_width = _WIDTH.search(tag)
        if found_id and found_width:
            try:
                widths[found_id.group(1)] = float(found_width.group(1))
            except ValueError:
                continue
    return widths


def style_rules(
    plumbing: dict,
    state: dict,
    line_mode: str | None = None,
    widths: dict[str, float] | None = None,
) -> str:
    """The prediction as CSS, for the server-rendered ``/state.svg``.

    Every rule carries ``!important``: queezz authored each pipe with an inline
    ``style`` attribute, and an inline style beats a stylesheet, so the plain
    rules this used to write were overridden by the drawing's own black and the
    saved render came back uncoloured.

    ``widths`` are the authored stroke widths, so a saved render carries the
    same solid band the page draws instead of a thinner drawing that reads
    differently from the screen it was saved from.
    """
    prediction = predict(plumbing, state, line_mode)
    rules = []
    for element_id, item in sorted(prediction["elements"].items()):
        if not _safe_id(element_id):
            continue
        declarations = []
        if _safe_color(item.get("stroke")):
            declarations.append(f"stroke:{item['stroke']} !important")
        authored = (widths or {}).get(element_id)
        if item.get("band") and authored:
            declarations.append(
                f"stroke-width:{round(authored * item['band'], 3)} !important"
            )
        if _safe_color(item.get("fill")):
            declarations.append(f"fill:{item['fill']} !important")
        if declarations:
            rules.append(f"#{element_id}{{{';'.join(declarations)}}}")
    return "".join(rules)
