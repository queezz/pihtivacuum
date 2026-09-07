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


def predict(plumbing: dict, state: dict) -> dict:
    """Name the predicted content of every volume, and of every drawn element.

    Air beats gas beats high vacuum beats rough vacuum: a volume open to
    atmosphere is reported as air even while a turbo is marked running on it,
    because that is the reading an operator needs first.
    """
    volumes: dict = plumbing.get("volumes") or {}
    names = list(volumes)
    edges = [
        tuple(valve["joins"])
        for valve in plumbing.get("valves") or []
        if len(valve.get("joins") or ()) == 2
        and _is(state, valve["id"], valve.get("open_when", "active"))
    ]
    by_volume: dict[str, str] = {}
    for component in _components(names, edges):
        verdict = ISOLATED
        if any(volumes[name].get("always") == "air" for name in component):
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

    colors = {item["id"]: item["color"] for item in plumbing.get("states") or []}
    elements: dict[str, dict] = {}
    for name, volume in volumes.items():
        verdict = by_volume.get(name, ISOLATED)
        for element_id in volume.get("elements") or []:
            elements[element_id] = {
                "volume": name,
                "state": verdict,
                "stroke": colors.get(verdict, "#000000"),
            }
    air = sorted(
        volumes[name].get("label", name)
        for name, verdict in by_volume.items()
        if verdict == "air" and volumes[name].get("always") != "air"
    )
    return {"volumes": by_volume, "elements": elements, "air": air}


def style_rules(plumbing: dict, state: dict) -> str:
    """The prediction as CSS, for the server-rendered ``/state.svg``."""
    prediction = predict(plumbing, state)
    rules = []
    for element_id, item in sorted(prediction["elements"].items()):
        stroke = item["stroke"]
        if all(ch.isalnum() or ch in "#-_" for ch in element_id) and all(
            ch.isalnum() or ch == "#" for ch in stroke
        ):
            rules.append(f"#{element_id}{{stroke:{stroke}}}")
    return "".join(rules)
