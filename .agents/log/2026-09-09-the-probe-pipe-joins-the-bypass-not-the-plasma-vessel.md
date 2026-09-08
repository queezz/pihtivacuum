# The probe pipe joins the bypass, not the plasma vessel (0.19.2)

Short closing ship in the coordinated PIHTI trio run, dispatched by Fleet
Commander to fix one recorded defect before the run closed: the standing
directions.md item on the Boron probe pipe (owner correction 2026-09-09,
letter `20260908-5d638879-1b617e`), collected but never built.

## The defect

queezz, on Boron deposition with both vessels drawn joined and pumped by both
turbos: *"Boron deposition, the pipe to the bypass cross (probe cross) is not
connected then."* The sample holder sits at the membrane position; the
crossover from the plasma vessel reaches the holder and ends there, a
plasma-side dead end (`vessel-crossover`, unchanged, still dead-ended at
`bypass-vcr-d`). The probe pipe (`probe-line` — `probe-pipe`, its cross, and
`probe-pipe-cross-to-GVBD`) is not connected at the holder end, so it belongs
to the bypass side and never to the plasma vessel except through the real
bypass gate valves.

Reading `plumbing.py`, the leak was `linked_valve.closed_modes`: it shut the
drawn `Membrane` element under *Membrane installed* and *Blank* but left it
forced **open** under *Boron*, exactly as under *Pipe open* — so `Membrane`
alone (not any real valve) bridged `bypass-manifold` to `probe-line` the
moment `GVBU` and `GVBD` were open, whatever `bypass-l1` was doing.

## The fix

One line in `plumbing.json`:

```json
"linked_valve": {"id": "Membrane", "closed_modes": ["membrane", "blank", "boron"], "plug_mode": "membrane"}
```

The sample holder occupies the same spot a membrane, a blank flange or a probe
would, so it blocks `Membrane` exactly as they do. No code changed in
`plumbing.py` — `closed_modes` is already the configuration's own edge set, a
list a valve reads generically for every mode, so this is one more mode
joining that list rather than a second special case bolted on beside
`dead_end_valve`. `probe-line` now reaches `bypass-manifold` only through the
real `bypass-l1` valve; the two vessels join only through the real bypass gate
valves (`GVBU`, `bypass-l1`, `GVBD`) when an operator opens them, never through
the crossover.

`tests/test_server.py::test_the_probe_pipe_belongs_to_the_bypass_side_under_boron_deposition`
pins three cases: every bypass valve shut (vessels separate, crossover mirrors
the plasma vessel, both probe segments read isolated); `GVBU` + `GVBD` alone,
with `bypass-l1` still shut (still separate — the regression test for the old
forced-open `Membrane`); and `GVBU` + `bypass-l1` + `GVBD` together (vessels
joined through the bypass, crossover isolated throughout). Two existing tests
needed updating to the corrected behaviour: the `linked_valve` shape assertion
and the `(mode, expect_open)` table in
`test_the_membrane_element_follows_the_line_configuration_not_a_press`, where
`boron` moves from `True` to `False`. `test_the_four_line_configurations_each_paint_the_line_their_own_way`
needed no change — its own fixture reaches the QMS side through `GVBD`
directly, never through `Membrane`.

## Verified on a scratch service

`lab start pihti-diagram --port 4287 --host 127.0.0.1` with `LAB_RUNTIME_ROOT`,
`LAB_LOG_ROOT`, and `PIHTI_DATA_ROOT` all under the scratchpad, an `operators.json`
seeded with one name. Selected Boron, pressed `TMPU`/`GVU`/`RoughU` and both
crossover valves: the plasma vessel read high vacuum, the QMS vessel read
isolated ("Nothing open to it"), the crossover read high vacuum in the plasma
vessel's own colour, and the probe pipe at the top of the drawing stayed grey.
Closed the crossover valves and opened `GVBU`, `bypass-l1`, and `GVBD` with
both turbos running: both vessels turned the same blue, each one's card read
"Open to: [the other vessel]," and the crossover's own valves stayed grey and
isolated the whole time — the join ran visibly through the top of the drawing
(bypass manifold, the cross, `GVBD`), never through the crossover. Console and
network tabs stayed clean (the one 404 logged was this session's own stray
debug fetch to a nonexistent path, not the app). Stopped the service afterward
and confirmed port 4287 was free again. Never touched the Pi (port 5000) or
queezz's own local instance (port 4186, confirmed still owned by its original
process throughout).

## Gates

`pytest -q`: 88 passed (87 before this ship, plus the one new test). This
repository's `AGENTS.md` names no ruff gate.

## Directions

Closed the standing item in `.agents/directions.md` with this release's detail
(owner decision 2026-09-09).

## Usage receipt

Provider Anthropic, model Claude Sonnet 5. Task: commander run closing:
Diagram Boron probe pipe. Child agents: 0. Provider usage: unavailable — no
meter was shown to this session.
