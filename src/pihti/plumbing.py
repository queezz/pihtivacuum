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
from copy import deepcopy
from datetime import datetime
from pathlib import Path

ISOLATED = "isolated"
ROUGH = "rough-vacuum"
AIR = "air"
GAS = "gas"


def themed_map(plumbing: dict, theme: str = "light") -> dict:
    """Change presentation only; the authored map and connectivity stay untouched."""
    if theme != "dark":
        return plumbing
    result = deepcopy(plumbing)
    dark = plumbing.get("dark_theme") or {}
    result["drawing"].update(dark.get("drawing") or {})
    for state in result["states"]:
        state["color"] = (dark.get("states") or {}).get(state["id"], state["color"])
    return result


def theme_palette(plumbing: dict) -> dict:
    """Ship the browser the same colour conversion used by saved SVGs.

    Include the quiet sealed tones: those blend toward each theme's own ground.
    No state, connection, timestamp or volume memory is changed by this mapping.
    """
    dark = themed_map(plumbing, "dark")
    colours = {}
    for light_state, dark_state in zip(plumbing["states"], dark["states"]):
        light, ink = light_state["color"], dark_state["color"]
        colours[light] = ink
        colours[sealed_pale(plumbing, light)] = sealed_pale(dark, ink)
    return {
        "colours": colours,
        "drawing": dark["drawing"],
        "states": dark["states"],
        "valve_inks": {
            plumbing["drawing"][key]: dark["drawing"][key]
            for key in ("valve_closed", "valve_closed_edge")
        },
        "surfaces": (plumbing.get("dark_theme") or {}).get("surfaces", {}),
    }

#: The one timestamp spelling this project writes everywhere — the same one
#: ``logs.csv`` carries, so a remembered moment and a history row are the same
#: kind of thing and can be compared without a second format to remember.
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

#: Where the per-volume memory lives inside ``elements_state.json``, beside the
#: valve positions. It is not an element id and never will be: every id on the
#: drawing comes from Inkscape, and none of them starts with an underscore.
MEMORY_KEY = "_volumes"


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


def line_modes(plumbing: dict) -> list[str]:
    """The configurations the card offers, in the order queezz named them.

    Four since 2026-09-08 (owner decision, letter ``20260908-b429ce4b-2ad897``):
    "1. membrane installed. 2. pipe open, but the membrane probe in or bellows,
    which is vacuum wise the same. 3. blank, bellows not connected. 4. boron
    deposition sample holder installed." ``unknown`` is never offered — it is
    what the app says before anyone has answered, not something to choose.
    """
    config = plumbing.get("line_configuration") or {}
    modes = config.get("modes") or {}
    order = [name for name in (config.get("order") or []) if name in modes]
    if order:
        return order
    return [name for name in modes if name != "unknown"]


def resolve_line_mode(plumbing: dict, value: str | None) -> str:
    """A stored configuration value, read as one of the modes this map knows.

    A recorded value outlives the release that wrote it, so an older spelling
    resolves through the map's own ``aliases`` table rather than being lost.
    Anything the map does not know becomes ``unknown``: the prediction says
    nothing rather than guessing which configuration an unreadable value meant.
    """
    config = plumbing.get("line_configuration") or {}
    modes = config.get("modes") or {}
    if not isinstance(value, str) or not value:
        return "unknown"
    if value in modes:
        return value
    alias = (config.get("aliases") or {}).get(value)
    return alias if alias in modes else "unknown"


def _mode(plumbing: dict, line_mode: str | None) -> dict:
    config = plumbing.get("line_configuration") or {}
    modes = config.get("modes") or {}
    return modes.get(resolve_line_mode(plumbing, line_mode), modes.get("unknown") or {})


def line_connects(plumbing: dict, line_mode: str | None) -> bool:
    """Is the line between the two vessels a connection in this configuration?

    Only ``Pipe open`` is. With a membrane installed, with a blank flange in
    place of the probe, or with the line set up for boron deposition, something
    is mounted in that pipe and the two vessels are separate spaces (owner
    review 2026-09-08). An unrecorded configuration is not a connection either:
    the prediction does not claim a route nobody has told it about.
    """
    return bool(_mode(plumbing, line_mode).get("connects"))


def _divided_volume(plumbing: dict, line_mode: str | None) -> str | None:
    """The volume a barrier in the line divides, or ``None`` when it is open."""
    config = plumbing.get("line_configuration") or {}
    volume = config.get("volume")
    if not volume or line_connects(plumbing, line_mode):
        return None
    return volume


def _dead_end_valve(plumbing: dict, line_mode: str | None) -> str | None:
    """The valve this mode treats as never reaching the divided volume at all.

    Boron deposition leaves the pipe's far end a dead end on the plasma side
    (queezz, 2026-09-08: "Boron uses same pipe. But other end not connected to
    downstream."). That is not the same as a *closed* valve: a closed valve
    would still read as isolated the moment it opened, where this one never
    reaches the pipe in this mode, whatever position it is actually in. Every
    other valve on the divided volume keeps the ordinary private-side-of-the-
    barrier treatment ``predict`` already gives it.
    """
    return _mode(plumbing, line_mode).get("dead_end_valve")


def _flange_element(plumbing: dict, line_mode: str | None) -> str | None:
    """The drawn segment this mode paints in the blank-flange tone, if any.

    Only *Blank* has one. queezz, 2026-09-08 (letter
    ``20260908-520505af-9047d4``): "Sometimes we remove the probe and put the
    blank instead of the probe. So vacuum wise it's like with membrane
    installed... show the blank (not green, not gray, blank-flange color)."
    """
    return _mode(plumbing, line_mode).get("flange_element")


def linked_valve(plumbing: dict) -> tuple[str, list[str]] | None:
    """The drawn valve the Line configuration overrides, and the modes that shut it.

    ``None`` when the map declares no such link. ``closed_mode`` — one name
    rather than a list — is still read, so a map written before *Blank* existed
    still resolves.
    """
    config = plumbing.get("line_configuration") or {}
    linked = config.get("linked_valve") or {}
    valve_id = linked.get("id")
    closed = linked.get("closed_modes") or (
        [linked["closed_mode"]] if linked.get("closed_mode") else []
    )
    if not valve_id or not closed:
        return None
    return valve_id, list(closed)


def linked_valve_status(plumbing: dict, line_mode: str | None) -> dict | None:
    """The linked valve's id, its status, and whether its plug is drawn.

    Two different questions, and *Blank* is why they had to come apart. Vacuum-
    wise a blank flange is a membrane: the valve is shut and the two vessels are
    separate spaces. On the drawing it is not: there is no probe mounted at that
    position to draw a plug for, so the plug belongs to *Membrane installed*
    alone and the blank says itself, further along the line, in the flange tone.
    """
    linked = linked_valve(plumbing)
    if not linked:
        return None
    valve_id, closed_modes = linked
    config = plumbing.get("line_configuration") or {}
    plug_mode = (config.get("linked_valve") or {}).get("plug_mode")
    mode = resolve_line_mode(plumbing, line_mode)
    shut = mode in closed_modes
    return {
        "id": valve_id,
        "status": "inactive" if shut else "active",
        "plug": shut if plug_mode is None else mode == plug_mode,
    }


def apply_line_mode_to_state(plumbing: dict, state: dict, line_mode: str | None) -> dict:
    """``state`` with the Line-configuration-linked valve overridden on read.

    queezz, 2026-09-08: "Membrane installed and the membrane 'valve' should be
    linked." The drawn ``Membrane`` element has no press of its own any more:
    whatever ``elements_state.json`` or a historical log recorded for it, the
    Line configuration always wins when the state is read back, so the
    valve's own colour and what it does to the diagram's connectivity can
    never disagree. A map that declares no ``linked_valve`` is returned
    unchanged.
    """
    status = linked_valve_status(plumbing, line_mode)
    if not status:
        return state
    overridden = dict(state)
    overridden[status["id"]] = status["status"]
    return overridden


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
    # Remove the authored narrow gas-line entries only for this route check.
    # The real connectivity and its colour remain unchanged. An alternative
    # unrestricted path means a pump is not limited to the slow route.
    slow = plumbing.get("slow_pumping") or {}
    restricted = {
        frozenset(valve.get("joins") or ())
        for valve in plumbing.get("valves") or []
        if valve["id"] in (slow.get("valves") or [])
    }
    direct = {
        name: component
        for component in _components(names, [edge for edge in plumbed if frozenset(edge) not in restricted])
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
                {
                    "id": source["id"],
                    "gas": source.get("gas", "gas"),
                    "symbol": source.get("symbol", ""),
                }
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
        pump_volumes = {pump["id"]: pump["volume"] for pump in plumbing.get("pumps") or []}
        for pump in answers[name]["pumps"]:
            if pump_volumes[pump["id"]] not in direct.get(name, {name}):
                pump["route_hint"] = slow.get("label", "slow gas-line route")
        pumps = answers[name]["pumps"]
        answers[name]["slow_route_only"] = bool(pumps) and all(pump.get("route_hint") for pump in pumps)
    return answers


def _verdict(
    plumbing: dict, state: dict, component: set[str], volumes: dict
) -> tuple[str, str | None]:
    """What one continuous space holds, and what else reaches it.

    The first answer is the **dominant** one: the best pump reaching the space,
    turbo before rough, with gas and vent air beating both because those are the
    readings an operator needs first. The second is the **contributing** one,
    and it exists because queezz asked what a two-sided pumping job should look
    like — "if I open a rotary into the TMP pumped volume, the pressure may drop
    a bit, but stay HV side" (2026-09-08). It is never painted on a pipe: a pipe
    wears one colour, the dominant one, and only the drawn shapes show the
    second ("we have shapes in all important places. plasma-vacuum, bypass
    connector, and qms-vacuum").

    High vacuum takes its colour from the side the reachable running turbo
    serves. A joined vessel does not supply a pumping colour on its own.

    **Corrected 2026-09-08** (owner, letter ``20260908-fe94c769-493d71``): the
    stub between a closed gate and its own turbo used to be a seventh state,
    ``sealed`` — pumped, sealed off — on the reasoning that it reached no vessel
    and so could not honestly wear one's colour. queezz took that apart in one
    sentence: *"between the turbo and its gate, the vacuum is High, not pumped
    sealed off. Not sealed. Pumped sealed off means I pump, close the valve.
    Vacuum holds, and degrades per the vessel's leak rate."* A volume with a
    running pump on it is that pump's state **now**, so the stub is high vacuum
    in the turbo's own side colour and a running rotary's line is rough. The
    closed gate — white, with the only black rim on the drawing — is what says
    the colour does not continue into the vessel; it never needed a colour of
    its own to say it. *Sealed off* moved to where it belongs, on a volume that
    is holding what it was last given: see :func:`sealed_readings`.

    **Corrected 2026-09-08** (owner, letter ``20260908-aed40a4e-c9a286``, on a
    frame with the plasma vessel vented while the roughing bypass still reached
    it): "Rotary from bypass is pumping, but I see no gradient." Air and gas used
    to suppress the second tone, which threw away exactly the case worth a
    glance. They no longer do: the second tone is whatever *else* reaches the
    space that is not the dominant thing, in every state, so a vented vessel with
    a rotary still pumping into it now shows red with an amber tone. One second
    tone only, and this is the order it is chosen in.
    """
    open_air = any(volumes.get(name, {}).get("always") == "air" for name in component)
    gases = [
        source
        for source in plumbing.get("gas_sources") or []
        if source["volume"] in component and _is(state, source["id"], "active")
    ]
    running = [
        pump
        for pump in plumbing.get("pumps") or []
        if pump["volume"] in component and _is(state, pump["id"], "active")
    ]
    turbos = [pump for pump in running if pump.get("kind") == "turbo"]
    roughs = [pump for pump in running if pump.get("kind") != "turbo"]
    # Both the main HV colour and its contribution come from reachable
    # running turbo sides, never from the names of the joined chambers.
    served = sorted(
        (volumes.get(pump.get("serves")) or {} for pump in turbos),
        key=lambda side: side.get("rank", 99),
    )
    turbo_sides = list(dict.fromkeys(
        side["high_vacuum"] for side in served if side.get("high_vacuum")
    ))
    turbo_state = (turbo_sides[0] if turbo_sides else ISOLATED) if turbos else None

    if open_air:
        dominant = AIR
    elif gases:
        dominant = GAS
    elif turbo_state:
        dominant = turbo_state
    elif roughs:
        dominant = ROUGH
    else:
        return ISOLATED, None

    # What else reaches this space, in the order the second tone is chosen:
    # a gas under vent air, then the best pump that is not already the
    # dominant reading. Two HV tones require both pumping sides to reach it.
    candidates: list[str | None] = []
    if dominant == AIR and gases:
        candidates.append(GAS)
    if dominant in (AIR, GAS):
        candidates.append(turbo_state or (ROUGH if roughs else None))
    else:
        if len(turbo_sides) > 1:
            candidates.append(turbo_sides[1])
        if turbo_state and roughs:
            candidates.append(ROUGH)
    mix = next((name for name in candidates if name and name != dominant), None)
    return dominant, mix


def passage_edges(plumbing: dict, state: dict) -> list[tuple[str, str]]:
    """The pumps that are, right now, a piece of pipe rather than a pump.

    queezz, 2026-09-09, watching TMPD stopped with the QMS rotary running on its
    backing line (letter ``20260908-948b8dbc-b1eb0d``): *"The rough pump pumps,
    it can really do that."* Gas goes through a stationary rotor, so a **stopped**
    turbo joins the two volumes it sits between exactly as an open valve would:
    the vessel above a stopped TMPD with its gate open is rough vacuum, pumped by
    the rotary *through* the stopped turbo, and the readout says so.

    A **running** turbo is the pump and stays a boundary; the rough pump behind
    it is its backing, which the second-tone rule already covers. Only a closed
    valve blocks. The two sides are the pump's own ``volume`` (its inlet) and its
    ``backed_by`` line, and a pump joins them only where the map itself says
    ``stopped: "passage"`` — a rough pump exhausts to the room and joins nothing.
    """
    edges = []
    for pump in plumbing.get("pumps") or []:
        backing = pump.get("backed_by")
        if pump.get("stopped") != "passage" or not backing:
            continue
        if _is(state, pump["id"], "active"):
            continue
        edges.append((pump["volume"], backing))
    return edges


def _component_gas_symbols(plumbing: dict, state: dict, component: set[str]) -> list[str]:
    """The bottle symbols open into one continuous space, in map order."""
    return [
        source["symbol"]
        for source in plumbing.get("gas_sources") or []
        if source.get("symbol")
        and source["volume"] in component
        and _is(state, source["id"], "active")
    ]


# -- the memory: what a volume was last under, and since when ---------------
#
# queezz, 2026-09-08 (letters `20260908-fe94c769-493d71` and
# `20260908-2c3d9837-37ab4a`): "Pumped sealed off means I pump, close the valve.
# Vacuum holds, and degrades per the vessel's leak rate... If we have air/N2 or
# isolation especially in the main two vessels, we need to keep a date so we can
# say: 'ah, that upstream was under N2 for two weeks!'"
#
# So the prediction needs one thing it never needed before: a memory. It is kept
# deliberately outside the predictor — passed in as an argument and handed back
# updated — so `predict` stays what it has always been, state in and prediction
# out, and the practice mode can run the same walk over its own copy of both.


def _parse_moment(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.strptime(value.strip().replace("T", " "), TIME_FORMAT)
    except ValueError:
        return None


def read_memory(state: dict) -> dict:
    """The per-volume memory carried inside a stored state, or an empty one."""
    memory = (state or {}).get(MEMORY_KEY)
    return {
        name: dict(entry)
        for name, entry in (memory or {}).items()
        if isinstance(entry, dict) and entry.get("state")
    }


def update_memory(plumbing: dict, memory: dict | None, prediction: dict, now) -> dict:
    """The memory after this reading. Pure: a new dict, the old one untouched.

    Two rules and nothing else. While something reaches a volume, the memory is
    simply *what it holds now*, with no isolation moment. The instant nothing
    reaches it any more, that moment is stamped on the memory it already had —
    and never re-stamped, because "since when" means since it was closed, not
    since the last time anybody looked.

    A volume that is open to the room (``always: "air"``) has no memory: it is
    not holding anything, it *is* the room.
    """
    volumes: dict = plumbing.get("volumes") or {}
    moment = now if isinstance(now, datetime) else _parse_moment(now)
    stamp = moment.strftime(TIME_FORMAT) if moment else None
    out = {
        name: dict(entry)
        for name, entry in (memory or {}).items()
        if name in volumes and not volumes[name].get("always")
    }
    for name, volume in volumes.items():
        if volume.get("always"):
            continue
        verdict = (prediction.get("volumes") or {}).get(name, ISOLATED)
        if verdict != ISOLATED:
            entry = {"state": verdict, "since": None}
            symbols = (prediction.get("gases") or {}).get(name) or []
            if symbols:
                entry["symbols"] = list(symbols)
            out[name] = entry
        else:
            entry = out.get(name)
            if entry and entry.get("state") and not entry.get("since") and stamp:
                entry["since"] = stamp
    return out


def duration_words(seconds: float) -> str:
    """A span in the units a person says out loud, never in decimals.

    The units are queezz's own three sentences: "that upstream was under N2 for
    two weeks", "the downstream was under air for a month", "the plasma-vacuum
    was under HV for a day". So the ladder is hours, then days, then weeks, then
    months, and it steps up to months at thirty days rather than later — a span
    he would call a month should not come back as four weeks.
    """
    if seconds < 3600:
        return "less than an hour"
    hours = seconds / 3600
    if hours < 24:
        count = int(hours)
        return f"{count} hour" if count == 1 else f"{count} hours"
    days = hours / 24
    if days < 14:
        count = int(days)
        return f"{count} day" if count == 1 else f"{count} days"
    if days < 30:
        count = int(days / 7)
        return f"{count} week" if count == 1 else f"{count} weeks"
    count = int(days / 30.44) or 1
    return f"{count} month" if count == 1 else f"{count} months"


def hint_thresholds(plumbing: dict) -> dict:
    """How long is long, in days, from the map rather than from this file."""
    written = plumbing.get("hint_thresholds") or {}
    return {
        "bake_air_days": float(written.get("bake_air_days", 2)),
        "bake_gas_days": float(written.get("bake_gas_days", 7)),
        "fresh_vacuum_days": float(written.get("fresh_vacuum_days", 3)),
    }


def _vessel_hint(plumbing: dict, name: str, was: str, days: float, duration: str) -> dict:
    """What to do about a vessel that has been shut for a while, in his words.

    Drawn from the three sentences queezz wrote (letter
    ``20260908-2c3d9837-37ab4a``): "Oh no, the downstream was under air for a
    month! Need to bake!" and "the plasma-vacuum was under HV for a day, check
    pirani and maybe we can open TMP directly into it. Or start a bypass just to
    be safe." The gauge is named from the map — the diagram predicts, the gauge
    measures — and the two ways the pump-down guides offer are answered
    separately, because the guide's question is *which way*, not *how bad*.

    It comes back in three pieces rather than one paragraph, because two vessels
    in the same state print side by side and a repeated lecture is what Fleet's
    `WEBUI.md` calls a textbook in disguise. ``advice`` is the clause after "read
    the gauge", ``gauges`` are that vessel's own, and the page joins them into
    **one** sentence naming the gauges it actually has, so the two lines differ
    by their own equipment rather than repeating the same three sentences.
    ``text`` is the same sentence with no gauge named, for any reader that has
    no names to put in.
    """
    limits = hint_thresholds(plumbing)
    gauges = [
        gauge["id"] for gauge in plumbing.get("gauges") or [] if gauge.get("volume") == name
    ]
    turbo = next(
        (pump for pump in plumbing.get("pumps") or [] if pump.get("serves") == name), None
    )
    if was == AIR:
        stale = days >= limits["bake_air_days"]
    elif was == GAS:
        stale = days >= limits["bake_gas_days"]
    else:
        stale = days > limits["fresh_vacuum_days"]
    if was in (AIR, GAS):
        advice = "rough through the bypass rather than opening a turbo straight onto it"
    elif stale:
        advice = "then rough through the bypass rather than opening the turbo straight in"
    else:
        advice = "opening the turbo directly may be fine, or rough through the bypass to be safe"
    bake = bool(stale and was in (AIR, GAS))
    text = f"{'Consider baking. ' if bake else ''}Read the gauge; {advice}."
    return {
        "text": text,
        "advice": advice,
        "bake": bake,
        "gauges": gauges,
        "turbo": turbo["id"] if turbo else None,
        "duration": duration,
    }


def sealed_readings(
    plumbing: dict, memory: dict | None, by_volume: dict, state: dict, now=None
) -> dict:
    """What each isolated volume is holding, and for how long.

    Only a volume that is isolated *and* remembers something gets a reading;
    everything else keeps the grey of ``isolated``, which is the absence of a
    claim and stays that way (queezz: "isolated unknown remains only for a
    volume with no memory"). ``way`` is the pump-down guides' own question —
    a vessel whose turbo is still spinning behind its shut gate has to be
    roughed through the bypass, and one whose turbo is stopped can be opened
    to the gate and pumped through it.
    """
    volumes: dict = plumbing.get("volumes") or {}
    moment = now if isinstance(now, datetime) else (_parse_moment(now) or datetime.now())
    readings: dict[str, dict] = {}
    for name, verdict in by_volume.items():
        if verdict != ISOLATED or name not in volumes:
            continue
        entry = (memory or {}).get(name) or {}
        was, since = entry.get("state"), _parse_moment(entry.get("since"))
        if not was or since is None:
            continue
        seconds = max(0.0, (moment - since).total_seconds())
        days = seconds / 86400
        reading = {
            "was": was,
            "since": since.strftime(TIME_FORMAT),
            "seconds": int(seconds),
            "duration": duration_words(seconds),
            "symbols": list(entry.get("symbols") or []),
        }
        if volumes[name].get("vessel"):
            hint = _vessel_hint(plumbing, name, was, days, reading["duration"])
            turbo_running = bool(hint["turbo"]) and _is(state, hint["turbo"], "active")
            hint["way"] = "bypass" if turbo_running else "gate"
            reading["hint"] = hint
        readings[name] = reading
    return readings


_FAMILY = {"upstream-high-vacuum": "high-vacuum", "downstream-high-vacuum": "high-vacuum"}


def _agreed_side(plumbing: dict, sides: list[str]) -> str:
    """The one state a divided pipe may claim, from what each of its sides holds.

    A single drawn line with a barrier partway along it cannot honestly carry
    two answers, so when its two sides hold different *kinds* of thing it stays
    ``isolated`` — the rule since 0.12.1. Splitting high vacuum in two (0.15.0)
    would otherwise turn every membrane-installed pipe grey the moment both
    vessels were pumped, which claims *less* than the truth rather than more:
    the two sides agree that this is high vacuum and disagree only about which
    chamber it belongs to. So sides of the same kind are allowed, and the line
    takes whichever of them the map lists first — the plasma side, by the order
    of ``states``.
    """
    if not sides:
        return ISOLATED
    if len({_FAMILY.get(side, side) for side in sides}) != 1:
        return ISOLATED
    order = [item["id"] for item in plumbing.get("states") or []]
    return sorted(sides, key=lambda side: order.index(side) if side in order else 99)[0]


def predict(
    plumbing: dict,
    state: dict,
    line_mode: str | None = None,
    memory: dict | None = None,
    now=None,
) -> dict:
    """Name the predicted content of every volume, and of every drawn element.

    Air beats gas beats high vacuum beats rough vacuum: a volume open to
    atmosphere is reported as air even while a turbo is marked running on it,
    because that is the reading an operator needs first.

    ``line_mode`` is the Line configuration annotation. When it says something
    is mounted in the pipe between the two vessels, that volume is divided:
    each valve on it opens onto its own side of the barrier, so the two vessels
    never join through it. The one drawn pipe then takes the state both sides
    agree on, or ``isolated`` when they differ — a single line cannot honestly
    carry two answers. Boron deposition divides it the same way, except the
    downstream valve named by that mode's ``dead_end_valve`` never reaches the
    pipe at all, in any position: the pipe can then only ever take what the
    plasma side gives it (queezz, 2026-09-08, "other end not connected to
    downstream").

    The state is read through :func:`apply_line_mode_to_state` first, so a
    drawn valve the Line configuration links to itself (the ``Membrane``
    element) cannot disagree with the configuration that governs it, whatever
    ``elements_state.json`` or a historical log says.

    ``memory`` is what each volume was last under and since when, and it is an
    argument rather than something read from a file here on purpose: this
    function is still state in, prediction out, so the practice mode can run it
    over a local copy of both. ``now`` is the clock, for the same reason — a
    test advances it rather than waiting a fortnight.
    """
    state = apply_line_mode_to_state(plumbing, state, line_mode)
    if memory is None:
        memory = read_memory(state)
    volumes: dict = plumbing.get("volumes") or {}
    names = list(volumes)
    divided = _divided_volume(plumbing, line_mode)
    if divided in volumes:
        names = [name for name in names if name != divided]
    else:
        divided = None
    dead_end = _dead_end_valve(plumbing, line_mode) if divided else None
    edges = []
    stubs: list[str] = []
    for valve in plumbing.get("valves") or []:
        joins = list(valve.get("joins") or ())
        if len(joins) != 2 or not _is(state, valve["id"], valve.get("open_when", "active")):
            continue
        if divided and divided in joins:
            if valve["id"] == dead_end:
                # Boron deposition: this end is a dead end on purpose, so the
                # valve reaches nothing through it, whatever position it is in.
                continue
            # One side of the barrier, private to this valve: an open valve
            # reaches the pipe, and the pipe reaches nothing through it.
            stub = f"{divided}@{valve['id']}"
            stubs.append(stub)
            names.append(stub)
            joins = [stub if name == divided else name for name in joins]
        edges.append(tuple(joins))
    # A stopped turbo is a passage, not a wall (owner ruling 2026-09-09). It
    # joins its inlet line to its backing line exactly as an open valve would,
    # so a rough pump behind it reaches whatever the gate above it is open to.
    edges.extend(passage_edges(plumbing, state))
    by_volume: dict[str, str] = {}
    mix_of: dict[str, str] = {}
    gases_of: dict[str, list[str]] = {}
    for component in _components(list(dict.fromkeys(names)), edges):
        verdict, mix = _verdict(plumbing, state, component, volumes)
        symbols = _component_gas_symbols(plumbing, state, component)
        for name in component:
            by_volume[name] = verdict
            if mix:
                mix_of[name] = mix
            if symbols:
                gases_of[name] = symbols

    if divided:
        # The drawn pipe is one line with a barrier partway along it. It may
        # only claim a state both sides agree on.
        sides = [by_volume.pop(stub) for stub in stubs]
        for stub in stubs:
            mix_of.pop(stub, None)
            gases_of.pop(stub, None)
        by_volume[divided] = _agreed_side(plumbing, sides)

    colors = {item["id"]: item["color"] for item in plumbing.get("states") or []}
    sealed = sealed_readings(plumbing, memory, by_volume, state, now)
    band = float((plumbing.get("drawing") or {}).get("band") or 1)
    elements: dict[str, dict] = {}
    for name, volume in volumes.items():
        verdict = by_volume.get(name, ISOLATED)
        held = sealed.get(name)
        # A sealed volume wears the colour of what it is still holding. The
        # vessel body says *sealed* with a hatch; everything else in that volume
        # says it by being paler, and stays solid — a hatch on a stroke is a
        # dashed line, and queezz read dashed pipes as broken ones three letters
        # running on 2026-09-09.
        colour = colors.get(held["was"], "#000000") if held else colors.get(verdict, "#000000")
        pale = sealed_pale(plumbing, colour) if held else colour
        # A vessel is a volume you can see into, and a T or a cross is a small
        # one, so they say their state by their body rather than by an outline.
        # queezz, 2026-09-08: "We can go very loud, why not? Color it the color
        # of the vacuum I say. Or gas. Or air." So the fill is the full state
        # colour, not a tint of it — and the outline takes that same colour,
        # which is to say it stops being an outline at all. His words on the
        # drawn result, later the same day: "I think I'd like it without black
        # shape borders. All one color. Why not? Color speaks vacuum. Black
        # border speaks... shapes?" Valves, pumps and gauges keep the black he
        # drew: they are equipment, not volumes. Every other element the map
        # names is a line, and a line was already in its volume's colour.
        bodies = set(volume.get("junctions") or ())
        # Only the drawn body of a *chamber* may carry the hatch. A tee or a
        # cross is a small volume and takes the paler tone like its pipes: in
        # his frame the cross, the tee above it and the gate valve between them
        # were all under one hatch and the valve's shape was lost in the blob
        # ("guess what shape this is and what this blob does", letter
        # 20260908-db3ff048-8394c2). His own letter offers the escape —
        # "drop it from tees too and hatch the two vessels alone" — and this is
        # it.
        chamber = volume.get("vessel")
        if chamber:
            bodies.add(chamber)
        mix = mix_of.get(name)
        for element_id in volume.get("elements") or []:
            if element_id in bodies:
                hatched = bool(held) and element_id == chamber
                body = {
                    "volume": name,
                    "state": verdict,
                    "fill": colour if hatched else pale,
                    "stroke": colour if hatched else pale,
                }
                # The two-tone body, and only the body. queezz on the signal:
                # "I think the shape gradient is a good signal. 'You are pumping
                # from two sides, take note'." A sealed volume never has one:
                # nothing is reaching it, which is the whole point of it.
                if held:
                    body["sealed"] = True
                    body["state"] = held["was"]
                    if hatched:
                        body["sealed_paint"] = _sealed_paint_id(colour)
                elif mix and mix in colors:
                    body["mix"] = colors[mix]
                    body["mix_state"] = mix
                elements[element_id] = body
            else:
                elements[element_id] = _line(
                    name, held["was"] if held else verdict, pale, band, sealed=bool(held)
                )
    # A gauge's stem is the short line from its symbol to what it reads, and it
    # belongs to that volume as much as any pipe does (queezz, 2026-09-08:
    # "all gauges stems don't have colors... If we can work with that, fine").
    # Bottle stems follow their connected line too (owner, 2026-09-10).
    # The explicit stem IDs preserve symbol colours and drawing groups.
    stemmed = list(plumbing.get("gauges") or []) + list(plumbing.get("gas_sources") or [])
    for component in stemmed:
        stem = component.get("stem")
        volume_name = component.get("volume")
        if not stem or volume_name not in volumes:
            continue
        verdict = by_volume.get(volume_name, ISOLATED)
        held = sealed.get(volume_name)
        shown = held["was"] if held else verdict
        stem_colour = colors.get(shown, "#000000")
        elements[stem] = _line(
            volume_name,
            shown,
            sealed_pale(plumbing, stem_colour) if held else stem_colour,
            band,
            sealed=bool(held),
        )
    # A valve says its position with its body, at every size. An open one wears
    # the colour flowing through it; a shut one wears the closed ink, so the
    # colour visibly stops short on both sides and a closed gate can never read
    # as an open one (queezz, 2026-09-08: "GVU is closed, so TMP is not pumping
    # plasma-vacuum. Yet at a glance it seems that it does", and, on the small
    # ones, "a green wedge against a grey wedge at that size").
    #
    # Its **outline** goes with its fill, settled the same evening (letter
    # 20260908-3308e02d-3021dd): "I think I like the valves edge to be same
    # color as the fill. When closed, black border white fill is good. Stands
    # out." So an open valve has no black edge at all and reads as part of the
    # pipe, while a closed one is the single dark-rimmed shape on the drawing.
    # This retires the older rule that a valve always keeps the black queezz
    # drew — for open valves only; a pump and a gauge still keep theirs.
    drawing = plumbing.get("drawing") or {}
    closed_ink = drawing.get("valve_closed") or "#ffffff"
    closed_edge = drawing.get("valve_closed_edge") or "#000000"
    # A source drawn as a valve uses the same painter, without adding a
    # connection to another volume. Bottle symbols keep their own palette.
    drawn_valves = list(plumbing.get("valves") or [])
    drawn_valves.extend(
        dict(source, joins=[source["volume"]])
        for source in plumbing.get("gas_sources") or []
        if source.get("valve")
    )
    for valve in drawn_valves:
        joins = list(valve.get("joins") or ())
        if _is(state, valve["id"], valve.get("open_when", "active")):
            # Both sides of an open valve are one space by construction, so
            # either side names the same colour; the barrier cases keep the
            # side the map lists first.
            through = next((name for name in joins if name in by_volume), None)
            held = sealed.get(through)
            verdict = held["was"] if held else by_volume.get(through, ISOLATED)
            colour = colors.get(verdict, "#000000")
            # **A valve is never hatched, in any state** (owner, 2026-09-09,
            # letter 20260908-db3ff048-8394c2, on a frame where the cross, the
            # tee and the gate valve between them were all one hatched blob:
            # "the dashed valve, it's like 'guess what shape this is and what
            # this blob does'"). A valve keeps its own two looks and nothing
            # else: open, filled and rimmed in the colour flowing through it;
            # closed, white with a black rim. Inside a sealed space that colour
            # is the paler sealed tone, so the valve still belongs to its pipes
            # and is still unmistakably a valve at arm's length.
            item = {
                "valve": True,
                "open": True,
                "volume": through,
                "state": verdict,
                "fill": sealed_pale(plumbing, colour) if held else colour,
                "stroke": sealed_pale(plumbing, colour) if held else colour,
            }
            if held:
                item["sealed"] = True
            elements[valve["id"]] = item
        else:
            elements[valve["id"]] = {
                "valve": True,
                "open": False,
                "state": "closed",
                "fill": closed_ink,
                "stroke": closed_edge,
            }
    # A pump wears what it is doing (queezz, 2026-09-08, letter
    # 20260908-3688eabd-587dfe: "why don't we change the TMP on color to its HV
    # color? Same for rough pumps. Rotaries and Scroll?"). A running turbo takes
    # the high-vacuum colour of the side it serves — a fact about the rig, not
    # about today's valves, so a turbo behind a closed gate still says which
    # chamber it belongs to — and a running rotary or scroll takes rough vacuum.
    #
    # **A stopped pump is left exactly as queezz drew it, in his own grey**, and
    # this entry carries no ink at all so that nothing paints over it. 0.16.0
    # made it yellow on a relayed line reading "stays as drawn (yellow)"; the
    # drawing's own fill is grey, and yellow was the app's *on* colour, so the
    # release turned the off signal into the on one. His answer, at once (letter
    # 20260908-93fb84a6-5a69cf): "No, no! Blue and yellow, yellow reads like on.
    # Gray for off was lost. Why? WHY???" Yellow is gone from every pump, here
    # and in `elementsConfig.json`.
    #
    # Every one of these already had a confirmed on/off an operator presses and
    # history records, and the prediction has always read it: a stopped turbo
    # has never made high vacuum here.
    #
    # **And a stopped pump's edges recede with it (2026-09-08, letter
    # 20260908-e2498698-5c9c50).** queezz, on a running rotary beside a stopped
    # turbo: "In diagram, we can also gray out pump edges and lines. Dark gray.
    # So it speaks more loudly that that is closed." So a stopped pump keeps his
    # grey body and its rim and inner symbol lines go dark grey; a running one
    # keeps the black rim and lines he drew, over its state colour. The inner
    # lines are drawn elements of their own with their own ids — `parts` in the
    # map, checked against the drawing by a test — because a group's stroke
    # cannot reach a child that carries its own inline one.
    stopped_edge = drawing.get("pump_stopped_edge") or "#5f5f5f"
    for pump in plumbing.get("pumps") or []:
        running = _is(state, pump["id"], "active")
        if running:
            if pump.get("kind") == "turbo":
                side = volumes.get(pump.get("serves")) or {}
                role = side.get("high_vacuum") or ISOLATED
            else:
                role = ROUGH
            elements[pump["id"]] = {
                "pump": True,
                "running": True,
                "state": role,
                "fill": colors.get(role, "#000000"),
                "stroke": "#000000",
            }
        else:
            elements[pump["id"]] = {
                "pump": True,
                "running": False,
                "state": "stopped",
                "stroke": stopped_edge,
            }
        edge = "#000000" if running else stopped_edge
        for part in pump.get("parts") or []:
            elements[part] = {"pump": True, "part": pump["id"], "stroke": edge}
    # The drawn valve the Line configuration governs, painted here rather than
    # in the page's JavaScript so `/state.svg` and the screen cannot disagree.
    # Under *Membrane installed* it is a solid plug across the line; under every
    # other configuration nothing of the app's is mounted there, so it is an
    # empty dashed outline and the line reads straight through it.
    linked = linked_valve_status(plumbing, line_mode)
    if linked and linked["id"] in elements:
        plug = bool(linked["plug"])
        elements[linked["id"]] = {
            "valve": True,
            "linked": True,
            "open": linked["status"] == "active",
            "plug": plug,
            "state": "closed" if linked["status"] == "inactive" else "open",
            "fill": closed_ink if plug else "none",
            "stroke": closed_edge,
            "dash": "none" if plug else "5 4",
            "opacity": 1.0 if plug else (plumbing.get("drawing") or {}).get("empty_marker_opacity", 0.45),
        }
    # A blank flange in place of the probe: the one drawn segment that is not a
    # vacuum claim at all. It wears the flange tone — neither a state colour nor
    # the closed grey — because with the bellows disconnected there is no volume
    # in it to predict (queezz, 2026-09-08, letter 20260908-520505af-9047d4).
    flange_element = _flange_element(plumbing, line_mode)
    if flange_element and flange_element in elements:
        elements[flange_element] = {
            "flange": True,
            "state": "blank-flange",
            "stroke": drawing.get("flange") or "#9aa7b5",
        }
    air = sorted(
        volumes[name].get("label", name)
        for name, verdict in by_volume.items()
        if verdict == "air" and volumes.get(name, {}).get("always") != "air"
    )
    connections = _connections(
        plumbing, state, list(dict.fromkeys(names)), edges, by_volume
    )
    for name, item in connections.items():
        if name in sealed:
            item["sealed"] = sealed[name]
    return {
        "volumes": by_volume,
        "mixes": mix_of,
        "gases": gases_of,
        "sealed": sealed,
        "elements": elements,
        "air": air,
        "connections": connections,
        "warnings": equipment_warnings(plumbing, state, by_volume, sealed, memory),
        "gas_symbols": _gas_symbols(volumes, connections, sealed),
        "line_mode": line_mode or "unknown",
        "linked_valve": linked_valve_status(plumbing, line_mode),
    }


def _sealed_paint_id(colour: str) -> str:
    """The name of the hatch pattern for one remembered colour."""
    return "pihti-sealed-" + colour.replace("#", "")


def _mix_hex(colour: str, toward: str, fraction: float) -> str:
    """One colour moved a fraction of the way toward another."""
    if not _safe_color(colour) or not _safe_color(toward):
        return colour
    a = [int(colour[index : index + 2], 16) for index in (1, 3, 5)]
    b = [int(toward[index : index + 2], 16) for index in (1, 3, 5)]
    fraction = min(1.0, max(0.0, fraction))
    return "#" + "".join(
        f"{round(left + (right - left) * fraction):02x}" for left, right in zip(a, b)
    )


def sealed_pale(plumbing: dict, colour: str) -> str:
    """A sealed volume's pipe tone: the remembered colour, but quieter.

    queezz, 2026-09-09, three letters in five minutes on the first build of the
    hatch (``20260908-b1c0ba9c-342679``, ``20260908-a8f73fdc-616055``,
    ``20260908-db3ff048-8394c2``): *"I don't like the broken lines. They are
    pipes. That reads like a breakage."* A hatch painted onto a 4 px stroke is a
    dashed line, whatever it was meant to be, and *"the dashed valve, it's like
    'guess what shape this is and what this blob does'."* So the hatch is on the
    two vessel bodies and nowhere else, and a sealed volume's pipes, tees,
    crosses, gauge stems and open valves are **solid** in this paler tone of what
    the volume is holding.

    It is honestly quieter than the palette's own 3:1 floor against the stone
    field, and that is the point: a sealed pipe is not a live claim. The floor
    still governs every live colour; the amount lives in the map as
    ``sealed_pale`` so it can be dialled without touching code.
    """
    drawing = plumbing.get("drawing") or {}
    ground = drawing.get("ground") or "#e3dfd6"
    return _mix_hex(colour, ground, float(drawing.get("sealed_pale") or 0.35))


MARK_FRACTION = 0.45
MARK_FLOOR = 6.0


def _mark_cap(volumes: dict) -> float:
    """The largest a gas mark may ever be: the plasma vessel's own.

    queezz, 2026-09-08 (letter ``20260908-8eaaa7a9-334955``): "The qms-vacuum
    gas circle is bigger for some reason... the mark's diameter is a fraction of
    the SMALLER dimension of the vessel body it sits in (about 0.45 of the
    smaller side, capped at the plasma mark's size)." It used to be one absolute
    size for both, which is nearly the whole width of the narrower QMS box. The
    cap is derived rather than typed: it is the smallest of the vessels' own
    marks, which on this rig is the plasma vessel's, so a vessel can never wear
    a bigger mark than the widest chamber does.
    """
    sizes = [
        MARK_FRACTION * min(box[2] - box[0], box[3] - box[1]) / 2
        for volume in volumes.values()
        for box in [volume.get("symbol_box")]
        if volume.get("vessel") and box and len(box) == 4
    ]
    return min(sizes) if sizes else MARK_FLOOR


def mark_radius(box: list, count: int, cap: float) -> float:
    """How big one gas mark is inside one vessel body, with several in a row."""
    left, top, right, bottom = (float(value) for value in box)
    width, height = right - left, bottom - top
    radius = min(MARK_FRACTION * min(width, height) / 2, cap)
    if count > 1:
        radius = min(radius, width / (2.2 * count))
    return max(MARK_FLOOR, radius)


def _gas_symbols(
    volumes: dict, connections: dict, sealed: dict | None = None
) -> list[dict]:
    """Which bottle symbol to draw inside which vessel, how many, and how big.

    queezz, 2026-09-08: "for the gas fill, we can put a gas in a circle (same as
    the bottle sign) inside the plasma vessel. Ar, O2, H2. So it's visible big
    at a glance." A vessel whose predicted state is *gas* carries one circle per
    gas open into it, and the symbol is the one written beside that bottle in
    the map rather than derived from its name.

    **A vessel that is sealed under a gas keeps its marks** (2026-09-08): the
    bottle is shut, but the vessel is still full of nitrogen, and that is
    exactly the thing his sentence wanted to see at a glance — "ah, that
    upstream was under N2 for two weeks!"

    The radius travels with the mark so the page and ``/state.svg`` cannot size
    them differently.
    """
    cap = _mark_cap(volumes)
    drawn = []
    for name, item in connections.items():
        volume = volumes.get(name) or {}
        element = volume.get("vessel")
        box = volume.get("symbol_box")
        held = (sealed or {}).get(name) or {}
        if item.get("state") == "gas":
            symbols = [
                source["symbol"] for source in item.get("gas") or [] if source.get("symbol")
            ]
        elif held.get("was") == GAS:
            symbols = [symbol for symbol in held.get("symbols") or [] if symbol]
        else:
            continue
        if element and box and symbols:
            drawn.append(
                {
                    "volume": name,
                    "element": element,
                    "box": box,
                    "symbols": symbols,
                    "radius": round(mark_radius(box, len(symbols), cap), 2),
                    "sealed": bool(held),
                }
            )
    return drawn


IONIZATION = "ionization"
TURBO = "turbo"


def _exposure(verdict: str) -> int:
    """How bad the predicted content of a volume is for something delicate in it.

    Nothing worth saying is ``0``, gas is ``1``, vent air is ``2``. Ranking
    them rather than merely listing them is what lets a press be judged against
    the state *before* it: a warning is owed when a press makes a volume worse
    for what is standing in it, never merely because it was already bad. It is
    also what keeps closing a vent quiet — air falling back to gas is an
    improvement, and an improvement is not a warning.
    """
    return {GAS: 1, AIR: 2}.get(verdict, 0)


def oil_warnings(plumbing: dict, state: dict, verdicts: dict, sealed: dict, memory: dict) -> list[dict]:
    """Owner advisory: stopped oil rotary with vacuum at its inlet, live or held."""
    vacuum = {ROUGH, "upstream-high-vacuum", "downstream-high-vacuum"}
    found = []
    for pump in plumbing.get("pumps") or []:
        if not pump.get("oil_sealed") or _is(state, pump["id"], "active"):
            continue
        volume = pump["volume"]
        verdict = verdicts.get(volume, ISOLATED)
        held = (sealed.get(volume) or {"was": (memory.get(volume) or {}).get("state")}) if verdict == ISOLATED else None
        shown = held.get("was") if held else verdict
        if shown in vacuum:
            found.append({"kind": "oil", "id": pump["id"], "volume": volume,
                          "state": shown, "sealed": bool(held), "level": 1})
    return found


def equipment_warnings(plumbing: dict, state: dict, verdicts: dict, sealed: dict, memory: dict) -> list[dict]:
    """Standing advisories, shared by the drawing and press comparisons."""
    found = oil_warnings(plumbing, state, verdicts, sealed, memory)
    for kind, items, wanted in [("gauge", plumbing.get("gauges", []), IONIZATION),
                                ("turbo", plumbing.get("pumps", []), TURBO)]:
        for item in items:
            if item.get("kind") != wanted or not _is(state, item["id"], "active"):
                continue
            volume = item.get("volume")
            verdict = verdicts.get(volume, ISOLATED)
            if verdict == ISOLATED:
                verdict = (sealed.get(volume) or {}).get("was", (memory.get(volume) or {}).get("state", ISOLATED))
            level = _exposure(verdict) if kind == "gauge" else (2 if verdict == AIR else 0)
            if level:
                found.append({"kind": kind, "id": item["id"], "volume": volume,
                              "state": verdict, "level": level})
    return found


def exposures(plumbing: dict, state: dict, line_mode: str | None = None) -> dict:
    """What each switched-on ion gauge and running turbo is predicted to stand in.

    Two things on this rig mind gas and air: an ionization gauge that is
    switched on, which minds both, and a turbo pump that is spinning, which
    minds vent air. Everything else on the drawing is happy at one atmosphere
    (queezz, 2026-09-04: the Baratrons, the Pirani, the Pfeiffer single gauge
    and the Ulvac membrane gauge all work there), so only the gauges the map
    marks ``kind: "ionization"`` are counted.

    A running turbo is a *boundary* in the prediction, so the volume that
    matters for it is its own — the one the vent would actually join — never
    everything behind it.

    Keyed by kind and id, so two readings of the same rig can be compared.
    """
    prediction = predict(plumbing, state, line_mode)
    return {(item["kind"], item["id"]): item for item in prediction["warnings"]}


def press_warnings(
    plumbing: dict,
    state: dict,
    element_id: str,
    status: str,
    line_mode: str | None = None,
) -> list[dict]:
    """What one press would newly expose, judged against the state without it.

    queezz asked for two warnings on 2026-09-08 (letter
    ``20260907-d5386824-f57dfd``): "create warning when putting gas/air on to
    IG", "and when vent goes on to TMP". Both are answered here the same way —
    by predicting from a *copy* of the entered state with the press applied and
    comparing it against the prediction for the state as it stands. Only what
    the press makes worse is returned, so a valve that changes nothing
    dangerous is quiet and one that changes something already bad does not cry
    twice.

    **This is a prediction from the valve positions an operator entered, and
    never an interlock.** Nothing here reads a pressure, refuses a press, or
    protects any hardware; it only says, in words, what the same walk that
    colours the pipes thinks the press would join.
    """
    before = exposures(plumbing, state, line_mode)
    after_state = dict(state)
    after_state[element_id] = status
    # Simulate the normal memory transition without writing: stopping the only
    # pump leaves vacuum held at its inlet, even when no prior memory exists.
    now = datetime.now()
    memory = update_memory(plumbing, read_memory(state), predict(plumbing, state, line_mode), now)
    after_prediction = predict(plumbing, after_state, line_mode, memory=memory, now=now)
    after_state[MEMORY_KEY] = update_memory(plumbing, memory, after_prediction, now)
    return [
        item
        for key, item in exposures(plumbing, after_state, line_mode).items()
        if item["level"] > before.get(key, {}).get("level", 0)
    ]


def _line(
    volume: str, verdict: str, colour: str, band: float, sealed: bool = False
) -> dict:
    """A drawn line in its volume's colour, and how much wider to draw it.

    The band is a solid widening of the pipe's own stroke, never a translucent
    glow: queezz saw the 0.11.2 halo and said "that's more readable, yes. Also
    way more ugly". An isolated line is never widened — the absence of a claim
    should not be the loudest thing on the drawing.

    **A pipe is always a solid stroke** (owner standing rule, 2026-09-09, letter
    ``20260908-a8f73fdc-616055``): *"I don't like the broken lines. They are
    pipes. That reads like a breakage."* So ``sealed`` here says only that the
    colour handed in is already the paler sealed tone; it never adds a pattern,
    a dash or a gap, in any state.
    """
    item = {"volume": volume, "state": verdict, "stroke": colour}
    if verdict != ISOLATED and band > 1:
        item["band"] = band
    if sealed:
        item["sealed"] = True
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


def _mix_gradient_id(dominant: str, contributing: str) -> str:
    return "pihti-mix-" + (dominant + "-" + contributing).replace("#", "")


def _bbox(svg_text: str, element_id: str) -> tuple[float, float, float, float] | None:
    """The drawn box of one authored shape, or ``None`` when it cannot be read.

    Only the five bodies need this, and queezz drew every one of them as a
    rectangle or as a closed run of horizontal and vertical moves, so the
    subset understood here is exactly ``M m H h V v Z z`` plus ``<rect>``.
    Anything else — a curve, an arc, a transform on the shape or its parent —
    returns ``None`` and the saved render simply carries no symbol rather than
    a symbol in the wrong place. Nothing is guessed.
    """
    tag = _element_tag(svg_text, element_id)
    if tag is None or "transform=" in tag:
        return None
    if tag.lstrip("<").startswith("rect"):
        try:
            x = float(re.search(r'\bx="([-0-9.]+)"', tag).group(1))
            y = float(re.search(r'\by="([-0-9.]+)"', tag).group(1))
            w = float(re.search(r'\bwidth="([-0-9.]+)"', tag).group(1))
            h = float(re.search(r'\bheight="([-0-9.]+)"', tag).group(1))
        except (AttributeError, ValueError):
            return None
        return x, y, x + w, y + h
    found = re.search(r'\bd="([^"]+)"', tag)
    if not found:
        return None
    tokens = re.findall(r"[A-Za-z]|-?[0-9.]+", found.group(1))
    x = y = 0.0
    xs: list[float] = []
    ys: list[float] = []
    index = 0
    command = ""
    while index < len(tokens):
        token = tokens[index]
        if token.isalpha():
            command = token
            index += 1
            if command in "Zz":
                continue
        if command in "Mm":
            try:
                dx, dy = float(tokens[index]), float(tokens[index + 1])
            except (IndexError, ValueError):
                return None
            x, y = (x + dx, y + dy) if command == "m" else (dx, dy)
            index += 2
            command = "l" if command == "m" else "L"
        elif command in "Hh":
            try:
                value = float(tokens[index])
            except (IndexError, ValueError):
                return None
            x = x + value if command == "h" else value
            index += 1
        elif command in "Vv":
            try:
                value = float(tokens[index])
            except (IndexError, ValueError):
                return None
            y = y + value if command == "v" else value
            index += 1
        elif command in "Ll":
            try:
                dx, dy = float(tokens[index]), float(tokens[index + 1])
            except (IndexError, ValueError):
                return None
            x, y = (x + dx, y + dy) if command == "l" else (dx, dy)
            index += 2
        else:
            return None
        xs.append(x)
        ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def box_inside(svg_text: str, element_id: str, box: list) -> bool:
    """Does an authored symbol box really sit inside the shape it names?

    The box is written in the map because the plasma vessel is a cross and the
    middle of its bounding box is not the middle of anything a circle fits in.
    Writing it down is only safe if a wandering box is caught, so this is the
    guard: a box that has left its shape draws nothing rather than a symbol
    floating in the wrong place. An unreadable shape is treated the same way.
    """
    drawn = _bbox(svg_text, element_id)
    if not drawn or len(box) != 4:
        return False
    left, top, right, bottom = (float(value) for value in box)
    return (
        drawn[0] - 0.5 <= left < right <= drawn[2] + 0.5
        and drawn[1] - 0.5 <= top < bottom <= drawn[3] + 0.5
    )


def _element_tag(svg_text: str, element_id: str) -> str | None:
    for tag in _TAG.findall(svg_text):
        found = _ID.search(tag)
        if found and found.group(1) == element_id:
            return tag
    return None


def overlay_markup(
    plumbing: dict, state: dict, line_mode: str | None, svg_text: str, now=None
) -> str:
    """The gradients and gas symbols a saved render needs, as SVG markup.

    ``style_rules`` can only write CSS, and two of this release's answers are
    not CSS: a two-colour body needs a gradient to point at, and a vessel
    holding gas needs the bottle symbol drawn inside it. Both are written here
    from the same prediction the page paints from, so ``/state.svg`` and the
    screen it was saved from still cannot disagree.
    """
    prediction = predict(plumbing, state, line_mode, now=now)
    parts = []
    definitions = []
    gradients = {
        _mix_gradient_id(item["fill"], item["mix"]): (item["fill"], item["mix"])
        for item in prediction["elements"].values()
        if item.get("mix") and _safe_color(item.get("fill")) and _safe_color(item["mix"])
    }
    definitions.extend(
        f'<linearGradient id="{name}" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{dominant}"/>'
        f'<stop offset="1" stop-color="{contributing}"/></linearGradient>'
        for name, (dominant, contributing) in sorted(gradients.items())
    )
    definitions.extend(sealed_pattern_markup(plumbing, prediction))
    if definitions:
        parts.append("<defs>" + "".join(definitions) + "</defs>")
    symbols = []
    for item in prediction.get("gas_symbols") or []:
        if not box_inside(svg_text, item["element"], item["box"]):
            continue
        symbols.append(
            _gas_symbol_markup(item["box"], item["symbols"], float(item["radius"]))
        )
    if symbols:
        parts.append(
            '<g id="pihti-gas-symbols" aria-hidden="true">' + "".join(symbols) + "</g>"
        )
    return "".join(parts)


def split_formula(symbol: str) -> tuple[str, str]:
    """A bottle symbol as its letters and its trailing count: ``H2`` -> H, 2.

    queezz, 2026-09-08 (letter ``20260908-e6ada507-7aa064``): "Can we do H2, O2
    with a subscript?" — drawn "the way the bottle symbols on his SVG draw them
    (an SVG tspan with baseline-shift sub or a dy offset and a smaller
    font-size, not a Unicode subscript glyph that a font may lack)". ``Ar`` and
    ``He`` have no digit and come back unchanged.
    """
    match = re.fullmatch(r"([A-Za-z]+)([0-9]*)", symbol or "")
    if not match:
        return symbol or "", ""
    return match.group(1), match.group(2)


def sealed_pattern_markup(plumbing: dict, prediction: dict) -> list[str]:
    """One hatch pattern per remembered colour a sealed volume is wearing.

    The hatch is the sealed marking, chosen over the lighter treatment the
    owner's letter also offered because lightening cannot hold the palette's own
    3:1 floor against the stone field. Stripes of the field's own colour are cut
    through the state colour at 45 degrees, so every coloured pixel stays at
    full strength and the texture, not the tint, is what says *sealed*. One
    pattern serves a filled body and a drawn line alike.
    """
    drawing = plumbing.get("drawing") or {}
    ground = drawing.get("ground") or "#e3dfd6"
    period = float(drawing.get("sealed_period") or 12)
    stripe = float(drawing.get("sealed_stripe") or 5)
    if not _safe_color(ground):
        return []
    colours = sorted(
        {
            item.get("fill") or item.get("stroke")
            for item in (prediction.get("elements") or {}).values()
            if item.get("sealed_paint")
            and _safe_color(item.get("fill") or item.get("stroke"))
        }
    )
    return [
        f'<pattern id="{_sealed_paint_id(colour)}" width="{period:g}" height="{period:g}" '
        f'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        f'<rect width="{period:g}" height="{period:g}" fill="{colour}"/>'
        f'<rect width="{stripe:g}" height="{period:g}" fill="{ground}"/></pattern>'
        for colour in colours
    ]


def _gas_symbol_markup(box: list, symbols: list[str], radius: float) -> str:
    """One white circle per gas, drawn across the middle of the vessel."""
    left, top, right, bottom = (float(value) for value in box)
    width, height = right - left, bottom - top
    middle_y = top + height / 2
    step = radius * 2.2
    start = left + width / 2 - step * (len(symbols) - 1) / 2
    out = []
    for index, symbol in enumerate(symbols):
        if not symbol.isalnum():
            continue
        centre = start + step * index
        letters, digits = split_formula(symbol)
        body = letters
        if digits:
            body += (
                f'<tspan dy="{radius * 0.22:.2f}" font-size="{radius * 0.62:.2f}">'
                f"{digits}</tspan>"
            )
        out.append(
            f'<circle cx="{centre:.2f}" cy="{middle_y:.2f}" r="{radius:.2f}" '
            f'fill="#ffffff" stroke="#111111" stroke-width="2"/>'
            f'<text x="{centre:.2f}" y="{middle_y:.2f}" text-anchor="middle" '
            f'dominant-baseline="central" fill="#111111" '
            f'font-family="sans-serif" font-weight="bold" '
            f'font-size="{radius * 0.9:.2f}">{body}</text>'
        )
    return "".join(out)


def style_rules(
    plumbing: dict,
    state: dict,
    line_mode: str | None = None,
    widths: dict[str, float] | None = None,
    wide: bool = False,
    now=None,
) -> str:
    """The prediction as CSS, for the server-rendered ``/state.svg``.

    Every rule carries ``!important``: queezz authored each pipe with an inline
    ``style`` attribute, and an inline style beats a stylesheet, so the plain
    rules this used to write were overridden by the drawing's own black and the
    saved render came back uncoloured.

    ``widths`` are the authored stroke widths, and ``wide`` is the page's own
    reading aid: off by default since 0.15.0, because queezz's strokes are the
    width he wants. ``/state.svg?wide=1`` turns it on, so a render saved from a
    browser with the switch on can still match the screen it was saved from.

    Round caps and joins are written on every painted line and body. With the
    widening off and his 4 px lines, a butt end stops exactly at its own
    coordinate, and a stem that meets a pipe there leaves a notch; a round cap
    reaches half a stroke past it and closes the seam without touching the
    drawing (queezz, 2026-09-08: "I see small defect when line is enlarged").
    """
    prediction = predict(plumbing, state, line_mode, now=now)
    rules = []
    for element_id, item in sorted(prediction["elements"].items()):
        if not _safe_id(element_id):
            continue
        declarations = []
        # A sealed volume is painted with its hatch rather than with a flat
        # colour, on the body and on the line alike — the pattern is written
        # into the render's own defs by `sealed_pattern_markup`.
        sealed_paint = (
            f"url(#{item['sealed_paint']})"
            if item.get("sealed_paint") and _safe_id(item["sealed_paint"])
            else None
        )
        if sealed_paint:
            declarations.append(f"stroke:{sealed_paint} !important")
        elif _safe_color(item.get("stroke")):
            declarations.append(f"stroke:{item['stroke']} !important")
        authored = (widths or {}).get(element_id)
        if wide and item.get("band") and authored:
            declarations.append(
                f"stroke-width:{round(authored * item['band'], 3)} !important"
            )
        if sealed_paint and item.get("fill"):
            declarations.append(f"fill:{sealed_paint} !important")
        elif item.get("mix") and _safe_color(item.get("fill")) and _safe_color(item["mix"]):
            gradient = _mix_gradient_id(item["fill"], item["mix"])
            declarations.append(f"fill:url(#{gradient}) !important")
        elif _safe_color(item.get("fill")):
            declarations.append(f"fill:{item['fill']} !important")
        # The one element with a dashed outline is the Line-configuration valve
        # when nothing is mounted at its position; the saved render draws it the
        # same way the page does.
        if item.get("dash") and all(ch.isdigit() or ch in " ." for ch in str(item["dash"])):
            declarations.append(f"stroke-dasharray:{item['dash']} !important")
        elif item.get("dash") == "none":
            declarations.append("stroke-dasharray:none !important")
        if isinstance(item.get("opacity"), (int, float)):
            declarations.append(f"opacity:{item['opacity']} !important")
        if not (item.get("valve") or item.get("pump")):
            declarations.append("stroke-linecap:round")
            declarations.append("stroke-linejoin:round")
        if declarations:
            rules.append(f"#{element_id}{{{';'.join(declarations)}}}")
    return "".join(rules)
