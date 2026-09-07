# Boron deposition is a dead end, and the membrane has no press of its own (0.12.1)

Commander-dispatched follow-up ship in the coordinated PIHTI trio run, on the
work Windows PC, 2026-09-08 midday JST — queezz awake. It closes the last two
questions 0.11.2 and 0.12.0 left open in `directions.md`.

## The letter

`20260907-dc825e44-e6d89e`, code/fleet -> code/2024-interactive-diagram: his
answer to the Boron deposition question, in his own words:

> "pipe open or membrane mode without a membrane are the same. Boron uses same
> pipe. But other end not connected to downstream. Could be pumped from plasma
> side via bypass. Membrane installed and the membrane 'valve' should be
> linked."

Collected with `fleet letters --collected 20260907-dc825e44-e6d89e` after the
work.

## Boron deposition: a dead end, not a second membrane

0.11.2 had read Boron the same way as a membrane — both left `connects: false`
in `line_configuration.modes`, so both divided the narrow pipe into two
private sides that could happen to agree. queezz's answer says Boron is
different: the far (downstream) end simply is not joined, whatever the
downstream valve (`bypass-vcr-d`) is doing, and the pipe just extends the
plasma side.

`line_configuration.modes.boron` in `plumbing.json` now names
`dead_end_valve: "bypass-vcr-d"`. In `plumbing.predict()`, a valve named there
is skipped outright when it touches the divided volume — no stub, no edge, not
even the private-side-of-the-barrier treatment membrane gets — so it can never
join the pipe to the QMS vessel, in any position. The near valve
(`bypass-vcr-u`) keeps the ordinary treatment, so the pipe's colour is simply
whatever component that one stub lands in: the plasma vessel's own state when
the near valve is open, or isolated when even that is shut. Watched live: with
the plasma side pumped to high vacuum and *both* crossover valves open, a
membrane divides the pipe to isolated (the two sides disagree — one pumped,
one not), while Boron deposition colours the same pipe the plasma vessel's own
blue, and the QMS vessel never joins it either way.

## The `Membrane` element: linked, not pressed

Separately, the drawn ellipse `Membrane` on the probe line (joining
`bypass-manifold` and `probe-line` — a different physical spot from the
vessel-crossover pipe, per `directions.md`'s open question about what it
actually is) had its own independent press, toggled through `/update` like
any other valve. queezz's answer settles that too: it is linked to the Line
configuration rather than pressed on its own.

`line_configuration.linked_valve` names it (`{"id": "Membrane", "closed_mode":
"membrane"}`). `plumbing.apply_line_mode_to_state()` overrides that one key in
the state dict on every read — closed only under *Membrane installed*, open
under *Pipe open*, *Boron deposition*, and *unknown* alike — and
`plumbing.predict()` calls it before anything else, so the element's own
connectivity (whether `probe-line` and `bypass-manifold` join) and its drawn
colour can never disagree with each other or with a stale
`elements_state.json`/history value. `predict()` now also returns
`linked_valve: {"id", "status"}` and `line_mode`, so a client (or a saved
`/state.svg`) can read the derived colour without re-deriving the rule.

Three places close the loop so it truly has no press of its own:

- `elementsConfig.json` marks it `"followsLineMode": true`.
- `diagram.js` skips the click handler and the raw press-state fill for a
  `followsLineMode` element (`applyState`), and instead paints it from
  `prediction.linked_valve` in `paintPrediction` — the same function that
  already colours the vessels and the pipes, so it repaints correctly on
  every live poll and every History replay without History's own code
  needing to know about it.
- `server.py`'s `/update` refuses a direct write to it (`400`, "follows the
  Line configuration and cannot be set directly"), and `render_state_svg`
  applies the same override before writing a saved render's fills, so
  `/state.svg` cannot disagree with the live page either.

A pre-existing test (`test_every_body_on_the_drawing_is_filled_with_its_full_state_colour`)
exercised `Membrane` implicitly by never setting it and expecting it closed;
it now says `"membrane"` explicitly, since *open*/*boron*/*unknown* all force
it open under the new link.

## Tests

Four new, one rewritten, in `tests/test_server.py`:

- `test_boron_deposition_leaves_the_pipe_a_dead_end_on_the_plasma_side` — the
  pipe mirrors the plasma vessel under Boron even with the downstream valve
  open and pumped differently on the QMS side, isolated only when the plasma
  side itself is shut, and never the "isolated-by-disagreement" a membrane
  would show.
- `test_the_readout_never_claims_the_qms_vessel_during_boron_deposition` — the
  plasma vessel's own `joined` list stays empty under Boron even with both
  crossover valves open and both sides pumped, where the same valve positions
  under *Pipe open* correctly do join them.
- `test_the_membrane_element_follows_the_line_configuration_not_a_press` — a
  stale `"active"` or `"inactive"` recorded for `Membrane` is overridden on
  every one of the five configurations pytest can name, both in
  `predict()["linked_valve"]` and in what it does to `probe-line`'s
  connectivity.
- `test_membrane_cannot_be_set_directly` — `/update` refuses it with a clear
  error.
- `test_the_line_between_the_vessels_follows_the_line_configuration` no
  longer folds Boron into the same "both sides isolated" loop as membrane and
  unknown, since Boron no longer behaves that way.

`directions.md`'s Boron/Membrane item is closed with the owner decision and
his words; the plumbing note documents both rules where an editor reading
`plumbing.json` finds them.

## Verify: scratch Perimeter Walk

`lab start pihti-diagram --port 48962 --host 127.0.0.1` under scratch
`LAB_CONFIG`/`LAB_RUNTIME_ROOT`/`LAB_LOG_ROOT`, every `PIHTI_*` write path
(`PIHTI_DATA_ROOT`, `PIHTI_SESSION_KEY_FILE`, `PIHTI_USERS_KEY_FILE`) inside a
marked `fleet-scratch-2024-interactive-diagram-boron` root in this session's
own scratchpad (outside Dropbox, outside `%LOCALAPPDATA%`), with a copied
`elements_state.json` (plasma side pumped to high vacuum, both crossover
valves open, QMS side untouched) and an `operation_context.json` starting at
*Pipe open*.

- **All three configurations, pressed on the real card**, read live off the
  DOM: *Pipe open* — both vessels `rgb(17,80,204)` (high vacuum), pipe the
  same blue at 6.05 px, `Membrane` green, readout says each vessel is "Open to"
  the other. *Membrane installed* — plasma vessel stays blue, QMS vessel and
  the pipe both drop to isolated grey `rgb(127,123,117)` at the unwidened
  3.78 px, `Membrane` turns grey (closed), the "Open to" clause disappears
  from both readout lines. *Boron deposition* — plasma vessel still blue, the
  pipe returns to blue at 6.05 px (mirroring the plasma side, not neutral),
  QMS vessel stays isolated and un-joined, `Membrane` is green again (open).
- **`/update` refuses `Membrane`** live (`{"error": "Membrane follows the
  Line configuration and cannot be set directly."}`), and a real press on
  `GVBD` succeeds and appears in History.
- **History**, opened cold and clicked to the `GVBD` moment: the pipe,
  vessels and `Membrane` all read the *Pipe open* configuration that was
  active at that real timestamp — the same mechanism History already used for
  the vessel colours, unmodified.
- **`/state.svg`** carries `#Membrane{fill:#9bf08d !important}` matching the
  live page's current configuration.
- **Rails at 76 px** across the full scroll range at 1280×720, both rails
  identical; document width 1265, no overflow. At **390×844** the document is
  exactly 390 px wide, no horizontal scroll.
- **Console clean** on every page and every configuration switch.
- `lab stop` killed the tree; `Get-NetTCPConnection -LocalPort 48962 -State
  Listen` returns nothing afterward (only a closing `TimeWait` socket from the
  test's own curl calls). The owner's `4186` was listening under its own PID
  before, during and after, and was never addressed; the Pi's `5000` was never
  touched. Scratch root marked `superseded`.

## The drawing on disk is untouched

`diagram.svg` does not appear in `git diff` — nothing here touches the SVG,
so 0.12.0's byte-identical Inkscape hashes still hold without re-exporting.

## Gates

`pytest` 48 passed (45 plus 3 net new), exit 0. `node --check` clean on
`diagram.js` and `history.js`. `git diff --check` clean. There is no ruff
configuration in this repository.

## Version

0.12.1 — a patch, since this closes two open questions and fixes the
membrane's connectivity rather than adding a page feature — in
`pyproject.toml`, `src/pihti/__init__.py`, `README.md`, and the three
assertions in `tests/test_server.py`. Static files changed
(`elementsConfig.json`, `plumbing.json`, `diagram.js`), so the bump keeps a
browser that already saw 0.12.0 from serving stale copies against this
release's server responses.

## Not pushed, not deployed

Told not to push and not to touch the Pi for this run. The commit sits on
local `master`. To get it live, in an ordinary terminal:

```powershell
git -C "$env:USERPROFILE\Dropbox\20-Code\2024-interactive-diagram" push
```

then on the Pi: `git pull --ff-only` in `/home/pi/pihtivacuum`, `sudo
systemctl restart pihti`, and confirm `/version` says 0.12.1.

## Mail

`20260907-dc825e44-e6d89e` collected. Nothing else owed.

## Usage receipt

Provider Anthropic, model Claude Sonnet 5. Task: commander run follow-up:
Diagram line configurations and membrane link. Child agents: 0. Provider
usage: unavailable — no meter was shown to this session.
