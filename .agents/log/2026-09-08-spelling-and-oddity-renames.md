# Spelling and oddity id renames (0.11.1)

Commander-dispatched follow-up ship in the coordinated PIHTI trio run, on the
work Windows PC, overnight 2026-09-08. This session did the id cleanup that
`directions.md` had left as the owner's call after the pipes-by-vacuum ship
(0.11.0), following an explicit owner decision relayed while queezz was
asleep.

## The owner's decision

Letter `20260907-b9fddf7b-4768ce`, code/fleet -> code/2024-interactive-diagram,
owner decision 2026-09-08 00:40 JST, relayed by the Commander answering the
id-anomaly question the pipes dispatch had handed back. queezz: "Right, you
may and should correct spelling. And oddities. QMS is the QMS itself, an
image. qms-vacuum is its pipe to the L valve." Collected with `fleet letters
--collected 20260907-b9fddf7b-4768ce`.

## The rename table

Applied in `diagram.svg`, `elementsConfig.json`, `plumbing.json`, and
`tests/test_server.py`. `operationGuides.json`, `diagram.js` and `history.js`
named none of these ids, so none of the three needed a change.

| old | new |
| --- | --- |
| `bypas-manifold-downstream-line` | `bypass-manifold-downstream-line` |
| `bypas-manifold-main` | `bypass-manifold-main` |
| `bypas-manifold-t-downstream-t` | `bypass-manifold-t-downstream-t` |
| `bypas-manifold-t-upsteram` | `bypass-manifold-t-upstream` |
| `bypas-manifold-upstream-gv` | `bypass-manifold-upstream-gv` |
| `bypas-manifold-upstream-t-to-pipe` | `bypass-manifold-upstream-t-to-pipe` |
| `bypas-pumpline` | `bypass-pumpline` |
| `bypas-pumpline-vent` | `bypass-pumpline-vent` |
| `bypas-pumpline-vent-air-side` | `bypass-pumpline-vent-air-side` |
| `plasma-vacuum-pump-portt` | `plasma-vacuum-pump-port` |
| `gasapanel-manifold-argon` | `gaspanel-manifold-argon` |
| `GVU-6` | `upstream-pumpline-vent-valve` |
| `GVU-6-9` | `downstream-pumpline-vent-valve` |
| `Rough-bypass-vent` | `bypass-pumpline-vent-valve` |
| `nitrogen-line` | `nitrogen-bottle` |
| `path1464-3-2-6` | `gasline-argon-1` (also moved into the `pipes-gasline-argon` group) |

Nine spellings, one mechanical typo each in a pump port id and a gas-panel
manifold id, three oddity renames for the vent valves (read off `plumbing.json`'s
own adjacency, not the name: `GVU-6` joins `plasma-foreline` and atmosphere,
`GVU-6-9` joins `qms-foreline` and atmosphere, `Rough-bypass-vent` joins
`bypass-pumpline` and atmosphere — matching the `upstream-`/`downstream-`
convention the plasma and QMS backing lines already use), a bottle drawn as a
line, and one unnamed argon pipe. `Rough-Bypass` (the pump) kept its id, as
asked. `QMS` and `qms-vacuum` were left exactly as they were — the letter's own
words say what they are, and say not to merge or rename either.

**One thing in the letter did not apply.** It asked to rename or drop an
element whose id was reportedly `false`. No such id exists in `diagram.svg`;
`grep -c 'id="false"'` and a full parse of every `id="..."` attribute both come
back empty. The one `false` in the file is `showgrid="false"` in the Inkscape
`namedview` — a session's earlier substring search evidently matched `id=` at
the tail of `showgrid` (`...gr-id=`) rather than an actual `id` attribute.
Recorded here rather than silently ignored; nothing was renamed or dropped.

## Render proof

Same method as the 0.11.0 ship: Inkscape exported both the pre-rename and
post-rename `diagram.svg` to PNG at 1683px and 3366px wide. SHA-256 matched
at both sizes, and matched the 0.11.0 ship's own hashes exactly —
`224d40b8…` at 1683px, `b78f7692…` at 3366px. Nothing moved, painted over
anything else, or changed colour, including `gasline-argon-1`'s move into its
pipes group (it is a plain grey stroke with no overlap at that coordinate, so
lifting it out of the ungrouped tail and into `pipes-gasline-argon` cost
nothing visually).

## History and the state file: an alias, applied on read

`elements_state.json` and `logs.csv` can carry a real id from a real day
before this rename — in practice only the three vent valves, since a pipe id
was never clickable and so never reached `/update`. `src/pihti/server.py` now
carries `ID_ALIASES` (old -> new, the same table above) and two small
functions, `apply_id_alias` and `apply_id_aliases_to_state`. They run once,
where the state file and the CSV are read into memory
(`create_app`'s `elements_state` and `load_history_events`); every downstream
consumer — `/elements-state`, `/state`, `/update`'s unchanged-check,
`/history/events`, `state_at_index`, `/predicted-vacuum?at=`, `/state.svg?at=`
— sees only the current id. Nothing on disk is rewritten to prove it.
`tests/test_server.py::test_an_old_permalink_still_selects_the_renamed_element`
seeds a scratch `elements_state.json` and `logs.csv` with `GVU-6`, confirms
`/elements-state`, `/history/events`, and a `/predicted-vacuum?at=<old
timestamp>` permalink all resolve to `upstream-pumpline-vent-valve`, then
reads both files back unchanged from disk.

## Directions

Closed the two open items this letter answered — the ten misspelled/oddity
ids, and the unnamed argon pipe — with `(owner decision 2026-09-08)` and this
table, in `.agents/directions.md`. The remaining open items (label wording,
the three plumbing guesses, the vent-guide route confirmation, the PIHTI Log
width match, the NAS folder address) are untouched.

## Verify: scratch Perimeter Walk

`lab start pihti-diagram --port 48943 --host 127.0.0.1` under scratch
`LAB_CONFIG`/`LAB_RUNTIME_ROOT`/`LAB_LOG_ROOT` with every `PIHTI_*` write path
(`PIHTI_DATA_ROOT`, `PIHTI_SESSION_KEY_FILE`, `PIHTI_USERS_KEY_FILE`) inside a
marked `fleet-scratch-2024-interactive-diagram-verify` TEMP root, a fresh
`elements_state.json`/`logs.csv` and a one-name `operators.json`; nothing
written inside Dropbox. The owner's Pi (5000) and local (4186) instances were
never addressed.

- **The three renamed vent valves, live in the browser DOM.** This
  environment's browser pane suppresses native `confirm()` dialogs outright
  (console: "native JavaScript dialogs are disabled in this browser; confirm()
  returned false to the page"), which would silently cancel every
  `confirmToggle` element including all three vent valves — so the page's own
  `window.confirm` was stubbed to auto-accept for this session only (never
  shipped code) and each valve was driven by dispatching a real `click` event
  at its element, the same event `diagram.js`'s own delegated listener reads.
  Opening `upstream-pumpline-vent-valve` turned `plasma-foreline` (and the
  live DOM stroke of `upstream-tmp-to-rotary-pipe`) to air-red
  `rgb(140, 11, 18)`; closing it returned both to isolated-black
  `rgb(0, 0, 0)`. Same pair for `downstream-pumpline-vent-valve` on
  `qms-foreline` / `downstream-tmp-to-scroll-pipe`, and for
  `bypass-pumpline-vent-valve` on `bypass-pumpline` / `bypass-pumpline`
  itself. Opening `argon-bottle` turned all three argon pipes —
  `gasline-argon`, the newly-grouped `gasline-argon-1`, and
  `gasline-argon-to-downstream` — the same gas-violet `rgb(122, 79, 208)`
  together, closing the directions item on the unnamed argon pipe.
- **Guide steps.** `Vent Plasma` still renders its five steps with readable
  names for `GVU`, `TMPU`, `valve_qms`, `GVBU`, `GVBD`, `Rough-Bypass`,
  `gaspanel-valve-n`, `gasline-main`, `bypass-ionization-gauge`,
  `upstream-baratron` — none of them touched by this rename, and none of them
  broken by it.
- **History.** The three renamed valves each show two rows with their current
  readable label (`Plasma backing line vent valve`, `QMS backing line vent
  valve`, `Bypass pumping line vent valve`) — no raw id, no retired marker,
  since these are the current ids. Selecting a row set `?at=` in the address
  bar; reloading that exact URL cold (a fresh navigation, not a client-side
  route) reproduced the same moment, element name, state, and live pipe
  stroke colour.
- **Console clean** of every application-originated message on both pages;
  the only console line at all was the harness's own dialog-suppression
  notice above.
- **Rails at 76px** (`getBoundingClientRect().top` on `.rail-left` and
  `.rail-right`) on History.
- `lab stop pihti-diagram` stopped the tracked process tree; `Test-NetConnection
  127.0.0.1 48943` came back `False` afterward.

## Gates

`pytest` 35 passed (34 plus the new alias test), `node --check` on
`diagram.js` and `history.js`, `git diff --check` clean. No ruff
configuration in this repository.

## Version

0.11.1 in `pyproject.toml`, `src/pihti/__init__.py`, `README.md`, and the
three assertions in `tests/test_server.py`.

## Not pushed, not deployed

Told not to push and not to touch the Pi. Commits sit on local `master`.

## Usage receipt

Provider Anthropic, model Claude Sonnet 5. Task: commander run follow-up:
Diagram id renames. Child agents: 0. Provider usage: unavailable — no meter
was shown to this session.
