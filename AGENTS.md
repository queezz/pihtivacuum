# PIHTI interactive diagram agent guide

## Purpose and boundary

This repository provides the local PIHTI vacuum-system state diagram, operator guidance, and control-unit plots. It replaces the earlier static diagram workflow. The diagram is an operator aid, not a pressure measurement, safety interlock, control panel, or source of hardware truth.

## Environment

- External venv name: `pihti-diagram`.
- Windows interpreter: `C:\Users\queez\.venvs\pihti-diagram\Scripts\python.exe`.
- macOS/Linux interpreter: `~/.venvs/pihti-diagram/bin/python`.
- Never create a venv, cache, test scratch, credential key, or decrypted user file inside this Dropbox repository.

## Entry points and gates

```powershell
& "$env:USERPROFILE\.venvs\pihti-diagram\Scripts\python.exe" -m pihti run
& "$env:USERPROFILE\.venvs\pihti-diagram\Scripts\python.exe" -m pytest
```

On macOS/Linux, use `~/.venvs/pihti-diagram/bin/python` for the same script and module arguments.

The server binds to `0.0.0.0:5000` by default: it answers on the LAN because it is served from one machine (the lab Raspberry Pi) and read on a laptop or a phone (owner decision 2026-09-04, "always LAN"). `PIHTI_HOST=127.0.0.1` or `--host 127.0.0.1` narrows a run to its own machine; debug mode remains loopback-only regardless. Long-running and scratch instances belong in `lab-cli/services.toml`; do not start a background shell process. Scratch runs must set `PIHTI_DATA_ROOT` and every other application write path outside Dropbox.

## Identity and security invariants

- Operator choice is attribution only, never authentication or access control. Read-only diagram, history, plot, and download routes remain public; diagram annotation writes require a selected operator.
- Operator selection expires after 12 hours without an attributable diagram change. Passive polling must not extend it.
- Operator names live in the gitignored roster `operators.json` in the data root (`PIHTI_OPERATORS_FILE`); manage it with `python -m pihti operators`. The encrypted legacy identity store may be tracked; its Fernet key may not, and it is read only as a fallback for account names. The default key lives at `%LOCALAPPDATA%\pihti-diagram\users.key` on Windows and exists only on machines where it was generated.
- Never print, paste, log, or commit keys, legacy password hashes, decrypted identities, session cookies, local data paths, or control-unit data.
- `PIHTI_DEBUG` is loopback-only. Network binding must never imply debug mode.
- Control-unit file selection stays within the configured directory.

## Diagram invariants

- **A pipe's name is what says which volume it belongs to.** queezz named every pipe, cross and T in `diagram.svg` by the volume it carries (`plasma-vacuum-*`, `qms-vacuum-*`, `bypass-manifold-*`, `gasline-*`, `*-vent-air-side`, and the rest), and `static/plumbing.json` is the map built from those names: which elements each volume owns, which two volumes each valve joins, which pump sits where. Connectivity is read from that file and never inferred from path geometry. This replaces the `zone-*` group plan of 0.5.0 — a name survives an edit that regroups the drawing (0.11.0). Ask the owner to name or split ambiguous pipework; never rename his ids without his say-so — the spelling and oddity corrections of 0.11.1 (owner decision 2026-09-08, letter 20260907-b9fddf7b-4768ce) are the one exception, and `src/pihti/server.py`'s `ID_ALIASES` keeps every old id from real history resolving to its current one on read.
- **The 18 `pipes-*` groups are the drawing's own filing, not a data structure.** They exist so a person can find a pipe by name in Inkscape's object list and so pipes paint below valves, gauges and labels. Group membership mirrors `plumbing.json` and nothing reads it at runtime. Regrouping must leave the render byte-identical: three opaque white junction shapes (`probe-pipe-cross`, the two `bypass-manifold-t-*`) sit on top of the lines they join, so alphabetical order inside a group is bent wherever a filled shape overlaps a line, and the two vessel bodies stay at their own depth. Prove it by exporting both SVGs to PNG and comparing the hash.
- Live component colors may be derived from the operator-entered diagram state (owner decision 2026-09-03), but must be labelled as a diagram connectivity prediction, not measured pressure or an interlock. Pipe colour (0.11.0) is that prediction: air beats gas beats high vacuum beats rough vacuum beats isolated, pumps are boundaries rather than connections, and the key sits under the drawing saying "predicted from the valve positions, not measured" — once per page, never twice.
- Pump and gauge fill colors remain operational state and must not be reused as
  pressure-domain colors. **Amended 2026-09-08 for valves alone** (owner review,
  letters `20260908-6819c50d-04e4ba` and `20260908-06105d79-6b7535`, applied in
  0.15.0). The rule existed to keep two vocabularies apart — bright pastel for
  what an operator entered, dark and saturated for what the prediction thinks —
  and it was right until it made a shut gate valve invisible. queezz, on the
  deployed drawing: *"GVU is closed, so TMP is not pumping plasma-vacuum. Yet at
  a glance it seems that it does."* And, on the small ones: they read *"too
  quietly... a green wedge against a grey wedge at that size."* So a valve now
  says its position with its own body — an open one wears the colour running
  through it, a closed one wears white — which makes a closed valve a visible
  break in the colour on both sides and an open GVBD readable from arm's length.
  Only valves moved. Pumps stay yellow when running, gauges keep their own
  colours, the gas bottles keep theirs, and `elementsConfig.json` keeps every
  valve's `colors` entry so nothing that has not moved is broken. A valve also
  keeps the black outline queezz drew, because it is still equipment.
- **A high-vacuum volume takes its colour from the vessel it is joined to
  (2026-09-08).** Upstream and downstream are two colours, not one — queezz: *"I
  think I'd rather have two high vacuum colors. Upstream and downstream. To see
  mixing clearly."* A volume a turbo reaches but no vessel does is neither: it is
  the seventh state, *pumped, sealed off*, which is what the pipe between a
  closed gate and its own turbo wears. Mixing — a rough pump reaching a
  turbo-pumped volume, or the two vessels joined — is shown on the drawn
  **shapes** alone, as a two-colour gradient from the dominant colour to the
  contributing one; a pipe wears one colour and only one, because an SVG
  gradient is painted across a bounding box rather than along a path and would
  streak the wrong way on a bend (queezz: *"we have shapes in all important
  places"*).
- Turbo-pump and gauge warnings derived from toggle state are advisory operator warnings, never proof of hardware state or safety (owner decision 2026-09-03). Actual pressure evidence must use Raspberry Pi fields with explicit instrument IDs, units, timestamps, and stale-data handling, and must fail to “unknown.”
- Operation guides only annotate the diagram and list operator steps. They never perform device mutations. The four sequences in `static/operationGuides.json` stopped being provisional on 2026-09-08, when queezz corrected them line by line (letter `20260908-7a3c9ac3-bbd7aa`); a route none of them names is a question for him, never a guess. A step may check the diagram (`targets`), ask the prediction whether two volumes are still joined (`separates`), place a beacon without judging it (`marks`), or apply only on a rig where something is plugged in (`onlyWhen`, answered by the machine-local settings file). Every id a step names, in `targets` or in `marks`, is read out loud in the rail, so it must carry a `label` in `elementsConfig.json`.
- **The beacon pulses under `prefers-reduced-motion: reduce` too.** Windows with its animation effects switched off makes Chromium — so queezz's Brave — answer *true* to that query, and a `@media` block that said `animation: none` left the beacons dead on his desk for two releases while the CSS read as correct. Under `reduce` the ring keeps a slow opacity pulse at one fixed radius: less motion, never less information. Proving a beacon means measuring it in a rendered browser — `element.getAnimations()` non-empty on the current step's ring, computed `animation-name` not `none`, and two frames a half period apart that differ — never reading the stylesheet.
- **A change costs one request and one redraw.** `/update` and the
  `/operation-context` write both answer with the new prediction, so the page
  repaints from the answer that made the change rather than asking
  `/predicted-vacuum` for it afterwards (0.15.0; queezz on 0.13.0: *"membrane
  installed to open pipe is VERY slow. And no reason for it to be slow."*).
  A route that changes the diagram carries its own consequence back; adding a
  second round trip to find out what just happened is the defect.
- **A volume's body is one colour; equipment keeps its outline.** The two vessels, the two bypass tees and the cross take the state colour as fill *and* stroke (owner decision 2026-09-08: "All one color... Color speaks vacuum. Black border speaks... shapes?"). Valves, pumps and gauges keep the black queezz drew. Both halves come from `predict()`, so `/state.svg` and the page cannot disagree.

## Web UI invariants

- Every page uses the one `.page` grid: left rail for controls, main column for content, right rail for context. Rail widths and the sticky offset (`--bar` + `--content-gap`) are shared, so rails stand at the same address on every tab and never move on scroll.
- The palette is Fleet's dark paperlib set; lecturedeck is never the model for this UI. The authored SVG keeps its own colours.
- Any UI change runs Fleet's Perimeter Walk on a scratch `lab` service before it ships.
- **No surface shows a person a component key.** A reader sees the equipment's name; `GVU`, `gaspanel-valve-n` and the rest stay in the files, the log and the SVG. The names are the `label` beside each `id` in `static/elementsConfig.json`, read through `window.pihtiElementName` (0.10.0), and History marks a component the current diagram no longer carries rather than passing its recorded key off as a name. Fleet `WEBUI.md`: what a viewer sees is for the viewer.
- **The top bar wraps; it never overflows.** Below about 470 px the five tabs and the operator selector cannot share one row, so the selector drops to a row of its own at the same right-hand corner and the tabs wrap before they can be pushed off screen (0.10.0, after the Mac audit found the selector clipped at 390 px). One DOM in a different placement — never a second phone-only control. The bar is taller when it wraps, which only rails below the 1199 px breakpoint would care about, and those are fixed drawers rather than sticky rails.
- **The key to the drawing lives under the drawing.** It is read, not pressed, so `WEBUI.md`'s rail law puts it in the main column; and measured at a 700px window the right rail is already full — the guide card alone wants its whole 604px with a summary, an alert and five steps. Two attempts at a third rail card were measured out again, one of them painting 113px of the guide's own words over the card below (0.11.0).
- **Change a static file and you must bump the version**, or a browser that saw the previous release keeps the old copy for a year. Static files are cached by release, everything else is `no-store` (0.9.0). A template writes a static URL with `asset('css/styles.css')`, never `url_for('static', ...)`, and JavaScript that fetches a static file stamps it with `document.body.dataset.assetVersion`. An unstamped or stale-stamped static URL is deliberately uncacheable, so a stale asset cannot outlive its release.
- The last control-unit plot is served as its own document (`/plot/last.html`) and framed, never injected into the page: Plotly's bundle is measured in megabytes and injecting it froze the tab. `X-Frame-Options` is `SAMEORIGIN` for that frame alone. The served document is prefixed with the frame's own reset, so a plot saved by an older release still fills the frame without white margins.
- The recording archive travels one month at a time (`/plot/recordings?month=`), never as one payload in the page. A month that has passed does not change, so the answer carries an ETag and is revalidated rather than re-sent.

## Deployment

The lab Raspberry Pi (`pihti:5000`) serves this diagram from an editable install of `/home/pi/pihtivacuum` on Python 3.9, run by `deploy/pihti.service`; laptops and phones read it. It deploys by pulling `master` from GitHub, so a shipping session pushes after committing (owner decision 2026-09-04, see `.agents/README.md`) and then pulls and restarts on the Pi. Keep the package importable on Python 3.9.

Read `.agents/README.md` for workflow, `.agents/directions.md` for open owner decisions, and `.agents/log/` for session evidence. Fleet-wide policy remains in Fleet's `RULES-BRIEF.md` and routed references.
